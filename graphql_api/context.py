from fastapi import Request

from database.connection import SessionLocal
from models.user import User
from repositories.company_user_repository import get_active_company_user
from security.jwt import decode_access_token


def get_context(request: Request):
    db = SessionLocal()

    try:
        user = None
        company_user = None
        company_id = None
        auth_error = None

        authorization = request.headers.get("Authorization")

        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1].strip()

            if not token:
                auth_error = "Token inválido o expirado"
            else:
                try:
                    company_user_id, token_company_id = (
                        decode_access_token(token)
                    )
                except Exception:
                    auth_error = "Token inválido o expirado"
                else:
                    company_user = get_active_company_user(
                        db,
                        company_user_id,
                    )

                    if company_user is None:
                        auth_error = (
                            "La membresía no existe o está inactiva"
                        )
                    elif company_user.company_id != token_company_id:
                        company_user = None
                        auth_error = (
                            "El token no corresponde a la empresa "
                            "de la membresía"
                        )
                    else:
                        user = db.query(User).filter(
                            User.id == company_user.user_id,
                            User.is_active.is_(True)
                        ).first()

                        if user is None:
                            company_user = None
                            auth_error = "El usuario no está activo"
                        else:
                            company_id = company_user.company_id

        yield {
            "db": db,
            "user": user,
            "company_user": company_user,
            "company_id": company_id,
            "auth_error": auth_error,
        }

    finally:
        db.close()
