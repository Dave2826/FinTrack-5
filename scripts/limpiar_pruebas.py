"""Limpieza de datos de pruebas. Solo sobre fintrack5_test. Dry-run por defecto.

Ademas de los datos de negocio del setup, retira el residuo de pruebas de
``role_permissions``: relaciones fuera de la matriz oficial que dejaron los
escenarios al conceder y luego retirar permisos (por ejemplo
CAPTURISTA/accounts.write). El catalogo oficial (roles, permisos y las 26
relaciones de MATRIZ_OFICIAL) nunca se elimina.
"""

import os
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from models.account import Account
from models.account_concept import AccountConcept
from models.company import Company
from models.company_user import CompanyUser
from models.company_user_role import CompanyUserRole
from models.concept import Concept
from models.permission import Permission
from models.role import Role
from models.role_permission import RolePermission
from models.transaction import Transaction
from models.user import User
from services.seed_service import MATRIZ_OFICIAL

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"

MARCADORES_EMPRESA = ("Pruebas Alpha SA", "Pruebas Beta SA")

# Marcadores inequívocos del setup: la lista exacta de usuarios creados.
# Un correo @test.local fuera de esta lista NUNCA se elimina.
EMAILS_SETUP = (
    "admin_a@test.local",
    "admin_b@test.local",
    "contador_a@test.local",
    "capturista_a@test.local",
    "consulta_a@test.local",
    "sin_membresia_a@test.local",
    "inactivo_a@test.local",
)


def _log(mensaje: str) -> None:
    print(f"[limpieza] {mensaje}", flush=True)


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

    _log("guardas verificadas: BD fintrack5_test y alembic")


def _identificar(db: Session) -> dict:
    empresas = (
        db.query(Company)
        .filter(Company.name.in_(MARCADORES_EMPRESA))
        .all()
    )
    empresa_ids = [c.id for c in empresas]

    membresias: list[CompanyUser] = []
    if empresa_ids:
        membresias = (
            db.query(CompanyUser)
            .filter(CompanyUser.company_id.in_(empresa_ids))
            .all()
        )
    membresia_ids = [m.id for m in membresias]

    relaciones: list[CompanyUserRole] = []
    if membresia_ids:
        relaciones = (
            db.query(CompanyUserRole)
            .filter(CompanyUserRole.company_user_id.in_(membresia_ids))
            .all()
        )

    cuentas: list[Account] = []
    conceptos: list[Concept] = []
    if empresa_ids:
        cuentas = (
            db.query(Account)
            .filter(Account.company_id.in_(empresa_ids))
            .all()
        )
        conceptos = (
            db.query(Concept)
            .filter(Concept.company_id.in_(empresa_ids))
            .all()
        )
    cuenta_ids = [c.id for c in cuentas]
    concepto_ids = [c.id for c in conceptos]

    movimientos: list[Transaction] = []
    asociaciones: list[AccountConcept] = []
    if cuenta_ids:
        movimientos = (
            db.query(Transaction)
            .filter(Transaction.account_id.in_(cuenta_ids))
            .all()
        )
        asociaciones = (
            db.query(AccountConcept)
            .filter(AccountConcept.account_id.in_(cuenta_ids))
            .all()
        )

    ids_membresia_rel = {m.user_id for m in membresias}
    candidatos = (
        db.query(User)
        .filter(
            (User.id.in_(ids_membresia_rel))
            | (User.email.in_(EMAILS_SETUP))
        )
        .all()
        if (ids_membresia_rel or EMAILS_SETUP)
        else []
    )

    usuarios_seguros: list[User] = []
    excluidos: list[str] = []
    for usuario in candidatos:
        ajenas = (
            db.query(CompanyUser)
            .filter(
                CompanyUser.user_id == usuario.id,
                ~CompanyUser.company_id.in_(empresa_ids)
                if empresa_ids
                else True,
            )
            .count()
        )
        if ajenas > 0:
            excluidos.append(
                f"user_id={usuario.id} pertenece a una empresa ajena"
            )
            continue
        en_membresia = usuario.id in ids_membresia_rel
        en_emails = usuario.email in EMAILS_SETUP
        if not (en_membresia or en_emails):
            excluidos.append(f"user_id={usuario.id} sin marcador inequivoco")
            continue
        usuarios_seguros.append(usuario)

    ajenos_test = (
        db.query(User)
        .filter(
            User.email.like("%@test.local"),
            ~User.email.in_(EMAILS_SETUP),
        )
        .all()
    )
    for usuario in ajenos_test:
        excluidos.append(
            f"user_id={usuario.id} correo @test.local fuera de la lista del setup"
        )

    return {
        "empresas": empresas,
        "membresias": membresias,
        "relaciones": relaciones,
        "cuentas": cuentas,
        "conceptos": conceptos,
        "asociaciones": asociaciones,
        "movimientos": movimientos,
        "usuarios_seguros": usuarios_seguros,
        "residuo": _residuo_role_permissions(db),
        "excluidos": excluidos,
    }


