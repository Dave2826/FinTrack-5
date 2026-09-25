from sqlalchemy.orm import Session

from models.account_concept import AccountConcept


def get_account_concept(
    db: Session,
    account_concept_id: int
) -> AccountConcept | None:
    return db.get(AccountConcept, account_concept_id)


def get_relation(
    db: Session,
    account_id: int,
    concept_id: int
) -> AccountConcept | None:
    return (
        db.query(AccountConcept)
        .filter(
            AccountConcept.account_id == account_id,
            AccountConcept.concept_id == concept_id
        )
        .first()
    )


def create_relation(
    db: Session,
    relation: AccountConcept
) -> AccountConcept:
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


def list_account_concepts(
    db: Session,
    account_id: int,
    active_only: bool = True
) -> list[AccountConcept]:
    query = (
        db.query(AccountConcept)
        .filter(AccountConcept.account_id == account_id)
    )

    if active_only:
        query = query.filter(
            AccountConcept.is_active.is_(True)
        )

    return query.order_by(AccountConcept.id).all()