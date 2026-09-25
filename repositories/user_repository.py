from sqlalchemy.orm import Session

from models.user import User


def get_user(
    db: Session,
    user_id: int
) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(
    db: Session,
    email: str
) -> User | None:
    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


def create_user(
    db: Session,
    user: User
) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session,
    active_only: bool = True
) -> list[User]:
    query = db.query(User)

    if active_only:
        query = query.filter(User.is_active.is_(True))

    return query.order_by(User.id).all()