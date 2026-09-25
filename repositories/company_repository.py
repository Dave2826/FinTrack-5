from sqlalchemy.orm import Session

from models.company import Company


def get_company(
    db: Session,
    company_id: int
) -> Company | None:
    return db.get(Company, company_id)


def create_company(
    db: Session,
    company: Company
) -> Company:
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def list_companies(
    db: Session,
    active_only: bool = True
) -> list[Company]:
    query = db.query(Company)

    if active_only:
        query = query.filter(Company.is_active.is_(True))

    return query.order_by(Company.id).all()