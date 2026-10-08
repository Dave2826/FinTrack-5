from sqlalchemy.orm import Session

from models.company_user_role import CompanyUserRole
from models.permission import Permission
from models.role import Role
from models.role_permission import RolePermission


def get_company_user_role(
    db: Session,
    company_user_role_id: int
) -> CompanyUserRole | None:
    return db.get(CompanyUserRole, company_user_role_id)


def get_active_company_user_role(
    db: Session,
    company_user_id: int
) -> CompanyUserRole | None:
    return (
        db.query(CompanyUserRole)
        .filter(
            CompanyUserRole.company_user_id == company_user_id,
            CompanyUserRole.is_active.is_(True),
        )
        .first()
    )


def get_company_user_role_by_company_user_and_role(
    db: Session,
    company_user_id: int,
    role_id: int
) -> CompanyUserRole | None:
    return (
        db.query(CompanyUserRole)
        .filter(
            CompanyUserRole.company_user_id == company_user_id,
            CompanyUserRole.role_id == role_id,
        )
        .first()
    )


def create_company_user_role(
    db: Session,
    company_user_role: CompanyUserRole
) -> CompanyUserRole:
    db.add(company_user_role)
    db.commit()
    db.refresh(company_user_role)
    return company_user_role


def list_active_permission_codes(
    db: Session,
    company_user_id: int
) -> list[str]:
    rows = (
        db.query(Permission.code)
        .select_from(CompanyUserRole)
        .join(Role, Role.id == CompanyUserRole.role_id)
        .join(
            RolePermission,
            RolePermission.role_id == Role.id,
        )
        .join(
            Permission,
            Permission.id == RolePermission.permission_id,
        )
        .filter(
            CompanyUserRole.company_user_id == company_user_id,
            CompanyUserRole.is_active.is_(True),
            Role.is_active.is_(True),
            RolePermission.is_active.is_(True),
            Permission.is_active.is_(True),
        )
        .all()
    )

    return [code for (code,) in rows]
