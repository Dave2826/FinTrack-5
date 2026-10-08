from sqlalchemy.orm import Session

from models.role_permission import RolePermission
from repositories.permission_repository import get_permission
from repositories.role_permission_repository import (
    create_role_permission,
    get_role_permission,
    list_role_permissions,
)
from repositories.role_repository import get_role
from services.authorization_service import exigir_permiso


def assign_permission_to_role_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int,
    permission_id: int
) -> RolePermission:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
    )

    role = get_role(db, role_id)

    if role is None:
        raise ValueError("El rol no existe")

    permission = get_permission(db, permission_id)

    if permission is None:
        raise ValueError("El permiso no existe")

    relation = get_role_permission(
        db,
        role_id,
        permission_id,
    )

    if relation is not None:
        if relation.is_active:
            raise ValueError(
                "El permiso ya está asignado al rol"
            )

        relation.is_active = True

        db.commit()
        db.refresh(relation)

        return relation

    relation = RolePermission(
        role_id=role_id,
        permission_id=permission_id,
        is_active=True,
    )

    return create_role_permission(db, relation)


def remove_permission_from_role_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int,
    permission_id: int
) -> RolePermission:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
    )

    relation = get_role_permission(
        db,
        role_id,
        permission_id,
    )

    if relation is None:
        raise ValueError(
            "El permiso no está asignado al rol"
        )

    if not relation.is_active:
        raise ValueError(
            "El permiso ya está removido del rol"
        )

    relation.is_active = False

    db.commit()
    db.refresh(relation)

    return relation


def list_role_permissions_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int,
    active_only: bool = True
) -> list[RolePermission]:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.read",
    )

    role = get_role(db, role_id)

    if role is None:
        raise ValueError("El rol no existe")

    return list_role_permissions(
        db,
        role_id,
        active_only=active_only,
    )
