"""Pruebas automatizadas de configuración de permisos por rol (Actividad 5).

Se ejecutan EXCLUSIVAMENTE contra la base fintrack5_test: las guardas
abortan la ejecución si DB_NAME, DB_HOST, current_database() o la
revisión de Alembic no coinciden con el entorno de pruebas. La base de
desarrollo actividad5 nunca se utiliza.

Cubren: catálogo filtrado, autorización, previsualización sin escrituras,
aplicación S0->S1, idempotencia, reactivación con el mismo ID de
relación, entradas inválidas, lista vacía, no reactivación por el seed
y rollback controlado (E07) verificado desde una sesión nueva. La
semántica de current en previews con desactivaciones exige que el
campo muestre la configuración activa completa del rol previa a la
propuesta.
"""

import os
import unittest
from unittest import mock

from sqlalchemy import text

from database.connection import SessionLocal
from models.role_permission import RolePermission
from repositories.permission_repository import (
    get_permission,
    get_permission_by_code,
)
from repositories.role_repository import get_role_by_code
from repositories.role_permission_repository import list_role_permissions
from services.role_permission_service import (
    permission_catalog_service,
    preview_role_permissions_service,
    set_role_permissions_service,
)
from services.role_service import list_roles_service
from services.permission_service import list_permissions_service
from services.seed_service import (
    MATRIZ_OFICIAL,
    PERMISOS_OFICIALES,
    cargar_catalogo_inicial,
)

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"


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
                f"alembic_version no es {ALEMBIC_ESPERADO}; prueba abortada"
            )
    finally:
        db.close()


_verificar_guardas()


def _membresia_activa(db, email: str):
    return db.execute(
        text(
            "SELECT cu.id FROM company_users cu "
            "JOIN users u ON u.id = cu.user_id "
            "WHERE u.email = :email AND cu.is_active"
        ),
        {"email": email},
    ).scalar()


def _estado_relaciones(db) -> list[tuple]:
    filas = db.execute(
        text(
            "SELECT rp.id, r.code, p.code, rp.is_active "
            "FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "ORDER BY r.code, p.code, rp.id"
        )
    ).fetchall()
    return [tuple(fila) for fila in filas]


def _activas_de(db, role_id: int) -> list[RolePermission]:
    return list_role_permissions(db, role_id, active_only=True)


class ConfiguracionPermisosTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        cls.ana = _membresia_activa(cls.db, "ana@test.local")
        cls.capturista_usuario = _membresia_activa(
            cls.db,
            "capturista_a@test.local",
        )

        if cls.ana is None or cls.capturista_usuario is None:
            raise SystemExit(
                "faltan usuarios de prueba (Ana o capturista_a); "
                "ejecute setup_pruebas.py"
            )

        cls.admin = get_role_by_code(cls.db, "ADMINISTRADOR")
        cls.capturista = get_role_by_code(cls.db, "CAPTURISTA")
        cls.contador = get_role_by_code(cls.db, "CONTADOR")
        cls.consulta = get_role_by_code(cls.db, "CONSULTA")

        cls.permisos = {
            code: get_permission_by_code(cls.db, code)
            for code in PERMISOS_OFICIALES
        }

        if any(v is None for v in cls.permisos.values()):
            raise SystemExit("catálogo de permisos incompleto")

        # La suite es autosuficiente: restaura la configuración oficial
        # de referencia antes de capturar el estado inicial, sin importar
        # con qué estado haya quedado la base.
        set_role_permissions_service(
            cls.db,
            cls.ana,
            cls.capturista.id,
            [
                cls.permisos[code].id
                for code in sorted(MATRIZ_OFICIAL["CAPTURISTA"])
            ],
        )
        set_role_permissions_service(
            cls.db,
            cls.ana,
            cls.contador.id,
            [
                cls.permisos[code].id
                for code in sorted(MATRIZ_OFICIAL["CONTADOR"])
            ],
        )

        # S0: configuración original de CAPTURISTA (capturada antes de
        # cualquier prueba de esta suite).
        cls.s0 = sorted(
            relation.permission_id
            for relation in _activas_de(cls.db, cls.capturista.id)
        )
        cls.s0_codigos = sorted(
            code
            for code, permission in cls.permisos.items()
            if permission.id in cls.s0
        )
        cls.s1_codigos = sorted(cls.s0_codigos + ["accounts.write"])
        cls.s1_ids = [
            cls.permisos[code].id for code in cls.s1_codigos
        ]

        cls.contador_inicial = sorted(
            relation.permission_id
            for relation in _activas_de(cls.db, cls.contador.id)
        )

        if cls.s0_codigos != sorted(MATRIZ_OFICIAL["CAPTURISTA"]):
            raise SystemExit(
                "CAPTURISTA no está en la configuración inicial S0"
            )

    @classmethod
    def tearDownClass(cls):
        # Restauración garantizada de la configuración original.
        set_role_permissions_service(
            cls.db, cls.ana, cls.capturista.id, list(cls.s0)
        )
        set_role_permissions_service(
            cls.db, cls.ana, cls.contador.id, list(cls.contador_inicial)
        )

        matriz = {
            rol: sorted(
                permission.code
                for permission in (
                    get_permission(cls.db, relation.permission_id)
                    for relation in _activas_de(
                        cls.db,
                        get_role_by_code(cls.db, rol).id,
                    )
                )
            )
            for rol in MATRIZ_OFICIAL
        }
        if matriz != {
            rol: sorted(codigos) for rol, codigos in MATRIZ_OFICIAL.items()
        }:
            raise SystemExit(
                f"la matriz no quedó restaurada: {matriz}"
            )

        cls.db.close()

    def setUp(self):
        # Cada prueba parte de la configuración original.
        set_role_permissions_service(
            self.db, self.ana, self.capturista.id, list(self.s0)
        )
        set_role_permissions_service(
            self.db, self.ana, self.contador.id, list(self.contador_inicial)
        )

    # ---------------------------------------------------------- catálogo

    def test_01_catalogo_sin_filtro(self):
        permisos = permission_catalog_service(
            self.db, self.ana, prefix=None
        )
        codigos = [p.code for p in permisos]

        self.assertEqual(codigos, sorted(PERMISOS_OFICIALES))
        self.assertEqual(len(codigos), 10)

    def test_02_catalogo_por_recurso(self):
        esperados = {
            "company.users.": [
                "company.users.read",
                "company.users.write",
            ],
            "accounts.": ["accounts.read", "accounts.write"],
            "concepts.": ["concepts.read", "concepts.write"],
            "transactions.": [
                "transactions.read",
                "transactions.write",
            ],
            "roles.": ["roles.read", "roles.write"],
        }

        for prefijo, codigos in esperados.items():
            with self.subTest(prefijo=prefijo):
                permisos = permission_catalog_service(
                    self.db, self.ana, prefix=prefijo
                )
                observados = [p.code for p in permisos]
                self.assertEqual(observados, sorted(codigos))
                self.assertTrue(
                    all(c.startswith(prefijo) for c in observados)
                )

    # ----------------------------------------------------- autorización

    def test_03_autorizacion_de_las_operaciones(self):
        with self.assertRaises(PermissionError) as contexto:
            permission_catalog_service(
                self.db, self.capturista_usuario, prefix=None
            )
        self.assertIn(
            "El rol no tiene el permiso roles.read",
            str(contexto.exception),
        )

        with self.assertRaises(PermissionError) as contexto:
            preview_role_permissions_service(
                self.db,
                self.capturista_usuario,
                self.capturista.id,
                self.s1_ids,
            )
        self.assertIn(
            "El rol no tiene el permiso roles.read",
            str(contexto.exception),
        )

        with self.assertRaises(PermissionError) as contexto:
            set_role_permissions_service(
                self.db,
                self.capturista_usuario,
                self.capturista.id,
                self.s1_ids,
            )
        self.assertIn(
            "El rol no tiene el permiso roles.write",
            str(contexto.exception),
        )

    # ----------------------------------------------------- previsualizar

    def test_04_preview_no_modifica_filas(self):
        sesion_nueva = SessionLocal()
        try:
            antes = _estado_relaciones(sesion_nueva)
        finally:
            sesion_nueva.close()

        plan = preview_role_permissions_service(
            self.db, self.ana, self.capturista.id, self.s1_ids
        )

        self.assertEqual(
            [p.code for p in plan["to_activate"]],
            ["accounts.write"],
        )
        self.assertEqual(
            [p.code for p in plan["to_deactivate"]],
            [],
        )
        self.assertEqual(plan["final_count"], 5)
        self.assertEqual(plan["final_count"], len(self.s1_codigos))

        sesion_nueva = SessionLocal()
        try:
            despues = _estado_relaciones(sesion_nueva)
        finally:
            sesion_nueva.close()

        self.assertEqual(antes, despues)

    # ------------------------------------------------------- aplicación

    def test_05_aplicar_s0_a_s1(self):
        resumen = set_role_permissions_service(
            self.db, self.ana, self.capturista.id, self.s1_ids
        )

        self.assertTrue(resumen["changed"])
        self.assertEqual(
            [p.code for p in resumen["activated"]],
            ["accounts.write"],
        )
        self.assertEqual(
            [p.code for p in resumen["deactivated"]],
            [],
        )
        self.assertEqual(resumen["final_count"], 5)

        sesion_nueva = SessionLocal()
        try:
            activas = sorted(
                p.code
                for p in (
                    get_permission(sesion_nueva, r.permission_id)
                    for r in _activas_de(sesion_nueva, self.capturista.id)
                )
            )
        finally:
            sesion_nueva.close()

        self.assertEqual(activas, self.s1_codigos)

    def test_06_repetir_s1_es_idempotente(self):
        set_role_permissions_service(
            self.db, self.ana, self.capturista.id, self.s1_ids
        )

        ids_antes = {
            r.permission_id: r.id
            for r in _activas_de(self.db, self.capturista.id)
        }

        resumen = set_role_permissions_service(
            self.db, self.ana, self.capturista.id, self.s1_ids
        )

        self.assertFalse(resumen["changed"])
        self.assertEqual(resumen["activated"], [])
        self.assertEqual(resumen["deactivated"], [])
        self.assertEqual(
            sorted(p.code for p in resumen["unchanged"]),
            self.s1_codigos,
        )
        self.assertEqual(resumen["final_count"], 5)

        ids_despues = {
            r.permission_id: r.id
            for r in _activas_de(self.db, self.capturista.id)
        }
        self.assertEqual(ids_antes, ids_despues)

        filas = [
            fila
            for fila in _estado_relaciones(self.db)
            if fila[1] == "CAPTURISTA"
        ]
        parejas = [(fila[2]) for fila in filas]
        self.assertEqual(len(parejas), len(set(parejas)))

    def test_07_desactivar_reactivar_conserva_el_id(self):
        set_role_permissions_service(
            self.db, self.ana, self.capturista.id, self.s1_ids
        )

        permission_id = self.permisos["accounts.write"].id
        id_concesion = next(
            r.id
            for r in _activas_de(self.db, self.capturista.id)
            if r.permission_id == permission_id
        )

        set_role_permissions_service(
            self.db, self.ana, self.capturista.id, list(self.s0)
        )

        fila_inactiva = next(
            r
            for r in list_role_permissions(
                self.db, self.capturista.id, active_only=False
            )
            if r.permission_id == permission_id
        )
        self.assertFalse(fila_inactiva.is_active)
        self.assertEqual(fila_inactiva.id, id_concesion)

        set_role_permissions_service(
            self.db, self.ana, self.capturista.id, self.s1_ids
        )

        fila_reactivada = next(
            r
            for r in list_role_permissions(
                self.db, self.capturista.id, active_only=False
            )
            if r.permission_id == permission_id
        )
        self.assertTrue(fila_reactivada.is_active)
        self.assertEqual(fila_reactivada.id, id_concesion)

        total_parejas = self.db.execute(
            text(
                "SELECT count(*) FROM role_permissions "
                "WHERE role_id = :role AND permission_id = :perm"
            ),
            {"role": self.capturista.id, "perm": permission_id},
        ).scalar()
        self.assertEqual(total_parejas, 1)

    # --------------------------------------------------- entradas malas

    def test_08_rol_inexistente(self):
        antes = _estado_relaciones(self.db)

        with self.assertRaises(ValueError) as contexto:
            preview_role_permissions_service(
                self.db, self.ana, 999999, self.s1_ids
            )
        self.assertIn("El rol no existe", str(contexto.exception))

        with self.assertRaises(ValueError) as contexto:
            set_role_permissions_service(
                self.db, self.ana, 999999, self.s1_ids
            )
        self.assertIn("El rol no existe", str(contexto.exception))

        self.assertEqual(antes, _estado_relaciones(self.db))

    def test_09_rol_inactivo(self):
        sesion = SessionLocal()
        try:
            consulta = get_role_by_code(sesion, "CONSULTA")
            consulta.is_active = False
            sesion.flush()

            with self.assertRaises(ValueError) as contexto:
                preview_role_permissions_service(
                    sesion,
                    self.ana,
                    consulta.id,
                    [self.permisos["accounts.read"].id],
                )
            self.assertIn(
                "El rol no está activo", str(contexto.exception)
            )

            with self.assertRaises(ValueError) as contexto:
                set_role_permissions_service(
                    sesion,
                    self.ana,
                    consulta.id,
                    [self.permisos["accounts.read"].id],
                )
            self.assertIn(
                "El rol no está activo", str(contexto.exception)
            )

            sesion.rollback()
        finally:
            sesion.close()

        verificacion = SessionLocal()
        try:
            consulta = get_role_by_code(verificacion, "CONSULTA")
            self.assertTrue(consulta.is_active)
        finally:
            verificacion.close()

    def test_10_propuesta_sobre_administrador(self):
        todos = [p.id for p in self.permisos.values()]
        antes = _estado_relaciones(self.db)

        with self.assertRaises(ValueError) as contexto:
            preview_role_permissions_service(
                self.db, self.ana, self.admin.id, todos
            )
        self.assertIn("ADMINISTRADOR", str(contexto.exception))

        with self.assertRaises(ValueError) as contexto:
            set_role_permissions_service(
                self.db, self.ana, self.admin.id, todos
            )
        self.assertIn("ADMINISTRADOR", str(contexto.exception))

        with self.assertRaises(ValueError) as contexto:
            set_role_permissions_service(
                self.db, self.ana, self.admin.id, []
            )
        self.assertIn("ADMINISTRADOR", str(contexto.exception))

        self.assertEqual(antes, _estado_relaciones(self.db))

    def test_11_permiso_inexistente(self):
        mezcla = list(self.s0) + [999999]
        antes = _estado_relaciones(self.db)

        with self.assertRaises(ValueError) as contexto:
            preview_role_permissions_service(
                self.db, self.ana, self.capturista.id, mezcla
            )
        self.assertIn(
            "El permiso con id 999999 no existe",
            str(contexto.exception),
        )

        with self.assertRaises(ValueError) as contexto:
            set_role_permissions_service(
                self.db, self.ana, self.capturista.id, mezcla
            )
        self.assertIn(
            "El permiso con id 999999 no existe",
            str(contexto.exception),
        )

        self.assertEqual(antes, _estado_relaciones(self.db))

    def test_12_permiso_inactivo(self):
        sesion = SessionLocal()
        try:
            permission = get_permission_by_code(sesion, "concepts.write")
            permission.is_active = False
            sesion.flush()

            with self.assertRaises(ValueError) as contexto:
                preview_role_permissions_service(
                    sesion,
                    self.ana,
                    self.capturista.id,
                    [permission.id],
                )
            self.assertIn(
                "El permiso concepts.write no está activo",
                str(contexto.exception),
            )

            with self.assertRaises(ValueError) as contexto:
                set_role_permissions_service(
                    sesion,
                    self.ana,
                    self.capturista.id,
                    [permission.id],
                )
            self.assertIn(
                "El permiso concepts.write no está activo",
                str(contexto.exception),
            )

            sesion.rollback()
        finally:
            sesion.close()

        verificacion = SessionLocal()
        try:
            permission = get_permission_by_code(
                verificacion, "concepts.write"
            )
            self.assertTrue(permission.is_active)
        finally:
            verificacion.close()

    def test_13_ids_repetidos(self):
        primero = self.s1_ids[0]
        antes = _estado_relaciones(self.db)

        with self.assertRaises(ValueError) as contexto:
            preview_role_permissions_service(
                self.db,
                self.ana,
                self.capturista.id,
                [primero, primero],
            )
        self.assertIn(
            "permissionIds contiene IDs repetidos",
            str(contexto.exception),
        )

        # Equivalente cadena/entero: "3" y 3 son el mismo ID.
        with self.assertRaises(ValueError) as contexto:
            set_role_permissions_service(
                self.db,
                self.ana,
                self.capturista.id,
                [str(primero), primero],
            )
        self.assertIn(
            "permissionIds contiene IDs repetidos",
            str(contexto.exception),
        )

        self.assertEqual(antes, _estado_relaciones(self.db))

    # ------------------------------------------- lista vacía y seed

    def test_14_lista_vacia_y_seed_no_reactiva(self):
        resumen = set_role_permissions_service(
            self.db, self.ana, self.contador.id, []
        )

        self.assertTrue(resumen["changed"])
        self.assertEqual(resumen["final_count"], 0)
        self.assertEqual(len(resumen["deactivated"]), 8)

        verificacion = SessionLocal()
        try:
            activas = _activas_de(verificacion, self.contador.id)
            self.assertEqual(activas, [])
            filas = list_role_permissions(
                verificacion, self.contador.id, active_only=False
            )
            self.assertEqual(len(filas), 8)
            self.assertTrue(all(not f.is_active for f in filas))

            # La carga inicial no debe restaurar la lista vacía.
            resultado = cargar_catalogo_inicial(verificacion)
            self.assertEqual(resultado["relaciones_creadas"], 0)
            self.assertEqual(resultado["relaciones_reactivadas"], 0)

            activas_tras_seed = _activas_de(
                verificacion, self.contador.id
            )
            self.assertEqual(activas_tras_seed, [])
        finally:
            verificacion.close()

        resumen_repetido = set_role_permissions_service(
            self.db, self.ana, self.contador.id, []
        )
        self.assertFalse(resumen_repetido["changed"])

    # ---------------------------------------------------------- E07

    def test_15_rollback_e07_tras_flush_sin_commit(self):
        sesion_previa = SessionLocal()
        try:
            antes = _estado_relaciones(sesion_previa)
        finally:
            sesion_previa.close()

        sesion = SessionLocal()
        try:
            with mock.patch(
                "services.role_permission_service._construir_resumen",
                side_effect=RuntimeError("fallo controlado E07"),
            ):
                with self.assertRaises(RuntimeError) as contexto:
                    set_role_permissions_service(
                        sesion,
                        self.ana,
                        self.capturista.id,
                        self.s1_ids,
                    )
            self.assertIn(
                "fallo controlado E07", str(contexto.exception)
            )
        finally:
            sesion.rollback()
            sesion.close()

        # Estado persistido consultado desde una sesión nueva.
        sesion_nueva = SessionLocal()
        try:
            despues = _estado_relaciones(sesion_nueva)
        finally:
            sesion_nueva.close()

        self.assertEqual(antes, despues)

    # --------------------------------------------------- continuidad

    def test_16_continuidad_de_operaciones_previas(self):
        roles = list_roles_service(self.db, self.ana)
        self.assertEqual(len(roles), 4)

        permisos = list_permissions_service(self.db, self.ana)
        self.assertEqual(len(permisos), 10)

        relaciones = list_role_permissions(
            self.db, self.capturista.id, active_only=True
        )
        self.assertEqual(len(relaciones), len(self.s0))

    def test_17_matriz_oficial_sin_duplicados(self):
        matriz = {
            rol: sorted(
                relation.permission_id
                for relation in _activas_de(
                    self.db,
                    get_role_by_code(self.db, rol).id,
                )
            )
            for rol in MATRIZ_OFICIAL
        }
        esperado = {
            rol: sorted(
                self.permisos[code].id for code in codigos
            )
            for rol, codigos in MATRIZ_OFICIAL.items()
        }
        self.assertEqual(matriz, esperado)

        duplicados = self.db.execute(
            text(
                "SELECT role_id, permission_id, count(*) "
                "FROM role_permissions "
                "GROUP BY role_id, permission_id "
                "HAVING count(*) > 1"
            )
        ).fetchall()
        self.assertEqual(duplicados, [])

    # --------------------------- previsualizar con desactivaciones

    def test_18_preview_desactivaciones_current_es_estado_previo(self):
        s0_codigos = list(self.s0_codigos)

        escenarios = [
            # (propuesta, current esperado, to_deactivate, unchanged,
            #  to_activate, final_count)
            (
                [self.permisos["accounts.read"].id],
                s0_codigos,
                sorted(c for c in s0_codigos if c != "accounts.read"),
                ["accounts.read"],
                [],
                1,
            ),
            (
                [],
                s0_codigos,
                s0_codigos,
                [],
                [],
                0,
            ),
        ]

        for propuesta, esperado_current, esperado_deactivate, \
                esperado_unchanged, esperado_activate, \
                esperado_final in escenarios:
            with self.subTest(propuesta=propuesta):
                sesion_previa = SessionLocal()
                try:
                    antes = _estado_relaciones(sesion_previa)
                finally:
                    sesion_previa.close()

                plan = preview_role_permissions_service(
                    self.db, self.ana, self.capturista.id, propuesta
                )

                # current es la configuración activa completa del rol,
                # no la intersección con la propuesta.
                self.assertEqual(
                    sorted(p.code for p in plan["current"]),
                    esperado_current,
                )
                self.assertEqual(
                    sorted(p.code for p in plan["to_deactivate"]),
                    esperado_deactivate,
                )
                self.assertEqual(
                    sorted(p.code for p in plan["unchanged"]),
                    esperado_unchanged,
                )
                self.assertEqual(
                    sorted(p.code for p in plan["to_activate"]),
                    esperado_activate,
                )
                self.assertEqual(plan["final_count"], esperado_final)

                if not propuesta:
                    self.assertNotEqual(
                        plan["current"], plan["unchanged"]
                    )

                sesion_posterior = SessionLocal()
                try:
                    despues = _estado_relaciones(sesion_posterior)
                finally:
                    sesion_posterior.close()

                self.assertEqual(antes, despues)


if __name__ == "__main__":
    unittest.main()
