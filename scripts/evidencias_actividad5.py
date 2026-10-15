"""Evidencias E01-E10 de la Actividad 5 (configuración de permisos).

Se ejecuta EXCLUSIVAMENTE dentro del contenedor API contra fintrack5_test:

    docker exec -e PYTHONPATH=/app fintrack5-test-api \
        python scripts/evidencias_actividad5.py <fase>

Fases: e01, e02, e03, e04, e05, e06, e08pre, e08post, e09, e10, final.

La fase e08post debe ejecutarse después de reiniciar el contenedor de la
API desde el host (docker restart fintrack5-test-api). Cada fase guarda
su transcripción en /app/evidencias_a5/.

E07 no es una fase de este script: se genera ejecutando la prueba
unitaria de rollback (tests.test_configuracion_permisos) y guardando su
salida.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from sqlalchemy import text

from database.connection import SessionLocal
from setup_pruebas import CONTRASENA_PRUEBAS

URL = "http://127.0.0.1:8000/graphql"
DIR_SALIDA = "/app/evidencias_a5"
ARCHIVO_OPERACIONES = "/app/operaciones.graphql"
DIR_VARIABLES = "/app/variables"

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"

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

OPERACIONES = open(ARCHIVO_OPERACIONES, encoding="utf-8").read()

_codigos_s0 = ["accounts.read", "concepts.read", "transactions.read",
               "transactions.write"]
_codigos_s1 = sorted(_codigos_s0 + ["accounts.write"])


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(mensaje: str) -> None:
    print(f"[evidencia] {mensaje}", file=sys.stderr, flush=True)


def _abortar(mensaje: str) -> None:
    _log(f"GUARDA: {mensaje}")
    sys.exit(1)


def _json_default(obj):
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def _guardar(nombre: str, datos: dict) -> None:
    os.makedirs(DIR_SALIDA, exist_ok=True)
    ruta = os.path.join(DIR_SALIDA, nombre)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(
            datos,
            archivo,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    _log(f"guardado {ruta}")


# ---------------------------------------------------------------- GraphQL


def _gql(query: str, variables: dict | None = None,
         token: str | None = None,
         operation_name: str | None = None) -> dict:
    payload: dict = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    if operation_name:
        payload["operationName"] = operation_name

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token

    requerimiento = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(requerimiento, timeout=30) as respuesta:
            return json.loads(respuesta.read().decode())
    except urllib.error.HTTPError as error:
        return {
            "http_error": error.code,
            "body": error.read().decode(errors="replace"),
        }


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


def _operacion(nombre: str, variables: dict, token: str | None = None) -> dict:
    """Ejecuta una operación nombrada de operaciones.graphql."""
    return _gql(
        OPERACIONES,
        variables=variables,
        token=token,
        operation_name=nombre,
    )


def _variables(archivo: str) -> dict:
    with open(os.path.join(DIR_VARIABLES, archivo), encoding="utf-8-sig") as f:
        return json.load(f)


# ---------------------------------------------------------------- SQL


def _sql(consulta: str, parametros: dict | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        filas = db.execute(text(consulta), parametros or {}).fetchall()
        return [dict(fila._mapping) for fila in filas]
    finally:
        db.close()


def _sql_ejecutar(consulta: str, parametros: dict | None = None) -> None:
    db = SessionLocal()
    try:
        db.execute(text(consulta), parametros or {})
        db.commit()
    finally:
        db.close()


def _guardas() -> None:
    if os.getenv("DB_NAME") != DB_ESPERADA:
        _abortar(f"DB_NAME no es {DB_ESPERADA}")
    if os.getenv("DB_HOST") != HOST_ESPERADO:
        _abortar(f"DB_HOST no es {HOST_ESPERADO}")
    db = SessionLocal()
    try:
        actual = db.execute(text("SELECT current_database()")).scalar()
        if actual != DB_ESPERADA:
            _abortar(f"current_database() no es {DB_ESPERADA}")
        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        if revision != ALEMBIC_ESPERADO:
            _abortar(f"alembic_version no es {ALEMBIC_ESPERADO}")
    finally:
        db.close()


def _matriz() -> dict[str, list[str]]:
    filas = _sql(
        "SELECT r.code AS rol, p.code AS permiso "
        "FROM role_permissions rp "
        "JOIN roles r ON r.id = rp.role_id "
        "JOIN permissions p ON p.id = rp.permission_id "
        "WHERE rp.is_active ORDER BY r.code, p.code"
    )
    matriz: dict[str, list[str]] = {}
    for fila in filas:
        matriz.setdefault(fila["rol"], []).append(fila["permiso"])
    return matriz


def _configuracion() -> dict[str, list[str]]:
    matriz = _matriz()
    return {rol: matriz.get(rol, []) for rol in sorted(MATRIZ_OFICIAL)}


def _ids(tabla: str) -> dict[str, int]:
    if tabla not in ("roles", "permissions"):
        _abortar("tabla no permitida")
    filas = _sql(f"SELECT id, code FROM {tabla}")
    return {fila["code"]: fila["id"] for fila in filas}


def _membresia(email: str) -> int:
    filas = _sql(
        "SELECT cu.id FROM company_users cu "
        "JOIN users u ON u.id = cu.user_id "
        "WHERE u.email = :email AND cu.is_active",
        {"email": email},
    )
    if not filas:
        _abortar(f"membresía activa no encontrada para {email}")
    return filas[0]["id"]


def _fila_concesion(role_id: int, permission_id: int) -> dict | None:
    filas = _sql(
        "SELECT id, is_active FROM role_permissions "
        "WHERE role_id = :r AND permission_id = :p",
        {"r": role_id, "p": permission_id},
    )
    return filas[0] if filas else None


def _duplicados() -> list[dict]:
    return _sql(
        "SELECT role_id, permission_id, count(*) AS total "
        "FROM role_permissions GROUP BY role_id, permission_id "
        "HAVING count(*) > 1"
    )


def _conteos() -> dict[str, int]:
    filas = _sql(
        "SELECT r.code AS rol, count(*) AS total, "
        "count(*) FILTER (WHERE rp.is_active) AS activas "
        "FROM role_permissions rp JOIN roles r ON r.id = rp.role_id "
        "GROUP BY r.code ORDER BY r.code"
    )
    return {fila["rol"]: fila["activas"] for fila in filas}


# ---------------------------------------------------------------- fases


def fase_e01() -> None:
    estado = {
        "fase": "E01",
        "concepto": "configuración inicial de permisos por rol",
        "utc": _ahora(),
        "base_datos": DB_ESPERADA,
        "configuracion": _configuracion(),
        "conteo_filas_activas_por_rol": _conteos(),
        "duplicados_role_permission": _duplicados(),
        "nota": "S0 de CAPTURISTA = configuración original de 4 permisos",
    }
    _guardar("E01_configuracion_inicial.json", estado)


def fase_e02() -> None:
    ana = _membresia("ana@test.local")
    capturista = _membresia("capturista_a@test.local")
    token_ana = _login("ana@test.local")
    token_capturista = _login("capturista_a@test.local")

    resultados = {}
    for archivo in sorted(os.listdir(DIR_VARIABLES)):
        if not archivo.startswith("explorar_catalogo_"):
            continue
        datos = _operacion(
            "ExplorarCatalogo", _variables(archivo), token=token_ana
        )
        resultados[archivo] = datos

    denegacion = _gql(
        "query ExplorarCatalogo($actorCompanyUserId: ID!)"
        "{permissionCatalog(actorCompanyUserId:$actorCompanyUserId){id}}",
        variables={"actorCompanyUserId": str(capturista)},
        token=token_capturista,
        operation_name="ExplorarCatalogo",
    )

    resumen = {}
    for archivo, datos in resultados.items():
        data = datos.get("data") or {}
        resumen[archivo] = {
            "todos": [p["code"] for p in (data.get("todos") or [])],
            "porRecurso": [p["code"] for p in (data.get("porRecurso") or [])],
            "errores": datos.get("errors"),
        }

    _guardar(
        "E02_catalogo_permisos.json",
        {
            "fase": "E02",
            "concepto": "catálogo de permisos activos con y sin filtro",
            "utc": _ahora(),
            "actor": {"email": "ana@test.local", "companyUserId": ana},
            "operacion": "query ExplorarCatalogo (operaciones.graphql)",
            "resultados": resumen,
            "autorizacion": {
                "actor": "capturista_a@test.local (sin roles.read)",
                "esperado": "El rol no tiene el permiso roles.read",
                "observado": _mensaje_error(denegacion),
                "respuesta": denegacion,
            },
            "usa_archivos": sorted(
                a for a in os.listdir(DIR_VARIABLES)
                if a.startswith("explorar_catalogo_")
            ),
        },
    )


def fase_e03() -> None:
    ana = _membresia("ana@test.local")
    token = _login("ana@test.local")
    antes = _configuracion()
    datos = _operacion(
        "RevisarConfiguracion",
        _variables("revisar_configuracion_s1.json"),
        token=token,
    )
    despues = _configuracion()

    plan = (datos.get("data") or {}).get("previewRolePermissions") or {}
    _guardar(
        "E03_preview_s1.json",
        {
            "fase": "E03",
            "concepto": "previsualización S0->S1 sin escrituras",
            "utc": _ahora(),
            "actor": {"email": "ana@test.local", "companyUserId": ana},
            "operacion": "query RevisarConfiguracion (operaciones.graphql)",
            "variables": _variables("revisar_configuracion_s1.json"),
            "respuesta": datos,
            "plan": {
                "toActivate": [p["code"] for p in plan.get("toActivate") or []],
                "toDeactivate": [
                    p["code"] for p in plan.get("toDeactivate") or []
                ],
                "unchanged": [
                    p["code"] for p in plan.get("unchanged") or []
                ],
                "finalCount": plan.get("finalCount"),
            },
            "configuracion_antes": antes,
            "configuracion_despues": despues,
            "solo_lectura": antes == despues,
        },
    )


def fase_e04() -> None:
    ana = _membresia("ana@test.local")
    token = _login("ana@test.local")
    variables = _variables("aplicar_configuracion_s1.json")
    ids = _ids("roles")
    permisos = _ids("permissions")

    primera = _operacion("AplicarConfiguracion", variables, token=token)
    fila1 = _fila_concesion(ids["CAPTURISTA"], permisos["accounts.write"])
    segunda = _operacion("AplicarConfiguracion", variables, token=token)
    fila2 = _fila_concesion(ids["CAPTURISTA"], permisos["accounts.write"])

    _guardar(
        "E04_aplicar_s1_dos_veces.json",
        {
            "fase": "E04",
            "concepto": "aplicar S1 dos veces: cambio y luego idempotencia",
            "utc": _ahora(),
            "actor": {"email": "ana@test.local", "companyUserId": ana},
            "operacion": "mutation AplicarConfiguracion (operaciones.graphql)",
            "variables": variables,
            "primera_aplicacion": primera,
            "segunda_aplicacion": segunda,
            "concesion_accounts_write": {
                "tras_primera": fila1,
                "tras_segunda": fila2,
            },
            "configuracion_final": _configuracion(),
        },
    )


def fase_e05() -> None:
    ana = _membresia("ana@test.local")
    token = _login("ana@test.local")
    ids = _ids("roles")
    permisos = _ids("permissions")

    ruta_e04 = os.path.join(DIR_SALIDA, "E04_aplicar_s1_dos_veces.json")
    with open(ruta_e04, encoding="utf-8") as archivo:
        e04 = json.load(archivo)
    id_original = e04["concesion_accounts_write"]["tras_primera"]["id"]

    volver_s0 = _operacion(
        "AplicarConfiguracion",
        _variables("aplicar_configuracion_s0.json"),
        token=token,
    )
    id_tras_s0 = _fila_concesion(
        ids["CAPTURISTA"], permisos["accounts.write"]
    )

    volver_s1 = _operacion(
        "AplicarConfiguracion",
        _variables("aplicar_configuracion_s1.json"),
        token=token,
    )
    id_tras_s1 = _fila_concesion(
        ids["CAPTURISTA"], permisos["accounts.write"]
    )

    _guardar(
        "E05_estable_identificador.json",
        {
            "fase": "E05",
            "concepto": (
                "aplicar S0 y volver a S1: la concesión accounts.write "
                "conserva su id original"
            ),
            "utc": _ahora(),
            "actor": {"email": "ana@test.local", "companyUserId": ana},
            "operacion": "mutation AplicarConfiguracion (operaciones.graphql)",
            "id_original_E04": id_original,
            "aplicar_s0": volver_s0,
            "concesion_tras_s0": id_tras_s0,
            "aplicar_s1": volver_s1,
            "concesion_tras_s1": id_tras_s1,
            "mismo_identificador": (
                id_tras_s0 is not None
                and id_tras_s1 is not None
                and id_original == id_tras_s0["id"] == id_tras_s1["id"]
            ),
            "configuracion_final": _configuracion(),
        },
    )


def fase_e06() -> None:
    ana = _membresia("ana@test.local")
    capturista = _membresia("capturista_a@test.local")
    token_ana = _login("ana@test.local")
    token_capturista = _login("capturista_a@test.local")
    ids = _ids("roles")
    permisos = _ids("permissions")
    todos = sorted(permisos.values())
    s1 = [permisos[c] for c in _codigos_s1]

    matriz_antes = _configuracion()
    intentos: list[dict] = []

    def _intentar(nombre: str, esperado: str, variables: dict,
                  token: str) -> None:
        datos = _operacion("AplicarConfiguracion", variables, token=token)
        observado = _mensaje_error(datos)
        intentos.append({
            "variante": nombre,
            "esperado": esperado,
            "observado": observado,
            "variables": variables,
            "respuesta": datos,
            "aprobado": esperado in observado
            and not (datos.get("data") or {}).get("setRolePermissions"),
        })

    # 1. rol inexistente
    _intentar(
        "rol inexistente",
        "El rol no existe",
        {"actorCompanyUserId": str(ana),
         "input": {"roleId": "999999",
                   "permissionIds": [str(v) for v in s1]}},
        token_ana,
    )

    # 2. rol inactivo (CONSULTA desactivado y restaurado por SQL)
    _sql_ejecutar(
        "UPDATE roles SET is_active = false WHERE code = 'CONSULTA'"
    )
    try:
        _intentar(
            "rol inactivo",
            "El rol no está activo",
            {"actorCompanyUserId": str(ana),
             "input": {"roleId": str(ids["CONSULTA"]),
                       "permissionIds": [str(permisos["accounts.read"])]}},
            token_ana,
        )
    finally:
        _sql_ejecutar(
            "UPDATE roles SET is_active = true WHERE code = 'CONSULTA'"
        )

    # 3. propuesta sobre ADMINISTRADOR
    _intentar(
        "propuesta sobre ADMINISTRADOR",
        "ADMINISTRADOR",
        {"actorCompanyUserId": str(ana),
         "input": {"roleId": str(ids["ADMINISTRADOR"]),
                   "permissionIds": [str(v) for v in todos]}},
        token_ana,
    )

    # 4. permiso inexistente mezclado con válidos
    _intentar(
        "permiso inexistente mezclado",
        "El permiso con id 999999 no existe",
        {"actorCompanyUserId": str(ana),
         "input": {"roleId": str(ids["CAPTURISTA"]),
                   "permissionIds": [str(v) for v in s1] + ["999999"]}},
        token_ana,
    )

    # 5. permiso inactivo (concepts.write desactivado y restaurado por SQL)
    _sql_ejecutar(
        "UPDATE permissions SET is_active = false "
        "WHERE code = 'concepts.write'"
    )
    try:
        _intentar(
            "permiso inactivo",
            "El permiso concepts.write no está activo",
            {"actorCompanyUserId": str(ana),
             "input": {"roleId": str(ids["CAPTURISTA"]),
                       "permissionIds": [str(permisos["concepts.write"])]}},
            token_ana,
        )
    finally:
        _sql_ejecutar(
            "UPDATE permissions SET is_active = true "
            "WHERE code = 'concepts.write'"
        )

    # 6. IDs repetidos (incluido equivalente "3" vs 3)
    _intentar(
        "IDs repetidos",
        "permissionIds contiene IDs repetidos",
        {"actorCompanyUserId": str(ana),
         "input": {"roleId": str(ids["CAPTURISTA"]),
                   "permissionIds": [str(permisos["accounts.read"]),
                                     str(permisos["accounts.read"])]}},
        token_ana,
    )

    # Verificación adicional: actor sin roles.write
    _intentar(
        "actor sin roles.write (adición)",
        "El rol no tiene el permiso roles.write",
        {"actorCompanyUserId": str(capturista),
         "input": {"roleId": str(ids["CAPTURISTA"]),
                   "permissionIds": [str(v) for v in s1]}},
        token_capturista,
    )

    matriz_despues = _configuracion()
    restaurado = _sql(
        "SELECT (SELECT is_active FROM roles WHERE code = 'CONSULTA') "
        "AS consulta_activa, "
        "(SELECT is_active FROM permissions "
        "WHERE code = 'concepts.write') AS concepts_write_activo"
    )[0]

    _guardar(
        "E06_entradas_invalidas.json",
        {
            "fase": "E06",
            "concepto": "seis entradas inválidas + denegación de autorización",
            "utc": _ahora(),
            "intentos": intentos,
            "todos_aprobados": all(i["aprobado"] for i in intentos),
            "configuracion_antes": matriz_antes,
            "configuracion_despues": matriz_despues,
            "estado_intacto": matriz_antes == matriz_despues,
            "restauracion_estado": restaurado,
        },
    )


def fase_e08pre() -> None:
    ana = _membresia("ana@test.local")
    token = _login("ana@test.local")
    datos = _operacion(
        "AplicarConfiguracion",
        _variables("aplicar_configuracion_vacia.json"),
        token=token,
    )
    _guardar(
        "E08_pre_lista_vacia.json",
        {
            "fase": "E08-pre",
            "concepto": "aplicar permissionIds vacío a CAPTURISTA",
            "utc": _ahora(),
            "actor": {"email": "ana@test.local", "companyUserId": ana},
            "operacion": "mutation AplicarConfiguracion (operaciones.graphql)",
            "variables": _variables("aplicar_configuracion_vacia.json"),
            "respuesta": datos,
            "configuracion_tras_aplicar": _configuracion(),
            "capturista_activas": _conteos().get("CAPTURISTA"),
        },
    )


def fase_e08post() -> None:
    with open("/proc/uptime", encoding="ascii") as archivo:
        uptime = float(archivo.read().split()[0])

    token = None
    for intento in range(12):
        try:
            token = _login("ana@test.local")
            break
        except SystemExit:
            if intento == 11:
                raise
            time.sleep(5)

    capturista = _membresia("capturista_a@test.local")
    verificacion = _operacion(
        "RevisarConfiguracion",
        {"actorCompanyUserId": "29",
         "input": {"roleId": "3", "permissionIds": []}},
        token=token,
    )

    _guardar(
        "E08_post_reinicio.json",
        {
            "fase": "E08-post",
            "concepto": (
                "persistencia de la lista vacía tras reiniciar la API"
            ),
            "utc": _ahora(),
            "uptime_host_segundos": uptime,
            "nota_uptime": (
                "uptime del host (visto desde /proc/uptime dentro del "
                "contenedor); StartedAt real del contenedor está en "
                "E08_reinicio_contenedor.json"
            ),
            "api_respondio": token is not None,
            "configuracion_tras_reinicio": _configuracion(),
            "capturista_activas": _conteos().get("CAPTURISTA"),
            "actor_sin_roles_read": {
                "companyUserId": capturista,
                "nota": "verificación de autorización post-reinicio",
            },
            "verificacion_preview": verificacion,
        },
    )


def fase_e09() -> None:
    ana = _membresia("ana@test.local")
    token = _login("ana@test.local")
    datos = _operacion(
        "AplicarConfiguracion",
        _variables("aplicar_configuracion_s0.json"),
        token=token,
    )
    configuracion = _configuracion()
    oficial = {rol: sorted(codigos)
               for rol, codigos in MATRIZ_OFICIAL.items()}

    _guardar(
        "E09_restauracion.json",
        {
            "fase": "E09",
            "concepto": "restauración de la matriz oficial de permisos",
            "utc": _ahora(),
            "actor": {"email": "ana@test.local", "companyUserId": ana},
            "operacion": "mutation AplicarConfiguracion (operaciones.graphql)",
            "variables": _variables("aplicar_configuracion_s0.json"),
            "respuesta": datos,
            "configuracion_final": configuracion,
            "conteos_activas_por_rol": _conteos(),
            "matriz_oficial_cumplida": configuracion == oficial,
            "duplicados": _duplicados(),
        },
    )


def fase_e10() -> None:
    ana = _membresia("ana@test.local")
    token = _login("ana@test.local")

    consulta_cuentas = _gql(
        "query CuentasDeLaEmpresa($actorCompanyUserId: Int!,"
        "$companyId: Int!){accounts(actorCompanyUserId:$actorCompanyUserId,"
        "companyId:$companyId){id name accountType isActive}}",
        variables={"actorCompanyUserId": ana, "companyId": 5},
        token=token,
        operation_name="CuentasDeLaEmpresa",
    )

    movimiento = _gql(
        "mutation MovimientoEvidencia($input: CreateTransactionInput!)"
        "{createTransaction(input:$input){id accountId conceptId amount "
        "transactionType shortDescription}}",
        variables={"input": {
            "actorCompanyUserId": ana,
            "accountId": 5,
            "conceptId": 7,
            "amount": 123.45,
            "transactionType": "INCOME",
            "shortDescription": "A5 E10 movimiento real",
        }},
        token=token,
        operation_name="MovimientoEvidencia",
    )

    persistido = _sql(
        "SELECT id, account_id, concept_id, amount, transaction_type, "
        "short_description FROM transactions "
        "WHERE short_description = 'A5 E10 movimiento real' "
        "ORDER BY id DESC LIMIT 1"
    )

    cuentas = (consulta_cuentas.get("data") or {}).get("accounts") or []
    _guardar(
        "E10_cuentas_y_movimiento.json",
        {
            "fase": "E10",
            "concepto": (
                "continuidad: consulta de cuentas y movimiento real "
                "cuenta 5 / concepto 7 INCOME"
            ),
            "utc": _ahora(),
            "actor": {"email": "ana@test.local", "companyUserId": ana},
            "consulta_cuentas": consulta_cuentas,
            "cuenta_5_visible": any(c.get("id") == 5 for c in cuentas),
            "movimiento": movimiento,
            "persistido_en_postgres": persistido,
        },
    )


def fase_final() -> None:
    estado = {
        "fase": "final",
        "concepto": "configuración final de permisos por rol",
        "utc": _ahora(),
        "base_datos": DB_ESPERADA,
        "configuracion": _configuracion(),
        "conteo_filas_activas_por_rol": _conteos(),
        "duplicados_role_permission": _duplicados(),
    }
    _guardar("configuracion_final.json", estado)


FASES = {
    "e01": fase_e01,
    "e02": fase_e02,
    "e03": fase_e03,
    "e04": fase_e04,
    "e05": fase_e05,
    "e06": fase_e06,
    "e08pre": fase_e08pre,
    "e08post": fase_e08post,
    "e09": fase_e09,
    "e10": fase_e10,
    "final": fase_final,
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in FASES:
        _abortar(f"fases válidas: {', '.join(sorted(FASES))}")
    _guardas()
    FASES[sys.argv[1]]()


if __name__ == "__main__":
    main()
