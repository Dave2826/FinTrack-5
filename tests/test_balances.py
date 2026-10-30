"""Pruebas de balances por cuenta y balance general (Actividad 7).

Se ejecutan EXCLUSIVAMENTE contra la base fintrack5_test y la API de
pruebas: las guardas abortan si DB_NAME, DB_HOST, current_database(),
la revision de Alembic o la disponibilidad del endpoint no coinciden con
el entorno de pruebas. La base de desarrollo actividad5 nunca se usa.

Los datos de referencia se crean en empresas propias de la suite y se
eliminan al finalizar. Los valores esperados se declaran de forma
independiente al servicio de balances (constantes Decimal y cadenas).
"""

import json
import os
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
from sqlalchemy import text

from database.connection import SessionLocal
from models.account import AccountType
from models.company import Company
from models.concept import ConceptType
from models.transaction import TransactionType
from models.user import User
from repositories.company_repository import create_company
from repositories.permission_repository import get_permission_by_code
from repositories.role_repository import get_role_by_code
from repositories.user_repository import create_user
from scripts.setup_pruebas import CONTRASENA_PRUEBAS
from security.password import hash_password
from services.account_concept_service import assign_concept_to_account
from services.account_service import create_account_service
from services.company_user_service import (
    assign_role_service,
    create_company_admin_service,
    create_company_user_service,
)
from services.concept_service import create_concept_service
from services.role_permission_service import (
    assign_permission_to_role_service,
    remove_permission_from_role_service,
)
from services.transaction_service import create_transaction_service


DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"
URL = "http://127.0.0.1:8000/graphql"

CONSULTA_CUENTA = """
query SaldoCuenta($accountId: ID!, $fromDate: Date!, $toDate: Date!) {
  accountBalance(accountId: $accountId, fromDate: $fromDate, toDate: $toDate) {
    accountId
    accountName
    isActive
    openingBalance
    totalIncome
    totalExpense
    profit
    closingBalance
    isInRed
    currency
  }
}
"""

CONSULTA_GENERAL = """
query BalanceGeneral($fromDate: Date!, $toDate: Date!) {
  generalBalance(fromDate: $fromDate, toDate: $toDate) {
    companyId
    fromDate
    toDate
    openingBalance
    totalIncome
    totalExpense
    profit
    closingBalance
    accountsInRed
    isInRed
    currency
    accounts {
      accountId
      accountName
      isActive
      openingBalance
      totalIncome
      totalExpense
      profit
      closingBalance
      isInRed
      currency
    }
  }
}
"""

CREAR_MOVIMIENTO = """
mutation CrearMovimiento($input: CreateTransactionInput!) {
  createTransaction(input: $input) {
    id
    transactionDate
    capturedAt
    amount
  }
}
"""

ELIMINAR_MOVIMIENTO = """
mutation EliminarMovimiento($transactionId: Int!) {
  deleteTransaction(transactionId: $transactionId) {
    id
    isActive
  }
}
"""


def _verificar_guardas() -> None:
    if os.getenv("DB_NAME") != DB_ESPERADA:
        raise SystemExit(
            f"DB_NAME no es {DB_ESPERADA}; prueba abortada"
        )
    if os.getenv("DB_HOST") != HOST_ESPERADO:
        raise SystemExit(
            f"DB_HOST no es {HOST_ESPERADO}; prueba abortada"
        )

    db = SessionLocal()
    try:
        actual = db.execute(
            text("SELECT current_database()")
        ).scalar()
        if actual != DB_ESPERADA:
            raise SystemExit(
                f"current_database() no es {DB_ESPERADA}; prueba abortada"
            )
        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        if revision != ALEMBIC_ESPERADO:
            raise SystemExit(
                f"alembic_version no es {ALEMBIC_ESPERADO}; "
                "prueba abortada"
            )
    finally:
        db.close()

    try:
        _gql("{__typename}")
    except Exception as exc:
        raise SystemExit(
            f"la API de pruebas no responde en {URL}: {exc}"
        )


def _gql(consulta: str, variables: dict | None = None,
         token: str | None = None) -> dict:
    payload: dict = {"query": consulta}
    if variables is not None:
        payload["variables"] = variables

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token

    requerimiento = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(requerimiento, timeout=30) as respuesta:
            return json.loads(respuesta.read().decode())
    except urllib.error.HTTPError as error:
        return {
            "http_error": error.code,
            "body": error.read().decode(errors="replace"),
        }


def _error(datos: dict) -> str:
    errores = datos.get("errors") or []
    if errores:
        return errores[0].get("message", "")
    return ""


def _login(email: str) -> str:
    consulta = (
        'mutation{login(input:{email:"%s",password:"%s"})'
        "{token tokenType}}" % (email, CONTRASENA_PRUEBAS)
    )
    datos = _gql(consulta)
    token = ((datos.get("data") or {}).get("login") or {}).get("token")
    if not token:
        raise AssertionError(f"login fallido para {email}: {datos}")
    return token


