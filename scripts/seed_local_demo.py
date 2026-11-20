"""Crea el administrador inicial para el entorno local de desarrollo.

Uso:
    docker compose up -d --build
    docker compose exec -it api python -m scripts.seed_local_demo
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import text

from database.connection import SessionLocal
from models.company import Company
from models.company_user import CompanyUser
from models.company_user_role import CompanyUserRole
from models.role import Role
from models.user import User
from security.password import hash_password
from services.company_user_service import (
    LONGITUD_MAXIMA_CONTRASENA,
    LONGITUD_MINIMA_CONTRASENA,
)
from services.seed_service import cargar_catalogo_inicial


DB_ESPERADA = "actividad5"
EMPRESA_TAX_ID = "FINTRACK-LOCAL-2026"
EMPRESA_NOMBRE = "FinTrack Local"


def abortar(mensaje: str) -> None:
    print(f"[seed-local] ERROR: {mensaje}", file=sys.stderr)
    raise SystemExit(1)


def obtener_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea el administrador inicial del entorno local."
    )
    parser.add_argument("--email", default="admin@fintrackapp.com")
    parser.add_argument("--name", default="Administrador Local")
    return parser.parse_args()


def solicitar_contrasena() -> str:
    contrasena = getpass.getpass("Contraseña del administrador local: ")
    confirmacion = getpass.getpass("Confirmar contraseña: ")

    if contrasena != confirmacion:
        abortar("las contraseñas no coinciden")
    if not LONGITUD_MINIMA_CONTRASENA <= len(contrasena) <= LONGITUD_MAXIMA_CONTRASENA:
        abortar(
            "la contraseña debe tener entre "
            f"{LONGITUD_MINIMA_CONTRASENA} y {LONGITUD_MAXIMA_CONTRASENA} caracteres"
        )
    return contrasena


def main() -> None:
    argumentos = obtener_argumentos()

    if os.getenv("DB_NAME") != DB_ESPERADA:
        abortar(f"DB_NAME debe ser {DB_ESPERADA}")

    db = SessionLocal()
    try:
        if db.execute(text("SELECT current_database()")).scalar() != DB_ESPERADA:
            abortar(f"la base conectada debe ser {DB_ESPERADA}")

        cargar_catalogo_inicial(db)

        empresa = (
            db.query(Company)
            .filter(Company.tax_id == EMPRESA_TAX_ID)
            .first()
        )
        if empresa is None:
            empresa = Company(
                name=EMPRESA_NOMBRE,
                legal_name=EMPRESA_NOMBRE,
                tax_id=EMPRESA_TAX_ID,
                email="contacto@fintrackapp.com",
                is_active=True,
            )
            db.add(empresa)
            db.flush()
        elif empresa.name != EMPRESA_NOMBRE or not empresa.is_active:
            abortar("la empresa local existente no es compatible")

        usuario = db.query(User).filter(User.email == argumentos.email).first()
        if usuario is None:
            contrasena = solicitar_contrasena()
            usuario = User(
                name=argumentos.name,
                email=argumentos.email,
                password_hash=hash_password(contrasena),
                email_verified=True,
                is_active=True,
            )
            db.add(usuario)
            db.flush()
        elif not usuario.is_active:
            abortar("el usuario existente está inactivo")

        membresia = (
            db.query(CompanyUser)
            .filter(
                CompanyUser.company_id == empresa.id,
                CompanyUser.user_id == usuario.id,
            )
            .first()
        )
        if membresia is None:
            rol = (
                db.query(Role)
                .filter(Role.code == "ADMINISTRADOR", Role.is_active.is_(True))
                .first()
            )
            if rol is None:
                abortar("no existe el rol ADMINISTRADOR activo")

            membresia = CompanyUser(
                company_id=empresa.id,
                user_id=usuario.id,
                is_admin=True,
                is_active=True,
            )
            db.add(membresia)
            db.flush()
            db.add(
                CompanyUserRole(
                    company_user_id=membresia.id,
                    role_id=rol.id,
                    is_active=True,
                )
            )
        elif not membresia.is_active or not membresia.is_admin:
            abortar("la membresía existente no es un administrador activo")

        db.commit()
        print(
            "[seed-local] Administrador local listo: "
            f"{usuario.email} (empresa: {empresa.name})"
        )
    except SystemExit:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        abortar(f"{type(exc).__name__}: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
