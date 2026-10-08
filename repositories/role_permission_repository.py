from sqlalchemy.orm import Session

from models.role_permission import RolePermission


def get_role_permission(
    db: Session,
    role_id: int,
    permission_id: int
) -> RolePermission | None:
    return (
        db.query(RolePermission)
        .filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        .first()
    )


def list_role_permissions(
    db: Session,
    role_id: int,
    active_only: bool = True
) -> list[RolePermission]:
    query = (
        db.query(RolePermission)
        .filter(RolePermission.role_id == role_id)
    )

    if active_only:
        query = query.filter(RolePermission.is_active.is_(True))

    return query.order_by(RolePermission.id).all()


def create_role_permission(
    db: Session,
    role_permission: RolePermission
) -> RolePermission:
    db.add(role_permission)
    db.commit()
    db.refresh(role_permission)
    return role_permission
