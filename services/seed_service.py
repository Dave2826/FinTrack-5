from sqlalchemy.orm import Session

from models.permission import Permission
from models.role import Role
from models.role_permission import RolePermission
from repositories.permission_repository import (
    create_permission,
    get_permission_by_code,
)
from repositories.role_permission_repository import (
    create_role_permission,
    list_role_permissions,
)
from repositories.role_repository import (
    create_role,
    get_role_by_code,
)


ROLES_OFICIALES = [
    "ADMINISTRADOR",
    "CONTADOR",
    "CAPTURISTA",
    "CONSULTA",
]

PERMISOS_OFICIALES = [
    "company.users.read",
    "company.users.write",
    "accounts.read",
    "accounts.write",
    "concepts.read",
    "concepts.write",
    "transactions.read",
    "transactions.write",
    "roles.read",
    "roles.write",
]

MATRIZ_OFICIAL = {
    "ADMINISTRADOR": [
        "company.users.read",
        "company.users.write",
        "accounts.read",
        "accounts.write",
        "concepts.read",
        "concepts.write",
        "transactions.read",
        "transactions.write",
        "roles.read",
        "roles.write",
    ],
    "CONTADOR": [
        "company.users.read",
        "accounts.read",
        "accounts.write",
        "concepts.read",
        "concepts.write",
        "transactions.read",
        "transactions.write",
        "roles.read",
    ],
    "CAPTURISTA": [
        "accounts.read",
        "concepts.read",
        "transactions.read",
        "transactions.write",
    ],
    "CONSULTA": [
        "company.users.read",
        "accounts.read",
        "concepts.read",
        "transactions.read",
    ],
}


def cargar_catalogo_inicial(db: Session) -> dict:
    roles_creados = 0
    roles_reutilizados = 0
    roles_reactivados = 0
    permisos_creados = 0
    permisos_reutilizados = 0
    relaciones_creadas = 0
    relaciones_reutilizadas = 0
    relaciones_reactivadas = 0

    roles: dict[str, Role] = {}

    for code in ROLES_OFICIALES:
        role = get_role_by_code(db, code)

        if role is None:
            role = create_role(
                db,
                Role(
                    code=code,
                    name=code,
                    description=None,
                    is_active=True,
                ),
            )
            roles_creados += 1
        elif role.is_active:
            roles_reutilizados += 1
        else:
            role.is_active = True

            db.commit()
            db.refresh(role)

            roles_reactivados += 1

        roles[code] = role

    permisos: dict[str, Permission] = {}

    for code in PERMISOS_OFICIALES:
        permission = get_permission_by_code(db, code)

        if permission is None:
            permission = create_permission(
                db,
                Permission(
                    code=code,
                    name=code,
                    description=None,
                    is_active=True,
                ),
            )
            permisos_creados += 1
        else:
            permisos_reutilizados += 1

        permisos[code] = permission

    for role_code, permiso_codes in MATRIZ_OFICIAL.items():
        role = roles[role_code]

        existentes = list_role_permissions(
            db,
            role.id,
            active_only=False,
        )

        if existentes:
            # Rol ya inicializado: aunque todas sus relaciones esten
            # inactivas (configuracion deliberadamente vacia) no se
            # restauran ni se reactivan permisos retirados. El criterio
            # es la existencia de filas historicas, no la ausencia de
            # relaciones activas.
            relaciones_reutilizadas += len(existentes)
            continue

        # Rol nunca inicializado: se crea la matriz oficial activa.
        for permission_code in permiso_codes:
            permission = permisos[permission_code]

            create_role_permission(
                db,
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                    is_active=True,
                ),
            )
            relaciones_creadas += 1

    return {
        "roles_creados": roles_creados,
        "roles_reutilizados": roles_reutilizados,
        "roles_reactivados": roles_reactivados,
        "permisos_creados": permisos_creados,
        "permisos_reutilizados": permisos_reutilizados,
        "relaciones_creadas": relaciones_creadas,
        "relaciones_reutilizadas": relaciones_reutilizadas,
        "relaciones_reactivadas": relaciones_reactivadas,
        "relaciones_oficiales": sum(
            len(codigos)
            for codigos in MATRIZ_OFICIAL.values()
        ),
    }