def _firmar(claims: dict) -> str:
    return jwt.encode(
        claims,
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


def _crear_usuario(db, nombre: str, email: str) -> User:
    return create_user(
        db,
        User(
            name=nombre,
            email=email,
            password_hash=hash_password(CONTRASENA_PRUEBAS),
            email_verified=True,
            is_active=True,
        ),
    )


def _crear_empresa(db, marca: str, slug: str):
    company = create_company(
        db,
        Company(
            name=f"Pruebas Balance A7 {slug} {marca}",
            legal_name=f"Pruebas Balance A7 {slug} ficticia",
            tax_id=f"TEST-A7-{marca}-{slug}"[:50],
            email=f"a7_{slug}_{marca}@test.local"[:255],
            is_active=True,
        ),
    )
    usuario = _crear_usuario(
        db,
        f"Admin Balance A7 {slug}",
        f"a7_admin_{slug}_{marca}@test.local"[:255],
    )
    membresia = create_company_admin_service(
        db,
        0,
        company.id,
        usuario.id,
    )
    return company, membresia, usuario


def _borrar_empresa(db, company_id: int) -> None:
    usuarios = [
        fila[0]
        for fila in db.execute(
            text(
                "SELECT user_id FROM company_users WHERE company_id = :c"
            ),
            {"c": company_id},
        ).fetchall()
    ]

    db.execute(
        text(
            "DELETE FROM transactions WHERE account_id IN "
            "(SELECT id FROM accounts WHERE company_id = :c)"
        ),
        {"c": company_id},
    )
    db.execute(
        text(
            "DELETE FROM account_concepts WHERE account_id IN "
            "(SELECT id FROM accounts WHERE company_id = :c)"
        ),
        {"c": company_id},
    )
    db.execute(
        text("DELETE FROM accounts WHERE company_id = :c"),
        {"c": company_id},
    )
    db.execute(
        text("DELETE FROM concepts WHERE company_id = :c"),
        {"c": company_id},
    )
    db.execute(
        text(
            "DELETE FROM company_user_roles WHERE company_user_id IN "
            "(SELECT id FROM company_users WHERE company_id = :c)"
        ),
        {"c": company_id},
    )
    db.execute(
        text("DELETE FROM company_users WHERE company_id = :c"),
        {"c": company_id},
    )
    db.execute(
        text("DELETE FROM companies WHERE id = :c"),
        {"c": company_id},
    )

    for usuario_id in usuarios:
        db.execute(
            text("DELETE FROM users WHERE id = :i"),
            {"i": usuario_id},
        )

    db.commit()


def _crear_cuenta(db, admin_id: int, company_id: int, nombre: str,
                  tipo: AccountType):
    return create_account_service(
        db,
        admin_id,
        company_id,
        tipo,
        nombre,
    )


def _crear_concepto(db, admin_id: int, company_id: int, nombre: str,
                    tipo: ConceptType):
    return create_concept_service(
        db,
        admin_id,
        company_id,
        tipo,
        nombre,
    )


def _asignar(db, admin_id: int, cuenta_id: int, concepto_id: int) -> None:
    assign_concept_to_account(
        db,
        admin_id,
        cuenta_id,
        concepto_id,
    )


def _movimiento(
    db,
    admin_id: int,
    cuenta_id: int,
    concepto_id: int,
    tipo: TransactionType,
    monto: str,
    fecha: datetime,
    capturado_por: int,
    descripcion: str,
):
    return create_transaction_service(
        db,
        admin_id,
        cuenta_id,
        concepto_id,
        tipo,
        Decimal(monto),
        captured_by=capturado_por,
        transaction_date=fecha,
        short_description=descripcion,
    )


def _snapshot(db, company_id: int):
    cuentas = db.execute(
        text(
            "SELECT id, name, is_active, updated_at FROM accounts "
            "WHERE company_id = :c ORDER BY id"
        ),
        {"c": company_id},
    ).fetchall()
    movimientos = db.execute(
        text(
            "SELECT t.id, t.account_id, t.concept_id, t.transaction_type, "
            "t.amount, t.transaction_date, t.captured_at, t.is_active, "
            "t.updated_at FROM transactions t "
            "JOIN accounts a ON a.id = t.account_id "
            "WHERE a.company_id = :c ORDER BY t.id"
        ),
        {"c": company_id},
    ).fetchall()
    return (
        [tuple(fila) for fila in cuentas],
        [tuple(fila) for fila in movimientos],
    )


class BalancesTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _verificar_guardas()

        cls.db = SessionLocal()
        cls.marca = datetime.now().strftime("%Y%m%d%H%M%S%f")
        cls.empresas_creadas: list[int] = []

        try:
            if get_role_by_code(cls.db, "ADMINISTRADOR") is None:
                raise SystemExit(
                    "falta el rol ADMINISTRADOR; ejecute setup_pruebas.py"
                )
            rol_consulta = get_role_by_code(cls.db, "CONSULTA")
            if rol_consulta is None:
                raise SystemExit(
                    "falta el rol CONSULTA; ejecute setup_pruebas.py"
                )

            # ------------------------------------------------ empresa A
            (
                cls.empresa_a,
                cls.admin_a,
                cls.usuario_admin_a,
            ) = _crear_empresa(cls.db, cls.marca, "ref")
            cls.empresas_creadas.append(cls.empresa_a.id)

            usuario_consulta = _crear_usuario(
                cls.db,
                "Consulta Balance A7",
                f"a7_consulta_{cls.marca}@test.local"[:255],
            )
            membresia_consulta = create_company_user_service(
                cls.db,
                cls.admin_a.id,
                cls.empresa_a.id,
                usuario_consulta.id,
            )
            assign_role_service(
                cls.db,
                cls.admin_a.id,
                membresia_consulta.id,
                rol_consulta.id,
            )
            cls.membresia_consulta = membresia_consulta.id
            cls.email_consulta = usuario_consulta.email

            cls.banco = _crear_cuenta(
                cls.db,
                cls.admin_a.id,
                cls.empresa_a.id,
                "Banco A7",
                AccountType.DEBIT,
            )
            cls.caja = _crear_cuenta(
                cls.db,
                cls.admin_a.id,
                cls.empresa_a.id,
                "Caja A7",
                AccountType.CASH,
            )
            cls.ahorro = _crear_cuenta(
                cls.db,
                cls.admin_a.id,
                cls.empresa_a.id,
                "Ahorro A7",
                AccountType.SAVINGS,
            )

            cls.ingreso_a = _crear_concepto(
                cls.db,
                cls.admin_a.id,
                cls.empresa_a.id,
                "Ingreso A7",
                ConceptType.INCOME,
            )
            cls.egreso_a = _crear_concepto(
                cls.db,
                cls.admin_a.id,
                cls.empresa_a.id,
                "Egreso A7",
                ConceptType.EXPENSE,
            )

            for cuenta in (cls.banco, cls.caja, cls.ahorro):
                _asignar(
                    cls.db,
                    cls.admin_a.id,
                    cuenta.id,
                    cls.ingreso_a.id,
                )
                _asignar(
                    cls.db,
                    cls.admin_a.id,
                    cuenta.id,
                    cls.egreso_a.id,
                )

            _movimiento(
                cls.db, cls.admin_a.id, cls.banco.id, cls.ingreso_a.id,
                TransactionType.INCOME, "1000.00",
                datetime(2026, 10, 25, 12, 0, 0),
                cls.usuario_admin_a.id, "B01 Banco ingreso previo",
            )
            _movimiento(
                cls.db, cls.admin_a.id, cls.banco.id, cls.ingreso_a.id,
                TransactionType.INCOME, "3000.00",
                datetime(2026, 10, 26, 12, 0, 0),
                cls.usuario_admin_a.id, "B01 Banco ingreso periodo",
            )
            _movimiento(
                cls.db, cls.admin_a.id, cls.banco.id, cls.egreso_a.id,
                TransactionType.EXPENSE, "1200.00",
                datetime(2026, 10, 27, 12, 0, 0),
                cls.usuario_admin_a.id, "B01 Banco egreso 27",
            )
            _movimiento(
                cls.db, cls.admin_a.id, cls.banco.id, cls.egreso_a.id,
                TransactionType.EXPENSE, "1000.00",
                datetime(2026, 10, 28, 12, 0, 0),
                cls.usuario_admin_a.id, "B01 Banco egreso 28",
            )
            _movimiento(
                cls.db, cls.admin_a.id, cls.caja.id, cls.ingreso_a.id,
                TransactionType.INCOME, "500.00",
                datetime(2026, 10, 26, 12, 0, 0),
                cls.usuario_admin_a.id, "B01 Caja ingreso",
            )
            _movimiento(
                cls.db, cls.admin_a.id, cls.caja.id, cls.egreso_a.id,
                TransactionType.EXPENSE, "700.00",
                datetime(2026, 10, 29, 12, 0, 0),
                cls.usuario_admin_a.id, "B01 Caja egreso",
            )

            # ------------------------------------------------ empresa B
            (
                cls.empresa_b,
                cls.admin_b,
                cls.usuario_admin_b,
            ) = _crear_empresa(cls.db, cls.marca, "beta")
            cls.empresas_creadas.append(cls.empresa_b.id)

            cls.cuenta_b = _crear_cuenta(
                cls.db,
                cls.admin_b.id,
                cls.empresa_b.id,
                "Cuenta Beta A7",
                AccountType.DEBIT,
            )
            cls.ingreso_b = _crear_concepto(
                cls.db,
                cls.admin_b.id,
                cls.empresa_b.id,
                "Ingreso Beta A7",
                ConceptType.INCOME,
            )
            _asignar(
                cls.db,
                cls.admin_b.id,
                cls.cuenta_b.id,
                cls.ingreso_b.id,
            )
            _movimiento(
                cls.db, cls.admin_b.id, cls.cuenta_b.id, cls.ingreso_b.id,
                TransactionType.INCOME, "100.00",
                datetime(2026, 10, 28, 12, 0, 0),
                cls.usuario_admin_b.id, "B12 ingreso Beta",
            )

            # ------------------------------------------ empresa vacia
            (
                cls.empresa_vacia,
                cls.admin_vacia,
                cls.usuario_admin_vacia,
            ) = _crear_empresa(cls.db, cls.marca, "vacia")
            cls.empresas_creadas.append(cls.empresa_vacia.id)

            # --------------------------------------- empresa negativa
            (
                cls.empresa_negativa,
                cls.admin_negativa,
                cls.usuario_admin_negativa,
            ) = _crear_empresa(cls.db, cls.marca, "neg")
            cls.empresas_creadas.append(cls.empresa_negativa.id)

            cls.cuenta_negativa = _crear_cuenta(
                cls.db,
                cls.admin_negativa.id,
                cls.empresa_negativa.id,
                "Unica A7",
                AccountType.CASH,
            )
            cls.egreso_negativa = _crear_concepto(
                cls.db,
                cls.admin_negativa.id,
                cls.empresa_negativa.id,
                "Egreso Negativo A7",
                ConceptType.EXPENSE,
            )
            _asignar(
                cls.db,
                cls.admin_negativa.id,
                cls.cuenta_negativa.id,
                cls.egreso_negativa.id,
            )
            _movimiento(
                cls.db, cls.admin_negativa.id, cls.cuenta_negativa.id,
                cls.egreso_negativa.id, TransactionType.EXPENSE, "50.00",
                datetime(2026, 10, 28, 12, 0, 0),
                cls.usuario_admin_negativa.id, "B15 egreso unico",
            )

            cls.tokens = {
                "admin_a": _login(cls.usuario_admin_a.email),
                "consulta_a": _login(cls.email_consulta),
                "admin_b": _login(cls.usuario_admin_b.email),
                "admin_vacia": _login(cls.usuario_admin_vacia.email),
                "admin_negativa": _login(cls.usuario_admin_negativa.email),
            }
        except Exception:
            for company_id in reversed(cls.empresas_creadas):
                _borrar_empresa(cls.db, company_id)
            cls.db.close()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            for company_id in reversed(cls.empresas_creadas):
                _borrar_empresa(cls.db, company_id)
        finally:
            cls.db.close()

    def setUp(self):
        self.temporales: list[int] = []

    def tearDown(self):
        for company_id in reversed(self.temporales):
            _borrar_empresa(self.db, company_id)
        self.temporales = []

    # ------------------------------------------------------- auxiliares

    def _empresa_temporal(self, slug: str):
        company, admin, usuario = _crear_empresa(
            self.db,
            self.marca,
            f"{slug}{len(self.temporales)}",
        )
        self.temporales.append(company.id)
        return company, admin, usuario

    def _consulta_cuenta(self, cuenta_id: int, desde: str, hasta: str,
                         token: str) -> dict:
        return _gql(
            CONSULTA_CUENTA,
            {
                "accountId": str(cuenta_id),
                "fromDate": desde,
                "toDate": hasta,
            },
            token=token,
        )

    def _consulta_general(self, desde: str, hasta: str,
                          token: str) -> dict:
        return _gql(
            CONSULTA_GENERAL,
            {"fromDate": desde, "toDate": hasta},
            token=token,
        )

    def _balance_cuenta(self, cuenta_id: int, desde: str, hasta: str,
                        token: str) -> dict:
        datos = self._consulta_cuenta(cuenta_id, desde, hasta, token)
        balance = (datos.get("data") or {}).get("accountBalance")
        self.assertIsNotNone(balance, _error(datos))
        return balance

    def _balance_general(self, desde: str, hasta: str,
                         token: str) -> dict:
        datos = self._consulta_general(desde, hasta, token)
        balance = (datos.get("data") or {}).get("generalBalance")
        self.assertIsNotNone(balance, _error(datos))
        return balance

    def _assert_importe(self, valor, esperado: str) -> None:
        self.assertIsNotNone(valor)
        self.assertEqual(Decimal(str(valor)), Decimal(esperado))

    def _assert_formato_dos_decimales(self, valor) -> None:
        self.assertRegex(str(valor), r"^-?\d+\.\d{2}$")

    # ------------------------------------------------------------ B01

    def test_01_b01_referencia_y_sin_mutaciones(self):
        antes = _snapshot(self.db, self.empresa_a.id)

        banco = self._balance_cuenta(
            self.banco.id, "2026-10-26", "2026-10-30",
            self.tokens["admin_a"],
        )
        self.assertEqual(banco["accountId"], str(self.banco.id))
        self.assertEqual(banco["accountName"], "Banco A7")
        self.assertTrue(banco["isActive"])
        self._assert_importe(banco["openingBalance"], "1000.00")
        self._assert_importe(banco["totalIncome"], "3000.00")
        self._assert_importe(banco["totalExpense"], "2200.00")
        self._assert_importe(banco["profit"], "800.00")
        self._assert_importe(banco["closingBalance"], "1800.00")
        self.assertFalse(banco["isInRed"])
        self.assertEqual(banco["currency"], "MXN")
        for campo in (
            "openingBalance", "totalIncome", "totalExpense",
            "profit", "closingBalance",
        ):
            self._assert_formato_dos_decimales(banco[campo])

        caja = self._balance_cuenta(
            self.caja.id, "2026-10-26", "2026-10-30",
            self.tokens["admin_a"],
        )
        self.assertEqual(caja["accountName"], "Caja A7")
        self._assert_importe(caja["openingBalance"], "0.00")
        self._assert_importe(caja["totalIncome"], "500.00")
        self._assert_importe(caja["totalExpense"], "700.00")
        self._assert_importe(caja["profit"], "-200.00")
        self._assert_importe(caja["closingBalance"], "-200.00")
        self.assertTrue(caja["isInRed"])

        ahorro = self._balance_cuenta(
            self.ahorro.id, "2026-10-26", "2026-10-30",
            self.tokens["admin_a"],
        )
        self.assertEqual(ahorro["accountName"], "Ahorro A7")
        for campo in (
            "openingBalance", "totalIncome", "totalExpense",
            "profit", "closingBalance",
        ):
            self._assert_importe(ahorro[campo], "0.00")
        self.assertFalse(ahorro["isInRed"])

        general = self._balance_general(
            "2026-10-26", "2026-10-30", self.tokens["admin_a"]
        )
        self._assert_importe(general["openingBalance"], "1000.00")
        self._assert_importe(general["totalIncome"], "3500.00")
        self._assert_importe(general["totalExpense"], "2900.00")
        self._assert_importe(general["profit"], "600.00")
        self._assert_importe(general["closingBalance"], "1600.00")
        self.assertEqual(general["accountsInRed"], 1)
        self.assertFalse(general["isInRed"])
        self.assertEqual(general["currency"], "MXN")
        self.assertEqual(general["fromDate"], "2026-10-26")
        self.assertEqual(general["toDate"], "2026-10-30")

        esperadas = sorted(
            [self.banco.id, self.caja.id, self.ahorro.id]
        )
        self.assertEqual(
            [int(cuenta["accountId"]) for cuenta in general["accounts"]],
            esperadas,
        )

        despues = _snapshot(self.db, self.empresa_a.id)
        self.assertEqual(antes, despues)

    # ------------------------------------------------------------ B02

    def test_02_b02_banco_un_solo_dia(self):
        banco = self._balance_cuenta(
            self.banco.id, "2026-10-28", "2026-10-28",
            self.tokens["admin_a"],
        )
        self._assert_importe(banco["openingBalance"], "2800.00")
        self._assert_importe(banco["totalIncome"], "0.00")
        self._assert_importe(banco["totalExpense"], "1000.00")
        self._assert_importe(banco["profit"], "-1000.00")
        self._assert_importe(banco["closingBalance"], "1800.00")
        self.assertFalse(banco["isInRed"])

    # ------------------------------------------------------------ B03

    def test_03_b03_empresa_sin_cuentas(self):
        general = self._balance_general(
            "2026-10-26", "2026-10-30", self.tokens["admin_vacia"]
        )
        self.assertEqual(general["accounts"], [])
        self._assert_importe(general["openingBalance"], "0.00")
        self._assert_importe(general["totalIncome"], "0.00")
        self._assert_importe(general["totalExpense"], "0.00")
        self._assert_importe(general["profit"], "0.00")
        self._assert_importe(general["closingBalance"], "0.00")
        self.assertEqual(general["accountsInRed"], 0)
        self.assertFalse(general["isInRed"])
        self.assertEqual(general["currency"], "MXN")

    # ------------------------------------------------------------ B04

    def test_04_b04_limites_utc(self):
        company, admin, usuario = self._empresa_temporal("b04")
        cuenta = _crear_cuenta(
            self.db, admin.id, company.id, "Cuenta B04",
            AccountType.DEBIT,
        )
        ingreso = _crear_concepto(
            self.db, admin.id, company.id, "Ingreso B04",
            ConceptType.INCOME,
        )
        egreso = _crear_concepto(
            self.db, admin.id, company.id, "Egreso B04",
            ConceptType.EXPENSE,
        )
        _asignar(self.db, admin.id, cuenta.id, ingreso.id)
        _asignar(self.db, admin.id, cuenta.id, egreso.id)

        _movimiento(
            self.db, admin.id, cuenta.id, ingreso.id,
            TransactionType.INCOME, "100.00",
            datetime(2026, 10, 25, 23, 59, 59, tzinfo=timezone.utc),
            usuario.id, "B04 antes del inicio",
        )
        _movimiento(
            self.db, admin.id, cuenta.id, ingreso.id,
            TransactionType.INCOME, "10.00",
            datetime(2026, 10, 26, 0, 0, 0, tzinfo=timezone.utc),
            usuario.id, "B04 inicio exacto",
        )
        _movimiento(
            self.db, admin.id, cuenta.id, egreso.id,
            TransactionType.EXPENSE, "5.00",
            datetime(2026, 10, 30, 23, 59, 59, tzinfo=timezone.utc),
            usuario.id, "B04 fin incluido",
        )
        _movimiento(
            self.db, admin.id, cuenta.id, ingreso.id,
            TransactionType.INCOME, "200.00",
            datetime(2026, 10, 31, 0, 0, 0, tzinfo=timezone.utc),
            usuario.id, "B04 limite exclusivo",
        )

        token = _login(usuario.email)
        balance = self._balance_cuenta(
            cuenta.id, "2026-10-26", "2026-10-30", token
        )
        self._assert_importe(balance["openingBalance"], "100.00")
        self._assert_importe(balance["totalIncome"], "10.00")
        self._assert_importe(balance["totalExpense"], "5.00")
        self._assert_importe(balance["profit"], "5.00")
        self._assert_importe(balance["closingBalance"], "105.00")
        self.assertFalse(balance["isInRed"])

        dia_25 = self._balance_cuenta(
            cuenta.id, "2026-10-25", "2026-10-25", token
        )
        self._assert_importe(dia_25["openingBalance"], "0.00")
        self._assert_importe(dia_25["totalIncome"], "100.00")
        self._assert_importe(dia_25["closingBalance"], "100.00")

        dia_31 = self._balance_cuenta(
            cuenta.id, "2026-10-31", "2026-10-31", token
        )
        self._assert_importe(dia_31["openingBalance"], "105.00")
        self._assert_importe(dia_31["totalIncome"], "200.00")
        self._assert_importe(dia_31["closingBalance"], "305.00")

    # ------------------------------------------------------------ B05

    def test_05_b05_fecha_operacion_manda_sobre_captura(self):
        company, admin, usuario = self._empresa_temporal("b05")
        cuenta = _crear_cuenta(
            self.db, admin.id, company.id, "Cuenta B05",
            AccountType.DEBIT,
        )
        ingreso = _crear_concepto(
            self.db, admin.id, company.id, "Ingreso B05",
            ConceptType.INCOME,
        )
        _asignar(self.db, admin.id, cuenta.id, ingreso.id)

        token = _login(usuario.email)
        datos = _gql(
            CREAR_MOVIMIENTO,
            {
                "input": {
                    "accountId": cuenta.id,
                    "conceptId": ingreso.id,
                    "transactionType": "INCOME",
                    "amount": "30.00",
                    "transactionDate": "2026-01-15T12:00:00Z",
                }
            },
            token=token,
        )
        creada = (datos.get("data") or {}).get("createTransaction")
        self.assertIsNotNone(creada, _error(datos))
        self.assertTrue(creada["transactionDate"].startswith(
            "2026-01-15T12:00:00"
        ))
        self.assertGreater(
            creada["capturedAt"],
            creada["transactionDate"],
        )

        balance = self._balance_cuenta(
            cuenta.id, "2026-01-15", "2026-01-15", token
        )
        self._assert_importe(balance["openingBalance"], "0.00")
        self._assert_importe(balance["totalIncome"], "30.00")
        self._assert_importe(balance["closingBalance"], "30.00")

        dia_siguiente = self._balance_cuenta(
            cuenta.id, "2026-01-16", "2026-01-16", token
        )
        self._assert_importe(dia_siguiente["openingBalance"], "30.00")
        self._assert_importe(dia_siguiente["totalIncome"], "0.00")
        self._assert_importe(dia_siguiente["closingBalance"], "30.00")

    # ------------------------------------------------------------ B06

    def test_06_b06_precision_decimal(self):
        company, admin, usuario = self._empresa_temporal("b06")
        cuenta = _crear_cuenta(
            self.db, admin.id, company.id, "Cuenta B06",
            AccountType.DEBIT,
        )
        ingreso = _crear_concepto(
            self.db, admin.id, company.id, "Ingreso B06",
            ConceptType.INCOME,
        )
        egreso = _crear_concepto(
            self.db, admin.id, company.id, "Egreso B06",
            ConceptType.EXPENSE,
        )
        _asignar(self.db, admin.id, cuenta.id, ingreso.id)
        _asignar(self.db, admin.id, cuenta.id, egreso.id)

        for monto in ("0.10", "0.20"):
            _movimiento(
                self.db, admin.id, cuenta.id, ingreso.id,
                TransactionType.INCOME, monto,
                datetime(2026, 10, 28, 12, 0, 0),
                usuario.id, f"B06 ingreso {monto}",
            )
        _movimiento(
            self.db, admin.id, cuenta.id, egreso.id,
            TransactionType.EXPENSE, "0.30",
            datetime(2026, 10, 28, 12, 0, 0),
            usuario.id, "B06 egreso 0.30",
        )

        token = _login(usuario.email)
        balance = self._balance_cuenta(
            cuenta.id, "2026-10-28", "2026-10-28", token
        )
        self.assertEqual(balance["totalIncome"], "0.30")
        self.assertEqual(balance["totalExpense"], "0.30")
        self.assertEqual(balance["profit"], "0.00")
        self.assertEqual(balance["closingBalance"], "0.00")
        self.assertFalse(balance["isInRed"])

    # ------------------------------------------------------------ B07

    def test_07_b07_movimiento_inactivo(self):
        company, admin, usuario = self._empresa_temporal("b07")
        cuenta = _crear_cuenta(
            self.db, admin.id, company.id, "Cuenta B07",
            AccountType.DEBIT,
        )
        ingreso = _crear_concepto(
            self.db, admin.id, company.id, "Ingreso B07",
            ConceptType.INCOME,
        )
        _asignar(self.db, admin.id, cuenta.id, ingreso.id)

        _movimiento(
            self.db, admin.id, cuenta.id, ingreso.id,
            TransactionType.INCOME, "100.00",
            datetime(2026, 10, 20, 12, 0, 0),
            usuario.id, "B07 ingreso previo",
        )
        eliminable = _movimiento(
            self.db, admin.id, cuenta.id, ingreso.id,
            TransactionType.INCOME, "50.00",
            datetime(2026, 10, 28, 12, 0, 0),
            usuario.id, "B07 ingreso a eliminar",
        )

        token = _login(usuario.email)
        datos = _gql(
            ELIMINAR_MOVIMIENTO,
            {"transactionId": eliminable.id},
            token=token,
        )
        borrado = (datos.get("data") or {}).get("deleteTransaction")
        self.assertIsNotNone(borrado, _error(datos))
        self.assertFalse(borrado["isActive"])

        balance = self._balance_cuenta(
            cuenta.id, "2026-10-28", "2026-10-28", token
        )
        self._assert_importe(balance["openingBalance"], "100.00")
        self._assert_importe(balance["totalIncome"], "0.00")
        self._assert_importe(balance["closingBalance"], "100.00")

    # ------------------------------------------------------------ B08

    def test_08_b08_cuenta_inactiva_conserva_historial(self):
        company, admin, usuario = self._empresa_temporal("b08")
        cuenta = _crear_cuenta(
            self.db, admin.id, company.id, "Cuenta B08",
            AccountType.DEBIT,
        )
        ingreso = _crear_concepto(
            self.db, admin.id, company.id, "Ingreso B08",
            ConceptType.INCOME,
        )
        _asignar(self.db, admin.id, cuenta.id, ingreso.id)

        _movimiento(
            self.db, admin.id, cuenta.id, ingreso.id,
            TransactionType.INCOME, "100.00",
            datetime(2026, 10, 20, 12, 0, 0),
            usuario.id, "B08 ingreso previo",
        )
        _movimiento(
            self.db, admin.id, cuenta.id, ingreso.id,
            TransactionType.INCOME, "50.00",
            datetime(2026, 10, 28, 12, 0, 0),
            usuario.id, "B08 ingreso periodo",
        )

        token = _login(usuario.email)

        try:
            self.db.execute(
                text(
                    "UPDATE accounts SET is_active = false WHERE id = :i"
                ),
                {"i": cuenta.id},
            )
            self.db.commit()

            balance = self._balance_cuenta(
                cuenta.id, "2026-10-28", "2026-10-28", token
            )
            self.assertFalse(balance["isActive"])
            self._assert_importe(balance["openingBalance"], "100.00")
            self._assert_importe(balance["totalIncome"], "50.00")
            self._assert_importe(balance["closingBalance"], "150.00")

            general = self._balance_general(
                "2026-10-28", "2026-10-28", token
            )
            self.assertEqual(len(general["accounts"]), 1)
            self.assertFalse(general["accounts"][0]["isActive"])
            self._assert_importe(
                general["accounts"][0]["closingBalance"], "150.00"
            )
            self._assert_importe(general["closingBalance"], "150.00")
        finally:
            self.db.execute(
                text(
                    "UPDATE accounts SET is_active = true WHERE id = :i"
                ),
                {"i": cuenta.id},
            )
            self.db.commit()

    # ------------------------------------------------------------ B09

    def test_09_b09_conceptos_adicionales_no_duplican(self):
        company, admin, usuario = self._empresa_temporal("b09")
        cuenta = _crear_cuenta(
            self.db, admin.id, company.id, "Cuenta B09",
            AccountType.DEBIT,
        )
        ingreso_1 = _crear_concepto(
            self.db, admin.id, company.id, "Ingreso B09 uno",
            ConceptType.INCOME,
        )
        ingreso_2 = _crear_concepto(
            self.db, admin.id, company.id, "Ingreso B09 dos",
            ConceptType.INCOME,
        )
        _asignar(self.db, admin.id, cuenta.id, ingreso_1.id)
        _asignar(self.db, admin.id, cuenta.id, ingreso_2.id)

        _movimiento(
            self.db, admin.id, cuenta.id, ingreso_1.id,
            TransactionType.INCOME, "10.00",
            datetime(2026, 10, 28, 12, 0, 0),
            usuario.id, "B09 ingreso concepto uno",
        )
        _movimiento(
            self.db, admin.id, cuenta.id, ingreso_2.id,
            TransactionType.INCOME, "10.00",
            datetime(2026, 10, 28, 12, 0, 0),
            usuario.id, "B09 ingreso concepto dos",
        )

        token = _login(usuario.email)
        balance = self._balance_cuenta(
            cuenta.id, "2026-10-28", "2026-10-28", token
        )
        self._assert_importe(balance["totalIncome"], "20.00")
        self._assert_importe(balance["profit"], "20.00")
        self._assert_importe(balance["closingBalance"], "20.00")

    # ------------------------------------------------------------ B10

    def test_10_b10_validacion_de_fechas(self):
        invertido = self._consulta_cuenta(
            self.banco.id, "2026-10-31", "2026-10-01",
            self.tokens["admin_a"],
        )
        self.assertIsNone(
            (invertido.get("data") or {}).get("accountBalance")
        )
        self.assertIn("posterior", _error(invertido))

        invalida = self._consulta_cuenta(
            self.banco.id, "2026-02-30", "2026-10-30",
            self.tokens["admin_a"],
        )
        self.assertIsNone(
            (invalida.get("data") or {}).get("accountBalance")
        )
        self.assertTrue(_error(invalida))

        general_invertido = self._consulta_general(
            "2026-10-31", "2026-10-01", self.tokens["admin_a"]
        )
        self.assertIsNone(
            (general_invertido.get("data") or {}).get("generalBalance")
        )
        self.assertIn("posterior", _error(general_invertido))

    # ------------------------------------------------------------ B11

    def test_11_b11_autenticacion_obligatoria(self):
        partes = self.tokens["admin_a"].split(".")
        firma = partes[2]
        # Cambiar el primer carácter de la firma altera sus bits
        # significativos; cambiar solo el último podría conservar los
        # bytes decodificados por el relleno Base64.
        partes[2] = ("A" if firma[0] != "A" else "B") + firma[1:]
        alterado = ".".join(partes)
        self.assertNotEqual(alterado, self.tokens["admin_a"])

        vencido = _firmar({
            "companyUserId": self.admin_a.id,
            "companyId": self.empresa_a.id,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        })

        for token in (None, alterado, vencido):
            cuenta = self._consulta_cuenta(
                self.banco.id, "2026-10-26", "2026-10-30", token
            )
            self.assertIsNone(
                (cuenta.get("data") or {}).get("accountBalance")
            )
            self.assertTrue(_error(cuenta))

            general = self._consulta_general(
                "2026-10-26", "2026-10-30", token
            )
            self.assertIsNone(
                (general.get("data") or {}).get("generalBalance")
            )
            self.assertTrue(_error(general))

    # ------------------------------------------------------------ B12

    def test_12_b12_aislamiento_multiempresa(self):
        inexistente_id = self.db.execute(
            text("SELECT COALESCE(MAX(id), 0) + 1000000 FROM accounts")
        ).scalar()

        ajeno = self._consulta_cuenta(
            self.cuenta_b.id, "2026-10-26", "2026-10-30",
            self.tokens["admin_a"],
        )
        self.assertIsNone(
            (ajeno.get("data") or {}).get("accountBalance")
        )
        self.assertIn("no existe", _error(ajeno))

        inexistente = self._consulta_cuenta(
            inexistente_id, "2026-10-26", "2026-10-30",
            self.tokens["admin_a"],
        )
        self.assertIsNone(
            (inexistente.get("data") or {}).get("accountBalance")
        )
        self.assertIn("no existe", _error(inexistente))
        self.assertEqual(_error(ajeno), _error(inexistente))

        ajeno_b = self._consulta_cuenta(
            self.banco.id, "2026-10-26", "2026-10-30",
            self.tokens["admin_b"],
        )
        self.assertIsNone(
            (ajeno_b.get("data") or {}).get("accountBalance")
        )
        self.assertIn("no existe", _error(ajeno_b))

        general_a = self._balance_general(
            "2026-10-26", "2026-10-30", self.tokens["admin_a"]
        )
        ids_a = {
            int(cuenta["accountId"])
            for cuenta in general_a["accounts"]
        }
        esperadas_a = {
            fila[0]
            for fila in self.db.execute(
                text(
                    "SELECT id FROM accounts WHERE company_id = :c"
                ),
                {"c": self.empresa_a.id},
            ).fetchall()
        }
        self.assertEqual(ids_a, esperadas_a)
        self.assertNotIn(self.cuenta_b.id, ids_a)

        general_b = self._balance_general(
            "2026-10-26", "2026-10-30", self.tokens["admin_b"]
        )
        ids_b = {
            int(cuenta["accountId"])
            for cuenta in general_b["accounts"]
        }
        esperadas_b = {
            fila[0]
            for fila in self.db.execute(
                text(
                    "SELECT id FROM accounts WHERE company_id = :c"
                ),
                {"c": self.empresa_b.id},
            ).fetchall()
        }
        self.assertEqual(ids_b, esperadas_b)
        self.assertEqual(ids_b, {self.cuenta_b.id})
        self.assertNotIn(self.banco.id, ids_b)

    # ------------------------------------------------------------ B13

    def test_13_b13_rol_consulta_lee_pero_no_escribe(self):
        balance = self._balance_cuenta(
            self.banco.id, "2026-10-26", "2026-10-30",
            self.tokens["consulta_a"],
        )
        self._assert_importe(balance["closingBalance"], "1800.00")

        general = self._balance_general(
            "2026-10-26", "2026-10-30", self.tokens["consulta_a"]
        )
        self._assert_importe(general["closingBalance"], "1600.00")

        antes = self.db.execute(
            text("SELECT count(*) FROM transactions")
        ).scalar()

        datos = _gql(
            CREAR_MOVIMIENTO,
            {
                "input": {
                    "accountId": self.banco.id,
                    "conceptId": self.ingreso_a.id,
                    "transactionType": "INCOME",
                    "amount": "10.00",
                    "transactionDate": "2026-10-28T12:00:00Z",
                }
            },
            token=self.tokens["consulta_a"],
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("createTransaction")
        )
        self.assertIn("transactions.write", _error(datos))

        despues = self.db.execute(
            text("SELECT count(*) FROM transactions")
        ).scalar()
        self.assertEqual(antes, despues)

    # ------------------------------------------------------------ B14

    def test_14_b14_retiro_temporal_de_transactions_read(self):
        rol_consulta = get_role_by_code(self.db, "CONSULTA")
        permiso = get_permission_by_code(self.db, "transactions.read")
        self.assertIsNotNone(rol_consulta)
        self.assertIsNotNone(permiso)

        removido = False
        try:
            remove_permission_from_role_service(
                self.db,
                self.admin_a.id,
                rol_consulta.id,
                permiso.id,
            )
            removido = True

            cuenta = self._consulta_cuenta(
                self.banco.id, "2026-10-26", "2026-10-30",
                self.tokens["consulta_a"],
            )
            self.assertIsNone(
                (cuenta.get("data") or {}).get("accountBalance")
            )
            self.assertIn("transactions.read", _error(cuenta))

            general = self._consulta_general(
                "2026-10-26", "2026-10-30", self.tokens["consulta_a"]
            )
            self.assertIsNone(
                (general.get("data") or {}).get("generalBalance")
            )
            self.assertIn("transactions.read", _error(general))
        finally:
            if removido:
                assign_permission_to_role_service(
                    self.db,
                    self.admin_a.id,
                    rol_consulta.id,
                    permiso.id,
                )

        balance = self._balance_cuenta(
            self.banco.id, "2026-10-26", "2026-10-30",
            self.tokens["consulta_a"],
        )
        self._assert_importe(balance["closingBalance"], "1800.00")

        activos = self.db.execute(
            text(
                "SELECT count(*) FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id "
                "JOIN permissions p ON p.id = rp.permission_id "
                "WHERE r.code = 'CONSULTA' AND p.code = 'transactions.read' "
                "AND rp.is_active"
            )
        ).scalar()
        self.assertEqual(activos, 1)

    # ------------------------------------------------------------ B15

    def test_15_b15_saldo_negativo(self):
        balance = self._balance_cuenta(
            self.cuenta_negativa.id, "2026-10-28", "2026-10-28",
            self.tokens["admin_negativa"],
        )
        self._assert_importe(balance["openingBalance"], "0.00")
        self._assert_importe(balance["totalIncome"], "0.00")
        self._assert_importe(balance["totalExpense"], "50.00")
        self._assert_importe(balance["profit"], "-50.00")
        self._assert_importe(balance["closingBalance"], "-50.00")
        self.assertTrue(balance["isInRed"])

        general = self._balance_general(
            "2026-10-28", "2026-10-28",
            self.tokens["admin_negativa"],
        )
        self._assert_importe(general["openingBalance"], "0.00")
        self._assert_importe(general["totalIncome"], "0.00")
        self._assert_importe(general["totalExpense"], "50.00")
        self._assert_importe(general["profit"], "-50.00")
        self._assert_importe(general["closingBalance"], "-50.00")
        self.assertEqual(general["accountsInRed"], 1)
        self.assertTrue(general["isInRed"])
        self.assertEqual(len(general["accounts"]), 1)
        self.assertTrue(general["accounts"][0]["isInRed"])

    # ------------------------------------------------------------ B16

    def test_16_b16_company_id_autenticada(self):
        general_a = self._balance_general(
            "2026-10-26", "2026-10-30", self.tokens["admin_a"]
        )
        self.assertEqual(general_a["companyId"], str(self.empresa_a.id))

        general_b = self._balance_general(
            "2026-10-26", "2026-10-30", self.tokens["admin_b"]
        )
        self.assertEqual(general_b["companyId"], str(self.empresa_b.id))
        self.assertNotEqual(general_a["companyId"], general_b["companyId"])
        self.assertEqual(
            {int(cuenta["accountId"]) for cuenta in general_b["accounts"]},
            {self.cuenta_b.id},
        )

        # La empresa no es un argumento de generalBalance: el cliente no
        # puede elegirla ni sustituir la identidad del token.
        intento = _gql(
            """
            query BalanceGeneralAjeno($fromDate: Date!, $toDate: Date!) {
              generalBalance(
                companyId: "%s"
                fromDate: $fromDate
                toDate: $toDate
              ) {
                companyId
              }
            }
            """
            % self.empresa_b.id,
            {"fromDate": "2026-10-26", "toDate": "2026-10-30"},
            token=self.tokens["admin_a"],
        )
        self.assertIsNone(
            (intento.get("data") or {}).get("generalBalance")
        )
        self.assertIn("companyId", _error(intento))

        # Tras el intento, el token de A sigue devolviendo la empresa A.
        self.assertEqual(
            self._balance_general(
                "2026-10-26", "2026-10-30", self.tokens["admin_a"]
            )["companyId"],
            str(self.empresa_a.id),
        )


if __name__ == "__main__":
    unittest.main()
