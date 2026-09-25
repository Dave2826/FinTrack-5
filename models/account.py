from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class AccountType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    WALLET = "WALLET"
    OTHER = "OTHER"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
        index=True
    )

    account_type: Mapped[AccountType] = mapped_column(
        SQLEnum(AccountType),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    bank_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    account_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    clabe: Mapped[str | None] = mapped_column(
        String(18),
        nullable=True
    )

    card_last_digits: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True
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

    company = relationship(
        "Company",
        back_populates="accounts"
    )

    account_concepts = relationship(
        "AccountConcept",
        back_populates="account",
        cascade="all, delete-orphan"
    )

    transactions = relationship(
        "Transaction",
        back_populates="account"
    )