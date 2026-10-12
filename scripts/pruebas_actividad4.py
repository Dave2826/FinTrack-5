"""Escenarios de la Actividad 4: configuracion de permisos por roles.

Solo sobre la base fintrack5_test (guardas propias). Emite JSONL en
/tmp/actividad4_resultados.jsonl dentro del contenedor y un resumen por
stdout. Restaura la matriz oficial de permisos y el rol inicial de Pedro
incluso ante errores, sin borrar registros historicos (bajas logicas).
"""

import json
import os
import sys
import urllib.request
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from repositories.company_repository import list_companies
from repositories.company_user_repository import (
    get_company_user_by_company_and_user,
)
from repositories.company_user_role_repository import (
    get_active_company_user_role,
)
from repositories.permission_repository import get_permission_by_code
from repositories.role_repository import get_role_by_code
from repositories.user_repository import get_user_by_email
from scripts.setup_pruebas import (
    CONTRASENA_PRUEBAS,
    preparar_usuarios_actividad4,
)

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"
URL = "http://127.0.0.1:8000/graphql"

MATRIZ_OFICIAL = {
    "ADMINISTRADOR": {
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
    },
    "CONTADOR": {
        "company.users.read",
        "accounts.read",
        "accounts.write",
        "concepts.read",
        "concepts.write",
        "transactions.read",
        "transactions.write",
        "roles.read",
    },
    "CAPTURISTA": {
        "accounts.read",
        "concepts.read",
        "transactions.read",
        "transactions.write",
    },
    "CONSULTA": {
        "company.users.read",
        "accounts.read",
        "concepts.read",
        "transactions.read",
    },
}

RUTA_SALIDA = "/tmp/actividad4_resultados.jsonl"

resultados: list[dict] = []


def _log(mensaje: str) -> None:
    print(f"[a4] {mensaje}", file=sys.stderr, flush=True)


def _abortar(mensaje: str) -> None:
    _log(f"GUARDA: {mensaje}")
    sys.exit(1)


def _registrar(caso, actor, operacion, esperado, observado, ok, nota=""):
    resultados.append(
        {
            "caso": caso,
            "actor": actor,
            "operacion": operacion,
            "esperado": esperado,
            "observado": observado,
            "resultado": "APROBADO" if ok else "FALLIDO",
            "nota": nota,
        }
    )


# ---------------------------------------------------------------- GraphQL


def _gql(query: str, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        URL,
        data=json.dumps({"query": query}).encode(),
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=30) as respuesta:
        return json.loads(respuesta.read().decode())


def _login(email: str) -> str:
    query = (
        'mutation{login(input:{email:"%s",password:"%s"})'
        "{accessToken tokenType}}" % (email, CONTRASENA_PRUEBAS)
    )
    datos = _gql(query)
    token = ((datos.get("data") or {}).get("login") or {}).get("accessToken")
    if not token:
        _abortar(f"login fallido para {email}: {datos}")
    return token


def _mensaje_error(datos: dict) -> str:
    errores = datos.get("errors") or []
    if errores:
        return errores[0].get("message", "")
    return ""


# ---------------------------------------------------------------- SQL


def _matriz(db: Session) -> dict[str, set[str]]:
    filas = db.execute(
        text(
            "SELECT r.code, p.code FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE rp.is_active ORDER BY r.code, p.code"
        )
    ).fetchall()
    matriz: dict[str, set[str]] = {}
    for rol, permiso in filas:
        matriz.setdefault(rol, set()).add(permiso)
    return matriz


def _conteos(db: Session) -> dict[str, int]:
    resultado = {}
    for tabla in ("role_permissions", "accounts", "transactions"):
        resultado[tabla] = db.execute(
            text(f"SELECT count(*) FROM {tabla}")
        ).scalar()
    return resultado


def _fila_historica(db: Session, rol_id: int, permiso_id: int) -> dict | None:
    fila = db.execute(
        text(
            "SELECT id, is_active FROM role_permissions "
            "WHERE role_id = :r AND permission_id = :p"
        ),
        {"r": rol_id, "p": permiso_id},
    ).first()
    if fila is None:
        return None
    return {"id": fila[0], "is_active": fila[1]}


