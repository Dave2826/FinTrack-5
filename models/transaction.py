from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class TransactionType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
        index=True
    )

    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id"),
        nullable=False,
        index=True
    )

    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType),
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    captured_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    short_description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    long_description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    account = relationship(
        "Account",
        back_populates="transactions"
    )

    concept = relationship(
        "Concept",
        back_populates="transactions"
    )

    captured_by_user = relationship(
        "User",
        foreign_keys=[captured_by]
    )