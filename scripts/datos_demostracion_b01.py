"""Conjunto de demostración B01 aislado para la Unidad III, Actividad 1.

Crea una empresa, un usuario administrador, tres cuentas y los movimientos
necesarios para reproducir exactamente el caso B01 del periodo
2026-10-26 a 2026-10-30.

Reglas de seguridad:

- Solo opera sobre la base ``fintrack5_test`` y el host ``postgres``.
- No toca la empresa #11, sus usuarios, cuentas, movimientos ni permisos.
- Es idempotente: si el conjunto ya existe, lo reutiliza y verifica; no
  duplica movimientos.
- ``--cleanup`` elimina únicamente los registros identificados por la
  empresa ``B01-DEMO-2026`` y el usuario ``demo_b01@test.local``.

Uso dentro del contenedor de pruebas:

    python - --check
    python - --apply
    python - --cleanup

La contraseña del usuario de demostración es la misma constante ficticia de
``scripts/setup_pruebas.py``; nunca se imprime ni se escribe en la salida.
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from models.account import Account, AccountType
from models.account_concept import AccountConcept
from models.company import Company
from models.company_user import CompanyUser
from models.company_user_role import CompanyUserRole
from models.concept import Concept, ConceptType
from models.transaction import Transaction, TransactionType
from models.user import User
from repositories.account_concept_repository import get_relation
from repositories.account_repository import list_accounts
from repositories.company_repository import create_company
from repositories.company_user_repository import (
    get_active_company_user_by_user,
    get_company_user_by_company_and_user,
)
from repositories.company_user_role_repository import (
    get_active_company_user_role,
)
from repositories.concept_repository import list_concepts
from repositories.transaction_repository import list_transactions
from repositories.user_repository import create_user, get_user_by_email
from security.password import hash_password
from services.account_concept_service import assign_concept_to_account
from services.account_service import create_account_service
from services.balance_service import general_balance_service
from services.company_user_service import create_company_admin_service
from services.concept_service import create_concept_service
from services.transaction_service import create_transaction_service
from scripts.setup_pruebas import CONTRASENA_PRUEBAS

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"

EMPRESA_TAX_ID = "B01-DEMO-2026"
EMPRESA_NOMBRE = "FinTrack-5 Demo B01"
EMPRESA_EMAIL = "demo.b01@fintrack.local"

USUARIO_EMAIL = "demo_b01@test.local"
USUARIO_NOMBRE = "Administrador Demo B01"

CUENTAS = {
    "Banco B01": AccountType.DEBIT,
    "Caja B01": AccountType.CASH,
    "Ahorro B01": AccountType.SAVINGS,
}

CONCEPTOS = {
    "Ingreso B01": ConceptType.INCOME,
    "Egreso B01": ConceptType.EXPENSE,
}

# Cada movimiento tiene un marcador único en short_description para que la
# ejecución repetida no lo duplique.
MOVIMIENTOS = [
    {
        "marcador": "B01 demo Banco ingreso previo",
        "cuenta": "Banco B01",
        "concepto": "Ingreso B01",
        "tipo": TransactionType.INCOME,
        "monto": Decimal("1000.00"),
        "fecha": datetime(2026, 10, 25, 12, 0, 0),
    },
    {
        "marcador": "B01 demo Banco ingreso periodo",
        "cuenta": "Banco B01",
        "concepto": "Ingreso B01",
        "tipo": TransactionType.INCOME,
        "monto": Decimal("3000.00"),
        "fecha": datetime(2026, 10, 26, 12, 0, 0),
    },
    {
        "marcador": "B01 demo Caja ingreso periodo",
        "cuenta": "Caja B01",
        "concepto": "Ingreso B01",
        "tipo": TransactionType.INCOME,
        "monto": Decimal("500.00"),
        "fecha": datetime(2026, 10, 27, 12, 0, 0),
    },
    {
        "marcador": "B01 demo Banco egreso periodo",
        "cuenta": "Banco B01",
        "concepto": "Egreso B01",
        "tipo": TransactionType.EXPENSE,
        "monto": Decimal("2200.00"),
        "fecha": datetime(2026, 10, 28, 12, 0, 0),
    },
    {
        "marcador": "B01 demo Caja egreso periodo",
        "cuenta": "Caja B01",
        "concepto": "Egreso B01",
        "tipo": TransactionType.EXPENSE,
        "monto": Decimal("700.00"),
        "fecha": datetime(2026, 10, 29, 12, 0, 0),
    },
]

ESPERADO = {
    "openingBalance": Decimal("1000.00"),
    "totalIncome": Decimal("3500.00"),
    "totalExpense": Decimal("2900.00"),
    "profit": Decimal("600.00"),
    "closingBalance": Decimal("1600.00"),
    "accountsInRed": 1,
    "isInRed": False,
}

ESPERADO_CUENTAS = {
    "Banco B01": {
        "openingBalance": Decimal("1000.00"),
        "totalIncome": Decimal("3000.00"),
        "totalExpense": Decimal("2200.00"),
        "profit": Decimal("800.00"),
        "closingBalance": Decimal("1800.00"),
        "isInRed": False,
    },
    "Caja B01": {
        "openingBalance": Decimal("0.00"),
        "totalIncome": Decimal("500.00"),
        "totalExpense": Decimal("700.00"),
        "profit": Decimal("-200.00"),
        "closingBalance": Decimal("-200.00"),
        "isInRed": True,
    },
    "Ahorro B01": {
        "openingBalance": Decimal("0.00"),
        "totalIncome": Decimal("0.00"),
        "totalExpense": Decimal("0.00"),
        "profit": Decimal("0.00"),
        "closingBalance": Decimal("0.00"),
        "isInRed": False,
    },
}


def _log(mensaje: str) -> None:
    print(f"[b01] {mensaje}", file=sys.stderr, flush=True)


def _abortar(mensaje: str) -> None:
    _log(f"GUARDA: {mensaje}")
    sys.exit(1)


def _verificar_guardas(db: Session) -> None:
    if os.getenv("DB_NAME") != DB_ESPERADA:
        _abortar(f"DB_NAME no es {DB_ESPERADA}")
    if os.getenv("DB_HOST") != HOST_ESPERADO:
        _abortar(f"DB_HOST no es {HOST_ESPERADO}")

    actual = db.execute(text("SELECT current_database()")).scalar()
    if actual != DB_ESPERADA:
        _abortar(f"current_database() no es {DB_ESPERADA}")

    revision = db.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar()
    if revision != ALEMBIC_ESPERADO:
        _abortar(f"alembic_version no es {ALEMBIC_ESPERADO}")


def _buscar_empresa(db: Session) -> Company | None:
    return (
        db.query(Company)
        .filter(Company.tax_id == EMPRESA_TAX_ID)
        .first()
    )


def _obtener_o_crear_empresa(db: Session) -> Company:
    empresa = _buscar_empresa(db)

    if empresa is not None:
        if empresa.name != EMPRESA_NOMBRE:
            _abortar(
                "el tax_id B01 ya existe con otro nombre; "
                "no se modifica para evitar afectar datos ajenos"
            )
        _log(f"empresa B01 reutilizada: id={empresa.id}")
        return empresa

    empresa = create_company(
        db,
        Company(
            name=EMPRESA_NOMBRE,
            legal_name=EMPRESA_NOMBRE,
            tax_id=EMPRESA_TAX_ID,
            email=EMPRESA_EMAIL,
            phone=None,
            is_active=True,
        ),
    )
    _log(f"empresa B01 creada: id={empresa.id}")
    return empresa


def _obtener_o_crear_usuario(db: Session) -> User:
    usuario = get_user_by_email(db, USUARIO_EMAIL)

    if usuario is not None:
        if usuario.name != USUARIO_NOMBRE:
            _abortar(
                "el correo demo_b01@test.local ya existe con otro nombre; "
                "no se modifica para evitar afectar datos ajenos"
            )
        _log(f"usuario B01 reutilizado: id={usuario.id}")
        return usuario

    usuario = create_user(
        db,
        User(
            name=USUARIO_NOMBRE,
            email=USUARIO_EMAIL,
            password_hash=hash_password(CONTRASENA_PRUEBAS),
            email_verified=True,
            is_active=True,
        ),
    )
    _log(f"usuario B01 creado: id={usuario.id}")
    return usuario


def _obtener_o_crear_membresia(
    db: Session,
    empresa: Company,
    usuario: User,
) -> CompanyUser:
    membresia = get_company_user_by_company_and_user(
        db,
        empresa.id,
        usuario.id,
    )

    if membresia is not None:
        if not membresia.is_active or not membresia.is_admin:
            _abortar(
                "la membresía B01 existe pero no es un administrador activo"
            )

        rol_activo = get_active_company_user_role(db, membresia.id)
        if rol_activo is None or rol_activo.role.code != "ADMINISTRADOR":
            _abortar(
                "la membresía B01 no tiene el rol ADMINISTRADOR activo"
            )

        _log(f"membresía B01 reutilizada: id={membresia.id}")
        return membresia

    # El actor no se usa en el bootstrap; el servicio está reservado para
    # scripts de inicialización y no está expuesto en GraphQL.
    membresia = create_company_admin_service(
        db,
        0,
        empresa.id,
        usuario.id,
    )
    _log(f"membresía B01 creada: id={membresia.id}")
    return membresia


def _obtener_o_crear_cuenta(
    db: Session,
    empresa: Company,
    membresia: CompanyUser,
    nombre: str,
    tipo: AccountType,
) -> Account:
    existentes = list_accounts(db, company_id=empresa.id, active_only=False)
    cuenta = next((a for a in existentes if a.name == nombre), None)

    if cuenta is not None:
        if cuenta.account_type != tipo:
            _abortar(f"la cuenta {nombre} existe con otro tipo")
        if not cuenta.is_active:
            cuenta.is_active = True
            db.commit()
            db.refresh(cuenta)
            _log(f"cuenta {nombre} reactivada: id={cuenta.id}")
        else:
            _log(f"cuenta {nombre} reutilizada: id={cuenta.id}")
        return cuenta

    cuenta = create_account_service(
        db,
        membresia.id,
        empresa.id,
        tipo,
        nombre,
        bank_name="Banco Demo B01" if tipo == AccountType.DEBIT else None,
        short_description="Cuenta del conjunto B01 para demostración",
    )
    _log(f"cuenta {nombre} creada: id={cuenta.id}")
    return cuenta


def _obtener_o_crear_concepto(
    db: Session,
    empresa: Company,
    membresia: CompanyUser,
    nombre: str,
    tipo: ConceptType,
) -> Concept:
    existentes = list_concepts(db, company_id=empresa.id, active_only=False)
    concepto = next((c for c in existentes if c.name == nombre), None)

    if concepto is not None:
        if concepto.concept_type != tipo:
            _abortar(f"el concepto {nombre} existe con otro tipo")
        if not concepto.is_active:
            concepto.is_active = True
            db.commit()
            db.refresh(concepto)
            _log(f"concepto {nombre} reactivado: id={concepto.id}")
        else:
            _log(f"concepto {nombre} reutilizado: id={concepto.id}")
        return concepto

    concepto = create_concept_service(
        db,
        membresia.id,
        empresa.id,
        tipo,
        nombre,
        short_description="Concepto del conjunto B01 para demostración",
    )
    _log(f"concepto {nombre} creado: id={concepto.id}")
    return concepto


def _asegurar_relacion(
    db: Session,
    membresia: CompanyUser,
    cuenta: Account,
    concepto: Concept,
) -> None:
    relacion = get_relation(
        db,
        account_id=cuenta.id,
        concept_id=concepto.id,
    )

    if relacion is not None:
        if not relacion.is_active:
            relacion.is_active = True
            db.commit()
            db.refresh(relacion)
            _log(
                f"relación reactivada: {cuenta.name} / {concepto.name}"
            )
        return

    assign_concept_to_account(
        db,
        membresia.id,
        cuenta.id,
        concepto.id,
    )
    _log(f"relación creada: {cuenta.name} / {concepto.name}")


def _asegurar_movimiento(
    db: Session,
    empresa: Company,
    membresia: CompanyUser,
    usuario: User,
    cuenta: Account,
    concepto: Concept,
    movimiento: dict,
) -> None:
    existentes = list_transactions(
        db,
        cuenta.id,
        limit=500,
        offset=0,
    )
    actual = next(
        (
            t
            for t in existentes
            if t.short_description == movimiento["marcador"]
        ),
        None,
    )

    if actual is not None:
        if (
            actual.transaction_type != movimiento["tipo"]
            or actual.amount != movimiento["monto"]
            or actual.transaction_date != movimiento["fecha"]
            or actual.concept_id != concepto.id
        ):
            _abortar(
                f"el movimiento {movimiento['marcador']} existe con "
                "valores distintos; no se sobrescribe"
            )
        _log(f"movimiento reutilizado: {movimiento['marcador']}")
        return

    create_transaction_service(
        db,
        membresia.id,
        cuenta.id,
        concepto.id,
        movimiento["tipo"],
        movimiento["monto"],
        captured_by=usuario.id,
        transaction_date=movimiento["fecha"],
        short_description=movimiento["marcador"],
    )
    _log(f"movimiento creado: {movimiento['marcador']}")


def _resumen_balance(db: Session, empresa: Company, membresia: CompanyUser):
    balance = general_balance_service(
        db,
        membresia.id,
        empresa.id,
        date(2026, 10, 26),
        date(2026, 10, 30),
    )

    cuentas = {
        cuenta.account_name: {
            "openingBalance": str(cuenta.opening_balance),
            "totalIncome": str(cuenta.total_income),
            "totalExpense": str(cuenta.total_expense),
            "profit": str(cuenta.profit),
            "closingBalance": str(cuenta.closing_balance),
            "isInRed": cuenta.is_in_red,
        }
        for cuenta in balance.accounts
    }

    return balance, cuentas


def _verificar_resultado(
    db: Session,
    empresa: Company,
    membresia: CompanyUser,
) -> dict:
    balance, cuentas = _resumen_balance(db, empresa, membresia)

    coincide_general = (
        balance.opening_balance == ESPERADO["openingBalance"]
        and balance.total_income == ESPERADO["totalIncome"]
        and balance.total_expense == ESPERADO["totalExpense"]
        and balance.profit == ESPERADO["profit"]
        and balance.closing_balance == ESPERADO["closingBalance"]
        and balance.accounts_in_red == ESPERADO["accountsInRed"]
        and balance.is_in_red == ESPERADO["isInRed"]
    )

    coincide_cuentas = all(
        nombre in cuentas
        and cuentas[nombre] == {
            "openingBalance": str(valores["openingBalance"]),
            "totalIncome": str(valores["totalIncome"]),
            "totalExpense": str(valores["totalExpense"]),
            "profit": str(valores["profit"]),
            "closingBalance": str(valores["closingBalance"]),
            "isInRed": valores["isInRed"],
        }
        for nombre, valores in ESPERADO_CUENTAS.items()
    )

    return {
        "empresa": {
            "id": empresa.id,
            "nombre": empresa.name,
            "taxId": empresa.tax_id,
        },
        "usuario": {
            "id": membresia.user_id,
            "email": USUARIO_EMAIL,
            "companyUserId": membresia.id,
        },
        "periodo": {
            "fromDate": "2026-10-26",
            "toDate": "2026-10-30",
        },
        "general": {
            "companyId": str(balance.company_id),
            "openingBalance": str(balance.opening_balance),
            "totalIncome": str(balance.total_income),
            "totalExpense": str(balance.total_expense),
            "profit": str(balance.profit),
            "closingBalance": str(balance.closing_balance),
            "accountsInRed": balance.accounts_in_red,
            "isInRed": balance.is_in_red,
            "currency": balance.currency,
        },
        "cuentas": cuentas,
        "coincideGeneral": coincide_general,
        "coincideCuentas": coincide_cuentas,
    }


def _aplicar(db: Session) -> None:
    empresa = _obtener_o_crear_empresa(db)
    usuario = _obtener_o_crear_usuario(db)

    otra_membresia = get_active_company_user_by_user(db, usuario.id)
    if otra_membresia is not None and otra_membresia.company_id != empresa.id:
        _abortar(
            "el usuario B01 ya tiene una membresía activa en otra empresa; "
            "el login elegiría esa empresa y no la demostración"
        )

    membresia = _obtener_o_crear_membresia(db, empresa, usuario)

    cuentas = {
        nombre: _obtener_o_crear_cuenta(db, empresa, membresia, nombre, tipo)
        for nombre, tipo in CUENTAS.items()
    }
    conceptos = {
        nombre: _obtener_o_crear_concepto(db, empresa, membresia, nombre, tipo)
        for nombre, tipo in CONCEPTOS.items()
    }

    for cuenta in cuentas.values():
        for concepto in conceptos.values():
            _asegurar_relacion(db, membresia, cuenta, concepto)

    for movimiento in MOVIMIENTOS:
        _asegurar_movimiento(
            db,
            empresa,
            membresia,
            usuario,
            cuentas[movimiento["cuenta"]],
            conceptos[movimiento["concepto"]],
            movimiento,
        )

    resumen = _verificar_resultado(db, empresa, membresia)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))

    if not resumen["coincideGeneral"] or not resumen["coincideCuentas"]:
        _abortar("el balance calculado no coincide con el caso B01")


def _limpiar(db: Session) -> None:
    empresa = _buscar_empresa(db)
    usuario = get_user_by_email(db, USUARIO_EMAIL)

    if empresa is None and usuario is None:
        _log("no existe el conjunto B01; nada que limpiar")
        return

    if empresa is not None:
        cuenta_ids = [
            cuenta.id
            for cuenta in list_accounts(
                db,
                company_id=empresa.id,
                active_only=False,
            )
        ]
        concepto_ids = [
            concepto.id
            for concepto in list_concepts(
                db,
                company_id=empresa.id,
                active_only=False,
            )
        ]
        membresia_ids = [
            membresia.id
            for membresia in db.query(CompanyUser)
            .filter(CompanyUser.company_id == empresa.id)
            .all()
        ]

        if cuenta_ids:
            db.query(Transaction).filter(
                Transaction.account_id.in_(cuenta_ids)
            ).delete(synchronize_session=False)
            db.query(AccountConcept).filter(
                AccountConcept.account_id.in_(cuenta_ids)
            ).delete(synchronize_session=False)
            db.query(Account).filter(
                Account.id.in_(cuenta_ids)
            ).delete(synchronize_session=False)

        if concepto_ids:
            db.query(AccountConcept).filter(
                AccountConcept.concept_id.in_(concepto_ids)
            ).delete(synchronize_session=False)
            db.query(Concept).filter(
                Concept.id.in_(concepto_ids)
            ).delete(synchronize_session=False)

        if membresia_ids:
            db.query(CompanyUserRole).filter(
                CompanyUserRole.company_user_id.in_(membresia_ids)
            ).delete(synchronize_session=False)
            db.query(CompanyUser).filter(
                CompanyUser.id.in_(membresia_ids)
            ).delete(synchronize_session=False)

        db.delete(empresa)
        db.commit()
        _log(f"empresa B01 eliminada: id={empresa.id}")

    if usuario is not None:
        otras = (
            db.query(CompanyUser)
            .filter(CompanyUser.user_id == usuario.id)
            .count()
        )
        if otras == 0:
            db.delete(usuario)
            db.commit()
            _log(f"usuario B01 eliminado: id={usuario.id}")
        else:
            _log(
                "el usuario B01 conserva membresías ajenas; "
                "no se elimina"
            )


def _revisar(db: Session) -> None:
    empresa = _buscar_empresa(db)
    usuario = get_user_by_email(db, USUARIO_EMAIL)

    if empresa is None or usuario is None:
        _log("el conjunto B01 no existe")
        print(
            json.dumps(
                {
                    "existe": False,
                    "empresa": empresa.id if empresa else None,
                    "usuario": usuario.id if usuario else None,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    membresia = get_company_user_by_company_and_user(
        db,
        empresa.id,
        usuario.id,
    )
    if membresia is None:
        _abortar("la empresa y el usuario B01 existen sin membresía")

    resumen = _verificar_resultado(db, empresa, membresia)
    resumen["existe"] = True
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Conjunto de demostración B01 aislado",
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--check",
        action="store_true",
        help="solo verifica el conjunto B01 (por defecto)",
    )
    grupo.add_argument(
        "--apply",
        action="store_true",
        help="crea o reutiliza el conjunto B01",
    )
    grupo.add_argument(
        "--cleanup",
        action="store_true",
        help="elimina únicamente los registros del conjunto B01",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        _verificar_guardas(db)

        if args.cleanup:
            _limpiar(db)
        elif args.apply:
            _aplicar(db)
        else:
            _revisar(db)
    except SystemExit:
        raise
    except Exception as exc:
        db.rollback()
        _log(f"FALLO: {type(exc).__name__}: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
