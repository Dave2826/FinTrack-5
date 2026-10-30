from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

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
from services.authorization_service import exigir_permiso


CENTAVO = Decimal("0.01")
MONTO_MAXIMO = Decimal("9999999999999.99")


def _normalizar_monto(amount) -> Decimal:
    """Valida y normaliza el importe sin redondear silenciosamente."""

    try:
        if isinstance(amount, Decimal):
            valor = amount
        elif isinstance(amount, bool):
            raise ValueError
        else:
            valor = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("El monto de la transacción no es válido")

    if not valor.is_finite():
        raise ValueError(
            "El monto de la transacción debe ser un número finito"
        )

    if valor <= Decimal("0"):
        raise ValueError(
            "El monto de la transacción debe ser mayor que cero"
        )

    try:
        cuantizado = valor.quantize(CENTAVO)
    except InvalidOperation:
        raise ValueError(
            "El monto de la transacción excede la precisión permitida"
        )

    if valor != cuantizado:
        raise ValueError(
            "El monto de la transacción no puede tener más de dos decimales"
        )

    if cuantizado > MONTO_MAXIMO:
        raise ValueError(
            "El monto de la transacción excede el máximo permitido"
        )

    return cuantizado


def _normalizar_fecha_operacion(valor: datetime | None) -> datetime:
    """Devuelve la fecha de operación como UTC sin zona horaria."""

    if valor is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    if not isinstance(valor, datetime):
        raise ValueError("La fecha de operación no es válida")

    if valor.tzinfo is not None and valor.utcoffset() is not None:
        return valor.astimezone(timezone.utc).replace(tzinfo=None)

    return valor


def create_transaction_service(
    db: Session,
    actor_company_user_id: int,
    account_id: int,
    concept_id: int,
    transaction_type: TransactionType,
    amount: Decimal,
    captured_by: int,
    transaction_date: datetime | None = None,
    short_description: str | None = None,
    long_description: str | None = None,
) -> Transaction:

    monto = _normalizar_monto(amount)
    fecha_operacion = _normalizar_fecha_operacion(transaction_date)

    account = get_account(db, account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    exigir_permiso(
        db,
        actor_company_user_id,
        "transactions.write",
        company_id=account.company_id,
    )

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
        amount=monto,
        transaction_date=fecha_operacion,
        captured_at=datetime.now(timezone.utc).replace(tzinfo=None),
        captured_by=captured_by,
        short_description=short_description,
        long_description=long_description,
        is_active=True,
    )

    return create_transaction(db, transaction)


def get_transaction_service(
    db: Session,
    actor_company_user_id: int,
    transaction_id: int
) -> Transaction:

    transaction = get_transaction(
        db,
        transaction_id
    )

    if transaction is None:
        raise ValueError("El movimiento no existe")

    account = get_account(db, transaction.account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    exigir_permiso(
        db,
        actor_company_user_id,
        "transactions.read",
        company_id=account.company_id,
    )

    return transaction


def list_transactions_service(
    db: Session,
    actor_company_user_id: int,
    account_id: int,
    transaction_type: TransactionType | None = None,
    limit: int = 50,
    offset: int = 0
) -> list[Transaction]:

    account = get_account(db, account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    exigir_permiso(
        db,
        actor_company_user_id,
        "transactions.read",
        company_id=account.company_id,
    )

    return list_transactions(
        db,
        account_id=account_id,
        transaction_type=transaction_type,
        limit=limit,
        offset=offset
    )


def delete_transaction_service(
    db: Session,
    actor_company_user_id: int,
    transaction_id: int
) -> Transaction:

    transaction = get_transaction(
        db,
        transaction_id
    )

    if transaction is None:
        raise ValueError("El movimiento no existe")

    account = get_account(db, transaction.account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    exigir_permiso(
        db,
        actor_company_user_id,
        "transactions.write",
        company_id=account.company_id,
    )

    if not transaction.is_active:
        raise ValueError("El movimiento ya está eliminado")

    transaction.is_active = False

    db.commit()
    db.refresh(transaction)

    return transaction