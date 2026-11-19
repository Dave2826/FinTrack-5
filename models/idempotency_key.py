from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class IdempotencyKey(Base):
    """Llave de idempotencia de una mutación (Unidad III, Actividad 13).

    La llave la genera el cliente una vez por acción. Se guarda en la misma
    transacción que el movimiento que crea: si el commit falla no queda ni
    el movimiento ni la llave; si el commit pasa y la respuesta se pierde,
    el reintento encuentra la llave y devuelve el mismo movimiento.
    """

    __tablename__ = "idempotency_keys"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_company_operation_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
    )

    operation: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # SHA-256 del cuerpo normalizado de la petición; distingue el reintento
    # legítimo de una llave reutilizada con otros datos.
    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False,
        index=True,
    )

    company_user_id: Mapped[int] = mapped_column(
        ForeignKey("company_users.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    transaction = relationship("Transaction")
