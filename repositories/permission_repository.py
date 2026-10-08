from sqlalchemy.orm import Session

from models.permission import Permission


def get_permission(
    db: Session,
    permission_id: int
) -> Permission | None:
    return db.get(Permission, permission_id)


def get_permission_by_code(
    db: Session,
    code: str
) -> Permission | None:
    return (
        db.query(Permission)
        .filter(Permission.code == code)
        .first()
    )


def list_permissions(
    db: Session,
    active_only: bool = True
) -> list[Permission]:
    query = db.query(Permission)

    if active_only:
        query = query.filter(Permission.is_active.is_(True))

    return query.order_by(Permission.id).all()


def create_permission(
    db: Session,
    permission: Permission
) -> Permission:
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission
