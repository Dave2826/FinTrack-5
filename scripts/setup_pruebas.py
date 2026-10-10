"""Inicializacion de datos ficticios de pruebas. Solo sobre fintrack5_test."""

import json
import os
import sys
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from models.account import AccountType
from models.company import Company
from models.concept import ConceptType
from models.permission import Permission
from models.role import Role
from models.transaction import TransactionType
from models.user import User
from repositories.company_repository import create_company
from repositories.company_user_role_repository import (
    get_active_company_user_role,
    get_company_user_role_by_company_user_and_role,
)
from repositories.permission_repository import get_permission_by_code
from repositories.role_repository import get_role_by_code
from repositories.user_repository import create_user
from security.password import hash_password
from services.account_concept_service import assign_concept_to_account
from services.account_service import create_account_service
from services.company_user_service import (
    assign_role_service,
    create_company_admin_service,
    create_company_user_service,
)
from services.concept_service import create_concept_service
from services.seed_service import cargar_catalogo_inicial
from services.transaction_service import create_transaction_service

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"

TABLAS_NEGOCIO = [
    "users",
    "companies",
    "company_users",
    "company_user_roles",
    "accounts",
    "concepts",
    "account_concepts",
    "transactions",
]

ROLES_OFICIALES = ["ADMINISTRADOR", "CONTADOR", "CAPTURISTA", "CONSULTA"]

PERMISOS_OFICIALES = [
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
]

# Contrasena ficticia exclusiva de pruebas locales. Nunca se imprime ni
# se incluye en el manifiesto.
CONTRASENA_PRUEBAS = "Pruebas-local-ficticias-2026!"


def _log(mensaje: str) -> None:
    print(f"[setup] {mensaje}", file=sys.stderr, flush=True)


def _abortar(mensaje: str) -> None:
    _log(f"GUARDA: {mensaje}")
    sys.exit(1)


def _conteo(db: Session, tabla: str) -> int:
    return db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar()


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

    for tabla in TABLAS_NEGOCIO:
        if _conteo(db, tabla) != 0:
            _abortar(
                f"la tabla {tabla} ya contiene datos; "
                "ejecute limpiar_pruebas.py antes del setup"
            )

    roles = db.query(Role).all()
    if roles:
        if {r.code for r in roles} != set(ROLES_OFICIALES):
            _abortar("el catalogo de roles existente no coincide con el oficial")

    permisos = db.query(Permission).all()
    if permisos:
        if {p.code for p in permisos} != set(PERMISOS_OFICIALES):
            _abortar("el catalogo de permisos existente no coincide con el oficial")

    _log("guardas verificadas: BD fintrack5_test, alembic, tablas vacias")


def _fase_catalogo(db: Session) -> dict:
    resultado = cargar_catalogo_inicial(db)

    roles = db.query(Role).all()
    permisos = db.query(Permission).all()
    activas = db.execute(
        text("SELECT count(*) FROM role_permissions WHERE is_active")
    ).scalar()

    if len(roles) != 4 or not all(r.is_active for r in roles):
        _abortar("el seed no dejo los 4 roles activos")
    if len(permisos) != 10:
        _abortar("el seed no dejo los 10 permisos")
    if activas != 26:
        _abortar("el seed no dejo las 26 relaciones activas")

    _log(f"catalogo listo: {resultado}")
    return resultado


def _fase_empresas(db: Session) -> tuple[Company, Company]:
    alpha = create_company(
        db,
        Company(
            name="Pruebas Alpha SA",
            legal_name="Pruebas Alpha SA ficticia",
            tax_id="TEST-ALPHA-001",
            email="alpha@test.local",
            is_active=True,
        ),
    )
    beta = create_company(
        db,
        Company(
            name="Pruebas Beta SA",
            legal_name="Pruebas Beta SA ficticia",
            tax_id="TEST-BETA-001",
            email="beta@test.local",
            is_active=True,
        ),
    )
    _log(f"empresas creadas: alpha_id={alpha.id} beta_id={beta.id}")
    return alpha, beta


def _crear_usuario(db: Session, nombre: str, email: str) -> User:
    usuario = create_user(
        db,
        User(
            name=nombre,
            email=email,
            password_hash=hash_password(CONTRASENA_PRUEBAS),
            email_verified=True,
            is_active=True,
        ),
    )
    return usuario


def _fase_usuarios(db: Session) -> dict[str, User]:
    usuarios = {
        "admin_a": _crear_usuario(db, "Admin Pruebas Alpha", "admin_a@test.local"),
        "admin_b": _crear_usuario(db, "Admin Pruebas Beta", "admin_b@test.local"),
        "contador_a": _crear_usuario(
            db, "Contador Pruebas Alpha", "contador_a@test.local"
        ),
        "capturista_a": _crear_usuario(
            db, "Capturista Pruebas Alpha", "capturista_a@test.local"
        ),
        "consulta_a": _crear_usuario(
            db, "Consulta Pruebas Alpha", "consulta_a@test.local"
        ),
        "sin_membresia_a": _crear_usuario(
            db, "Sin Membresia Pruebas", "sin_membresia_a@test.local"
        ),
        "inactivo_a": _crear_usuario(
            db, "Inactivo Pruebas", "inactivo_a@test.local"
        ),
    }

    # No existe servicio de gestion de usuarios en el proyecto; la unica
    # escritura directa del setup, limitada a la BD de pruebas.
    usuarios["inactivo_a"].is_active = False
    db.commit()
    db.refresh(usuarios["inactivo_a"])

    _log(f"usuarios creados: {sorted(usuarios)}")
    return usuarios


def _verificar_admin(db: Session, company_user_id: int, role_id: int) -> None:
    relation = get_company_user_role_by_company_user_and_role(
        db, company_user_id, role_id
    )
    if relation is None or not relation.is_active:
        _abortar(f"membresia {company_user_id} sin rol ADMINISTRADOR activo")


def _fase_admins(
    db: Session, alpha: Company, beta: Company, usuarios: dict[str, User]
) -> tuple[int, int]:
    # create_company_admin_service ignora actor_company_user_id (no exige
    # permisos: es el bootstrap diseñado para la primera membresia).
    admin_a = create_company_admin_service(db, 0, alpha.id, usuarios["admin_a"].id)
    admin_b = create_company_admin_service(db, 0, beta.id, usuarios["admin_b"].id)

    rol_admin = get_role_by_code(db, "ADMINISTRADOR")
    if rol_admin is None:
        _abortar("rol ADMINISTRADOR inexistente tras el seed")

    for cu in (admin_a, admin_b):
        if not cu.is_active or not cu.is_admin:
            _abortar(f"membresia admin {cu.id} no es admin activa")
        _verificar_admin(db, cu.id, rol_admin.id)

    _log(f"admins bootstrap: alpha={admin_a.id} beta={admin_b.id}")
    return admin_a.id, admin_b.id


def _fase_roles_operativos(
    db: Session, alpha: Company, usuarios: dict[str, User], admin_a_id: int
) -> dict[str, int]:
    asignaciones = {"contador_a": "CONTADOR", "capturista_a": "CAPTURISTA", "consulta_a": "CONSULTA"}
    membresias: dict[str, int] = {}

    for clave, codigo_rol in asignaciones.items():
        cu = create_company_user_service(
            db, admin_a_id, alpha.id, usuarios[clave].id, is_admin=False
        )
        rol = get_role_by_code(db, codigo_rol)
        if rol is None:
            _abortar(f"rol {codigo_rol} inexistente")
        assign_role_service(db, admin_a_id, cu.id, rol.id)

        activa = get_active_company_user_role(db, cu.id)
        if activa is None or activa.role_id != rol.id:
            _abortar(f"membresia {cu.id} no tiene el rol {codigo_rol} activo")
        membresias[clave] = cu.id

    _log(f"roles operativos asignados: {membresias}")
    return membresias


