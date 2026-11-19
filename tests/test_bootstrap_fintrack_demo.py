"""Pruebas del bootstrap de las cuatro cuentas de FinTrack Demo.

Solo contra fintrack5_test. Se crea una empresa ficticia con un nombre
único que reproduce el estado de partida del equipo (David histórico como
administrador principal con movimientos, Luis con otro rol, Alexander y la
nueva cuenta de David inexistentes) y se ejecuta el script en sus tres
modos. Al final se elimina todo lo creado.
"""

import io
import os
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from unittest import mock

from sqlalchemy import text

from database.connection import SessionLocal
from models.account import Account, AccountType
from models.account_concept import AccountConcept
from models.company import Company
from models.company_user import CompanyUser
from models.company_user_role import CompanyUserRole
from models.concept import Concept, ConceptType
from models.role import Role
from models.transaction import Transaction, TransactionType
from models.user import User
from scripts import bootstrap_fintrack_demo as bootstrap
from security.password import hash_password, verify_password

DB_ESPERADA = "fintrack5_test"


def _ejecutar(*argumentos: str, entorno: dict | None = None) -> tuple[int, str, str]:
    salida, errores = io.StringIO(), io.StringIO()
    with mock.patch.dict(os.environ, entorno or {}), \
            mock.patch("sys.stdin.isatty", return_value=False), \
            redirect_stdout(salida), redirect_stderr(errores):
        codigo = bootstrap.main(list(argumentos))
    return codigo, salida.getvalue(), errores.getvalue()


class BootstrapFinTrackDemoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.getenv("DB_NAME") != DB_ESPERADA:
            raise SystemExit(f"DB_NAME no es {DB_ESPERADA}; prueba abortada")

        cls.db = SessionLocal()
        db = cls.db
        cls.empresa_id = None
        cls.nombre = f"FinTrack Demo prueba {uuid.uuid4().hex[:8]}"
        cls.correos_previos = [
            c.correo for c in bootstrap.CUENTAS
        ]
        for correo in cls.correos_previos:
            if db.query(User).filter(User.email == correo).first():
                # Las cuentas reales ya viven en esta base (por ejemplo,
                # FinTrack Demo está en fintrack5_test). La prueba no las
                # toca: se omite y el resto de las suites sigue corriendo.
                db.close()
                raise unittest.SkipTest(
                    f"{correo} ya existe en fintrack5_test; se omite para no "
                    "tocar las cuentas reales (use --verificar del script)"
                )

        roles = {r.code: r for r in db.query(Role).all()}

        empresa = Company(name=cls.nombre, legal_name=cls.nombre,
                          tax_id=f"FTD-{uuid.uuid4().hex[:8]}", is_active=True)
        db.add(empresa)
        db.flush()
        cls.empresa_id = empresa.id

        def persona(nombre, correo, rol, es_admin):
            usuario = User(name=nombre, email=correo,
                           password_hash=hash_password("Historica-2026!"),
                           email_verified=False, is_active=True)
            db.add(usuario)
            db.flush()
            membresia = CompanyUser(company_id=empresa.id, user_id=usuario.id,
                                    is_admin=es_admin, is_active=True)
            db.add(membresia)
            db.flush()
            db.add(CompanyUserRole(company_user_id=membresia.id,
                                   role_id=roles[rol].id, is_active=True))
            db.flush()
            return usuario, membresia

        historico, cls.membresia_historica = persona(
            "David Morales", "david.demo@fintrack.local", "ADMINISTRADOR", True,
        )
        cls.hash_historico = historico.password_hash
        persona("Edwuard Chay", "luis.chay@tecdesoftware.edu.mx",
                "CAPTURISTA", False)
        cls.membresia_historica_id = cls.membresia_historica.id

        cuenta = Account(company_id=empresa.id, account_type=AccountType.CASH,
                         name="Caja demo", is_active=True)
        concepto = Concept(company_id=empresa.id,
                           concept_type=ConceptType.INCOME,
                           name="Ventas demo", is_active=True)
        db.add_all([cuenta, concepto])
        db.flush()
        db.add(AccountConcept(account_id=cuenta.id, concept_id=concepto.id,
                              is_active=True))
        db.add(Transaction(account_id=cuenta.id, concept_id=concepto.id,
                           transaction_type=TransactionType.INCOME,
                           amount=Decimal("1500.00"),
                           captured_by=historico.id, is_active=True))
        db.commit()

        cls.huella = bootstrap.huella_financiera(db, empresa.id)
        cls.entorno = {
            "BOOTSTRAP_PASSWORD_ALEXANDER": "Alexander-demo-2026",
            "BOOTSTRAP_PASSWORD_DAVID": "David-admin-2026",
        }

    @classmethod
    def tearDownClass(cls):
        if cls.empresa_id is None:
            return
        db = cls.db
        db.rollback()
        c = {"c": cls.empresa_id}
        usuarios = db.execute(text(
            "SELECT user_id FROM company_users WHERE company_id = :c"), c
        ).scalars().all()
        for sentencia in (
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
        ):
            db.execute(text(sentencia), c)
        for user_id in usuarios:
            db.execute(text("DELETE FROM users WHERE id = :i"), {"i": user_id})
        db.commit()
        db.close()

    def test_1_plan_es_de_solo_lectura(self):
        codigo, salida, _ = _ejecutar("--empresa", self.nombre)
        self.assertEqual(codigo, 0)
        self.assertIn("crear usuario alexander.rodriguez", salida)
        self.assertIn("CAPTURISTA'] -> [CONSULTA]", salida)
        self.assertIn("isAdmin True -> False", salida)
        self.db.rollback()
        self.assertIsNone(bootstrap._usuario(self.db, "david.morales@tecdesoftware.edu.mx"))

        codigo, _, errores = _ejecutar("--empresa", self.nombre, "--verificar")
        self.assertEqual(codigo, 1)

    def test_2_sin_contrasenas_aborta_sin_cambios(self):
        codigo, _, errores = _ejecutar("--empresa", self.nombre, "--aplicar")
        self.assertEqual(codigo, 2)
        self.assertIn("BOOTSTRAP_PASSWORD_ALEXANDER", errores)
        self.db.rollback()
        self.assertIsNone(bootstrap._usuario(self.db, "alexander.rodriguez@tecdesoftware.edu.mx"))
        self.assertTrue(
            self.db.get(CompanyUser, self.membresia_historica_id).is_admin
        )

    def test_2b_fallo_a_mitad_hace_rollback_completo(self):
        original = bootstrap._fijar_rol
        llamadas = {"n": 0}

        def fallar_en_la_tercera(db, membresia, rol):
            llamadas["n"] += 1
            if llamadas["n"] == 3:
                raise RuntimeError("fallo simulado")
            return original(db, membresia, rol)

        with mock.patch.object(bootstrap, "_fijar_rol", fallar_en_la_tercera):
            codigo, _, errores = _ejecutar(
                "--empresa", self.nombre, "--aplicar", entorno=self.entorno,
            )
        self.assertEqual(codigo, 1)
        self.assertIn("ROLLBACK", errores)
        self.db.rollback()
        # Nada quedó a medias: ni usuarios nuevos ni el cambio de admin.
        self.assertIsNone(bootstrap._usuario(self.db, "alexander.rodriguez@tecdesoftware.edu.mx"))
        self.assertTrue(
            self.db.get(CompanyUser, self.membresia_historica_id).is_admin
        )
        self.assertEqual(
            bootstrap.huella_financiera(self.db, self.empresa_id), self.huella
        )

    def test_3_aplicar_y_verificar(self):
        codigo, salida, errores = _ejecutar(
            "--empresa", self.nombre, "--aplicar", entorno=self.entorno,
        )
        self.assertEqual(codigo, 0, errores + salida)
        self.assertNotIn("Alexander-demo-2026", salida + errores)
        self.assertNotIn("David-admin-2026", salida + errores)

        db = self.db
        db.rollback()
        empresa = db.get(Company, self.empresa_id)
        self.assertEqual(bootstrap.verificar(db, empresa, self.membresia_historica_id), [])
        self.assertEqual(bootstrap.huella_financiera(db, self.empresa_id), self.huella)

        historica = db.get(CompanyUser, self.membresia_historica_id)
        self.assertTrue(historica.is_active)
        self.assertFalse(historica.is_admin)
        self.assertEqual(
            db.get(User, historica.user_id).password_hash, self.hash_historico
        )

        nuevo = bootstrap._usuario(db, "david.morales@tecdesoftware.edu.mx")
        self.assertTrue(verify_password("David-admin-2026", nuevo.password_hash))

        codigo, _, _ = _ejecutar("--empresa", self.nombre, "--verificar")
        self.assertEqual(codigo, 0)

        # Repetir --aplicar no cambia nada.
        codigo, _, errores = _ejecutar("--empresa", self.nombre, "--aplicar")
        self.assertEqual(codigo, 0)
        self.assertIn("ya está aplicada", errores)


if __name__ == "__main__":
    unittest.main()
