from sqlalchemy.orm import Session

from models.company_user import CompanyUser
from repositories.company_user_repository import get_active_company_user
from repositories.company_user_role_repository import (
    get_active_company_user_role,
    list_active_permission_codes,
)


def exigir_permiso(
    db: Session,
    company_user_id: int,
    codigo: str
) -> CompanyUser:

    company_user = get_active_company_user(db, company_user_id)

    if company_user is None:
        raise PermissionError(
            "La membresía no tiene un rol activo"
        )

    company_user_role = get_active_company_user_role(
        db,
        company_user_id
    )

    if company_user_role is None:
        raise PermissionError(
            "La membresía no tiene un rol activo"
        )

    if not company_user_role.role.is_active:
        raise PermissionError(
            "La membresía no tiene un rol activo"
        )

    permisos = list_active_permission_codes(
        db,
        company_user_id
    )

    if codigo not in permisos:
        raise PermissionError(
            f"El rol no tiene el permiso {codigo}"
        )

    return company_user