def _restaurar(db: Session, ctx: dict) -> list[str]:
    """Restaura la matriz oficial y el rol de Pedro. GraphQL con token de
    Ana; respaldo SQL logico (solo is_active) si GraphQL no esta
    disponible. Nunca borra filas."""

    incidencias: list[str] = []
    token = ctx.get("ana_token")
    ana_id = ctx.get("ana_cu")
    pedro_cu = ctx.get("pedro_cu")
    roles_ids = ctx.get("roles_ids", {})
    permisos_ids = ctx.get("permisos_ids", {})

    matriz = _matriz(db)
    ajustes: list[tuple[str, str, bool]] = []
    for rol, oficiales in MATRIZ_OFICIAL.items():
        activos = matriz.get(rol, set())
        for codigo in activos - oficiales:
            ajustes.append((rol, codigo, False))
        for codigo in oficiales - activos:
            ajustes.append((rol, codigo, True))

    activo_pedro = (
        get_active_company_user_role(db, pedro_cu) if pedro_cu else None
    )
    necesita_pedro = (
        pedro_cu is not None
        and activo_pedro is not None
        and activo_pedro.role_id != roles_ids.get("CONSULTA")
    )

    if not ajustes and not necesita_pedro:
        return incidencias

    if token and ana_id:
        for rol, codigo, activar in ajustes:
            mutacion = (
                "mutation{assignPermissionToRole(input:{"
                "actorCompanyUserId:%d,roleId:%d,permissionId:%d})"
                "{id isActive}}"
                if activar
                else "mutation{removePermissionFromRole("
                "actorCompanyUserId:%d,roleId:%d,permissionId:%d)"
                "{id isActive}}"
            ) % (ana_id, roles_ids[rol], permisos_ids[codigo])
            try:
                datos = _gql(mutacion, token)
                ok = bool(
                    (datos.get("data") or {}).get("assignPermissionToRole")
                    or (datos.get("data") or {}).get("removePermissionFromRole")
                )
                if not ok:
                    incidencias.append(
                        f"GraphQL no aplico {rol}/{codigo}: {_mensaje_error(datos)}"
                    )
            except Exception as exc:
                incidencias.append(f"GraphQL fallo en {rol}/{codigo}: {exc}")

        if necesita_pedro:
            mutacion = (
                "mutation{assignRole(input:{actorCompanyUserId:%d,"
                "companyUserId:%d,roleId:%d}){id roleId isActive}}"
                % (ana_id, pedro_cu, roles_ids["CONSULTA"])
            )
            try:
                datos = _gql(mutacion, token)
                if not (datos.get("data") or {}).get("assignRole"):
                    incidencias.append(
                        "GraphQL no restauro rol de Pedro: "
                        + _mensaje_error(datos)
                    )
            except Exception as exc:
                incidencias.append(f"GraphQL fallo restaurando Pedro: {exc}")

    # Verificacion + respaldo SQL logico.
    db.rollback()
    matriz = _matriz(db)
    pendientes = [
        (rol, codigo, activar)
        for rol, oficiales in MATRIZ_OFICIAL.items()
        for codigo, activar in (
            [(c, True) for c in oficiales - matriz.get(rol, set())]
            + [(c, False) for c in matriz.get(rol, set()) - oficiales]
        )
    ]
    for rol, codigo, activar in pendientes:
        db.execute(
            text(
                "UPDATE role_permissions SET is_active = :a "
                "WHERE role_id = :r AND permission_id = :p"
            ),
            {
                "a": activar,
                "r": roles_ids[rol],
                "p": permisos_ids[codigo],
            },
        )
        incidencias.append(
            f"respaldo SQL: {rol}/{codigo} is_active={activar}"
        )

    if pedro_cu:
        activo = get_active_company_user_role(db, pedro_cu)
        if activo is not None and activo.role_id != roles_ids["CONSULTA"]:
            db.execute(
                text(
                    "UPDATE company_user_roles SET is_active = false "
                    "WHERE company_user_id = :cu AND is_active"
                ),
                {"cu": pedro_cu},
            )
            db.execute(
                text(
                    "UPDATE company_user_roles SET is_active = true "
                    "WHERE company_user_id = :cu AND role_id = :r"
                ),
                {"cu": pedro_cu, "r": roles_ids["CONSULTA"]},
            )
            incidencias.append("respaldo SQL: rol de Pedro -> CONSULTA")

    db.commit()
    return incidencias


