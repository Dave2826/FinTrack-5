from sqlalchemy.orm import Session

from models.company_user import CompanyUser


def get_company_user(
    db: Session,
    company_user_id: int
) -> CompanyUser | None:
    return db.get(CompanyUser, company_user_id)


def get_company_user_by_company_and_user(
    db: Session,
    company_id: int,
    user_id: int
) -> CompanyUser | None:
    return (
        db.query(CompanyUser)
        .filter(
            CompanyUser.company_id == company_id,
            CompanyUser.user_id == user_id,
        )
        .first()
    )


def get_active_company_user(
    db: Session,
    company_user_id: int
) -> CompanyUser | None:
    return (
        db.query(CompanyUser)
        .filter(
            CompanyUser.id == company_user_id,
            CompanyUser.is_active.is_(True),
        )
        .first()
    )


def get_active_company_user_by_user(
    db: Session,
    user_id: int
) -> CompanyUser | None:
    """Primera membresía activa del usuario, ordenada por id.

    Supuesto D4: si el usuario tiene varias membresías activas se elige
    de forma determinista la de menor `CompanyUser.id`. El cliente nunca
    elige la empresa; el `companyId` del token sale de esta membresía.
    """

    return (
        db.query(CompanyUser)
        .filter(
            CompanyUser.user_id == user_id,
            CompanyUser.is_active.is_(True),
        )
        .order_by(CompanyUser.id)
        .first()
    )


def get_active_company_admin(
    db: Session,
    company_id: int
) -> CompanyUser | None:
    return (
        db.query(CompanyUser)
        .filter(
            CompanyUser.company_id == company_id,
            CompanyUser.is_active.is_(True),
            CompanyUser.is_admin.is_(True),
        )
        .first()
    )


def create_company_user(
    db: Session,
    company_user: CompanyUser
) -> CompanyUser:
    db.add(company_user)
    db.commit()
    db.refresh(company_user)
    return company_user
