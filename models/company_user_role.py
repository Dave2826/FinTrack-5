from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class CompanyUserRole(Base):
    __tablename__ = "company_user_roles"

    __table_args__ = (
        UniqueConstraint(
            "company_user_id",
            "role_id",
            name="uq_company_user_role"
        ),
        Index(
            "uq_company_user_role_active",
            "company_user_id",
            unique=True,
            postgresql_where=text("is_active")
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    company_user_id: Mapped[int] = mapped_column(
        ForeignKey("company_users.id"),
        nullable=False,
        index=True
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"),
        nullable=False,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    company_user = relationship(
        "CompanyUser",
        back_populates="company_user_roles"
    )

    role = relationship(
        "Role",
        back_populates="company_user_roles"
    )