# ---------------------------------------------------------------- main


def main() -> int:
    db = SessionLocal()
    ctx: dict = {}
    try:
        if os.getenv("DB_NAME") != DB_ESPERADA:
            _abortar(f"DB_NAME no es {DB_ESPERADA}")
        if os.getenv("DB_HOST") != HOST_ESPERADO:
            _abortar(f"DB_HOST no es {HOST_ESPERADO}")
        actual = db.execute(text("SELECT current_database()")).scalar()
        if actual != DB_ESPERADA:
            _abortar(f"current_database() no es {DB_ESPERADA}")
        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        if revision != ALEMBIC_ESPERADO:
            _abortar(f"alembic_version no es {ALEMBIC_ESPERADO}")

        membresias_a4 = preparar_usuarios_actividad4(db)
        _log(f"usuarios Actividad 4: {membresias_a4}")

        alpha = next(
            (c for c in list_companies(db) if c.name == "Pruebas Alpha SA"),
            None,
        )
        if alpha is None:
            _abortar("empresa Alpha inexistente")

        correos = {
            "ana": "ana@test.local",
            "luis": "luis@test.local",
            "maria": "maria@test.local",
            "jose": "jose@test.local",
            "pedro": "pedro@test.local",
        }
        usuarios = {
            clave: get_user_by_email(db, correo)
            for clave, correo in correos.items()
        }
        if any(u is None for u in usuarios.values()):
            _abortar("faltan usuarios de la Actividad 4")

        cu = {
            clave: get_company_user_by_company_and_user(db, alpha.id, u.id)
            for clave, u in usuarios.items()
        }
        if any(m is None for m in cu.values()):
            _abortar("faltan membresias de la Actividad 4")

        roles = {codigo: get_role_by_code(db, codigo) for codigo in MATRIZ_OFICIAL}
        permisos = {
            codigo: get_permission_by_code(db, codigo)
            for codigo in (
                "accounts.write",
                "roles.read",
                "transactions.write",
            )
        }
        if any(v is None for v in {**roles, **permisos}.values()):
            _abortar("catalogo incompleto")

        ctx["roles_ids"] = {k: v.id for k, v in roles.items()}
        ctx["permisos_ids"] = {
            codigo: ident
            for codigo, ident in db.execute(
                text("SELECT code, id FROM permissions")
            ).fetchall()
        }
        ctx["ana_cu"] = cu["ana"].id
        ctx["pedro_cu"] = cu["pedro"].id

        cuenta_alpha = db.execute(
            text(
                "SELECT id FROM accounts WHERE company_id = :c "
                "AND is_active ORDER BY id LIMIT 1"
            ),
            {"c": alpha.id},
        ).scalar()
        concepto_alpha = db.execute(
            text(
                "SELECT id FROM concepts WHERE company_id = :c "
                "AND concept_type = 'INCOME' AND is_active "
                "ORDER BY id LIMIT 1"
            ),
            {"c": alpha.id},
        ).scalar()
        if cuenta_alpha is None or concepto_alpha is None:
            _abortar("recursos de Alpha inexistentes")

        tok = {
            clave: _login(usuarios[clave].email)
            for clave in ("ana", "maria", "jose", "pedro")
        }
        ctx["ana_token"] = tok["ana"]

        matriz_base = _matriz(db)
        conteo_base = _conteos(db)
        contador_base = set(matriz_base.get("CONTADOR", set()))
        consulta_base = set(matriz_base.get("CONSULTA", set()))
        _log(f"baseline: conteos={conteo_base}")

        # Sufijo unico por ejecucion: las cuentas creadas por los
        # escenarios no pueden repetir nombre (regla de unicidad).
        marca = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # ------------------------------------------------ V9c: fixture
        activo_luis = get_active_company_user_role(db, cu["luis"].id)
        _registrar(
            "A4-V9c",
            "verificacion",
            "fixture Luis (CONTADOR)",
            "membresia activa con rol CONTADOR",
            f"role_id={(activo_luis.role_id if activo_luis else None)}",
            activo_luis is not None
            and activo_luis.role_id == roles["CONTADOR"].id,
        )

        # ------------------------------------------------ V1: aliases
        d_alias = _gql(
            "{roles(actorCompanyUserId:%d){id code name isActive}}"
            % cu["ana"].id,
            tok["ana"],
        )
        d_lista = _gql(
            "{listRoles(actorCompanyUserId:%d){id code name isActive}}"
            % cu["ana"].id,
            tok["ana"],
        )
        roles_alias = [
            f["code"] for f in (d_alias.get("data") or {}).get("roles") or []
        ]
        roles_lista = [
            f["code"] for f in (d_lista.get("data") or {}).get("listRoles") or []
        ]
        _registrar(
            "A4-V1a",
            "ana",
            "query roles",
            "respuesta con 4 roles",
            f"roles={roles_alias}",
            len(roles_alias) == 4,
        )
        _registrar(
            "A4-V1b",
            "ana",
            "roles == listRoles",
            "mismo resultado que listRoles",
            f"alias={roles_alias} lista={roles_lista}",
            roles_alias == roles_lista and len(roles_alias) == 4,
        )

        d_alias = _gql(
            "{permissions(actorCompanyUserId:%d){id code isActive}}"
            % cu["ana"].id,
            tok["ana"],
        )
        d_lista = _gql(
            "{listPermissions(actorCompanyUserId:%d){id code isActive}}"
            % cu["ana"].id,
            tok["ana"],
        )
        perm_alias = [
            f["code"] for f in (d_alias.get("data") or {}).get("permissions") or []
        ]
        perm_lista = [
            f["code"]
            for f in (d_lista.get("data") or {}).get("listPermissions") or []
        ]
        _registrar(
            "A4-V1c",
            "ana",
            "query permissions",
            "respuesta con 10 permisos",
            f"total={len(perm_alias)}",
            len(perm_alias) == 10,
        )
        _registrar(
            "A4-V1d",
            "ana",
            "permissions == listPermissions",
            "mismo resultado que listPermissions",
            f"iguales={perm_alias == perm_lista}",
            perm_alias == perm_lista and len(perm_alias) == 10,
        )

        rol_capturista = roles["CAPTURISTA"].id
        d_alias = _gql(
            "{rolePermissions(actorCompanyUserId:%d,roleId:%d)"
            "{id roleId permissionId isActive}}"
            % (cu["ana"].id, rol_capturista),
            tok["ana"],
        )
        d_lista = _gql(
            "{listRolePermissions(actorCompanyUserId:%d,roleId:%d)"
            "{id roleId permissionId isActive}}"
            % (cu["ana"].id, rol_capturista),
            tok["ana"],
        )
        rp_alias = [
            (f["permissionId"], f["isActive"])
            for f in (d_alias.get("data") or {}).get("rolePermissions") or []
        ]
        rp_lista = [
            (f["permissionId"], f["isActive"])
            for f in (d_lista.get("data") or {}).get("listRolePermissions") or []
        ]
        _registrar(
            "A4-V1e",
            "ana",
            "query rolePermissions(roleId:)",
            "respuesta con permisos activos del rol CAPTURISTA",
            f"filas={len(rp_alias)}",
            len(rp_alias) > 0,
        )
        _registrar(
            "A4-V1f",
            "ana",
            "rolePermissions == listRolePermissions",
            "mismo resultado que listRolePermissions",
            f"iguales={rp_alias == rp_lista}",
            rp_alias == rp_lista and len(rp_alias) > 0,
        )

        # ------------------------------------------------ V2: catalogo
        _registrar(
            "A4-V2a",
            "ana",
            "catalogo de roles",
            "4 roles oficiales sin duplicados",
            f"roles={sorted(roles_alias)}",
            sorted(roles_alias)
            == ["ADMINISTRADOR", "CAPTURISTA", "CONSULTA", "CONTADOR"]
            and len(roles_alias) == len(set(roles_alias)),
        )
        esperados_10 = {
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
        }
        _registrar(
            "A4-V2b",
            "ana",
            "catalogo de permisos",
            "10 permisos oficiales sin duplicados",
            f"total={len(perm_alias)} unicos={len(set(perm_alias)) == len(perm_alias)}",
            set(perm_alias) == esperados_10
            and len(perm_alias) == len(set(perm_alias)),
        )

        # ------------------------------------------------ V3a: antes
        def intento_cuenta(actor: str, nombre: str) -> tuple[bool, dict]:
            consulta = (
                "mutation{createAccount(input:{actorCompanyUserId:%d,"
                "companyId:%d,accountType:DEBIT,name:\"%s\"}){id companyId name}}"
                % (cu[actor].id, alpha.id, nombre)
            )
            datos = _gql(consulta, tok[actor])
            ok = bool((datos.get("data") or {}).get("createAccount"))
            return ok, datos

        ok, datos = intento_cuenta("maria", f"Cuenta A4 Maria {marca}")
        _registrar(
            "A4-V3a",
            "maria",
            "createAccount sin accounts.write",
            "denegado: El rol no tiene el permiso accounts.write",
            _mensaje_error(datos) or "CREADA",
            not ok
            and "El rol no tiene el permiso accounts.write"
            in _mensaje_error(datos),
        )
        ok, datos = intento_cuenta("jose", f"Cuenta A4 Jose {marca}")
        _registrar(
            "A4-V3a2",
            "jose",
            "createAccount sin accounts.write",
            "denegado: El rol no tiene el permiso accounts.write",
            _mensaje_error(datos) or "CREADA",
            not ok
            and "El rol no tiene el permiso accounts.write"
            in _mensaje_error(datos),
        )

        tras_rechazos = _conteos(db)
        _registrar(
            "A4-V8a",
            "verificacion",
            "conteos tras rechazos V3a",
            f"sin escrituras: {conteo_base}",
            f"observado: {tras_rechazos}",
            tras_rechazos == conteo_base,
        )

        # ------------------------------------------------ V4: concesion
        datos = _gql(
            "mutation{assignPermissionToRole(input:{actorCompanyUserId:%d,"
            "roleId:%d,permissionId:%d}){id roleId permissionId isActive}}"
            % (cu["ana"].id, rol_capturista, permisos["accounts.write"].id),
            tok["ana"],
        )
        concesion = (datos.get("data") or {}).get("assignPermissionToRole")
        _registrar(
            "A4-V4a",
            "ana",
            "assignPermissionToRole(CAPTURISTA, accounts.write)",
            "concedido",
            f"isActive={(concesion or {}).get('isActive')}",
            bool(concesion) and concesion.get("isActive") is True,
        )

        # ------------------------------------------------ V3b: despues
        ok, datos = intento_cuenta("maria", f"Cuenta A4 Maria {marca}")
        _registrar(
            "A4-V3b",
            "maria",
            "createAccount con accounts.write",
            "creada",
            f"id={((datos.get('data') or {}).get('createAccount') or {}).get('id')}",
            ok,
        )
        ok, datos = intento_cuenta("jose", f"Cuenta A4 Jose {marca}")
        _registrar(
            "A4-V3c",
            "jose",
            "createAccount con accounts.write",
            "creada",
            f"id={((datos.get('data') or {}).get('createAccount') or {}).get('id')}",
            ok,
        )

        # ------------------------------------------------ V4: retiro
        conteo_con_concesion = _conteos(db)
        datos = _gql(
            "mutation{removePermissionFromRole(actorCompanyUserId:%d,"
            "roleId:%d,permissionId:%d){id roleId permissionId isActive}}"
            % (cu["ana"].id, rol_capturista, permisos["accounts.write"].id),
            tok["ana"],
        )
        retiro = (datos.get("data") or {}).get("removePermissionFromRole")
        _registrar(
            "A4-V4b",
            "ana",
            "removePermissionFromRole(CAPTURISTA, accounts.write)",
            "retirado con is_active=false",
            f"isActive={(retiro or {}).get('isActive')}",
            bool(retiro) and retiro.get("isActive") is False,
        )

        fila = _fila_historica(db, rol_capturista, permisos["accounts.write"].id)
        _registrar(
            "A4-V7c",
            "verificacion",
            "historial tras el retiro",
            "fila conservada con is_active=false",
            f"fila={fila}",
            fila is not None and fila["is_active"] is False,
        )
        conteo_tras_retiro = _conteos(db)
        _registrar(
            "A4-V4c",
            "verificacion",
            "conteo de role_permissions tras el retiro",
            f"sin filas borradas (>= {conteo_con_concesion['role_permissions']})",
            f"observado={conteo_tras_retiro['role_permissions']}",
            conteo_tras_retiro["role_permissions"]
            >= conteo_con_concesion["role_permissions"],
        )

        ok, datos = intento_cuenta("maria", f"Cuenta A4 Maria 2 {marca}")
        _registrar(
            "A4-V3d",
            "maria",
            "createAccount tras retirar accounts.write",
            "denegado: El rol no tiene el permiso accounts.write",
            _mensaje_error(datos) or "CREADA",
            not ok
            and "El rol no tiene el permiso accounts.write"
            in _mensaje_error(datos),
        )
        ok, datos = intento_cuenta("jose", f"Cuenta A4 Jose 2 {marca}")
        _registrar(
            "A4-V3e",
            "jose",
            "createAccount tras retirar accounts.write",
            "denegado: El rol no tiene el permiso accounts.write",
            _mensaje_error(datos) or "CREADA",
            not ok
            and "El rol no tiene el permiso accounts.write"
            in _mensaje_error(datos),
        )

        # ------------------------------------------------ V7: Jose vs Ana
        datos = _gql(
            "mutation{assignPermissionToRole(input:{actorCompanyUserId:%d,"
            "roleId:%d,permissionId:%d}){id isActive}}"
            % (cu["jose"].id, rol_capturista, permisos["roles.read"].id),
            tok["jose"],
        )
        _registrar(
            "A4-V7a",
            "jose",
            "assignPermissionToRole (CAPTURISTA, roles.read)",
            "denegado: El rol no tiene el permiso roles.write",
            _mensaje_error(datos) or "ASIGNADO",
            not (datos.get("data") or {}).get("assignPermissionToRole")
            and "El rol no tiene el permiso roles.write"
            in _mensaje_error(datos),
        )
        conteo_tras_jose = _conteos(db)
        _registrar(
            "A4-V8b",
            "verificacion",
            "conteos tras rechazo de Jose",
            f"sin escrituras: {conteo_con_concesion}",
            f"observado: {conteo_tras_jose}",
            conteo_tras_jose == conteo_con_concesion,
        )

        datos = _gql(
            "mutation{assignPermissionToRole(input:{actorCompanyUserId:%d,"
            "roleId:%d,permissionId:%d}){id roleId permissionId isActive}}"
            % (cu["ana"].id, rol_capturista, permisos["roles.read"].id),
            tok["ana"],
        )
        concesion = (datos.get("data") or {}).get("assignPermissionToRole")
        _registrar(
            "A4-V7b",
            "ana",
            "assignPermissionToRole (CAPTURISTA, roles.read)",
            "concedido",
            f"isActive={(concesion or {}).get('isActive')}",
            bool(concesion) and concesion.get("isActive") is True,
        )
        datos = _gql(
            "mutation{removePermissionFromRole(actorCompanyUserId:%d,"
            "roleId:%d,permissionId:%d){id isActive}}"
            % (cu["ana"].id, rol_capturista, permisos["roles.read"].id),
            tok["ana"],
        )
        retiro = (datos.get("data") or {}).get("removePermissionFromRole")
        _registrar(
            "A4-V7d",
            "ana",
            "removePermissionFromRole (CAPTURISTA, roles.read)",
            "retirado; matriz oficial restaurada",
            f"isActive={(retiro or {}).get('isActive')}",
            bool(retiro) and retiro.get("isActive") is False,
        )

        # ------------------------------------------------ V5: Pedro
        datos = _gql(
            "mutation{createTransaction(input:{actorCompanyUserId:%d,"
            "accountId:%d,conceptId:%d,amount:15.5,"
            "transactionType:INCOME,shortDescription:\"A4 Pedro\"}){id}}"
            % (cu["pedro"].id, cuenta_alpha, concepto_alpha),
            tok["pedro"],
        )
        _registrar(
            "A4-V5a",
            "pedro",
            "createTransaction como CONSULTA",
            "denegado: El rol no tiene el permiso transactions.write",
            _mensaje_error(datos) or "CREADO",
            not (datos.get("data") or {}).get("createTransaction")
            and "El rol no tiene el permiso transactions.write"
            in _mensaje_error(datos),
        )

        datos = _gql(
            "mutation{assignRole(input:{actorCompanyUserId:%d,"
            "companyUserId:%d,roleId:%d}){id companyUserId roleId isActive}}"
            % (cu["ana"].id, cu["pedro"].id, rol_capturista),
            tok["ana"],
        )
        rotado = (datos.get("data") or {}).get("assignRole")
        _registrar(
            "A4-V5b",
            "ana",
            "assignRole(pedro: CONSULTA -> CAPTURISTA)",
            "rol rotado",
            f"roleId={(rotado or {}).get('roleId')} "
            f"isActive={(rotado or {}).get('isActive')}",
            bool(rotado)
            and rotado.get("roleId") == rol_capturista
            and rotado.get("isActive") is True,
        )

        activo = get_active_company_user_role(db, cu["pedro"].id)
        filas_pedro = db.execute(
            text(
                "SELECT count(*) FROM company_user_roles "
                "WHERE company_user_id = :cu AND is_active"
            ),
            {"cu": cu["pedro"].id},
        ).scalar()
        _registrar(
            "A4-V5d",
            "verificacion",
            "roles activos de Pedro tras assignRole",
            "exactamente 1 rol activo (CAPTURISTA)",
            f"activos={filas_pedro} "
            f"role_id={(activo.role_id if activo else None)}",
            filas_pedro == 1
            and activo is not None
            and activo.role_id == rol_capturista,
        )

        datos = _gql(
            "mutation{createTransaction(input:{actorCompanyUserId:%d,"
            "accountId:%d,conceptId:%d,amount:15.5,"
            "transactionType:INCOME,shortDescription:\"A4 Pedro\"}){id}}"
            % (cu["pedro"].id, cuenta_alpha, concepto_alpha),
            tok["pedro"],
        )
        creado = (datos.get("data") or {}).get("createTransaction")
        _registrar(
            "A4-V5c",
            "pedro",
            "createTransaction como CAPTURISTA",
            "creado",
            f"id={(creado or {}).get('id')}",
            bool(creado),
        )

        datos = _gql(
            "mutation{assignRole(input:{actorCompanyUserId:%d,"
            "companyUserId:%d,roleId:%d}){id companyUserId roleId isActive}}"
            % (cu["ana"].id, cu["pedro"].id, roles["CONSULTA"].id),
            tok["ana"],
        )
        restaurado = (datos.get("data") or {}).get("assignRole")
        activo = get_active_company_user_role(db, cu["pedro"].id)
        _registrar(
            "A4-V5e",
            "ana",
            "assignRole(pedro: CAPTURISTA -> CONSULTA)",
            "rol original restaurado (1 rol activo)",
            f"role_id={(activo.role_id if activo else None)}",
            bool(restaurado)
            and activo is not None
            and activo.role_id == roles["CONSULTA"].id,
        )

        # ------------------------------------------------ V6/V9 finales
        matriz_final = _matriz(db)
        _registrar(
            "A4-V6a",
            "verificacion",
            "permisos de CONTADOR durante la prueba",
            f"intactos: {sorted(contador_base)}",
            f"final: {sorted(matriz_final.get('CONTADOR', set()))}",
            matriz_final.get("CONTADOR", set()) == contador_base,
        )
        _registrar(
            "A4-V6b",
            "verificacion",
            "permisos de CONSULTA durante la prueba",
            f"intactos: {sorted(consulta_base)}",
            f"final: {sorted(matriz_final.get('CONSULTA', set()))}",
            matriz_final.get("CONSULTA", set()) == consulta_base,
        )
        conteos_finales = (
            len(matriz_final.get("ADMINISTRADOR", set())),
            len(matriz_final.get("CONTADOR", set())),
            len(matriz_final.get("CAPTURISTA", set())),
            len(matriz_final.get("CONSULTA", set())),
        )
        oficial_final = {
            rol: matriz_final.get(rol, set()) for rol in MATRIZ_OFICIAL
        }
        _registrar(
            "A4-V9a",
            "verificacion",
            "matriz final de los 4 roles oficiales vs tabla del profesor",
            "10/8/4/4 (26 permisos activos)",
            f"final={conteos_finales[0]}/{conteos_finales[1]}/"
            f"{conteos_finales[2]}/{conteos_finales[3]}",
            oficial_final == MATRIZ_OFICIAL,
        )
        _registrar(
            "A4-V9b",
            "verificacion",
            "matriz final vs baseline (todos los roles)",
            "identica al inicio de la prueba",
            f"iguales={matriz_final == matriz_base}",
            matriz_final == matriz_base,
        )

        # ------------------------------------------------ V10: SQL final
        filas_sql = db.execute(
            text(
                "SELECT rp.id, r.code, p.code, rp.is_active "
                "FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id "
                "JOIN permissions p ON p.id = rp.permission_id "
                "WHERE r.code IN ('ADMINISTRADOR','CONTADOR',"
                "'CAPTURISTA','CONSULTA') "
                "ORDER BY r.code, p.code, rp.id"
            )
        ).fetchall()
        filas_json = [
            {
                "id": f[0],
                "rol": f[1],
                "permiso": f[2],
                "is_active": f[3],
            }
            for f in filas_sql
        ]
        activos_sql = sum(1 for f in filas_json if f["is_active"])
        _registrar(
            "A4-V10",
            "verificacion",
            "SELECT final de role_permissions",
            "26 filas activas (matriz oficial) en la consulta",
            f"filas={len(filas_json)} activas={activos_sql}",
            activos_sql == 26,
            nota=json.dumps(filas_json, ensure_ascii=False),
        )

    except SystemExit:
        raise
    except Exception as exc:
        _registrar(
            "A4-FATAL",
            "runner",
            "excepcion no controlada",
            "sin excepcion",
            f"{type(exc).__name__}: {exc}",
            False,
        )
    finally:
        try:
            incidencias = _restaurar(db, ctx)
            if incidencias:
                _log(f"restauracion: {incidencias}")
        except Exception as exc:
            _registrar(
                "A4-RESTAURA",
                "verificacion",
                "restauracion en finally",
                "matriz y rol de Pedro restaurados",
                f"{type(exc).__name__}: {exc}",
                False,
            )
        db.rollback()
        db.close()

    with open(RUTA_SALIDA, "w", encoding="utf-8") as archivo:
        for fila in resultados:
            archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")

    aprobados = sum(1 for r in resultados if r["resultado"] == "APROBADO")
    fallidos = sum(1 for r in resultados if r["resultado"] == "FALLIDO")
    print(
        json.dumps(
            {
                "TOTAL": len(resultados),
                "APROBADOS": aprobados,
                "FALLIDOS": fallidos,
                "salida": RUTA_SALIDA,
            }
        )
    )
    return 1 if fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