def _residuo_role_permissions(db: Session) -> list[dict]:
    """Relaciones de role_permissions ajenas a la matriz oficial.

    Los escenarios de pruebas conceden permisos que no pertenecen al rol
    (por ejemplo CAPTURISTA/accounts.write) y al retirarlos dejan la fila
    inactiva. Esas filas no forman parte del catalogo oficial y, si
    permanecen, hacen que setup_pruebas.py aborte por "par no oficial".
    Solo se informan relaciones; las oficiales nunca se tocan.
    """

    pares_oficiales: set[tuple[int, int]] = set()
    for codigo_rol, codigos_permiso in MATRIZ_OFICIAL.items():
        rol = db.query(Role).filter(Role.code == codigo_rol).one_or_none()
        if rol is None:
            continue
        for codigo_permiso in codigos_permiso:
            permiso = (
                db.query(Permission)
                .filter(Permission.code == codigo_permiso)
                .one_or_none()
            )
            if permiso is not None:
                pares_oficiales.add((rol.id, permiso.id))

    residuo = []
    for fila in db.query(RolePermission).all():
        if (fila.role_id, fila.permission_id) in pares_oficiales:
            continue
        rol = db.query(Role).filter(Role.id == fila.role_id).one_or_none()
        permiso = (
            db.query(Permission)
            .filter(Permission.id == fila.permission_id)
            .one_or_none()
        )
        residuo.append(
            {
                "id": fila.id,
                "rol": rol.code if rol else fila.role_id,
                "permiso": permiso.code if permiso else fila.permission_id,
                "is_active": fila.is_active,
            }
        )
    return residuo


def _imprimir_plan(db: Session, datos: dict) -> None:
    _log("MODO DRY-RUN (sin escrituras)" if not _confirmado() else "MODO --confirm")
    _log(
        "empresas: "
        + str([(c.id, c.name) for c in datos["empresas"]])
    )
    _log(f"company_users: {[m.id for m in datos['membresias']]}")
    _log(f"company_user_roles: {[r.id for r in datos['relaciones']]}")
    _log(f"accounts: {[c.id for c in datos['cuentas']]}")
    _log(f"concepts: {[c.id for c in datos['conceptos']]}")
    _log(f"account_concepts: {[r.id for r in datos['asociaciones']]}")
    _log(f"transactions: {[t.id for t in datos['movimientos']]}")
    _log(f"users: {[(u.id, u.email) for u in datos['usuarios_seguros']]}")
    _log(
        "roles/permissions: NO se eliminan (catalogo oficial)"
    )
    _log(
        "role_permissions: se conservan las 26 relaciones oficiales; "
        "residuo de pruebas a eliminar: "
        + str(
            [
                (r["id"], r["rol"], r["permiso"], r["is_active"])
                for r in datos["residuo"]
            ]
        )
    )
    for motivo in datos["excluidos"]:
        _log(f"EXCLUIDO (no se eliminara): {motivo}")


def _confirmado() -> bool:
    return "--confirm" in sys.argv[1:]


def _eliminar(db: Session, datos: dict) -> None:
    ids_mov = [t.id for t in datos["movimientos"]]
    ids_rel = [r.id for r in datos["asociaciones"]]
    ids_cue = [c.id for c in datos["cuentas"]]
    ids_con = [c.id for c in datos["conceptos"]]
    ids_mru = [r.id for r in datos["relaciones"]]
    ids_cu = [m.id for m in datos["membresias"]]
    ids_emp = [c.id for c in datos["empresas"]]
    ids_usu = [u.id for u in datos["usuarios_seguros"]]
    ids_res = [r["id"] for r in datos["residuo"]]

    total = sum(
        len(x)
        for x in (
            ids_mov,
            ids_rel,
            ids_cue,
            ids_con,
            ids_mru,
            ids_emp,
            ids_usu,
            ids_res,
        )
    )
    if total == 0:
        _log("nada que limpiar")
        return

    orden = [
        ("transactions", Transaction, ids_mov),
        ("account_concepts", AccountConcept, ids_rel),
        ("accounts", Account, ids_cue),
        ("concepts", Concept, ids_con),
        ("company_user_roles", CompanyUserRole, ids_mru),
        ("company_users", CompanyUser, ids_cu),
        ("companies", Company, ids_emp),
        ("users", User, ids_usu),
        ("role_permissions(residuo)", RolePermission, ids_res),
    ]

    borrados = {}
    try:
        for nombre, modelo, ids in orden:
            if not ids:
                borrados[nombre] = 0
                continue
            cantidad = (
                db.query(modelo)
                .filter(modelo.id.in_(ids))
                .delete(synchronize_session=False)
            )
            borrados[nombre] = cantidad
        db.commit()
    except Exception as exc:
        db.rollback()
        _abortar(f"rollback por fallo: {type(exc).__name__}: {exc}")

    for nombre in borrados:
        _log(f"eliminados {nombre}: {borrados[nombre]}")
    _log("LIMPIEZA COMPLETADA")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] not in ("--confirm",):
        _abortar(f"argumento desconocido: {sys.argv[1]}")

    db = SessionLocal()
    try:
        _verificar_guardas(db)
        datos = _identificar(db)
        _imprimir_plan(db, datos)

        if not _confirmado():
            _log("dry-run finalizado sin escrituras")
            return

        if datos["excluidos"]:
            _log("existen registros excluidos; la limpieza solo borrara los seguros")

        _eliminar(db, datos)
    finally:
        db.close()


if __name__ == "__main__":
    main()
