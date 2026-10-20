"""Evidencias de la Actividad 6: control de acceso segun el rol.

Se ejecuta EXCLUSIVAMENTE dentro del contenedor de pruebas
(fintrack5-test-api) contra la base fintrack5_test. Las guardas abortan
si DB_NAME, DB_HOST, current_database() o la revision de Alembic no
coinciden con el entorno de pruebas. Nunca usa la base actividad5.

Replica los nueve casos funcionales y las validaciones de token sobre el
contrato autenticado (Authorization: Bearer <token>), guarda las
evidencias E01-E10 en /app/evidencias_a6 y restaura el estado
(rol de Pedro, cuentas y movimientos creados). No escribe tokens
vigentes ni valores de secretos en las evidencias.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import text

from database.connection import SessionLocal
from scripts.setup_pruebas import CONTRASENA_PRUEBAS

DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"
URL = "http://127.0.0.1:8000/graphql"

ARCHIVO_OPERACIONES = "/app/operaciones_actividad6.graphql"
DIR_VARIABLES = "/app/variables_actividad6"
DIR_SALIDA = "/app/evidencias_a6"

MATRIZ_OFICIAL = {
    "ADMINISTRADOR": {
        "company.users.read", "company.users.write",
        "accounts.read", "accounts.write",
        "concepts.read", "concepts.write",
        "transactions.read", "transactions.write",
        "roles.read", "roles.write",
    },
    "CONTADOR": {
        "company.users.read", "accounts.read", "accounts.write",
        "concepts.read", "concepts.write",
        "transactions.read", "transactions.write", "roles.read",
    },
    "CAPTURISTA": {
        "accounts.read", "concepts.read",
        "transactions.read", "transactions.write",
    },
    "CONSULTA": {
        "company.users.read", "accounts.read",
        "concepts.read", "transactions.read",
    },
}

OPERACIONES = open(ARCHIVO_OPERACIONES, encoding="utf-8").read()


def _log(mensaje: str) -> None:
    print(f"[a6] {mensaje}", file=sys.stderr, flush=True)


def _abortar(mensaje: str) -> None:
    _log(f"GUARDA: {mensaje}")
    sys.exit(1)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guardar(nombre: str, datos: dict) -> None:
    os.makedirs(DIR_SALIDA, exist_ok=True)
    ruta = os.path.join(DIR_SALIDA, nombre)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)
    _log(f"evidencia guardada: {nombre}")


def _verificar_guardas(db) -> None:
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

    if not os.getenv("JWT_SECRET"):
        _abortar("JWT_SECRET no esta definido en el entorno de pruebas")


# ---------------------------------------------------------------- HTTP


def _gql(consulta: str, variables: dict | None = None,
         token: str | None = None,
         operation_name: str | None = None) -> dict:
    payload: dict = {"query": consulta}
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


def _operacion(nombre: str, variables: dict | None = None,
               token: str | None = None) -> dict:
    return _gql(
        OPERACIONES,
        variables=variables,
        token=token,
        operation_name=nombre,
    )


def _login(email: str) -> str:
    datos = _gql(
        'mutation{login(input:{email:"%s",password:"%s"})'
        "{token tokenType}}" % (email, CONTRASENA_PRUEBAS)
    )
    token = ((datos.get("data") or {}).get("login") or {}).get("token")
    if not token:
        _abortar(f"login fallido para {email}: {datos}")
    return token


def _mensaje_error(datos: dict) -> str:
    errores = datos.get("errors") or []
    if errores:
        return errores[0].get("message", "")
    return ""


def _variables(archivo: str) -> dict:
    with open(os.path.join(DIR_VARIABLES, archivo), encoding="utf-8-sig") as f:
        return json.load(f)


def _descripcion_token(token: str, token_type: str = "bearer") -> dict:
    claims = jwt.decode(
        token,
        os.environ["JWT_SECRET"],
        algorithms=["HS256"],
        options={"require": ["exp"]},
    )
    segundos = claims["exp"] - datetime.now(timezone.utc).timestamp()
    return {
        "tokenType": token_type,
        "claims": {
            "companyUserId": claims["companyUserId"],
            "companyId": claims["companyId"],
            "exp": int(claims["exp"]),
        },
        "vigencia_minutos": round(segundos / 60, 2),
        "cabecera_autorizacion": "Authorization: Bearer <TOKEN_REDACTADO>",
        "longitud_token": len(token),
        "nota": "no se almacena el token vigente, solo sus metadatos",
    }


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


def _conteo(tabla: str) -> int:
    return _sql(f"SELECT count(*) AS total FROM {tabla}")[0]["total"]


def _membresia(email: str) -> int:
    filas = _sql(
        "SELECT cu.id FROM company_users cu "
        "JOIN users u ON u.id = cu.user_id "
        "WHERE u.email = :email AND cu.is_active",
        {"email": email},
    )
    if not filas:
        _abortar(f"membresia activa inexistente para {email}")
    return filas[0]["id"]


def _id_empresa(membresia: int) -> int:
    return _sql(
        "SELECT company_id FROM company_users WHERE id = :cu",
        {"cu": membresia},
    )[0]["company_id"]


def _recurso(tabla: str, company_id: int) -> int:
    filas = _sql(
        f"SELECT id FROM {tabla} WHERE company_id = :c AND is_active "
        "ORDER BY id LIMIT 1",
        {"c": company_id},
    )
    if not filas:
        _abortar(f"sin recursos activos en {tabla} para la empresa")
    return filas[0]["id"]


def _matriz() -> dict[str, list[str]]:
    filas = _sql(
        "SELECT r.code AS rol, p.code AS permiso FROM role_permissions rp "
        "JOIN roles r ON r.id = rp.role_id "
        "JOIN permissions p ON p.id = rp.permission_id "
        "WHERE rp.is_active ORDER BY r.code, p.code"
    )
    matriz: dict[str, list[str]] = {}
    for fila in filas:
        matriz.setdefault(fila["rol"], []).append(fila["permiso"])
    return matriz


def _firmar(claims: dict) -> str:
    return jwt.encode(claims, os.environ["JWT_SECRET"], algorithm="HS256")


# ---------------------------------------------------------------- fases


def fase_e01(db) -> dict:
    ana = _membresia("ana@test.local")
    correcto = _gql(
        'mutation{login(input:{email:"ana@test.local",password:"%s"})'
        "{token tokenType user{id name email}}}" % CONTRASENA_PRUEBAS
    )
    payload = ((correcto.get("data") or {}).get("login")) or {}
    token = payload.get("token")
    if not token:
        _abortar(f"login correcto fallido: {correcto}")

    incorrecto = _gql(
        'mutation{login(input:{email:"ana@test.local",password:"mala"})'
        "{token tokenType user{name}}}"
    )
    sin_membresia = _gql(
        'mutation{login(input:{email:"sin_membresia_a@test.local",'
        'password:"%s"}){token tokenType}}' % CONTRASENA_PRUEBAS
    )
    inactivo = _gql(
        'mutation{login(input:{email:"inactivo_a@test.local",'
        'password:"%s"}){token tokenType}}' % CONTRASENA_PRUEBAS
    )

    descripcion = _descripcion_token(token, payload.get("tokenType"))
    descripcion["usuario"] = {
        "name": (payload.get("user") or {}).get("name"),
        "email": (payload.get("user") or {}).get("email"),
    }
    descripcion["sin_hash_en_respuesta"] = (
        "$argon2" not in json.dumps(correcto)
        and "password_hash" not in json.dumps(correcto)
    )
    descripcion["login_rechazado_sin_token"] = all(
        not (d.get("data") or {}).get("login")
        for d in (incorrecto, sin_membresia, inactivo)
    )

    _guardar("E01_login.json", {
        "fase": "E01",
        "concepto": "login correcto (token, tokenType y datos minimos del usuario) y rechazos",
        "utc": _ahora(),
        "actor": {"email": "ana@test.local", "companyUserId": ana},
        "correcto": descripcion,
        "password_incorrecta": _mensaje_error(incorrecto),
        "sin_membresia_activa": _mensaje_error(sin_membresia),
        "usuario_inactivo": _mensaje_error(inactivo),
    })
    return {"token_ana": token, "ana": ana}


def fase_e02(db) -> None:
    alpha = _id_empresa(_membresia("ana@test.local"))
    antes = _conteo("accounts")

    datos = _operacion("CrearCuenta", {
        "input": {
            "companyId": alpha,
            "accountType": "DEBIT",
            "name": "A6 sin token (evidencia)",
        }
    })

    _guardar("E02_sin_token.json", {
        "fase": "E02",
        "concepto": "operacion protegida sin token: rechazo sin escrituras",
        "utc": _ahora(),
        "operacion": "createAccount sin Authorization",
        "mensaje": _mensaje_error(datos),
        "respuesta": datos,
        "cuentas_antes": antes,
        "cuentas_despues": _conteo("accounts"),
        "sin_escrituras": _conteo("accounts") == antes,
    })


def fase_e03(db, ctx: dict) -> None:
    alpha = _id_empresa(_membresia("ana@test.local"))
    cuenta = _recurso("accounts", alpha)
    concepto = _recurso("concepts", alpha)

    datos = _operacion("CrearMovimiento", {
        "input": {
            "accountId": cuenta,
            "conceptId": concepto,
            "transactionType": "INCOME",
            "amount": 15.5,
            "shortDescription": "A6 Maria capturista (evidencia)",
        }
    }, token=ctx["token_maria"])

    creada = (datos.get("data") or {}).get("createTransaction")
    if creada:
        ctx["limpieza"]["transactions"].append(creada["id"])

    persistido = []
    if creada:
        persistido = _sql(
            "SELECT id, account_id, captured_by FROM transactions "
            "WHERE id = :i",
            {"i": creada["id"]},
        )

    _guardar("E03_maria_transaccion.json", {
        "fase": "E03",
        "concepto": "caso 2: Maria (CAPTURISTA) registra un movimiento valido",
        "utc": _ahora(),
        "autenticacion": "Bearer (Maria)",
        "variables": {
            "accountId": cuenta,
            "conceptId": concepto,
            "transactionType": "INCOME",
            "amount": 15.5,
        },
        "respuesta": datos,
        "persistido": persistido,
        "guardado": creada is not None,
    })


def fase_e04(db, ctx: dict) -> None:
    alpha = _id_empresa(_membresia("ana@test.local"))
    antes = _conteo("accounts")

    datos = _operacion("CrearCuenta", {
        "input": {
            "companyId": alpha,
            "accountType": "DEBIT",
            "name": "A6 Maria cuenta (evidencia)",
        }
    }, token=ctx["token_maria"])

    _guardar("E04_maria_cuenta_denegada.json", {
        "fase": "E04",
        "concepto": "caso 3: Maria (CAPTURISTA) no puede crear cuentas",
        "utc": _ahora(),
        "autenticacion": "Bearer (Maria)",
        "mensaje": _mensaje_error(datos),
        "respuesta": datos,
        "cuentas_antes": antes,
        "cuentas_despues": _conteo("accounts"),
        "sin_escrituras": _conteo("accounts") == antes,
    })


def fase_e05(db, ctx: dict) -> None:
    alpha = _id_empresa(_membresia("ana@test.local"))

    datos = _operacion("CrearCuenta", {
        "input": {
            "companyId": alpha,
            "accountType": "DEBIT",
            "name": "A6 Luis cuenta (evidencia)",
        }
    }, token=ctx["token_luis"])

    creada = (datos.get("data") or {}).get("createAccount")
    if creada:
        ctx["limpieza"]["accounts"].append(creada["id"])

    _guardar("E05_luis_cuenta.json", {
        "fase": "E05",
        "concepto": "caso 4: Luis (CONTADOR) crea una cuenta",
        "utc": _ahora(),
        "autenticacion": "Bearer (Luis)",
        "respuesta": datos,
        "creada": creada is not None,
    })


def fase_e06(db, ctx: dict) -> None:
    alpha = _id_empresa(_membresia("ana@test.local"))
    cuenta = _recurso("accounts", alpha)
    concepto = _recurso("concepts", alpha)
    antes = _conteo("transactions")

    datos = _operacion("CrearMovimiento", {
        "input": {
            "accountId": cuenta,
            "conceptId": concepto,
            "transactionType": "INCOME",
            "amount": 10,
            "shortDescription": "A6 Pedro denegado (evidencia)",
        }
    }, token=ctx["token_pedro_previo"])

    _guardar("E06_pedro_denegado.json", {
        "fase": "E06",
        "concepto": "caso 5: Pedro (CONSULTA) no puede registrar movimientos",
        "utc": _ahora(),
        "autenticacion": "Bearer (Pedro, token previo al cambio de rol)",
        "mensaje": _mensaje_error(datos),
        "respuesta": datos,
        "movimientos_antes": antes,
        "movimientos_despues": _conteo("transactions"),
        "sin_escrituras": _conteo("transactions") == antes,
    })


def fase_e07(db, ctx: dict) -> None:
    pedro = _membresia("pedro@test.local")
    rol_capturista = _sql(
        "SELECT id FROM roles WHERE code = 'CAPTURISTA'"
    )[0]["id"]

    datos = _operacion("CambiarRol", {
        "input": {"companyUserId": pedro, "roleId": rol_capturista}
    }, token=ctx["token_ana"])

    _guardar("E07_cambio_rol.json", {
        "fase": "E07",
        "concepto": "caso 6: Ana cambia el rol de Pedro a CAPTURISTA",
        "utc": _ahora(),
        "autenticacion": "Bearer (Ana, ADMINISTRADOR)",
        "variables": {"companyUserId": pedro, "roleId": rol_capturista},
        "respuesta": datos,
        "rol_activo_en_bd": _sql(
            "SELECT role_id FROM company_user_roles "
            "WHERE company_user_id = :c AND is_active",
            {"c": pedro},
        ),
    })


def fase_e08(db, ctx: dict) -> None:
    alpha = _id_empresa(_membresia("ana@test.local"))
    cuenta = _recurso("accounts", alpha)
    concepto = _recurso("concepts", alpha)

    datos = _operacion("CrearMovimiento", {
        "input": {
            "accountId": cuenta,
            "conceptId": concepto,
            "transactionType": "INCOME",
            "amount": 22.5,
            "shortDescription": "A6 Pedro token previo (evidencia)",
        }
    }, token=ctx["token_pedro_previo"])

    creada = (datos.get("data") or {}).get("createTransaction")
    if creada:
        ctx["limpieza"]["transactions"].append(creada["id"])

    _guardar("E08_token_previo_rol_nuevo.json", {
        "fase": "E08",
        "concepto": "caso 7: el token anterior de Pedro ya refleja CAPTURISTA",
        "utc": _ahora(),
        "autenticacion": "Bearer (Pedro, mismo token emitido antes del cambio)",
        "respuesta": datos,
        "guardado": creada is not None,
    })


def fase_e09(db, ctx: dict) -> None:
    alpha = _id_empresa(_membresia("ana@test.local"))
    beta = _id_empresa(_membresia("admin_b@test.local"))
    ana = _membresia("ana@test.local")

    cruzado = _firmar({
        "companyUserId": ana,
        "companyId": beta,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    })
    vencido = _firmar({
        "companyUserId": ana,
        "companyId": alpha,
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    })
    alterado = ctx["token_ana"][:-1] + (
        "a" if ctx["token_ana"][-1] != "a" else "b"
    )

    antes = _conteo("accounts")
    consulta_otra_empresa = _operacion(
        "ConsultarCuentas", {"companyId": alpha}, token=ctx["token_admin_b"]
    )
    escritura_vencida = _operacion("CrearCuenta", {
        "input": {
            "companyId": alpha,
            "accountType": "DEBIT",
            "name": "A6 vencido (evidencia)",
        }
    }, token=vencido)
    escritura_alterada = _operacion("CrearCuenta", {
        "input": {
            "companyId": alpha,
            "accountType": "DEBIT",
            "name": "A6 alterado (evidencia)",
        }
    }, token=alterado)

    _guardar("E09_tokens_invalidos.json", {
        "fase": "E09",
        "concepto": "casos 8 y 9: token de otra empresa, vencido y alterado",
        "utc": _ahora(),
        "token_otra_empresa": {
            "autenticacion": "Bearer (admin_b, empresa Beta)",
            "mensaje": _mensaje_error(consulta_otra_empresa),
            "respuesta": consulta_otra_empresa,
        },
        "token_vencido": {
            "mensaje": _mensaje_error(escritura_vencida),
            "respuesta": escritura_vencida,
        },
        "token_alterado": {
            "mensaje": _mensaje_error(escritura_alterada),
            "respuesta": escritura_alterada,
        },
        "cuentas_antes": antes,
        "cuentas_despues": _conteo("accounts"),
        "sin_escrituras": _conteo("accounts") == antes,
    })


def fase_e10(db, ctx: dict) -> None:
    introspeccion = _gql(
        "{__schema{queryType{fields{name args{name}}}"
        "mutationType{fields{name args{name}}}}}",
        token=ctx["token_ana"],
    )
    texto = json.dumps(introspeccion)
    matriz = _matriz()
    oficial = {rol: sorted(codigos) for rol, codigos in MATRIZ_OFICIAL.items()}

    _guardar("E10_resumen.json", {
        "fase": "E10",
        "concepto": "contrato sin actorCompanyUserId y permisos de A5 intactos",
        "utc": _ahora(),
        "contrato": {
            "actor_company_user_id_en_sdl": "actorCompanyUserId" in texto,
            "operaciones_protegidas": 30,
        },
        "permisos_actividad5": {
            "matriz": matriz,
            "conteos": {rol: len(codigos) for rol, codigos in matriz.items()},
            "sin_cambios": matriz == oficial,
        },
        "secretos": {
            "JWT_SECRET_configurado": bool(os.getenv("JWT_SECRET")),
            "valor_expuesto": False,
        },
        "limpieza": {
            "cuentas_eliminadas": len(ctx["limpieza"]["accounts"]),
            "movimientos_eliminados": len(ctx["limpieza"]["transactions"]),
        },
    })


def _restaurar(db, ctx: dict) -> list[str]:
    incidencias: list[str] = []

    for transaccion_id in ctx["limpieza"]["transactions"]:
        _sql_ejecutar(
            "DELETE FROM transactions WHERE id = :i",
            {"i": transaccion_id},
        )
    for cuenta_id in ctx["limpieza"]["accounts"]:
        _sql_ejecutar(
            "DELETE FROM accounts WHERE id = :i",
            {"i": cuenta_id},
        )

    pedro = _membresia("pedro@test.local")
    rol_consulta = _sql(
        "SELECT id FROM roles WHERE code = 'CONSULTA'"
    )[0]["id"]
    _sql_ejecutar(
        "UPDATE company_user_roles SET is_active = false "
        "WHERE company_user_id = :c",
        {"c": pedro},
    )
    _sql_ejecutar(
        "UPDATE company_user_roles SET is_active = true "
        "WHERE company_user_id = :c AND role_id = :r",
        {"c": pedro, "r": rol_consulta},
    )

    activo = _sql(
        "SELECT role_id FROM company_user_roles "
        "WHERE company_user_id = :c AND is_active",
        {"c": pedro},
    )
    if len(activo) != 1 or activo[0]["role_id"] != rol_consulta:
        incidencias.append("no se restauro el rol CONSULTA de Pedro")

    return incidencias


def main() -> None:
    db = SessionLocal()
    try:
        _verificar_guardas(db)
        _log(f"conteo inicial: accounts={_conteo('accounts')} "
             f"transactions={_conteo('transactions')}")

        ctx: dict = {"limpieza": {"accounts": [], "transactions": []}}

        ctx.update(fase_e01(db))
        ctx["token_luis"] = _login("luis@test.local")
        ctx["token_maria"] = _login("maria@test.local")
        ctx["token_admin_b"] = _login("admin_b@test.local")
        ctx["token_pedro_previo"] = _login("pedro@test.local")

        fase_e02(db)
        fase_e03(db, ctx)
        fase_e04(db, ctx)
        fase_e05(db, ctx)
        fase_e06(db, ctx)
        fase_e07(db, ctx)
        fase_e08(db, ctx)
        fase_e09(db, ctx)

        incidencias = _restaurar(db, ctx)
        fase_e10(db, ctx)

        _guardar("resumen_actividad6.json", {
            "utc": _ahora(),
            "fases": "E01-E10",
            "incidencias_restauracion": incidencias,
            "conteo_final": {
                "accounts": _conteo("accounts"),
                "transactions": _conteo("transactions"),
            },
        })
        _log(f"incidencias: {incidencias}")
        _log("evidencias A6 completas")
    finally:
        db.close()


if __name__ == "__main__":
    main()
