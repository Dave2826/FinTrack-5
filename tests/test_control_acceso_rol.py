"""Pruebas de control de acceso segun el rol (Actividad 6).

Se ejecutan EXCLUSIVAMENTE contra la base fintrack5_test y la API de
pruebas: las guardas abortan si DB_NAME, DB_HOST, current_database(),
la revision de Alembic o la disponibilidad del endpoint no coinciden con
el entorno de pruebas. La base de desarrollo actividad5 nunca se usa.

Cubren el contrato autenticado con JWT (login, claims, vigencia de 30
minutos), el rechazo seguro (sin token, token alterado, vencido,
membresia inactiva, companyId cruzado, secreto ausente), la ausencia de
escrituras en los rechazos, la seleccion determinista de membresia
(D4), el contrato GraphQL sin actorCompanyUserId, la matriz de permisos
de la Actividad 5 sin cambios y los nueve casos funcionales de la
actividad.
"""

import json
import os
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt
from sqlalchemy import text

from database.connection import SessionLocal
from models.company_user import CompanyUser
from models.user import User
from repositories.company_user_repository import (
    get_active_company_user_by_user,
)
from repositories.user_repository import get_user_by_email
from scripts.setup_pruebas import CONTRASENA_PRUEBAS
from security import jwt as jwt_seguridad
from security.password import hash_password

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"
URL = "http://127.0.0.1:8000/graphql"

MATRIZ_OFICIAL = {
    "ADMINISTRADOR": {
        "company.users.read",
        "company.users.write",
        "accounts.read",
        "accounts.write",
        "concepts.read",
        "concepts.write",
        "transactions.read",
        "transactions.write",
        "roles.read",
        "roles.write",
    },
    "CONTADOR": {
        "company.users.read",
        "accounts.read",
        "accounts.write",
        "concepts.read",
        "concepts.write",
        "transactions.read",
        "transactions.write",
        "roles.read",
    },
    "CAPTURISTA": {
        "accounts.read",
        "concepts.read",
        "transactions.read",
        "transactions.write",
    },
    "CONSULTA": {
        "company.users.read",
        "accounts.read",
        "concepts.read",
        "transactions.read",
    },
}


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
         token: str | None = None,
         operation_name: str | None = None) -> dict:
    payload: dict = {"query": consulta}
    if variables is not None:
        payload["variables"] = variables
    if operation_name:
        payload["operationName"] = operation_name

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


def _conteo(db, tabla: str) -> int:
    return db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar()


def _matriz(db) -> dict[str, set[str]]:
    filas = db.execute(
        text(
            "SELECT r.code, p.code FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE rp.is_active ORDER BY r.code, p.code"
        )
    ).fetchall()
    matriz: dict[str, set[str]] = {}
    for rol, permiso in filas:
        matriz.setdefault(rol, set()).add(permiso)
    return matriz


def _membresia(db, email: str) -> int | None:
    return db.execute(
        text(
            "SELECT cu.id FROM company_users cu "
            "JOIN users u ON u.id = cu.user_id "
            "WHERE u.email = :email AND cu.is_active"
        ),
        {"email": email},
    ).scalar()


def _usuario(db, email: str) -> int | None:
    return db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).scalar()


def _firmar(claims: dict) -> str:
    return jwt.encode(
        claims,
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )


class ControlAccesoRolTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        cls.correos = {
            "ana": "ana@test.local",
            "luis": "luis@test.local",
            "maria": "maria@test.local",
            "jose": "jose@test.local",
            "pedro": "pedro@test.local",
            "admin_b": "admin_b@test.local",
            "sin_membresia": "sin_membresia_a@test.local",
            "inactivo": "inactivo_a@test.local",
        }

        cls.membresias = {
            clave: _membresia(cls.db, correo)
            for clave, correo in cls.correos.items()
        }

        cls.usuarios = {
            clave: _usuario(cls.db, correo)
            for clave, correo in cls.correos.items()
        }

        faltantes = [
            clave for clave, valor in cls.membresias.items()
            if valor is None and clave not in ("sin_membresia", "inactivo")
        ]
        if faltantes:
            raise SystemExit(
                "faltan usuarios de prueba "
                f"{faltantes}; ejecute setup_pruebas.py"
            )

        cls.empresa_alpha = cls.db.execute(
            text(
                "SELECT company_id FROM company_users WHERE id = :cu"
            ),
            {"cu": cls.membresias["ana"]},
        ).scalar()
        cls.empresa_beta = cls.db.execute(
            text(
                "SELECT company_id FROM company_users WHERE id = :cu"
            ),
            {"cu": cls.membresias["admin_b"]},
        ).scalar()

        cls.rol_capturista = cls.db.execute(
            text("SELECT id FROM roles WHERE code = 'CAPTURISTA'")
        ).scalar()
        cls.rol_consulta = cls.db.execute(
            text("SELECT id FROM roles WHERE code = 'CONSULTA'")
        ).scalar()

        cls.cuenta_alpha = cls.db.execute(
            text(
                "SELECT id FROM accounts WHERE company_id = :c "
                "AND is_active ORDER BY id LIMIT 1"
            ),
            {"c": cls.empresa_alpha},
        ).scalar()
        cls.concepto_alpha = cls.db.execute(
            text(
                "SELECT id FROM concepts WHERE company_id = :c "
                "AND concept_type = 'INCOME' AND is_active "
                "ORDER BY id LIMIT 1"
            ),
            {"c": cls.empresa_alpha},
        ).scalar()

        if cls.cuenta_alpha is None or cls.concepto_alpha is None:
            raise SystemExit(
                "faltan recursos de la empresa Alpha (cuenta o concepto)"
            )

        cls.tokens = {
            clave: _login(correo)
            for clave, correo in cls.correos.items()
            if cls.membresias.get(clave) is not None
        }

        cls.conteo_base = {
            tabla: _conteo(cls.db, tabla)
            for tabla in ("accounts", "transactions", "company_users")
        }

        cls.limpieza: dict[str, list[int]] = {
            "accounts": [],
            "transactions": [],
            "usuarios": [],
            "membresias": [],
        }
        cls.marca = datetime.now().strftime("%Y%m%d%H%M%S%f")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.rollback()

            if cls.limpieza["transactions"]:
                for transaccion_id in cls.limpieza["transactions"]:
                    cls.db.execute(
                        text("DELETE FROM transactions WHERE id = :i"),
                        {"i": transaccion_id},
                    )
            if cls.limpieza["accounts"]:
                for cuenta_id in cls.limpieza["accounts"]:
                    cls.db.execute(
                        text("DELETE FROM accounts WHERE id = :i"),
                        {"i": cuenta_id},
                    )
            if cls.limpieza["membresias"]:
                for membresia_id in cls.limpieza["membresias"]:
                    cls.db.execute(
                        text(
                            "DELETE FROM company_user_roles "
                            "WHERE company_user_id = :i"
                        ),
                        {"i": membresia_id},
                    )
                    cls.db.execute(
                        text("DELETE FROM company_users WHERE id = :i"),
                        {"i": membresia_id},
                    )
            if cls.limpieza["usuarios"]:
                for usuario_id in cls.limpieza["usuarios"]:
                    cls.db.execute(
                        text("DELETE FROM users WHERE id = :i"),
                        {"i": usuario_id},
                    )

            pedro = cls.membresias["pedro"]
            cls.db.execute(
                text(
                    "UPDATE company_user_roles SET is_active = false "
                    "WHERE company_user_id = :c"
                ),
                {"c": pedro},
            )
            cls.db.execute(
                text(
                    "UPDATE company_user_roles SET is_active = true "
                    "WHERE company_user_id = :c AND role_id = :r"
                ),
                {"c": pedro, "r": cls.rol_consulta},
            )
            cls.db.execute(
                text(
                    "UPDATE company_users SET is_active = true "
                    "WHERE id = :c"
                ),
                {"c": cls.membresias["jose"]},
            )
            cls.db.commit()
        finally:
            cls.db.close()

    # ------------------------------------------------------------ login

    def test_01_login_ok_devuelve_token_con_claims_y_30_minutos(self):
        datos = _gql(
            'mutation{login(input:{email:"%s",password:"%s"})'
            "{token tokenType user{id name email}}}"
            % (self.correos["ana"], CONTRASENA_PRUEBAS)
        )

        payload = (datos.get("data") or {}).get("login") or {}
        token = payload.get("token")
        self.assertTrue(token)
        self.assertEqual(payload.get("tokenType"), "bearer")

        usuario = payload.get("user") or {}
        self.assertEqual(usuario.get("name"), "Ana Pruebas Alpha")
        self.assertEqual(usuario.get("email"), self.correos["ana"])
        self.assertEqual(usuario.get("id"), self.usuarios["ana"])

        texto = json.dumps(datos)
        for prohibido in ("$argon2", "password_hash", CONTRASENA_PRUEBAS):
            self.assertNotIn(prohibido, texto)

        secreto = os.environ["JWT_SECRET"]

        claims = jwt.decode(
            token,
            secreto,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )

        self.assertEqual(
            set(claims.keys()),
            {"companyUserId", "companyId", "exp"},
        )
        self.assertEqual(
            claims["companyUserId"],
            self.membresias["ana"],
        )
        self.assertEqual(claims["companyId"], self.empresa_alpha)

        segundos = claims["exp"] - datetime.now(timezone.utc).timestamp()
        self.assertGreater(segundos, 29 * 60)
        self.assertLessEqual(segundos, 30 * 60)

        for prohibido in ("password", "role", "permission", "hash"):
            self.assertNotIn(prohibido, claims)

    def test_02_login_credenciales_invalidas_sin_token_ni_secretos(self):
        consulta = (
            'mutation{login(input:{email:"%s",password:"incorrecta"})'
            "{token tokenType user{name}}}"
        )

        datos = _gql(consulta % self.correos["ana"])
        self.assertIsNone(
            (datos.get("data") or {}).get("login")
        )
        self.assertIn("Credenciales", _error(datos))

        datos = _gql(consulta % "nadie@test.local")
        self.assertIsNone(
            (datos.get("data") or {}).get("login")
        )
        self.assertIn("Credenciales", _error(datos))

        texto = json.dumps(datos)
        for prohibido in ("token", "$argon2", "password_hash", CONTRASENA_PRUEBAS):
            self.assertNotIn(prohibido, texto)

    def test_03_login_sin_membresia_activa_rechaza(self):
        datos = _gql(
            'mutation{login(input:{email:"%s",password:"%s"})'
            "{token tokenType user{name}}}"
            % (self.correos["sin_membresia"], CONTRASENA_PRUEBAS)
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("login")
        )
        self.assertIn("membresía activa", _error(datos))
        self.assertNotIn(
            "token",
            json.dumps((datos.get("data") or {})),
        )

    def test_04_login_usuario_inactivo_rechaza(self):
        datos = _gql(
            'mutation{login(input:{email:"%s",password:"%s"})'
            "{token tokenType user{name}}}"
            % (self.correos["inactivo"], CONTRASENA_PRUEBAS)
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("login")
        )
        self.assertIn("inactivo", _error(datos))
        self.assertNotIn(
            "token",
            json.dumps((datos.get("data") or {})),
        )

    def test_05_membresia_multiple_elige_la_de_menor_id(self):
        email = f"multi_{self.marca}@test.local"
        usuario = get_user_by_email(self.db, email)
        if usuario is None:
            usuario = User(
                name="Usuario Multi Membresia",
                email=email,
                password_hash=hash_password(CONTRASENA_PRUEBAS),
                email_verified=True,
                is_active=True,
            )
            self.db.add(usuario)
            self.db.commit()
            self.db.refresh(usuario)
            self.limpieza["usuarios"].append(usuario.id)

        primera = CompanyUser(
            company_id=self.empresa_beta,
            user_id=usuario.id,
            is_active=True,
        )
        self.db.add(primera)
        self.db.commit()
        self.db.refresh(primera)
        self.limpieza["membresias"].append(primera.id)

        segunda = CompanyUser(
            company_id=self.empresa_alpha,
            user_id=usuario.id,
            is_active=True,
        )
        self.db.add(segunda)
        self.db.commit()
        self.db.refresh(segunda)
        self.limpieza["membresias"].append(segunda.id)

        seleccionada = get_active_company_user_by_user(
            self.db, usuario.id
        )
        self.assertIsNotNone(seleccionada)
        self.assertEqual(seleccionada.id, primera.id)
        self.assertLess(primera.id, segunda.id)

        token = _login(email)
        claims = jwt.decode(
            token,
            os.environ["JWT_SECRET"],
            algorithms=["HS256"],
        )
        self.assertEqual(claims["companyUserId"], primera.id)
        self.assertEqual(claims["companyId"], self.empresa_beta)

    # ------------------------------------------------- validaciones token

    def test_06_operacion_protegida_sin_token_rechazada_sin_escrituras(self):
        antes = _conteo(self.db, "accounts")
        datos = _gql(
            "mutation{createAccount(input:{companyId:%d,"
            "accountType:DEBIT,name:\"A6 sin token %s\"}){id}}"
            % (self.empresa_alpha, self.marca)
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("createAccount")
        )
        self.assertTrue(_error(datos))
        self.assertEqual(_conteo(self.db, "accounts"), antes)

    def test_07_token_alterado_rechazado_sin_escrituras(self):
        token = self.tokens["ana"]
        alterado = token[:-1] + ("a" if token[-1] != "a" else "b")

        antes = _conteo(self.db, "accounts")
        datos = _gql(
            "mutation{createAccount(input:{companyId:%d,"
            "accountType:DEBIT,name:\"A6 alterado %s\"}){id}}"
            % (self.empresa_alpha, self.marca),
            token=alterado,
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("createAccount")
        )
        self.assertTrue(_error(datos))
        self.assertEqual(_conteo(self.db, "accounts"), antes)

    def test_08_token_vencido_rechazado_sin_escrituras(self):
        vencido = _firmar({
            "companyUserId": self.membresias["ana"],
            "companyId": self.empresa_alpha,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        })

        antes = _conteo(self.db, "accounts")
        datos = _gql(
            "mutation{createAccount(input:{companyId:%d,"
            "accountType:DEBIT,name:\"A6 vencido %s\"}){id}}"
            % (self.empresa_alpha, self.marca),
            token=vencido,
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("createAccount")
        )
        self.assertTrue(_error(datos))
        self.assertEqual(_conteo(self.db, "accounts"), antes)

    def test_09_company_id_cruzado_rechazado(self):
        cruzado = _firmar({
            "companyUserId": self.membresias["ana"],
            "companyId": self.empresa_beta,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        })

        antes = _conteo(self.db, "accounts")
        datos = _gql(
            "{accounts(companyId:%d){id name}}" % self.empresa_alpha,
            token=cruzado,
        )
        self.assertIsNone((datos.get("data") or {}).get("accounts"))
        self.assertIn("no corresponde a la empresa", _error(datos))

        datos = _gql(
            "mutation{createAccount(input:{companyId:%d,"
            "accountType:DEBIT,name:\"A6 cruzado %s\"}){id}}"
            % (self.empresa_alpha, self.marca),
            token=cruzado,
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("createAccount")
        )
        self.assertEqual(_conteo(self.db, "accounts"), antes)

    def test_10_membresia_inactiva_rechaza_y_restaura(self):
        try:
            self.db.execute(
                text(
                    "UPDATE company_users SET is_active = false "
                    "WHERE id = :c"
                ),
                {"c": self.membresias["jose"]},
            )
            self.db.commit()

            datos = _gql(
                "{accounts(companyId:%d){id}}" % self.empresa_alpha,
                token=self.tokens["jose"],
            )
            self.assertIsNone((datos.get("data") or {}).get("accounts"))
            self.assertIn("membresía", _error(datos).lower())

            datos = _gql(
                'mutation{login(input:{email:"%s",password:"%s"})'
                "{token}}" % (self.correos["jose"], CONTRASENA_PRUEBAS)
            )
            self.assertIsNone((datos.get("data") or {}).get("login"))
            self.assertIn("membresía activa", _error(datos))
        finally:
            self.db.execute(
                text(
                    "UPDATE company_users SET is_active = true "
                    "WHERE id = :c"
                ),
                {"c": self.membresias["jose"]},
            )
            self.db.commit()

        token = _login(self.correos["jose"])
        self.assertTrue(token)

    def test_11_contrato_graphql_sin_actor_company_user_id(self):
        consulta = _gql(
            '{__type(name:"Query"){fields{name args{name}}}}',
            token=self.tokens["ana"],
        )
        mutacion = _gql(
            '{__type(name:"Mutation"){fields{name args{name}}}}',
            token=self.tokens["ana"],
        )
        tipos = _gql(
            "{__schema{types{kind name inputFields{name}}}}",
            token=self.tokens["ana"],
        )

        texto = json.dumps([consulta, mutacion, tipos])
        self.assertNotIn("actorCompanyUserId", texto)

        campos = {
            campo["name"]: sorted(a["name"] for a in campo["args"])
            for campo in (
                (consulta.get("data") or {})
                .get("__type", {}).get("fields", [])
            )
        }
        self.assertEqual(
            campos.get("accounts"),
            ["accountType", "activeOnly", "companyId"],
        )
        self.assertEqual(campos.get("permissionCatalog"), ["resource"])

        mutaciones = {
            campo["name"]: sorted(a["name"] for a in campo["args"])
            for campo in (
                (mutacion.get("data") or {})
                .get("__type", {}).get("fields", [])
            )
        }
        self.assertIn("login", mutaciones)
        self.assertEqual(mutaciones.get("setRolePermissions"), ["input"])

    def test_12_permisos_actividad5_sin_cambios(self):
        self.assertEqual(_matriz(self.db), MATRIZ_OFICIAL)

        filas = self.db.execute(
            text(
                "SELECT r.code, count(*) FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id "
                "WHERE rp.is_active GROUP BY r.code"
            )
        ).fetchall()
        conteos = {rol: total for rol, total in filas}
        self.assertEqual(
            conteos,
            {
                "ADMINISTRADOR": 10,
                "CONTADOR": 8,
                "CAPTURISTA": 4,
                "CONSULTA": 4,
            },
        )

    def test_13_ausencia_de_jwt_secret_falla_seguro(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("JWT_SECRET", None)
            with self.assertRaises(RuntimeError):
                jwt_seguridad.create_access_token(1, 1)
            with self.assertRaises(RuntimeError):
                jwt_seguridad.decode_access_token("token.cualquiera")

    # ------------------------------------------------- casos funcionales

    def test_14_maria_capturista_transaccion_valida(self):
        datos = _gql(
            "mutation{createTransaction(input:{accountId:%d,"
            "conceptId:%d,transactionType:INCOME,amount:15.5,"
            "shortDescription:\"A6 Maria %s\"})"
            "{id accountId capturedBy amount}}"
            % (self.cuenta_alpha, self.concepto_alpha, self.marca),
            token=self.tokens["maria"],
        )
        creada = (datos.get("data") or {}).get("createTransaction")
        self.assertIsNotNone(creada, _error(datos))
        self.limpieza["transactions"].append(creada["id"])

        capturador = self.db.execute(
            text("SELECT captured_by FROM transactions WHERE id = :i"),
            {"i": creada["id"]},
        ).scalar()
        usuario_maria = self.db.execute(
            text(
                "SELECT user_id FROM company_users WHERE id = :c"
            ),
            {"c": self.membresias["maria"]},
        ).scalar()
        self.assertEqual(capturador, usuario_maria)

    def test_15_maria_capturista_cuenta_denegada_sin_escrituras(self):
        antes = _conteo(self.db, "accounts")
        datos = _gql(
            "mutation{createAccount(input:{companyId:%d,"
            "accountType:DEBIT,name:\"A6 Maria cuenta %s\"}){id}}"
            % (self.empresa_alpha, self.marca),
            token=self.tokens["maria"],
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("createAccount")
        )
        self.assertIn("accounts.write", _error(datos))
        self.assertEqual(_conteo(self.db, "accounts"), antes)

    def test_16_luis_contador_cuenta_permitida(self):
        datos = _gql(
            "mutation{createAccount(input:{companyId:%d,"
            "accountType:DEBIT,name:\"A6 Luis cuenta %s\"})"
            "{id companyId name}}"
            % (self.empresa_alpha, self.marca),
            token=self.tokens["luis"],
        )
        creada = (datos.get("data") or {}).get("createAccount")
        self.assertIsNotNone(creada, _error(datos))
        self.limpieza["accounts"].append(creada["id"])
        self.assertEqual(creada["companyId"], self.empresa_alpha)

    def test_17_pedro_consulta_transaccion_denegada_sin_escrituras(self):
        antes = _conteo(self.db, "transactions")
        datos = _gql(
            "mutation{createTransaction(input:{accountId:%d,"
            "conceptId:%d,transactionType:INCOME,amount:10,"
            "shortDescription:\"A6 Pedro denegado %s\"}){id}}"
            % (self.cuenta_alpha, self.concepto_alpha, self.marca),
            token=self.tokens["pedro"],
        )
        self.assertIsNone(
            (datos.get("data") or {}).get("createTransaction")
        )
        self.assertIn("transactions.write", _error(datos))
        self.assertEqual(_conteo(self.db, "transactions"), antes)

    def test_18_cambio_de_rol_afecta_token_previo(self):
        token_previo = _login(self.correos["pedro"])

        datos = _gql(
            "mutation{assignRole(input:{companyUserId:%d,roleId:%d})"
            "{id companyUserId roleId isActive}}"
            % (self.membresias["pedro"], self.rol_capturista),
            token=self.tokens["ana"],
        )
        rotado = (datos.get("data") or {}).get("assignRole")
        self.assertIsNotNone(rotado, _error(datos))
        self.assertEqual(rotado["roleId"], self.rol_capturista)

        rol_activo = self.db.execute(
            text(
                "SELECT role_id FROM company_user_roles "
                "WHERE company_user_id = :c AND is_active"
            ),
            {"c": self.membresias["pedro"]},
        ).scalar()
        self.assertEqual(rol_activo, self.rol_capturista)

        datos = _gql(
            "mutation{createTransaction(input:{accountId:%d,"
            "conceptId:%d,transactionType:INCOME,amount:22.5,"
            "shortDescription:\"A6 Pedro capturista %s\"})"
            "{id}}"
            % (self.cuenta_alpha, self.concepto_alpha, self.marca),
            token=token_previo,
        )
        creada = (datos.get("data") or {}).get("createTransaction")
        self.assertIsNotNone(creada, _error(datos))
        self.limpieza["transactions"].append(creada["id"])

    def test_19_token_de_otra_empresa_no_consulta(self):
        datos = _gql(
            "{accounts(companyId:%d){id name}}" % self.empresa_alpha,
            token=self.tokens["admin_b"],
        )
        self.assertIsNone((datos.get("data") or {}).get("accounts"))
        self.assertIn("no pertenece a la empresa", _error(datos))

    def test_20_resumen_final_sin_secretos(self):
        texto = json.dumps(self.conteo_base)
        self.assertNotIn("JWT_SECRET", texto)
        self.assertNotIn(os.environ["JWT_SECRET"], texto)
