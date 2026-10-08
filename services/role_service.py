from sqlalchemy.orm import Session

from models.role import Role
from repositories.role_repository import (
    create_role,
    get_role,
    get_role_by_code,
    list_roles,
)
from services.authorization_service import exigir_permiso


def create_role_service(
    db: Session,
    actor_company_user_id: int,
    code: str,
    name: str,
    description: str | None = None
) -> Role:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
    )

    existing_role = get_role_by_code(db, code)

    if existing_role is not None:
        raise ValueError(
            "Ya existe un rol con ese código"
        )

    role = Role(
        code=code,
        name=name,
        description=description,
        is_active=True,
    )

    return create_role(db, role)


def deactivate_role_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int
) -> Role:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
    )

    role = get_role(db, role_id)

    if role is None:
        raise ValueError("El rol no existe")

    if not role.is_active:
        raise ValueError("El rol ya está desactivado")

    role.is_active = False

    db.commit()
    db.refresh(role)

    return role


def list_roles_service(
    db: Session,
    actor_company_user_id: int,
    active_only: bool = True
) -> list[Role]:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.read",
    )

    return list_roles(db, active_only=active_only)
