from sqlalchemy.orm import Session

from models.company_user import CompanyUser
from models.company_user_role import CompanyUserRole
from repositories.company_repository import get_company
from repositories.company_user_repository import (
    create_company_user,
    get_active_company_admin,
    get_active_company_user,
    get_company_user,
    get_company_user_by_company_and_user,
)
from repositories.company_user_role_repository import (
    create_company_user_role,
    get_active_company_user_role,
    get_company_user_role_by_company_user_and_role,
)
from repositories.role_repository import get_role, get_role_by_code
from repositories.user_repository import get_user
from services.authorization_service import exigir_permiso


def create_company_user_service(
    db: Session,
    actor_company_user_id: int,
    company_id: int,
    user_id: int,
    is_admin: bool = False
) -> CompanyUser:

    exigir_permiso(
        db,
        actor_company_user_id,
        "company.users.write",
        company_id=company_id,
    )

    company = get_company(db, company_id)

    if company is None:
        raise ValueError("La empresa no existe")

    if not company.is_active:
        raise ValueError("La empresa no está activa")

    user = get_user(db, user_id)

    if user is None:
        raise ValueError("El usuario no existe")

    if not user.is_active:
        raise ValueError("El usuario no está activo")

    existing_membership = get_company_user_by_company_and_user(
        db,
        company_id,
        user_id,
    )

    if existing_membership is not None:
        raise ValueError(
            "El usuario ya pertenece a la empresa"
        )

    if is_admin:
        existing_admin = get_active_company_admin(db, company_id)

        if existing_admin is not None:
            raise ValueError(
                "La empresa ya tiene un administrador principal"
            )

        admin_role = get_role_by_code(db, "ADMINISTRADOR")

        if admin_role is None or not admin_role.is_active:
            raise ValueError(
                "El rol ADMINISTRADOR no existe o no está activo"
            )

    company_user = CompanyUser(
        company_id=company_id,
        user_id=user_id,
        is_admin=is_admin,
        is_active=True,
    )

    if is_admin:
        db.add(company_user)
        db.flush()

        relation = CompanyUserRole(
            company_user_id=company_user.id,
            role_id=admin_role.id,
            is_active=True,
        )

        db.add(relation)
        db.commit()
        db.refresh(company_user)

        return company_user

    return create_company_user(db, company_user)


def deactivate_company_user_service(
    db: Session,
    actor_company_user_id: int,
    company_user_id: int
) -> CompanyUser:

    company_user = get_company_user(db, company_user_id)

    if company_user is None:
        raise ValueError("La membresía no existe")

    exigir_permiso(
        db,
        actor_company_user_id,
        "company.users.write",
        company_id=company_user.company_id,
    )

    if not company_user.is_active:
        raise ValueError("La membresía ya está inactiva")

    company_user.is_active = False

    db.commit()
    db.refresh(company_user)

    return company_user


def assign_role_service(
    db: Session,
    actor_company_user_id: int,
    company_user_id: int,
    role_id: int
) -> CompanyUserRole:

    company_user = get_active_company_user(db, company_user_id)

    if company_user is None:
        raise ValueError(
            "La membresía no existe o está inactiva"
        )

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
        company_id=company_user.company_id,
    )

    role = get_role(db, role_id)

    if role is None:
        raise ValueError("El rol no existe")

    if not role.is_active:
        raise ValueError("El rol no está activo")

    active_role = get_active_company_user_role(
        db,
        company_user_id,
    )

    if active_role is not None:
        if active_role.role_id == role_id:
            raise ValueError(
                "La membresía ya tiene asignado este rol"
            )

        active_role.is_active = False

        db.commit()
        db.refresh(active_role)

    existing_relation = get_company_user_role_by_company_user_and_role(
        db,
        company_user_id,
        role_id,
    )

    if existing_relation is not None:
        existing_relation.is_active = True

        db.commit()
        db.refresh(existing_relation)

        return existing_relation

    relation = CompanyUserRole(
        company_user_id=company_user_id,
        role_id=role_id,
        is_active=True,
    )

    return create_company_user_role(db, relation)


def create_company_admin_service(
    db: Session,
    actor_company_user_id: int,
    company_id: int,
    user_id: int
) -> CompanyUser:

    company = get_company(db, company_id)

    if company is None:
        raise ValueError("La empresa no existe")

    if not company.is_active:
        raise ValueError("La empresa no está activa")

    user = get_user(db, user_id)

    if user is None:
        raise ValueError("El usuario no existe")

    if not user.is_active:
        raise ValueError("El usuario no está activo")

    existing_membership = get_company_user_by_company_and_user(
        db,
        company_id,
        user_id,
    )

    if existing_membership is not None:
        raise ValueError(
            "El usuario ya pertenece a la empresa"
        )

    existing_admin = get_active_company_admin(db, company_id)

    if existing_admin is not None:
        raise ValueError(
            "La empresa ya tiene un administrador principal"
        )

    admin_role = get_role_by_code(db, "ADMINISTRADOR")

    if admin_role is None or not admin_role.is_active:
        raise ValueError(
            "El rol ADMINISTRADOR no existe o no está activo"
        )

    company_user = CompanyUser(
        company_id=company_id,
        user_id=user_id,
        is_admin=True,
        is_active=True,
    )

    company_user = create_company_user(db, company_user)

    relation = CompanyUserRole(
        company_user_id=company_user.id,
        role_id=admin_role.id,
        is_active=True,
    )

    create_company_user_role(db, relation)

    return company_user
