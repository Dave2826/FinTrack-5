from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class ConceptType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
        index=True
    )

    concept_type: Mapped[ConceptType] = mapped_column(
        SQLEnum(ConceptType),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
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
        back_populates="concepts"
    )

    account_concepts = relationship(
        "AccountConcept",
        back_populates="concept",
        cascade="all, delete-orphan"
    )

    transactions = relationship(
        "Transaction",
        back_populates="concept"
    ) 