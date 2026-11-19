import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.transaction import Transaction, TransactionType
from models.company_user import CompanyUser
from models.idempotency_key import IdempotencyKey
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
OPERACION_CREATE_TRANSACTION = "createTransaction"
LONGITUD_MAXIMA_LLAVE = 255
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


def _normalizar_llave(idempotency_key: str | None) -> str | None:
    """Valida la llave de idempotencia enviada por el cliente."""

    if idempotency_key is None:
        return None

    if not isinstance(idempotency_key, str):
        raise ValueError("La llave de idempotencia no es válida")

    llave = idempotency_key.strip()

    if not llave:
        raise ValueError("La llave de idempotencia no puede estar vacía")

    if len(llave) > LONGITUD_MAXIMA_LLAVE:
        raise ValueError(
            "La llave de idempotencia excede la longitud permitida"
        )

    return llave


def _hash_cuerpo(
    account_id: int,
    concept_id: int,
    transaction_type: TransactionType,
    monto: Decimal,
    transaction_date: datetime | None,
    short_description: str | None,
    long_description: str | None,
) -> str:
    """SHA-256 del cuerpo normalizado de createTransaction.

    La fecha ausente se guarda como null (el servidor la completa), así un
    reintento sin fecha coincide con el primer envío sin fecha.
    """

    cuerpo = {
        "accountId": int(account_id),
        "conceptId": int(concept_id),
        "transactionType": transaction_type.value,
        "amount": str(monto),
        "transactionDate": (
            transaction_date.isoformat()
            if transaction_date is not None
            else None
        ),
        "shortDescription": short_description,
        "longDescription": long_description,
    }

    serializado = json.dumps(
        cuerpo,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _buscar_llave(
    db: Session,
    company_id: int,
    llave: str,
) -> IdempotencyKey | None:
    return (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.company_id == company_id,
            IdempotencyKey.operation == OPERACION_CREATE_TRANSACTION,
            IdempotencyKey.idempotency_key == llave,
        )
        .first()
    )


def _resolver_reintento(
    registro: IdempotencyKey,
    request_hash: str,
) -> Transaction:
    """Devuelve el movimiento guardado o rechaza la llave reutilizada."""

    if registro.request_hash != request_hash:
        raise ValueError(
            "La llave de idempotencia ya se usó con otros datos"
        )

    return registro.transaction


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
    idempotency_key: str | None = None,
) -> Transaction:
    """Crea un movimiento.

    Con `idempotency_key`, el movimiento y la llave se confirman en un único
    COMMIT. Un reintento con la misma llave y el mismo cuerpo devuelve el
    movimiento ya guardado sin otro INSERT; la misma llave con otros datos
    se rechaza. Sin llave, el comportamiento es el de los parciales previos.
    """

    monto = _normalizar_monto(amount)
    llave = _normalizar_llave(idempotency_key)
    fecha_enviada = (
        _normalizar_fecha_operacion(transaction_date)
        if transaction_date is not None
        else None
    )
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

    request_hash = None

    if llave is not None:
        request_hash = _hash_cuerpo(
            account_id,
            concept_id,
            transaction_type,
            monto,
            fecha_enviada,
            short_description,
            long_description,
        )

        # El reintento se resuelve antes de las validaciones de negocio:
        # devuelve el mismo movimiento aunque, por ejemplo, la cuenta se
        # haya desactivado después del primer envío.
        registro = _buscar_llave(db, account.company_id, llave)

        if registro is not None:
            return _resolver_reintento(registro, request_hash)

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

    if llave is None:
        return create_transaction(db, transaction)

    try:
        db.add(transaction)
        db.flush()

        db.add(
            IdempotencyKey(
                company_id=account.company_id,
                operation=OPERACION_CREATE_TRANSACTION,
                idempotency_key=llave,
                request_hash=request_hash,
                transaction_id=transaction.id,
                company_user_id=actor_company_user_id,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        # Un solo COMMIT: si falla, no queda ni el movimiento ni la llave.
        db.commit()
    except IntegrityError:
        # Otra petición con la misma llave confirmó primero (doble clic
        # concurrente). Se descarta este INSERT y se lee el ganador.
        db.rollback()

        registro = _buscar_llave(db, account.company_id, llave)

        if registro is None:
            raise

        return _resolver_reintento(registro, request_hash)
    except Exception:
        db.rollback()
        raise

    db.refresh(transaction)

    return transaction


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