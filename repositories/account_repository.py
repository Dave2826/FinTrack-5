from sqlalchemy.orm import Session

from models.account import Account, AccountType


def get_account(
    db: Session,
    account_id: int
) -> Account | None:
    return db.get(Account, account_id)


def create_account(
    db: Session,
    account: Account
) -> Account:
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def list_accounts(
    db: Session,
    company_id: int,
    account_type: AccountType | None = None,
    active_only: bool = True
) -> list[Account]:
    query = (
        db.query(Account)
        .filter(Account.company_id == company_id)
    )

    if account_type is not None:
        query = query.filter(
            Account.account_type == account_type
        )

    if active_only:
        query = query.filter(Account.is_active.is_(True))

    return query.order_by(Account.id).all()