def _fase_recursos(
    db: Session,
    alpha: Company,
    beta: Company,
    usuarios: dict[str, User],
    admin_a_id: int,
    admin_b_id: int,
) -> dict:
    cuenta_a = create_account_service(
        db,
        admin_a_id,
        alpha.id,
        AccountType.DEBIT,
        "Cuenta Alpha Pruebas",
        bank_name="Banco Pruebas",
        account_number="0001",
        short_description="Cuenta ficticia de pruebas",
    )
    ingreso_a = create_concept_service(
        db,
        admin_a_id,
        alpha.id,
        ConceptType.INCOME,
        "Ingreso Alpha Pruebas",
        short_description="Concepto ficticio",
    )
    egreso_a = create_concept_service(
        db,
        admin_a_id,
        alpha.id,
        ConceptType.EXPENSE,
        "Egreso Alpha Pruebas",
        short_description="Concepto ficticio",
    )
    rel_a1 = assign_concept_to_account(db, admin_a_id, cuenta_a.id, ingreso_a.id)
    rel_a2 = assign_concept_to_account(db, admin_a_id, cuenta_a.id, egreso_a.id)
    mov_a1 = create_transaction_service(
        db,
        admin_a_id,
        cuenta_a.id,
        ingreso_a.id,
        TransactionType.INCOME,
        Decimal("1500.00"),
        captured_by=usuarios["admin_a"].id,
        transaction_date=datetime(2026, 1, 10, 12, 0, 0),
        short_description="Movimiento ficticio ingreso",
    )
    mov_a2 = create_transaction_service(
        db,
        admin_a_id,
        cuenta_a.id,
        egreso_a.id,
        TransactionType.EXPENSE,
        Decimal("300.00"),
        captured_by=usuarios["admin_a"].id,
        transaction_date=datetime(2026, 1, 11, 12, 0, 0),
        short_description="Movimiento ficticio egreso",
    )

    cuenta_b = create_account_service(
        db,
        admin_b_id,
        beta.id,
        AccountType.DEBIT,
        "Cuenta Beta Pruebas",
        bank_name="Banco Pruebas",
        account_number="0002",
        short_description="Cuenta ficticia de pruebas",
    )
    ingreso_b = create_concept_service(
        db,
        admin_b_id,
        beta.id,
        ConceptType.INCOME,
        "Ingreso Beta Pruebas",
        short_description="Concepto ficticio",
    )
    rel_b1 = assign_concept_to_account(db, admin_b_id, cuenta_b.id, ingreso_b.id)
    mov_b1 = create_transaction_service(
        db,
        admin_b_id,
        cuenta_b.id,
        ingreso_b.id,
        TransactionType.INCOME,
        Decimal("900.00"),
        captured_by=usuarios["admin_b"].id,
        transaction_date=datetime(2026, 1, 12, 12, 0, 0),
        short_description="Movimiento ficticio ingreso beta",
    )

    recursos = {
        "alpha": {
            "cuenta_id": cuenta_a.id,
            "conceptos": [ingreso_a.id, egreso_a.id],
            "relaciones": [rel_a1.id, rel_a2.id],
            "transacciones": [mov_a1.id, mov_a2.id],
        },
        "beta": {
            "cuenta_id": cuenta_b.id,
            "conceptos": [ingreso_b.id],
            "relaciones": [rel_b1.id],
            "transacciones": [mov_b1.id],
        },
    }
    _log("recursos ficticios creados en ambas empresas")
    return recursos


def _verificacion_final(
    db: Session,
    admin_a_id: int,
    admin_b_id: int,
    membresias: dict[str, int],
) -> None:
    rol_admin = get_role_by_code(db, "ADMINISTRADOR")
    for clave, cu_id in membresias.items():
        activa = get_active_company_user_role(db, cu_id)
        if activa is None:
            _abortar(f"membresia {clave} ({cu_id}) sin rol activo")

    esperados = {"contador_a": "CONTADOR", "capturista_a": "CAPTURISTA", "consulta_a": "CONSULTA"}
    for clave, codigo in esperados.items():
        rol = get_role_by_code(db, codigo)
        activa = get_active_company_user_role(db, membresias[clave])
        if activa is None or activa.role_id != rol.id:
            _abortar(f"membresia {clave} no conserva el rol {codigo}")

    if rol_admin is None:
        _abortar("rol ADMINISTRADOR desaparecio")
    for cu_id in (admin_a_id, admin_b_id):
        _verificar_admin(db, cu_id, rol_admin.id)

    for tabla, esperado in (
        ("users", 7),
        ("companies", 2),
        ("company_users", 5),
        ("company_user_roles", 5),
        ("accounts", 2),
        ("concepts", 3),
        ("account_concepts", 3),
        ("transactions", 3),
    ):
        if _conteo(db, tabla) != esperado:
            _abortar(f"conteo inesperado en {tabla}")

    _log("verificacion final: integridad confirmada")


