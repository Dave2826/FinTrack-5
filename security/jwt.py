import os
from datetime import datetime, timedelta, timezone

import jwt


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

CAMPOS_REQUERIDOS = {"companyUserId", "companyId", "exp"}


def _obtener_secreto() -> str:
    secreto = os.getenv("JWT_SECRET")

    if not secreto or not secreto.strip():
        raise RuntimeError(
            "JWT_SECRET no está configurado; el token no puede emitirse"
        )

    return secreto


def create_access_token(
    company_user_id: int,
    company_id: int,
) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "companyUserId": int(company_user_id),
        "companyId": int(company_id),
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        _obtener_secreto(),
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> tuple[int, int]:
    payload = jwt.decode(
        token,
        _obtener_secreto(),
        algorithms=[ALGORITHM],
        options={"require": ["exp"]},
    )

    if set(payload.keys()) != CAMPOS_REQUERIDOS:
        raise ValueError(
            "El token no contiene los campos de identidad requeridos"
        )

    company_user_id = payload.get("companyUserId")
    company_id = payload.get("companyId")

    if not isinstance(company_user_id, int) or isinstance(
        company_user_id, bool
    ):
        raise ValueError("companyUserId inválido en el token")

    if not isinstance(company_id, int) or isinstance(company_id, bool):
        raise ValueError("companyId inválido en el token")

    return company_user_id, company_id
