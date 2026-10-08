from sqlalchemy.orm import Session

from models.permission import Permission
from repositories.permission_repository import (
    create_permission,
    get_permission_by_code,
    list_permissions,
)
from services.authorization_service import exigir_permiso


def create_permission_service(
    db: Session,
    actor_company_user_id: int,
    code: str,
    name: str,
    description: str | None = None
) -> Permission:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
    )

    existing_permission = get_permission_by_code(db, code)

    if existing_permission is not None:
        raise ValueError(
            "Ya existe un permiso con ese código"
        )

    permission = Permission(
        code=code,
        name=name,
        description=description,
        is_active=True,
    )

    return create_permission(db, permission)


def list_permissions_service(
    db: Session,
    actor_company_user_id: int,
    active_only: bool = True
) -> list[Permission]:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.read",
    )

    return list_permissions(db, active_only=active_only)
