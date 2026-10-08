from sqlalchemy.orm import Session

from models.role import Role


def get_role(
    db: Session,
    role_id: int
) -> Role | None:
    return db.get(Role, role_id)


def get_role_by_code(
    db: Session,
    code: str
) -> Role | None:
    return (
        db.query(Role)
        .filter(Role.code == code)
        .first()
    )


def list_roles(
    db: Session,
    active_only: bool = True
) -> list[Role]:
    query = db.query(Role)

    if active_only:
        query = query.filter(Role.is_active.is_(True))

    return query.order_by(Role.id).all()


def create_role(
    db: Session,
    role: Role
) -> Role:
    db.add(role)
    db.commit()
    db.refresh(role)
    return role
