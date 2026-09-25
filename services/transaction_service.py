from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from models.transaction import Transaction, TransactionType
from models.company_user import CompanyUser
from repositories.account_concept_repository import get_relation
from repositories.account_repository import get_account
from repositories.concept_repository import get_concept
from repositories.transaction_repository import (
    create_transaction,
    get_transaction,
    list_transactions,
)
from repositories.user_repository import get_user


def create_transaction_service(
    db: Session,
    account_id: int,
    concept_id: int,
    transaction_type: TransactionType,
    amount: Decimal,
    captured_by: int,
    transaction_date: datetime | None = None,
    short_description: str | None = None,
    long_description: str | None = None,
) -> Transaction:

    if amount <= Decimal("0"):
        raise ValueError(
            "El monto de la transacción debe ser mayor que cero"
        )

    account = get_account(db, account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    if not account.is_active:
        raise ValueError("La cuenta no está activa")

    concept = get_concept(db, concept_id)

    if concept is None:
        raise ValueError("El concepto no existe")

    if not concept.is_active:
        raise ValueError("El concepto no está activo")

    user = get_user(db, captured_by)

    if user is None:
        raise ValueError("El usuario no existe")

    if not user.is_active:
        raise ValueError("El usuario no está activo")

    if account.company_id != concept.company_id:
        raise ValueError(
            "La cuenta y el concepto deben pertenecer a la misma empresa"
        )

    company_user = (
        db.query(CompanyUser)
        .filter(
            CompanyUser.company_id == account.company_id,
            CompanyUser.user_id == user.id,
            CompanyUser.is_active.is_(True),
        )
        .first()
    )

    if company_user is None:
        raise ValueError(
            "El usuario no pertenece a la empresa de la cuenta"
        )

    relation = get_relation(
        db,
        account_id=account_id,
        concept_id=concept_id
    )

    if relation is None or not relation.is_active:
        raise ValueError(
            "El concepto no está permitido para esta cuenta"
        )

    if transaction_type.value != concept.concept_type.value:
        raise ValueError(
            "El tipo de movimiento no coincide con el tipo de concepto"
        )

    transaction = Transaction(
        account_id=account_id,
        concept_id=concept_id,
        transaction_type=transaction_type,
        amount=amount,
        transaction_date=transaction_date or datetime.utcnow(),
        captured_at=datetime.utcnow(),
        captured_by=captured_by,
        short_description=short_description,
        long_description=long_description,
        is_active=True,
    )

    return create_transaction(db, transaction)


def get_transaction_service(
    db: Session,
    transaction_id: int
) -> Transaction:

    transaction = get_transaction(
        db,
        transaction_id
    )

    if transaction is None:
        raise ValueError("El movimiento no existe")

    return transaction


def list_transactions_service(
    db: Session,
    account_id: int,
    transaction_type: TransactionType | None = None,
    limit: int = 50,
    offset: int = 0
) -> list[Transaction]:

    account = get_account(db, account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    return list_transactions(
        db,
        account_id=account_id,
        transaction_type=transaction_type,
        limit=limit,
        offset=offset
    )


def delete_transaction_service(
    db: Session,
    transaction_id: int
) -> Transaction:

    transaction = get_transaction(
        db,
        transaction_id
    )

    if transaction is None:
        raise ValueError("El movimiento no existe")

    if not transaction.is_active:
        raise ValueError("El movimiento ya está eliminado")

    transaction.is_active = False

    db.commit()
    db.refresh(transaction)

    return transaction