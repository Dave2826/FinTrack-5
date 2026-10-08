from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permission"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"),
        nullable=False,
        index=True
    )

    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id"),
        nullable=False,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    role = relationship(
        "Role",
        back_populates="role_permissions"
    )

    permission = relationship(
        "Permission",
        back_populates="role_permissions"
    )