def _manifiesto(
    db: Session,
    seed: dict,
    alpha: Company,
    beta: Company,
    usuarios: dict[str, User],
    admin_a_id: int,
    admin_b_id: int,
    membresias: dict[str, int],
    recursos: dict,
) -> dict:
    roles = {
        code: get_role_by_code(db, code).id for code in ROLES_OFICIALES
    }
    return {
        "estado": "OK",
        "alembic": ALEMBIC_ESPERADO,
        "empresas": {
            "alpha": {"id": alpha.id, "nombre": alpha.name},
            "beta": {"id": beta.id, "nombre": beta.name},
        },
        "usuarios": {
            "admin_a": {
                "id": usuarios["admin_a"].id,
                "email": usuarios["admin_a"].email,
                "membresia_id": admin_a_id,
                "rol": "ADMINISTRADOR",
            },
            "admin_b": {
                "id": usuarios["admin_b"].id,
                "email": usuarios["admin_b"].email,
                "membresia_id": admin_b_id,
                "rol": "ADMINISTRADOR",
            },
            "contador_a": {
                "id": usuarios["contador_a"].id,
                "email": usuarios["contador_a"].email,
                "membresia_id": membresias["contador_a"],
                "rol": "CONTADOR",
            },
            "capturista_a": {
                "id": usuarios["capturista_a"].id,
                "email": usuarios["capturista_a"].email,
                "membresia_id": membresias["capturista_a"],
                "rol": "CAPTURISTA",
            },
            "consulta_a": {
                "id": usuarios["consulta_a"].id,
                "email": usuarios["consulta_a"].email,
                "membresia_id": membresias["consulta_a"],
                "rol": "CONSULTA",
            },
            "sin_membresia_a": {
                "id": usuarios["sin_membresia_a"].id,
                "email": usuarios["sin_membresia_a"].email,
                "membresia_id": None,
                "rol": None,
            },
            "inactivo_a": {
                "id": usuarios["inactivo_a"].id,
                "email": usuarios["inactivo_a"].email,
                "membresia_id": None,
                "rol": None,
                "is_active": False,
            },
        },
        "roles": roles,
        "permisos": {
            code: get_permission_by_code(db, code).id
            for code in PERMISOS_OFICIALES
        },
        "recursos": recursos,
        "seed": seed,
    }


def main() -> None:
    db = SessionLocal()
    try:
        _verificar_guardas(db)

        _log("fase 1: catalogo oficial (seed)")
        seed = _fase_catalogo(db)

        _log("fase 2: empresas ficticias")
        alpha, beta = _fase_empresas(db)

        _log("fase 3: usuarios ficticios")
        usuarios = _fase_usuarios(db)

        _log("fase 4: administradores bootstrap")
        admin_a_id, admin_b_id = _fase_admins(db, alpha, beta, usuarios)

        _log("fase 5: membresias CONTADOR/CAPTURISTA/CONSULTA")
        membresias = _fase_roles_operativos(db, alpha, usuarios, admin_a_id)

        _log("fase 6: recursos financieros ficticios")
        recursos = _fase_recursos(db, alpha, beta, usuarios, admin_a_id, admin_b_id)

        _log("fase 7: verificacion final")
        _verificacion_final(db, admin_a_id, admin_b_id, membresias)

        manifiesto = _manifiesto(
            db,
            seed,
            alpha,
            beta,
            usuarios,
            admin_a_id,
            admin_b_id,
            membresias,
            recursos,
        )
        print(json.dumps(manifiesto, ensure_ascii=False, indent=2))
        _log("SETUP COMPLETADO")
    except SystemExit:
        raise
    except Exception as exc:
        _log(f"FALLO: {type(exc).__name__}: {exc}")
        _log("no se emite manifiesto de exito")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
