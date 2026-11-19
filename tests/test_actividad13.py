"""Pruebas de la Unidad III, Actividad 13 (idempotencia y administración).

Se ejecutan EXCLUSIVAMENTE contra la base fintrack5_test y la API de
pruebas (mismas guardas que las suites anteriores). Cada ejecución crea su
propia empresa ficticia "A13 Pruebas <sufijo>" y la elimina al terminar, de
modo que no toca los datos de Alpha/Beta ni los de B01.

Cubren:
- createTransaction idempotente: misma llave -> mismo id y una sola fila;
  otra llave -> otro movimiento; misma llave con otros datos -> rechazo;
  envíos concurrentes con la misma llave -> una sola fila; la llave y el
  movimiento se confirman juntos (un rechazo no deja llave huérfana).
- me: empresa, rol y permisos efectivos de la sesión.
- companyUsers con nombre, correo y rol, sin exponer la contraseña.
- createCompanyUser con nombre/correo/contraseña, correo duplicado,
  segundo administrador, baja lógica y permisos de escritura.
- accountConcepts con el concepto anidado, duplicado y quitar.
"""

import json
import os
import threading
import unittest
import urllib.error
import urllib.request
import uuid

from sqlalchemy import text

from database.connection import SessionLocal
from models.company import Company
from models.role import Role
from models.user import User
from repositories.company_user_role_repository import create_company_user_role
from models.company_user import CompanyUser
from models.company_user_role import CompanyUserRole
from security.password import hash_password

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "4d2a7c9e1b30"
URL = "http://127.0.0.1:8000/graphql"
CONTRASENA = "A13-pruebas-ficticias-2026!"


def _verificar_guardas() -> None:
    if os.getenv("DB_NAME") != DB_ESPERADA:
        raise SystemExit(f"DB_NAME no es {DB_ESPERADA}; prueba abortada")
    if os.getenv("DB_HOST") != HOST_ESPERADO:
        raise SystemExit(f"DB_HOST no es {HOST_ESPERADO}; prueba abortada")

    db = SessionLocal()
    try:
        if db.execute(text("SELECT current_database()")).scalar() != DB_ESPERADA:
            raise SystemExit("current_database() inesperada; prueba abortada")
        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        if revision != ALEMBIC_ESPERADO:
            raise SystemExit(
                f"alembic_version no es {ALEMBIC_ESPERADO}; prueba abortada"
            )
    finally:
        db.close()

    try:
        _gql("{__typename}")
    except Exception as exc:
        raise SystemExit(f"la API de pruebas no responde en {URL}: {exc}")


def _gql(consulta: str, variables: dict | None = None,
         token: str | None = None) -> dict:
    payload: dict = {"query": consulta}
    if variables is not None:
        payload["variables"] = variables
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        URL, data=json.dumps(payload).encode(), headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as respuesta:
            return json.loads(respuesta.read().decode())
    except urllib.error.HTTPError as error:
        return {"http_error": error.code, "body": error.read().decode()}


def _error(datos: dict) -> str:
    errores = datos.get("errors") or []
    return errores[0].get("message", "") if errores else ""


def _login(email: str, password: str = CONTRASENA) -> str:
    datos = _gql(
        "mutation($i:LoginInput!){login(input:$i){token}}",
        {"i": {"email": email, "password": password}},
    )
    token = ((datos.get("data") or {}).get("login") or {}).get("token")
    if not token:
        raise AssertionError(f"login fallido para {email}: {datos}")
    return token


CREATE_TX = """
mutation($input: CreateTransactionInput!) {
  createTransaction(input: $input) { id amount transactionType }
}
"""

CREATE_CU = """
mutation($input: CreateCompanyUserInput!) {
  createCompanyUser(input: $input) {
    id isAdmin isActive user { id name email } role { code }
  }
}
"""

COMPANY_USERS = """
query($c: Int!, $a: Boolean!) {
  companyUsers(companyId: $c, activeOnly: $a) {
    id isAdmin isActive user { name email } role { code name }
  }
}
"""


