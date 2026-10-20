from sqlalchemy.orm import Session

from models.user import User
from repositories.company_user_repository import (
    get_active_company_user_by_user,
)
from repositories.user_repository import get_user_by_email
from security.jwt import create_access_token
from security.password import verify_password


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[str, User]:
    """Verifica la credencial y devuelve (token JWT, usuario).

    El usuario devuelto solo alimenta los datos minimos de la respuesta
    de login; el hash nunca se expone.
    """
    user = get_user_by_email(db, email)

    if user is None:
        raise ValueError("Credenciales inválidas")

    if not user.is_active:
        raise ValueError("El usuario está inactivo")

    if not verify_password(password, user.password_hash):
        raise ValueError("Credenciales inválidas")

    company_user = get_active_company_user_by_user(db, user.id)

    if company_user is None:
        raise ValueError(
            "El usuario no tiene una membresía activa"
        )

    token = create_access_token(
        company_user.id,
        company_user.company_id,
    )

    return token, user
