from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    role_permissions = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan"
    )