class Actividad13Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _verificar_guardas()

        cls.sufijo = uuid.uuid4().hex[:8]
        cls.db = SessionLocal()
        db = cls.db

        roles = {
            r.code: r for r in db.query(Role).filter(Role.is_active).all()
        }
        for requerido in ("ADMINISTRADOR", "CAPTURISTA", "CONSULTA"):
            if requerido not in roles:
                raise SystemExit(
                    f"falta el rol {requerido}; ejecute setup_pruebas.py"
                )

        empresa = Company(
            name=f"A13 Pruebas {cls.sufijo}",
            legal_name=f"A13 Pruebas {cls.sufijo}",
            tax_id=f"A13-{cls.sufijo}",
            email=f"a13_{cls.sufijo}@test.local",
            is_active=True,
        )
        db.add(empresa)
        db.commit()
        cls.empresa = empresa.id
        cls.usuarios_creados: list[int] = []

        cls.correos = {}
        cls.membresias = {}
        for clave, rol, es_admin in (
            ("admin", "ADMINISTRADOR", True),
            ("capturista", "CAPTURISTA", False),
            ("consulta", "CONSULTA", False),
        ):
            correo = f"a13_{clave}_{cls.sufijo}@test.local"
            usuario = User(
                name=f"A13 {clave.capitalize()}",
                email=correo,
                password_hash=hash_password(CONTRASENA),
                email_verified=False,
                is_active=True,
            )
            db.add(usuario)
            db.flush()
            cls.usuarios_creados.append(usuario.id)
            membresia = CompanyUser(
                company_id=cls.empresa,
                user_id=usuario.id,
                is_admin=es_admin,
                is_active=True,
            )
            db.add(membresia)
            db.flush()
            create_company_user_role(
                db,
                CompanyUserRole(
                    company_user_id=membresia.id,
                    role_id=roles[rol].id,
                    is_active=True,
                ),
            )
            cls.correos[clave] = correo
            cls.membresias[clave] = membresia.id

        cls.tokens = {clave: _login(c) for clave, c in cls.correos.items()}
        admin = cls.tokens["admin"]

        cuenta = _gql(
            "mutation($i:CreateAccountInput!){createAccount(input:$i){id}}",
            {"i": {"companyId": cls.empresa, "accountType": "CASH",
                   "name": "Caja A13"}},
            admin,
        )
        cls.cuenta = cuenta["data"]["createAccount"]["id"]
        concepto = _gql(
            "mutation($i:CreateConceptInput!){createConcept(input:$i){id}}",
            {"i": {"companyId": cls.empresa, "conceptType": "EXPENSE",
                   "name": "Renta A13"}},
            admin,
        )
        cls.concepto = concepto["data"]["createConcept"]["id"]
        asignacion = _gql(
            "mutation($i:AssignConceptToAccountInput!)"
            "{assignConceptToAccount(input:$i){id}}",
            {"i": {"accountId": cls.cuenta, "conceptId": cls.concepto}},
            admin,
        )
        assert "errors" not in asignacion, asignacion

    @classmethod
    def tearDownClass(cls):
        db = cls.db
        db.rollback()
        c = {"c": cls.empresa}
        ids_usuarios = db.execute(
            text("SELECT user_id FROM company_users WHERE company_id = :c"), c
        ).scalars().all()
        sentencias = [
            "DELETE FROM idempotency_keys WHERE company_id = :c",
            "DELETE FROM transactions WHERE account_id IN "
            "(SELECT id FROM accounts WHERE company_id = :c)",
            "DELETE FROM account_concepts WHERE account_id IN "
            "(SELECT id FROM accounts WHERE company_id = :c)",
            "DELETE FROM accounts WHERE company_id = :c",
            "DELETE FROM concepts WHERE company_id = :c",
            "DELETE FROM company_user_roles WHERE company_user_id IN "
            "(SELECT id FROM company_users WHERE company_id = :c)",
            "DELETE FROM company_users WHERE company_id = :c",
            "DELETE FROM companies WHERE id = :c",
        ]
        for sentencia in sentencias:
            db.execute(text(sentencia), c)
        for user_id in set(ids_usuarios) | set(cls.usuarios_creados):
            db.execute(text("DELETE FROM users WHERE id = :i"), {"i": user_id})
        db.commit()
        db.close()

    # ---------- utilidades ----------

    def _tx(self, monto="100.00", llave=None, token=None, **extra):
        entrada = {
            "accountId": self.cuenta,
            "conceptId": self.concepto,
            "transactionType": "EXPENSE",
            "amount": monto,
            "shortDescription": "Renta A13",
        }
        if llave is not None:
            entrada["idempotencyKey"] = llave
        entrada.update(extra)
        return _gql(CREATE_TX, {"input": entrada},
                    token or self.tokens["admin"])

    def _filas_movimiento(self) -> int:
        self.db.rollback()
        return self.db.execute(
            text("SELECT count(*) FROM transactions WHERE account_id = :a"),
            {"a": self.cuenta},
        ).scalar()

    def _filas_llave(self, llave: str) -> int:
        self.db.rollback()
        return self.db.execute(
            text(
                "SELECT count(*) FROM idempotency_keys "
                "WHERE company_id = :c AND idempotency_key = :k"
            ),
            {"c": self.empresa, "k": llave},
        ).scalar()

    # ---------- Parte 1: idempotencia ----------

    def test_01_misma_llave_devuelve_el_mismo_movimiento(self):
        llave = str(uuid.uuid4())
        antes = self._filas_movimiento()

        primero = self._tx(llave=llave)
        segundo = self._tx(llave=llave)

        self.assertNotIn("errors", primero, primero)
        self.assertNotIn("errors", segundo, segundo)
        self.assertEqual(
            primero["data"]["createTransaction"]["id"],
            segundo["data"]["createTransaction"]["id"],
        )
        self.assertEqual(self._filas_movimiento(), antes + 1)
        self.assertEqual(self._filas_llave(llave), 1)

    def test_02_otra_llave_crea_otro_movimiento_aunque_el_monto_coincida(self):
        antes = self._filas_movimiento()
        uno = self._tx(llave=str(uuid.uuid4()))
        dos = self._tx(llave=str(uuid.uuid4()))
        self.assertNotEqual(
            uno["data"]["createTransaction"]["id"],
            dos["data"]["createTransaction"]["id"],
        )
        self.assertEqual(self._filas_movimiento(), antes + 2)

    def test_03_misma_llave_con_otros_datos_se_rechaza(self):
        llave = str(uuid.uuid4())
        self._tx(monto="100.00", llave=llave)
        antes = self._filas_movimiento()

        otro = self._tx(monto="250.00", llave=llave)

        self.assertIn("ya se usó con otros datos", _error(otro))
        self.assertEqual(self._filas_movimiento(), antes)
        self.assertEqual(self._filas_llave(llave), 1)

    def test_04_sin_llave_conserva_el_comportamiento_previo(self):
        antes = self._filas_movimiento()
        self._tx()
        self._tx()
        self.assertEqual(self._filas_movimiento(), antes + 2)

    def test_05_envios_concurrentes_con_la_misma_llave(self):
        llave = str(uuid.uuid4())
        antes = self._filas_movimiento()
        resultados: list[dict] = []

        def enviar():
            resultados.append(self._tx(llave=llave))

        hilos = [threading.Thread(target=enviar) for _ in range(6)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        ids = {
            r["data"]["createTransaction"]["id"]
            for r in resultados
            if r.get("data") and r["data"].get("createTransaction")
        }
        self.assertEqual(len(ids), 1, resultados)
        self.assertEqual(self._filas_movimiento(), antes + 1)
        self.assertEqual(self._filas_llave(llave), 1)

    def test_06_rechazo_no_deja_llave_ni_movimiento(self):
        llave = str(uuid.uuid4())
        antes = self._filas_movimiento()

        sin_permiso = self._tx(llave=llave, token=self.tokens["consulta"])
        self.assertIn("transactions.write", _error(sin_permiso))

        invalido = self._tx(monto="-5.00", llave=llave)
        self.assertTrue(_error(invalido))

        self.assertEqual(self._filas_movimiento(), antes)
        self.assertEqual(self._filas_llave(llave), 0)

        # Tras los rechazos, la llave sigue libre para el envío correcto.
        valido = self._tx(llave=llave)
        self.assertNotIn("errors", valido, valido)
        self.assertEqual(self._filas_llave(llave), 1)

    def test_07_llave_vacia_se_rechaza(self):
        antes = self._filas_movimiento()
        respuesta = self._tx(llave="   ")
        self.assertIn("no puede estar vacía", _error(respuesta))
        self.assertEqual(self._filas_movimiento(), antes)

    # ---------- Parte 2: sesión ----------

    def test_10_me_devuelve_empresa_rol_y_permisos(self):
        consulta = "{me{companyUserId isAdmin company{id name} " \
                   "user{email} role{code} permissions}}"
        admin = _gql(consulta, token=self.tokens["admin"])["data"]["me"]
        self.assertEqual(admin["company"]["id"], self.empresa)
        self.assertEqual(admin["role"]["code"], "ADMINISTRADOR")
        self.assertTrue(admin["isAdmin"])
        self.assertIn("company.users.write", admin["permissions"])

        consulta_rol = _gql(consulta, token=self.tokens["consulta"])
        datos = consulta_rol["data"]["me"]
        self.assertEqual(datos["role"]["code"], "CONSULTA")
        self.assertNotIn("company.users.write", datos["permissions"])
        self.assertNotIn("accounts.write", datos["permissions"])
        self.assertIn("company.users.read", datos["permissions"])

        sin_token = _gql(consulta)
        self.assertIn("no autenticado", _error(sin_token).lower())

    def test_11_el_esquema_no_expone_contrasenas(self):
        datos = _gql(
            '{a:__type(name:"CompanyUser"){fields{name}} '
            'b:__type(name:"User"){fields{name}} '
            'c:__type(name:"SessionInfo"){fields{name}}}'
        )["data"]
        for tipo in datos.values():
            nombres = {f["name"].lower() for f in tipo["fields"]}
            self.assertFalse(
                any("password" in n or "hash" in n for n in nombres),
                nombres,
            )

    # ---------- Parte 2: usuarios ----------

    def test_20_company_users_trae_nombre_correo_y_rol(self):
        datos = _gql(
            COMPANY_USERS, {"c": self.empresa, "a": False},
            self.tokens["consulta"],
        )
        self.assertNotIn("errors", datos, datos)
        filas = {f["user"]["email"]: f for f in datos["data"]["companyUsers"]}
        admin = filas[self.correos["admin"]]
        self.assertTrue(admin["isAdmin"])
        self.assertEqual(admin["role"]["code"], "ADMINISTRADOR")
        self.assertEqual(
            filas[self.correos["capturista"]]["role"]["code"], "CAPTURISTA"
        )

    def test_21_alta_baja_y_errores_de_usuario(self):
        correo = f"a13_nuevo_{self.sufijo}@test.local"
        entrada = {
            "companyId": self.empresa,
            "name": "Persona Nueva A13",
            "email": correo,
            "password": "Clave-nueva-A13",
        }

        alta = _gql(CREATE_CU, {"input": entrada}, self.tokens["admin"])
        self.assertNotIn("errors", alta, alta)
        nuevo = alta["data"]["createCompanyUser"]
        self.assertEqual(nuevo["user"]["email"], correo)
        self.assertFalse(nuevo["isAdmin"])
        self.assertIsNone(nuevo["role"])
        self.assertNotIn("password", json.dumps(alta).lower())

        self.db.rollback()
        hash_guardado = self.db.execute(
            text("SELECT password_hash FROM users WHERE email = :e"),
            {"e": correo},
        ).scalar()
        self.assertTrue(hash_guardado)
        self.assertNotEqual(hash_guardado, "Clave-nueva-A13")

        # La persona puede iniciar sesión con la contraseña del formulario.
        _login(correo, "Clave-nueva-A13")

        duplicado = _gql(
            CREATE_CU,
            {"input": {**entrada, "email": correo.upper()}},
            self.tokens["admin"],
        )
        self.assertIn("Ya existe un usuario con ese correo", _error(duplicado))

        segundo_admin = _gql(
            CREATE_CU,
            {"input": {**entrada, "email": f"a13_adm2_{self.sufijo}@test.local",
                       "isAdmin": True}},
            self.tokens["admin"],
        )
        self.assertIn("administrador principal", _error(segundo_admin))

        corta = _gql(
            CREATE_CU,
            {"input": {**entrada, "email": f"a13_c_{self.sufijo}@test.local",
                       "password": "123"}},
            self.tokens["admin"],
        )
        self.assertIn("al menos", _error(corta))

        baja = _gql(
            "mutation($id:Int!){deactivateCompanyUser(companyUserId:$id)"
            "{id isActive}}",
            {"id": nuevo["id"]},
            self.tokens["admin"],
        )
        self.assertFalse(baja["data"]["deactivateCompanyUser"]["isActive"])

        todas = _gql(
            COMPANY_USERS, {"c": self.empresa, "a": False},
            self.tokens["admin"],
        )["data"]["companyUsers"]
        fila = next(f for f in todas if f["id"] == nuevo["id"])
        self.assertFalse(fila["isActive"])

        activas = _gql(
            COMPANY_USERS, {"c": self.empresa, "a": True},
            self.tokens["admin"],
        )["data"]["companyUsers"]
        self.assertNotIn(nuevo["id"], {f["id"] for f in activas})

    def test_22_sin_permiso_de_escritura_no_da_de_alta(self):
        for clave in ("consulta", "capturista"):
            respuesta = _gql(
                CREATE_CU,
                {"input": {
                    "companyId": self.empresa,
                    "name": "No debe existir",
                    "email": f"a13_no_{clave}_{self.sufijo}@test.local",
                    "password": "Clave-no-valida-1",
                }},
                self.tokens[clave],
            )
            self.assertIn("company.users.write", _error(respuesta))
        self.db.rollback()
        self.assertEqual(
            self.db.execute(
                text("SELECT count(*) FROM users WHERE email LIKE :p"),
                {"p": f"a13_no_%_{self.sufijo}@test.local"},
            ).scalar(),
            0,
        )

    def test_23_user_id_y_credenciales_juntos_se_rechazan(self):
        respuesta = _gql(
            CREATE_CU,
            {"input": {"companyId": self.empresa, "userId": 1,
                       "email": "x@test.local"}},
            self.tokens["admin"],
        )
        self.assertIn("no ambos", _error(respuesta))

    # ---------- Parte 2: conceptos por cuenta ----------

    def test_30_account_concepts_con_concepto_anidado(self):
        admin = self.tokens["admin"]
        concepto = _gql(
            "mutation($i:CreateConceptInput!){createConcept(input:$i){id}}",
            {"i": {"companyId": self.empresa, "conceptType": "EXPENSE",
                   "name": "Papelería A13"}},
            admin,
        )["data"]["createConcept"]["id"]
        asignar = (
            "mutation($i:AssignConceptToAccountInput!)"
            "{assignConceptToAccount(input:$i){id isActive}}"
        )
        variables = {"i": {"accountId": self.cuenta, "conceptId": concepto}}

        self.assertNotIn("errors", _gql(asignar, variables, admin))
        duplicado = _gql(asignar, variables, admin)
        self.assertIn("ya está asignado", _error(duplicado))

        lista = _gql(
            "query($a:Int!){accountConcepts(accountId:$a)"
            "{id isActive concept{id name conceptType}}}",
            {"a": self.cuenta},
            self.tokens["consulta"],
        )["data"]["accountConcepts"]
        nombres = {r["concept"]["name"] for r in lista}
        self.assertIn("Papelería A13", nombres)

        quitar = _gql(
            "mutation($a:Int!,$c:Int!){removeConceptFromAccount"
            "(accountId:$a,conceptId:$c){isActive}}",
            {"a": self.cuenta, "c": concepto},
            admin,
        )
        self.assertFalse(quitar["data"]["removeConceptFromAccount"]["isActive"])

        catalogo = _gql(
            "query($c:Int!){concepts(companyId:$c){id}}",
            {"c": self.empresa},
            admin,
        )["data"]["concepts"]
        self.assertIn(concepto, {c["id"] for c in catalogo})


if __name__ == "__main__":
    unittest.main()
