from sqlalchemy.orm import Session

from models.user import User
from repositories.user_repository import get_user_by_email
from security.jwt import create_access_token
from security.password import verify_password


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> str:
    user = get_user_by_email(db, email)

    if user is None:
        raise ValueError("Credenciales inválidas")

    if not user.is_active:
        raise ValueError("El usuario está inactivo")

    if not verify_password(password, user.password_hash):
        raise ValueError("Credenciales inválidas")

    return create_access_token(user.id)