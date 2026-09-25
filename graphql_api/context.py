from fastapi import Request
from database.connection import SessionLocal
from models.user import User
from security.jwt import decode_access_token


def get_context(request: Request):
    db = SessionLocal()

    try:
        user = None

        authorization = request.headers.get("Authorization")

        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]

            try:
                user_id = decode_access_token(token)
                user = db.query(User).filter(
                    User.id == user_id,
                    User.is_active.is_(True)
                ).first()
            except Exception:
                user = None

        yield {
            "db": db,
            "user": user
        }

    finally:
        db.close()