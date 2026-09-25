from sqlalchemy.orm import Session

from models.transaction import Transaction, TransactionType


def get_transaction(
    db: Session,
    transaction_id: int
) -> Transaction | None:
    return db.get(Transaction, transaction_id)


def create_transaction(
    db: Session,
    transaction: Transaction
) -> Transaction:
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def list_transactions(
    db: Session,
    account_id: int,
    transaction_type: TransactionType | None = None,
    limit: int = 50,
    offset: int = 0
) -> list[Transaction]:
    query = (
        db.query(Transaction)
        .filter(
            Transaction.account_id == account_id,
            Transaction.is_active.is_(True)
        )
    )

    if transaction_type is not None:
        query = query.filter(
            Transaction.transaction_type == transaction_type
        )

    return (
        query
        .order_by(Transaction.transaction_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )