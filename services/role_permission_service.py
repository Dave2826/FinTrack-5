from sqlalchemy.orm import Session

from models.permission import Permission
from models.role import Role
from models.role_permission import RolePermission
from repositories.permission_repository import (
    get_permission,
    list_permissions_by_prefix,
)
from repositories.role_permission_repository import (
    create_role_permission,
    get_role_permission,
    list_role_permissions,
)
from repositories.role_repository import get_role
from services.authorization_service import exigir_permiso


def assign_permission_to_role_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int,
    permission_id: int
) -> RolePermission:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
    )

    role = get_role(db, role_id)

    if role is None:
        raise ValueError("El rol no existe")

    permission = get_permission(db, permission_id)

    if permission is None:
        raise ValueError("El permiso no existe")

    relation = get_role_permission(
        db,
        role_id,
        permission_id,
    )

    if relation is not None:
        if relation.is_active:
            raise ValueError(
                "El permiso ya está asignado al rol"
            )

        relation.is_active = True

        db.commit()
        db.refresh(relation)

        return relation

    relation = RolePermission(
        role_id=role_id,
        permission_id=permission_id,
        is_active=True,
    )

    return create_role_permission(db, relation)


def remove_permission_from_role_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int,
    permission_id: int
) -> RolePermission:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
    )

    relation = get_role_permission(
        db,
        role_id,
        permission_id,
    )

    if relation is None:
        raise ValueError(
            "El permiso no está asignado al rol"
        )

    if not relation.is_active:
        raise ValueError(
            "El permiso ya está removido del rol"
        )

    role = get_role(db, role_id)
    permission = get_permission(db, permission_id)

    if (
        role is not None
        and permission is not None
        and role.code == "ADMINISTRADOR"
        and permission.code == "roles.write"
    ):
        raise ValueError(
            "No se puede retirar el permiso roles.write del rol ADMINISTRADOR"
        )

    relation.is_active = False

    db.commit()
    db.refresh(relation)

    return relation


def list_role_permissions_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int,
    active_only: bool = True
) -> list[RolePermission]:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.read",
    )

    role = get_role(db, role_id)

    if role is None:
        raise ValueError("El rol no existe")

    return list_role_permissions(
        db,
        role_id,
        active_only=active_only,
    )


def permission_catalog_service(
    db: Session,
    actor_company_user_id: int,
    prefix: str | None = None
) -> list[Permission]:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.read",
    )

    return list_permissions_by_prefix(db, prefix=prefix)


def _normalizar_ids(permission_ids: list) -> list[int]:
    normalizados: list[int] = []

    for valor in permission_ids:
        try:
            normalizados.append(int(valor))
        except (TypeError, ValueError):
            raise ValueError(
                f"El ID de permiso no es válido: {valor}"
            )

    vistos = set()
    repetidos = set()

    for identificador in normalizados:
        if identificador in vistos:
            repetidos.add(identificador)
        vistos.add(identificador)

    if repetidos:
        ordenados = ", ".join(str(v) for v in sorted(repetidos))
        raise ValueError(
            f"permissionIds contiene IDs repetidos: {ordenados}"
        )

    return normalizados


def _validar_propuesta(
    db: Session,
    role_id: int,
    permission_ids: list
) -> tuple[Role, list[Permission]]:

    role = get_role(db, role_id)

    if role is None:
        raise ValueError("El rol no existe")

    if not role.is_active:
        raise ValueError("El rol no está activo")

    if role.code == "ADMINISTRADOR":
        raise ValueError(
            "No se puede modificar la configuración de permisos "
            "del rol ADMINISTRADOR"
        )

    normalizados = _normalizar_ids(permission_ids)

    permisos: list[Permission] = []

    for identificador in normalizados:
        permission = get_permission(db, identificador)

        if permission is None:
            raise ValueError(
                f"El permiso con id {identificador} no existe"
            )

        if not permission.is_active:
            raise ValueError(
                f"El permiso {permission.code} no está activo"
            )

        permisos.append(permission)

    permisos.sort(key=lambda permission: permission.code)

    return role, permisos


def _calcular_plan(
    db: Session,
    role: Role,
    deseados: list[Permission],
    activas: list[RolePermission]
) -> dict:

    activas_por_permiso = {
        relation.permission_id: relation
        for relation in activas
    }

    # Configuración activa completa del rol, no la intersección con la
    # propuesta: current refleja el estado previo tal cual es.
    actuales: list[Permission] = []

    for permission_id in activas_por_permiso:
        permission = get_permission(db, permission_id)

        if permission is None:
            raise ValueError(
                f"El permiso con id {permission_id} no existe"
            )

        actuales.append(permission)

    actuales.sort(key=lambda permission: permission.code)

    deseados_por_id = {permission.id: permission for permission in deseados}

    to_activate = sorted(
        [
            permission
            for permission in deseados
            if permission.id not in activas_por_permiso
        ],
        key=lambda permission: permission.code,
    )

    to_deactivate = sorted(
        [
            permission
            for permission in actuales
            if permission.id not in deseados_por_id
        ],
        key=lambda permission: permission.code,
    )

    unchanged = sorted(
        [
            permission
            for permission in actuales
            if permission.id in deseados_por_id
        ],
        key=lambda permission: permission.code,
    )

    return {
        "role": role,
        "current": actuales,
        "to_activate": to_activate,
        "to_deactivate": to_deactivate,
        "unchanged": unchanged,
        "final_count": len(deseados),
    }


def _construir_resumen(plan: dict) -> dict:

    changed = bool(plan["to_activate"] or plan["to_deactivate"])

    return {
        "role": plan["role"],
        "activated": plan["to_activate"],
        "deactivated": plan["to_deactivate"],
        "unchanged": plan["unchanged"],
        "final_count": plan["final_count"],
        "changed": changed,
    }


def preview_role_permissions_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int,
    permission_ids: list
) -> dict:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.read",
    )

    role, deseados = _validar_propuesta(db, role_id, permission_ids)

    activas = list_role_permissions(
        db,
        role.id,
        active_only=True,
    )

    return _calcular_plan(db, role, deseados, activas)


def set_role_permissions_service(
    db: Session,
    actor_company_user_id: int,
    role_id: int,
    permission_ids: list
) -> dict:

    exigir_permiso(
        db,
        actor_company_user_id,
        "roles.write",
    )

    role, deseados = _validar_propuesta(db, role_id, permission_ids)

    filas = list_role_permissions(
        db,
        role.id,
        active_only=False,
    )

    activas = [fila for fila in filas if fila.is_active]

    plan = _calcular_plan(db, role, deseados, activas)

    try:
        filas_por_permiso = {
            fila.permission_id: fila for fila in filas
        }

        for permission in plan["to_activate"]:
            fila = filas_por_permiso.get(permission.id)

            if fila is None:
                db.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                        is_active=True,
                    )
                )
            else:
                fila.is_active = True

        for permission in plan["to_deactivate"]:
            filas_por_permiso[permission.id].is_active = False

        db.flush()

        resumen = _construir_resumen(plan)

        db.commit()

        return resumen
    except Exception:
        db.rollback()
        raise
