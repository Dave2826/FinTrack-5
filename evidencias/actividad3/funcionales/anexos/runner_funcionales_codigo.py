"""Runner temporal de pruebas funcionales. NO forma parte de la implementacion."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")

import jwt as pyjwt

from scripts.setup_pruebas import CONTRASENA_PRUEBAS

URL = "http://127.0.0.1:8000/graphql"

NO_AUTH = "Usuario no autenticado"
NO_MEMBERSHIP = "La membresia no existe o esta inactiva"
ACTOR_MISMATCH = "El actor no corresponde al usuario autenticado"
SCOPE = "El actor no pertenece a la empresa del recurso"


def _norm(texto):
    return (texto or "").replace("á", "a").replace("é", "e").replace(
        "í", "i").replace("ó", "o").replace("ú", "u")


def _msg_matches(msg, esperado):
    return _norm(msg).lower() == _norm(esperado).lower()


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"}
    )
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"errors": [{"message": "HTTP %s sin cuerpo" % e.code}]}
    except Exception as exc:
        return None, {"errors": [{"message": "ERROR_CONEXION: %s" % exc}]}


TOKENS = {}


def login(actor, email, password=None):
    status, payload = gql(
        None,
        """mutation($input: LoginInput!) {
            login(input: $input) { accessToken tokenType }
        }""",
        {"input": {"email": email, "password": password or CONTRASENA_PRUEBAS}},
    )
    if status != 200 or "errors" in payload:
        return None, status, payload
    token = payload["data"]["login"]["accessToken"]
    TOKENS[actor] = token
    return token, status, payload


def token_firmado(user_id, minutos):
    secret = os.environ["JWT_SECRET_KEY"]
    alg = os.environ.get("JWT_ALGORITHM", "HS256")
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    return pyjwt.encode({"sub": str(user_id), "exp": exp}, secret, algorithm=alg)


def caso(cid, actor, rol, operacion, permiso_esperado, resultado_esperado,
         token, query, variables=None, expect="error", mensaje=None,
         efecto="sin cambio"):
    status, payload = gql(token, query, variables)
    errores = payload.get("errors") or []
    data = payload.get("data")

    if expect == "ok":
        aprobado = status == 200 and not errores and data is not None
        observado = "OK" if aprobado else json.dumps(
            {"http": status, "errors": errores, "data": data}, ensure_ascii=False
        )[:300]
    else:
        if errores:
            msg = errores[0].get("message", "")
            aprobado = status == 200 and _msg_matches(msg, mensaje)
            observado = msg
        elif data is None:
            aprobado = False
            observado = "sin errors y sin data: %s" % json.dumps(payload)[:200]
        else:
            aprobado = False
            observado = "ESPERABA ERROR pero hubo data: %s" % json.dumps(
                data, ensure_ascii=False)[:200]

    registro = {
        "caso": cid,
        "actor": actor,
        "rol": rol,
        "operacion": operacion,
        "permiso_esperado": permiso_esperado,
        "resultado_esperado": resultado_esperado,
        "resultado_observado": observado,
        "http": status,
        "estado": "APROBADO" if aprobado else "FALLIDO",
        "efecto_datos": efecto,
    }
    print(json.dumps(registro, ensure_ascii=False), flush=True)
    if not aprobado:
        return False, status, payload
    return True, status, payload


Q_ACCOUNTS = """query($a: Int!, $c: Int!) {
  accounts(actorCompanyUserId: $a, companyId: $c) { id name companyId isActive }
}"""
Q_ACCOUNT = """query($a: Int!, $id: Int!) {
  account(actorCompanyUserId: $a, accountId: $id) { id companyId name }
}"""
Q_CONCEPTS = """query($a: Int!, $c: Int!) {
  concepts(actorCompanyUserId: $a, companyId: $c) { id name }
}"""
Q_CONCEPT = """query($a: Int!, $id: Int!) {
  concept(actorCompanyUserId: $a, conceptId: $id) { id companyId name }
}"""
Q_AC = """query($a: Int!, $acc: Int!) {
  accountConcepts(actorCompanyUserId: $a, accountId: $acc) { id isActive }
}"""
Q_TX = """query($a: Int!, $acc: Int!) {
  transactions(actorCompanyUserId: $a, accountId: $acc) { id isActive capturedBy }
}"""
Q_ROLES = """query($a: Int!) { listRoles(actorCompanyUserId: $a) { id code } }"""
Q_PERMS = """query($a: Int!) { listPermissions(actorCompanyUserId: $a) { id code } }"""
Q_RPERMS = """query($a: Int!, $r: Int!) {
  listRolePermissions(actorCompanyUserId: $a, roleId: $r) { id isActive }
}"""

M_CREATE_ACCOUNT = """mutation($input: CreateAccountInput!) {
  createAccount(input: $input) { id name companyId }
}"""
M_CREATE_CONCEPT = """mutation($input: CreateConceptInput!) {
  createConcept(input: $input) { id name }
}"""
M_ASSIGN_AC = """mutation($input: AssignConceptToAccountInput!) {
  assignConceptToAccount(input: $input) { id isActive }
}"""
M_REMOVE_AC = """mutation($a: Int!, $acc: Int!, $con: Int!) {
  removeConceptFromAccount(actorCompanyUserId: $a, accountId: $acc, conceptId: $con) { id isActive }
}"""
M_CREATE_TX = """mutation($input: CreateTransactionInput!) {
  createTransaction(input: $input) { id capturedBy isActive }
}"""
M_DELETE_TX = """mutation($a: Int!, $id: Int!) {
  deleteTransaction(actorCompanyUserId: $a, transactionId: $id) { id isActive }
}"""
M_CREATE_ROLE = """mutation($input: CreateRoleInput!) {
  createRole(input: $input) { id code }
}"""
M_DEACT_ROLE = """mutation($a: Int!, $id: Int!) {
  deactivateRole(actorCompanyUserId: $a, roleId: $id) { id code isActive }
}"""
M_CREATE_PERM = """mutation($input: CreatePermissionInput!) {
  createPermission(input: $input) { id code }
}"""
M_ASSIGN_PERM = """mutation($input: AssignPermissionToRoleInput!) {
  assignPermissionToRole(input: $input) { id isActive }
}"""
M_REMOVE_PERM = """mutation($a: Int!, $r: Int!, $p: Int!) {
  removePermissionFromRole(actorCompanyUserId: $a, roleId: $r, permissionId: $p) { id isActive }
}"""
M_CREATE_CU = """mutation($input: CreateCompanyUserInput!) {
  createCompanyUser(input: $input) { id companyId userId isAdmin isActive }
}"""
M_DEACT_CU = """mutation($a: Int!, $id: Int!) {
  deactivateCompanyUser(actorCompanyUserId: $a, companyUserId: $id) { id isActive }
}"""
M_ASSIGN_ROLE = """mutation($input: AssignRoleInput!) {
  assignRole(input: $input) { id companyUserId roleId isActive }
}"""

FALLOS = []


def falla(bloque, detalle):
    FALLOS.append({"bloque": bloque, "detalle": detalle})
    print(json.dumps({"ABORTA_BLOQUE": bloque, "detalle": detalle},
                     ensure_ascii=False), flush=True)


def bloque_p02():
    token, status, payload = login("admin_a", "admin_a@test.local")
    ok = token is not None
    tipo = ""
    if ok:
        tipo = payload["data"]["login"]["tokenType"]
        ok = tipo == "bearer"
    print(json.dumps({
        "caso": "P02", "actor": "admin_a", "rol": "ADMINISTRADOR",
        "operacion": "login + accounts(company 3)",
        "permiso_esperado": "accounts.read",
        "resultado_esperado": "login OK y 1 cuenta (id 3)",
        "resultado_observado": ("login OK tokenType=%s; " % tipo) if ok
            else "login FALLIDO (sin token)",
        "http": status, "estado": "APROBADO" if ok else "FALLIDO",
        "efecto_datos": "sin cambio",
    }, ensure_ascii=False), flush=True)
    if not ok:
        return False
    ok2, _, _ = caso(
        "P02b", "admin_a", "ADMINISTRADOR", "accounts",
        "accounts.read", "1 cuenta id=3", TOKENS["admin_a"],
        Q_ACCOUNTS, {"a": 6, "c": 3}, expect="ok", efecto="sin cambio")
    return ok2


def bloque_a():
    aprobados = 0

    token, status, payload = login("admin_a", "admin_a@test.local")
    ok = (token is not None and payload["data"]["login"]["tokenType"] == "bearer")
    print(json.dumps({
        "caso": "A01", "actor": "admin_a", "rol": "ADMINISTRADOR",
        "operacion": "login", "permiso_esperado": "-",
        "resultado_observado": "token_type=bearer" if ok else json.dumps(payload)[:200],
        "http": status, "estado": "APROBADO" if ok else "FALLIDO",
        "efecto_datos": "sin cambio",
        "resultado_esperado": "token bearer",
    }, ensure_ascii=False), flush=True)
    if ok:
        aprobados += 1

    _, status, payload = login("x", "admin_a@test.local", password="incorrecta-ficticia")
    msg = (payload.get("errors") or [{}])[0].get("message", "")
    ok = _msg_matches(msg, "Credenciales invalidas")
    print(json.dumps({
        "caso": "A02", "actor": "-", "rol": "-", "operacion": "login password mala",
        "permiso_esperado": "-", "resultado_esperado": "Credenciales invalidas",
        "resultado_observado": msg, "http": status,
        "estado": "APROBADO" if ok else "FALLIDO", "efecto_datos": "sin cambio",
    }, ensure_ascii=False), flush=True)
    if ok:
        aprobados += 1

    _, status, payload = login("x", "inactivo_a@test.local")
    msg = (payload.get("errors") or [{}])[0].get("message", "")
    ok = _msg_matches(msg, "El usuario esta inactivo")
    print(json.dumps({
        "caso": "A03", "actor": "inactivo_a", "rol": "-",
        "operacion": "login usuario inactivo",
        "permiso_esperado": "-", "resultado_esperado": "El usuario esta inactivo",
        "resultado_observado": msg, "http": status,
        "estado": "APROBADO" if ok else "FALLIDO", "efecto_datos": "sin cambio",
    }, ensure_ascii=False), flush=True)
    if ok:
        aprobados += 1

    casos_a = [
        ("A04", None, NO_AUTH, "sin header Authorization"),
        ("A05", "token-corrupto-no-jwt", NO_AUTH, "Bearer corrupto"),
        ("A06", token_firmado(8, -10), NO_AUTH, "token vencido (exp -10min)"),
        ("A07", token_firmado(999, 30), NO_AUTH, "token sub=999 inexistente"),
        ("A08", token_firmado(14, 30), NO_AUTH, "token de usuario inactivo (user 14)"),
    ]
    for cid, tok, esperado, desc in casos_a:
        ok, status, payload = caso(
            cid, "-", "-", "accounts(company 3)", "-", esperado,
            tok, Q_ACCOUNTS, {"a": 6, "c": 3},
            expect="error", mensaje=esperado,
            efecto="sin cambio (%s)" % desc)
        if ok:
            aprobados += 1
    return aprobados


def bloque_b_sin_b05():
    aprobados = 0
    t_admin = TOKENS.get("admin_a")
    t_sinm = TOKENS.get("sin_membresia_a")

    ok, _, _ = caso(
        "B01", "admin_a", "ADMINISTRADOR", "accounts(actor=7)",
        "-", ACTOR_MISMATCH, t_admin, Q_ACCOUNTS, {"a": 7, "c": 3},
        expect="error", mensaje=ACTOR_MISMATCH,
        efecto="sin cambio (membresia ajena)")
    if ok:
        aprobados += 1

    ok, _, _ = caso(
        "B02", "admin_a", "ADMINISTRADOR", "accounts(actor=9999)",
        "-", NO_MEMBERSHIP, t_admin, Q_ACCOUNTS, {"a": 9999, "c": 3},
        expect="error", mensaje=NO_MEMBERSHIP,
        efecto="sin cambio (membresia inexistente)")
    if ok:
        aprobados += 1

    ok, _, _ = caso(
        "B03", "sin_membresia_a", "-", "accounts(actor=6)",
        "-", ACTOR_MISMATCH, t_sinm, Q_ACCOUNTS, {"a": 6, "c": 3},
        expect="error", mensaje=ACTOR_MISMATCH,
        efecto="sin cambio")
    if ok:
        aprobados += 1

    ok, _, _ = caso(
        "B04", "sin_membresia_a", "-", "accounts(actor=9999)",
        "-", NO_MEMBERSHIP, t_sinm, Q_ACCOUNTS, {"a": 9999, "c": 3},
        expect="error", mensaje=NO_MEMBERSHIP,
        efecto="sin cambio")
    if ok:
        aprobados += 1
    return aprobados


def bloque_c1():
    aprobados = 0
    t_consu = TOKENS["consulta_a"]
    t_capt = TOKENS["capturista_a"]
    t_cont = TOKENS["contador_a"]
    t_admin = TOKENS["admin_a"]

    ok, _, _ = caso("C01", "consulta_a", "CONSULTA", "accounts(3)",
                    "accounts.read", "1 cuenta", t_consu, Q_ACCOUNTS,
                    {"a": 10, "c": 3}, expect="ok")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C02", "consulta_a", "CONSULTA", "account(3)",
                    "accounts.read", "cuenta 3", t_consu, Q_ACCOUNT,
                    {"a": 10, "id": 3}, expect="ok")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C03", "consulta_a", "CONSULTA", "concepts(3)",
                    "concepts.read", "2 conceptos", t_consu, Q_CONCEPTS,
                    {"a": 10, "c": 3}, expect="ok")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C04", "consulta_a", "CONSULTA", "concept(4)",
                    "concepts.read", "concepto 4", t_consu, Q_CONCEPT,
                    {"a": 10, "id": 4}, expect="ok")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C05", "consulta_a", "CONSULTA", "accountConcepts(3)",
                    "accounts.read", "2 relaciones", t_consu, Q_AC,
                    {"a": 10, "acc": 3}, expect="ok")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C06", "consulta_a", "CONSULTA", "transactions(3)",
                    "transactions.read", "2 transacciones", t_consu, Q_TX,
                    {"a": 10, "acc": 3}, expect="ok")
    aprobados += 1 if ok else 0

    for cid, op, query, variables, perm in [
        ("C07", "listRoles", Q_ROLES, {"a": 10}, "roles.read"),
        ("C08", "listPermissions", Q_PERMS, {"a": 10}, "roles.read"),
        ("C09", "listRolePermissions(role 4)", Q_RPERMS, {"a": 10, "r": 4}, "roles.read"),
    ]:
        ok, _, _ = caso(cid, "consulta_a", "CONSULTA", op, perm,
                        "denegado: El rol no tiene el permiso " + perm,
                        t_consu, query, variables, expect="error",
                        mensaje="El rol no tiene el permiso " + perm)
        aprobados += 1 if ok else 0

    ok, _, _ = caso("C10", "consulta_a", "CONSULTA", "createAccount(3)",
                    "accounts.write",
                    "denegado: El rol no tiene el permiso accounts.write",
                    t_consu, M_CREATE_ACCOUNT,
                    {"input": {"actorCompanyUserId": 10, "companyId": 3,
                               "accountType": "DEBIT", "name": "Cuenta Denegada"}},
                    expect="error",
                    mensaje="El rol no tiene el permiso accounts.write")
    aprobados += 1 if ok else 0
    _, _, p = caso("C10v", "admin_a", "ADMINISTRADOR", "accounts(3) verificacion",
                   "-", "sigue 1 cuenta", t_admin, Q_ACCOUNTS,
                   {"a": 6, "c": 3}, expect="ok",
                   efecto="C10 no altero datos")

    ok, _, _ = caso("C11", "consulta_a", "CONSULTA", "createConcept(3)",
                    "concepts.write",
                    "denegado: El rol no tiene el permiso concepts.write",
                    t_consu, M_CREATE_CONCEPT,
                    {"input": {"actorCompanyUserId": 10, "companyId": 3,
                               "conceptType": "INCOME", "name": "Concepto Denegado"}},
                    expect="error",
                    mensaje="El rol no tiene el permiso concepts.write")
    aprobados += 1 if ok else 0

    ok, _, _ = caso("C12", "consulta_a", "CONSULTA", "createTransaction(3,4)",
                    "transactions.write",
                    "denegado: El rol no tiene el permiso transactions.write",
                    t_consu, M_CREATE_TX,
                    {"input": {"actorCompanyUserId": 10, "accountId": 3,
                               "conceptId": 4, "transactionType": "INCOME",
                               "amount": "1.00"}},
                    expect="error",
                    mensaje="El rol no tiene el permiso transactions.write")
    aprobados += 1 if ok else 0

    ok, _, _ = caso("C13", "consulta_a", "CONSULTA", "deleteTransaction(4)",
                    "transactions.write",
                    "denegado: El rol no tiene el permiso transactions.write",
                    t_consu, M_DELETE_TX, {"a": 10, "id": 4},
                    expect="error",
                    mensaje="El rol no tiene el permiso transactions.write")
    aprobados += 1 if ok else 0
    ok, _, payload = caso(
        "C13v", "admin_a", "ADMINISTRADOR", "transactions(3) verificacion",
        "-", "tx4 sigue activa", t_admin, Q_TX, {"a": 6, "acc": 3},
        expect="ok", efecto="C13 no altero datos")
    if ok:
        txs = payload["data"]["transactions"]
        tx4 = next((t for t in txs if t["id"] == 4), None)
        detalle = "tx4=%s" % json.dumps(tx4)
        print(json.dumps({"caso": "C13v-detalle", "detalle": detalle,
                          "estado": "APROBADO" if tx4 and tx4["isActive"] else "FALLIDO"},
                         ensure_ascii=False), flush=True)

    ok, _, _ = caso("C14", "consulta_a", "CONSULTA", "assignRole(cu10, role3)",
                    "roles.write",
                    "denegado: El rol no tiene el permiso roles.write",
                    t_consu, M_ASSIGN_ROLE,
                    {"input": {"actorCompanyUserId": 10, "companyUserId": 10,
                               "roleId": 3}},
                    expect="error",
                    mensaje="El rol no tiene el permiso roles.write")
    aprobados += 1 if ok else 0

    ok, _, _ = caso("C15", "consulta_a", "CONSULTA", "createCompanyUser(3, user13)",
                    "company.users.write",
                    "denegado: El rol no tiene el permiso company.users.write",
                    t_consu, M_CREATE_CU,
                    {"input": {"actorCompanyUserId": 10, "companyId": 3,
                               "userId": 13, "isAdmin": False}},
                    expect="error",
                    mensaje="El rol no tiene el permiso company.users.write")
    aprobados += 1 if ok else 0

    ok, _, _ = caso("C16", "consulta_a", "CONSULTA", "createRole",
                    "roles.write",
                    "denegado: El rol no tiene el permiso roles.write",
                    t_consu, M_CREATE_ROLE,
                    {"input": {"actorCompanyUserId": 10, "code": "ROL_X",
                               "name": "Rol X"}},
                    expect="error",
                    mensaje="El rol no tiene el permiso roles.write")
    aprobados += 1 if ok else 0

    ok, _, _ = caso("C17", "capturista_a", "CAPTURISTA", "accounts(3)",
                    "accounts.read", "1 cuenta", t_capt, Q_ACCOUNTS,
                    {"a": 9, "c": 3}, expect="ok")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C18", "capturista_a", "CAPTURISTA", "transactions(3)",
                    "transactions.read", "2 transacciones", t_capt, Q_TX,
                    {"a": 9, "acc": 3}, expect="ok")
    aprobados += 1 if ok else 0

    ok, status, payload = caso(
        "C19", "capturista_a", "CAPTURISTA", "createTransaction(3,4,INCOME,10)",
        "transactions.write", "transaccion creada captured_by=11",
        t_capt, M_CREATE_TX,
        {"input": {"actorCompanyUserId": 9, "accountId": 3, "conceptId": 4,
                   "transactionType": "INCOME", "amount": "10.00",
                   "shortDescription": "Prueba funcional C19"}},
        expect="ok", efecto="+1 transaccion (se soft-delete en C24)")
    aprobados += 1 if ok else 0
    tx_c19 = None
    if ok:
        tx_c19 = payload["data"]["createTransaction"]["id"]
        cb = payload["data"]["createTransaction"]["capturedBy"]
        okcb = cb == 11
        print(json.dumps({
            "caso": "C19v", "detalle": "captured_by=%s (esperado 11)" % cb,
            "estado": "APROBADO" if okcb else "FALLIDO",
        }, ensure_ascii=False), flush=True)

    ok, _, _ = caso("C20", "capturista_a", "CAPTURISTA", "createAccount(3)",
                    "accounts.write",
                    "denegado: El rol no tiene el permiso accounts.write",
                    t_capt, M_CREATE_ACCOUNT,
                    {"input": {"actorCompanyUserId": 9, "companyId": 3,
                               "accountType": "DEBIT", "name": "Cuenta Denegada 2"}},
                    expect="error",
                    mensaje="El rol no tiene el permiso accounts.write")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C21", "capturista_a", "CAPTURISTA", "createConcept(3)",
                    "concepts.write",
                    "denegado: El rol no tiene el permiso concepts.write",
                    t_capt, M_CREATE_CONCEPT,
                    {"input": {"actorCompanyUserId": 9, "companyId": 3,
                               "conceptType": "INCOME", "name": "Concepto Denegado 2"}},
                    expect="error",
                    mensaje="El rol no tiene el permiso concepts.write")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C22", "capturista_a", "CAPTURISTA",
                    "assignConceptToAccount(cuenta3, concepto Beta 6)",
                    "concepts.write",
                    "denegado por permiso ANTES del chequeo de empresa",
                    t_capt, M_ASSIGN_AC,
                    {"input": {"actorCompanyUserId": 9, "accountId": 3,
                               "conceptId": 6}},
                    expect="error",
                    mensaje="El rol no tiene el permiso concepts.write")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C23", "capturista_a", "CAPTURISTA", "listRoles",
                    "roles.read",
                    "denegado: El rol no tiene el permiso roles.read",
                    t_capt, Q_ROLES, {"a": 9}, expect="error",
                    mensaje="El rol no tiene el permiso roles.read")
    aprobados += 1 if ok else 0

    if tx_c19:
        ok, _, payload = caso(
            "C24", "capturista_a", "CAPTURISTA",
            "deleteTransaction(%s)" % tx_c19, "transactions.write",
            "transaccion soft-deleted", t_capt, M_DELETE_TX,
            {"a": 9, "id": tx_c19}, expect="ok",
            efecto="tx C19 pasa a is_active=false")
        aprobados += 1 if ok else 0

    ok, _, _ = caso("C25", "capturista_a", "CAPTURISTA", "createCompanyUser",
                    "company.users.write",
                    "denegado: El rol no tiene el permiso company.users.write",
                    t_capt, M_CREATE_CU,
                    {"input": {"actorCompanyUserId": 9, "companyId": 3,
                               "userId": 13, "isAdmin": False}},
                    expect="error",
                    mensaje="El rol no tiene el permiso company.users.write")
    aprobados += 1 if ok else 0

    ok, _, _ = caso("C26", "contador_a", "CONTADOR", "accounts(3)",
                    "accounts.read", "1 cuenta", t_cont, Q_ACCOUNTS,
                    {"a": 8, "c": 3}, expect="ok")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C27", "contador_a", "CONTADOR",
                    "createAccount nombre duplicado (Cuenta Alpha Pruebas)",
                    "accounts.write",
                    "demuestra accounts.write via 'Ya existe una cuenta activa con ese nombre'",
                    t_cont, M_CREATE_ACCOUNT,
                    {"input": {"actorCompanyUserId": 8, "companyId": 3,
                               "accountType": "DEBIT", "name": "Cuenta Alpha Pruebas"}},
                    expect="error",
                    mensaje="Ya existe una cuenta activa con ese nombre",
                    efecto="sin cambio (duplicado rechazado)")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C28", "contador_a", "CONTADOR",
                    "createConcept nombre duplicado (Ingreso Alpha Pruebas)",
                    "concepts.write",
                    "demuestra concepts.write via 'Ya existe un concepto activo con ese nombre'",
                    t_cont, M_CREATE_CONCEPT,
                    {"input": {"actorCompanyUserId": 8, "companyId": 3,
                               "conceptType": "INCOME", "name": "Ingreso Alpha Pruebas"}},
                    expect="error",
                    mensaje="Ya existe un concepto activo con ese nombre",
                    efecto="sin cambio (duplicado rechazado)")
    aprobados += 1 if ok else 0

    ok, status, payload = caso(
        "C29a", "contador_a", "CONTADOR", "createTransaction(3,4,INCOME,5)",
        "transactions.write", "transaccion creada",
        t_cont, M_CREATE_TX,
        {"input": {"actorCompanyUserId": 8, "accountId": 3, "conceptId": 4,
                   "transactionType": "INCOME", "amount": "5.00",
                   "shortDescription": "Prueba funcional C29"}},
        expect="ok", efecto="+1 transaccion (se soft-delete en C29b)")
    aprobados += 1 if ok else 0
    if ok:
        tx_c29 = payload["data"]["createTransaction"]["id"]
        ok2, _, _ = caso(
            "C29b", "contador_a", "CONTADOR", "deleteTransaction(%s)" % tx_c29,
            "transactions.write", "soft-delete OK", t_cont, M_DELETE_TX,
            {"a": 8, "id": tx_c29}, expect="ok",
            efecto="tx C29 pasa a is_active=false")
        aprobados += 1 if ok2 else 0

    ok, _, _ = caso("C30", "contador_a", "CONTADOR", "assignRole(cu10, role3)",
                    "roles.write",
                    "denegado: El rol no tiene el permiso roles.write",
                    t_cont, M_ASSIGN_ROLE,
                    {"input": {"actorCompanyUserId": 8, "companyUserId": 10,
                               "roleId": 3}},
                    expect="error",
                    mensaje="El rol no tiene el permiso roles.write")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C31", "contador_a", "CONTADOR", "createRole",
                    "roles.write",
                    "denegado: El rol no tiene el permiso roles.write",
                    t_cont, M_CREATE_ROLE,
                    {"input": {"actorCompanyUserId": 8, "code": "ROL_X",
                               "name": "Rol X"}},
                    expect="error",
                    mensaje="El rol no tiene el permiso roles.write")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C32", "contador_a", "CONTADOR", "listRoles",
                    "roles.read", "4 roles", t_cont, Q_ROLES, {"a": 8},
                    expect="ok")
    aprobados += 1 if ok else 0
    ok, _, _ = caso("C33", "contador_a", "CONTADOR", "createCompanyUser(3, user13)",
                    "company.users.write",
                    "denegado: El rol no tiene el permiso company.users.write",
                    t_cont, M_CREATE_CU,
                    {"input": {"actorCompanyUserId": 8, "companyId": 3,
                               "userId": 13, "isAdmin": False}},
                    expect="error",
                    mensaje="El rol no tiene el permiso company.users.write")
    aprobados += 1 if ok else 0
    return aprobados


def bloque_c2_b05():
    aprobados = 0
    t_adminb = TOKENS["admin_b"]

    ok, status, payload = caso(
        "C34", "admin_b", "ADMINISTRADOR (Beta)",
        "createCompanyUser(empresa 4, user 13, is_admin=false)",
        "company.users.write",
        "membresia creada para sin_membresia_a en Beta",
        t_adminb, M_CREATE_CU,
        {"input": {"actorCompanyUserId": 7, "companyId": 4, "userId": 13,
                   "isAdmin": False}},
        expect="ok", efecto="+1 company_user en Beta (se desactiva en C35)")
    aprobados += 1 if ok else 0
    cu_nueva = None
    if ok:
        cu_nueva = payload["data"]["createCompanyUser"]["id"]
        print(json.dumps({"caso": "C34-id", "membresia_nueva": cu_nueva},
                         ensure_ascii=False), flush=True)
    else:
        falla("C2/B05", "C34 fallo; no se puede continuar el bloque")
        return aprobados

    ok, _, _ = caso(
        "C35", "admin_b", "ADMINISTRADOR (Beta)",
        "deactivateCompanyUser(%s)" % cu_nueva,
        "company.users.write", "membresia inactiva",
        t_adminb, M_DEACT_CU, {"a": 7, "id": cu_nueva}, expect="ok",
        efecto="membresia %s is_active=false" % cu_nueva)
    aprobados += 1 if ok else 0
    if not ok:
        falla("C2/B05", "C35 fallo; la membresia quedo activa, B05 no aplica")
        return aprobados

    ok, _, _ = caso(
        "B05", "sin_membresia_a", "-",
        "accounts(actor=%s) con membresia inactiva en Beta" % cu_nueva,
        "-", NO_MEMBERSHIP, TOKENS["sin_membresia_a"], Q_ACCOUNTS,
        {"a": cu_nueva, "c": 4}, expect="error", mensaje=NO_MEMBERSHIP,
        efecto="sin cambio (membresia inactiva)")
    aprobados += 1 if ok else 0
    return aprobados


def bloque_c3():
    aprobados = 0
    t_admin = TOKENS["admin_a"]
    t_cont = TOKENS["contador_a"]
    t_consu = TOKENS["consulta_a"]

    ok, _, payload = caso(
        "C36", "admin_a", "ADMINISTRADOR", "assignRole(cu10, role3 CAPTURISTA)",
        "roles.write", "rotacion CONSULTA->CAPTURISTA",
        t_admin, M_ASSIGN_ROLE,
        {"input": {"actorCompanyUserId": 6, "companyUserId": 10, "roleId": 3}},
        expect="ok", efecto="cu10 ahora CAPTURISTA; +1 fila role inactiva")
    aprobados += 1 if ok else 0
    if not ok:
        falla("C3", "C36 fallo; no se intenta restaurar")
        return aprobados

    ok, _, payload = caso(
        "C37", "admin_a", "ADMINISTRADOR", "assignRole(cu10, role4 CONSULTA)",
        "roles.write", "restauracion a CONSULTA",
        t_admin, M_ASSIGN_ROLE,
        {"input": {"actorCompanyUserId": 6, "companyUserId": 10, "roleId": 4}},
        expect="ok", efecto="cu10 restaurado a CONSULTA")
    aprobados += 1 if ok else 0
    if not ok:
        falla("C3", "C37 fallo; cu10 quedo CAPTURISTA, RESTAURACION PENDIENTE")
        return aprobados

    ok, _, _ = caso(
        "C38", "admin_a", "ADMINISTRADOR", "assignRole(cu10, role4) repetido",
        "roles.write", "denegado: La membresia ya tiene asignado este rol",
        t_admin, M_ASSIGN_ROLE,
        {"input": {"actorCompanyUserId": 6, "companyUserId": 10, "roleId": 4}},
        expect="error", mensaje="La membresia ya tiene asignado este rol",
        efecto="sin cambio")
    aprobados += 1 if ok else 0

    ok, _, _ = caso(
        "C39", "admin_a", "ADMINISTRADOR", "deactivateRole(1 ADMINISTRADOR)",
        "roles.write", "denegado: El rol ADMINISTRADOR no se puede desactivar",
        t_admin, M_DEACT_ROLE, {"a": 6, "id": 1}, expect="error",
        mensaje="El rol ADMINISTRADOR no se puede desactivar",
        efecto="sin cambio (rol 1 sigue activo)")
    aprobados += 1 if ok else 0

    ok, _, _ = caso(
        "C40", "admin_a", "ADMINISTRADOR",
        "removePermissionFromRole(role 1, perm 10 roles.write)",
        "roles.write",
        "denegado: No se puede retirar el permiso roles.write del rol ADMINISTRADOR",
        t_admin, M_REMOVE_PERM, {"a": 6, "r": 1, "p": 10}, expect="error",
        mensaje="No se puede retirar el permiso roles.write del rol ADMINISTRADOR",
        efecto="sin cambio (relacion 1-10 sigue activa)")
    aprobados += 1 if ok else 0

    ok, _, _ = caso(
        "C41", "admin_a", "ADMINISTRADOR", "createRole(code=ADMINISTRADOR)",
        "roles.write", "denegado: Ya existe un rol con ese codigo",
        t_admin, M_CREATE_ROLE,
        {"input": {"actorCompanyUserId": 6, "code": "ADMINISTRADOR",
                   "name": "Duplicado"}},
        expect="error", mensaje="Ya existe un rol con ese codigo",
        efecto="sin cambio")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "C42", "admin_a", "ADMINISTRADOR", "createPermission(code=accounts.read)",
        "roles.write", "denegado: Ya existe un permiso con ese codigo",
        t_admin, M_CREATE_PERM,
        {"input": {"actorCompanyUserId": 6, "code": "accounts.read",
                   "name": "Duplicado"}},
        expect="error", mensaje="Ya existe un permiso con ese codigo",
        efecto="sin cambio")
    aprobados += 1 if ok else 0

    _, _, payload = caso(
        "C43-pre", "admin_a", "ADMINISTRADOR",
        "listRolePermissions(role 2) conteo PRE", "roles.read",
        "8 relaciones activas de CONTADOR", t_admin, Q_RPERMS,
        {"a": 6, "r": 2}, expect="ok")
    pre = len((payload.get("data") or {}).get("listRolePermissions") or [])
    print(json.dumps({"caso": "C43-pre-conteo", "relaciones_activas": pre},
                     ensure_ascii=False), flush=True)
    if pre != 8:
        falla("C3", "C43-pre conteo %s != 8; no se ejecuta el par reversible" % pre)
        return aprobados

    ok, _, _ = caso(
        "C43", "admin_a", "ADMINISTRADOR",
        "removePermissionFromRole(CONTADOR, roles.read)",
        "roles.write", "relacion desactivada (26->25 activas)",
        t_admin, M_REMOVE_PERM, {"a": 6, "r": 2, "p": 9}, expect="ok",
        efecto="role_permissions activas: 26->25 (temporal)")
    aprobados += 1 if ok else 0
    if not ok:
        falla("C3", "C43 fallo; nada que restaurar")
        return aprobados

    ok, _, _ = caso(
        "C43v", "contador_a", "CONTADOR", "listRoles tras quitar roles.read",
        "roles.read", "denegado: El rol no tiene el permiso roles.read",
        t_cont, Q_ROLES, {"a": 8}, expect="error",
        mensaje="El rol no tiene el permiso roles.read",
        efecto="sin cambio")
    aprobados += 1 if ok else 0

    ok, _, payload = caso(
        "C45", "admin_a", "ADMINISTRADOR",
        "assignPermissionToRole(CONTADOR, roles.read) RESTAURACION",
        "roles.write", "relacion reactivada (vuelve a 26)",
        t_admin, M_ASSIGN_PERM,
        {"input": {"actorCompanyUserId": 6, "roleId": 2, "permissionId": 9}},
        expect="ok", efecto="role_permissions activas: 25->26 RESTAURADO")
    aprobados += 1 if ok else 0
    if not ok:
        falla("C3", "C45 RESTAURACION FALLIDA; CONTADOR sin roles.read")
        return aprobados

    ok, _, payload = caso(
        "C45v", "contador_a", "CONTADOR", "listRoles tras restaurar",
        "roles.read", "4 roles de nuevo", t_cont, Q_ROLES, {"a": 8},
        expect="ok", efecto="estado restaurado")
    aprobados += 1 if ok else 0
    _, _, payload = caso(
        "C45c", "admin_a", "ADMINISTRADOR",
        "listRolePermissions(role 2) conteo POST", "roles.read",
        "8 relaciones activas de CONTADOR", t_admin, Q_RPERMS,
        {"a": 6, "r": 2}, expect="ok")
    post = len((payload.get("data") or {}).get("listRolePermissions") or [])
    print(json.dumps({"caso": "C45c-conteo", "relaciones_activas": post,
                      "estado": "APROBADO" if post == 8 else "FALLIDO"},
                     ensure_ascii=False), flush=True)
    if post != 8:
        falla("C3", "C45c conteo %s != 8; RESTAURACION INCOMPLETA" % post)
        return aprobados

    ok, _, _ = caso(
        "C46", "admin_a", "ADMINISTRADOR",
        "assignPermissionToRole(CONTADOR, roles.read) repetido",
        "roles.write", "denegado: El permiso ya esta asignado al rol",
        t_admin, M_ASSIGN_PERM,
        {"input": {"actorCompanyUserId": 6, "roleId": 2, "permissionId": 9}},
        expect="error", mensaje="El permiso ya esta asignado al rol",
        efecto="sin cambio")
    aprobados += 1 if ok else 0

    ok, _, _ = caso(
        "C47", "admin_a", "ADMINISTRADOR",
        "createCompanyUser(3, user13, is_admin=true)",
        "company.users.write",
        "denegado: La empresa ya tiene un administrador principal",
        t_admin, M_CREATE_CU,
        {"input": {"actorCompanyUserId": 6, "companyId": 3, "userId": 13,
                   "isAdmin": True}},
        expect="error",
        mensaje="La empresa ya tiene un administrador principal",
        efecto="sin cambio")
    aprobados += 1 if ok else 0
    return aprobados


def bloque_d():
    aprobados = 0
    ta = TOKENS["admin_a"]
    tb = TOKENS["admin_b"]

    d_alpha_beta = [
        ("D01", "accounts(empresa 4)", Q_ACCOUNTS, {"a": 6, "c": 4}, "accounts.read"),
        ("D02", "account(4)", Q_ACCOUNT, {"a": 6, "id": 4}, "accounts.read"),
        ("D03", "concepts(empresa 4)", Q_CONCEPTS, {"a": 6, "c": 4}, "concepts.read"),
        ("D04", "concept(6)", Q_CONCEPT, {"a": 6, "id": 6}, "concepts.read"),
        ("D05", "accountConcepts(cuenta 4)", Q_AC, {"a": 6, "acc": 4}, "accounts.read"),
        ("D06", "transactions(cuenta 4)", Q_TX, {"a": 6, "acc": 4}, "transactions.read"),
    ]
    for cid, op, query, variables, perm in d_alpha_beta:
        ok, _, _ = caso(cid, "admin_a", "ADMINISTRADOR (Alpha)", op, perm,
                        "denegado: " + SCOPE, ta, query, variables,
                        expect="error", mensaje=SCOPE,
                        efecto="sin cambio (recurso Beta protegido)")
        aprobados += 1 if ok else 0

    ok, _, _ = caso(
        "D07", "admin_a", "ADMINISTRADOR (Alpha)", "createAccount(empresa 4)",
        "accounts.write", "denegado: " + SCOPE, ta, M_CREATE_ACCOUNT,
        {"input": {"actorCompanyUserId": 6, "companyId": 4,
                   "accountType": "DEBIT", "name": "Cuenta Hack"}},
        expect="error", mensaje=SCOPE,
        efecto="sin cambio (empresa Beta sin cuentas nuevas)")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "D08", "admin_a", "ADMINISTRADOR (Alpha)", "createConcept(empresa 4)",
        "concepts.write", "denegado: " + SCOPE, ta, M_CREATE_CONCEPT,
        {"input": {"actorCompanyUserId": 6, "companyId": 4,
                   "conceptType": "INCOME", "name": "Concepto Hack"}},
        expect="error", mensaje=SCOPE,
        efecto="sin cambio")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "D09", "admin_a", "ADMINISTRADOR (Alpha)",
        "createTransaction(cuenta 4, concepto 6)",
        "transactions.write", "denegado: " + SCOPE, ta, M_CREATE_TX,
        {"input": {"actorCompanyUserId": 6, "accountId": 4, "conceptId": 6,
                   "transactionType": "INCOME", "amount": "1.00"}},
        expect="error", mensaje=SCOPE,
        efecto="sin cambio")
    aprobados += 1 if ok else 0

    ok, _, _ = caso(
        "D10", "admin_a", "ADMINISTRADOR (Alpha)",
        "assignConceptToAccount(cuenta Alpha 3, concepto Beta 6)",
        "concepts.write (scope pasa; falla validacion de empresa)",
        "denegado VALIDACION: La cuenta y el concepto deben pertenecer a la misma empresa",
        ta, M_ASSIGN_AC,
        {"input": {"actorCompanyUserId": 6, "accountId": 3, "conceptId": 6}},
        expect="error",
        mensaje="La cuenta y el concepto deben pertenecer a la misma empresa",
        efecto="sin cambio")
    aprobados += 1 if ok else 0

    ok, _, _ = caso(
        "D11", "admin_a", "ADMINISTRADOR (Alpha)",
        "removeConceptFromAccount(cuenta 4, concepto 6)",
        "concepts.write", "denegado: " + SCOPE, ta, M_REMOVE_AC,
        {"a": 6, "acc": 4, "con": 6}, expect="error", mensaje=SCOPE,
        efecto="sin cambio")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "D12", "admin_a", "ADMINISTRADOR (Alpha)", "assignRole(cu7 Beta, role2)",
        "roles.write", "denegado: " + SCOPE, ta, M_ASSIGN_ROLE,
        {"input": {"actorCompanyUserId": 6, "companyUserId": 7, "roleId": 2}},
        expect="error", mensaje=SCOPE,
        efecto="sin cambio (admin_b conserva rol)")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "D13", "admin_a", "ADMINISTRADOR (Alpha)", "deactivateCompanyUser(cu7)",
        "company.users.write", "denegado: " + SCOPE, ta, M_DEACT_CU,
        {"a": 6, "id": 7}, expect="error", mensaje=SCOPE,
        efecto="sin cambio (cu7 sigue activa)")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "D14", "admin_a", "ADMINISTRADOR (Alpha)",
        "createCompanyUser(empresa 4, user13)",
        "company.users.write", "denegado: " + SCOPE, ta, M_CREATE_CU,
        {"input": {"actorCompanyUserId": 6, "companyId": 4, "userId": 13,
                   "isAdmin": False}},
        expect="error", mensaje=SCOPE,
        efecto="sin cambio")
    aprobados += 1 if ok else 0

    ok, _, _ = caso(
        "D15", "admin_b", "ADMINISTRADOR (Beta)", "account(3 Alpha)",
        "accounts.read", "denegado: " + SCOPE, tb, Q_ACCOUNT,
        {"a": 7, "id": 3}, expect="error", mensaje=SCOPE,
        efecto="sin cambio")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "D16", "admin_b", "ADMINISTRADOR (Beta)", "createAccount(empresa 3)",
        "accounts.write", "denegado: " + SCOPE, tb, M_CREATE_ACCOUNT,
        {"input": {"actorCompanyUserId": 7, "companyId": 3,
                   "accountType": "DEBIT", "name": "Cuenta Hack 2"}},
        expect="error", mensaje=SCOPE,
        efecto="sin cambio")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "D17", "admin_b", "ADMINISTRADOR (Beta)", "transactions(cuenta 3)",
        "transactions.read", "denegado: " + SCOPE, tb, Q_TX,
        {"a": 7, "acc": 3}, expect="error", mensaje=SCOPE,
        efecto="sin cambio")
    aprobados += 1 if ok else 0
    ok, _, _ = caso(
        "D18", "admin_b", "ADMINISTRADOR (Beta)", "assignRole(cu8 Alpha, role4)",
        "roles.write", "denegado: " + SCOPE, tb, M_ASSIGN_ROLE,
        {"input": {"actorCompanyUserId": 7, "companyUserId": 8, "roleId": 4}},
        expect="error", mensaje=SCOPE,
        efecto="sin cambio (contador_a conserva CONTADOR)")
    aprobados += 1 if ok else 0
    return aprobados


def main():
    if len(sys.argv) < 2:
        print("uso: runner.py <bloque>", file=sys.stderr)
        sys.exit(2)
    bloque = sys.argv[1]

    correos = {
        "admin_a": "admin_a@test.local",
        "admin_b": "admin_b@test.local",
        "contador_a": "contador_a@test.local",
        "capturista_a": "capturista_a@test.local",
        "consulta_a": "consulta_a@test.local",
        "sin_membresia_a": "sin_membresia_a@test.local",
    }

    if bloque == "P02":
        sys.exit(0 if bloque_p02() else 1)

    necesarios = {
        "A": ["admin_a"],
        "B": ["admin_a", "sin_membresia_a"],
        "C1": ["admin_a", "consulta_a", "capturista_a", "contador_a"],
        "C2": ["admin_b", "sin_membresia_a"],
        "C3": ["admin_a", "contador_a", "consulta_a"],
        "D": ["admin_a", "admin_b"],
    }
    if bloque not in necesarios:
        print(json.dumps({"error": "bloque desconocido: %s" % bloque}))
        sys.exit(2)

    for actor in necesarios[bloque]:
        token, status, payload = login(actor, correos[actor])
        if token is None:
            print(json.dumps({"error": "login fallo", "actor": actor,
                              "detalle": json.dumps(payload, ensure_ascii=False)[:200],
                              "http": status}, ensure_ascii=False))
            sys.exit(1)

    if bloque == "A":
        n = bloque_a()
    elif bloque == "B":
        n = bloque_b_sin_b05()
    elif bloque == "C1":
        n = bloque_c1()
    elif bloque == "C2":
        n = bloque_c2_b05()
    elif bloque == "C3":
        n = bloque_c3()
    elif bloque == "D":
        n = bloque_d()

    print(json.dumps({"resumen_bloque": bloque, "aprobados": n,
                      "fallos": FALLOS}, ensure_ascii=False), flush=True)
    sys.exit(1 if FALLOS else 0)


if __name__ == "__main__":
    main()
