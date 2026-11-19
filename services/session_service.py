from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.company import Company
from models.company_user import CompanyUser
from models.role import Role
from models.user import User
from repositories.company_user_role_repository import (
    get_active_company_user_role,
    list_active_permission_codes,
)


@dataclass
class SessionSnapshot:
    company_user: CompanyUser
    company: Company
    user: User
    role: Role | None
    permissions: list[str]


def active_role_for(db: Session, company_user_id: int) -> Role | None:
    """Rol activo de la membresía, o None si no tiene (o está inactivo)."""

    relation = get_active_company_user_role(db, company_user_id)

    if relation is None or relation.role is None:
        return None

    if not relation.role.is_active:
        return None

    return relation.role


def session_snapshot_service(
    db: Session,
    company_user: CompanyUser,
) -> SessionSnapshot:
    """Identidad de la sesión: empresa, usuario, rol y permisos efectivos.

    No exige un permiso concreto: cada membresía puede leer su propia
    sesión. El dashboard la usa solo para decidir qué botones dibujar; el
    backend sigue autorizando cada operación con `exigir_permiso`.
    """

    role = active_role_for(db, company_user.id)

    permissions = (
        sorted(set(list_active_permission_codes(db, company_user.id)))
        if role is not None
        else []
    )

    return SessionSnapshot(
        company_user=company_user,
        company=company_user.company,
        user=company_user.user,
        role=role,
        permissions=permissions,
    )
