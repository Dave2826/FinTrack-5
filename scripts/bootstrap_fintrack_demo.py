"""Configuración autorizada de las cuatro cuentas de "FinTrack Demo".

Unidad III, Actividad 13. Deja la empresa FinTrack Demo con exactamente
esta distribución:

    Correo                                   Rol            Admin principal
    luis.chay@tecdesoftware.edu.mx           CONSULTA       No
    alexander.rodriguez@tecdesoftware.edu.mx CAPTURISTA     No
    david.morales@tecdesoftware.edu.mx       ADMINISTRADOR  Sí (nueva)
    david.demo@fintrack.local                CONTADOR       No (histórica)

Reglas que el script garantiza (y verifica antes del COMMIT):
- La empresa se conserva; no se crea ni se modifica.
- Movimientos, cuentas, conceptos y relaciones cuenta-concepto quedan
  intactos (se compara una huella antes y después, en la misma transacción).
- La membresía histórica de David conserva su ID; nunca se crea de nuevo.
- La nueva cuenta de David es el único administrador principal activo.
- Cada una de las cuatro membresías queda con exactamente un rol activo.
- Las demás membresías de la empresa no se tocan.

Modos:
    (sin opciones)  Plan en solo lectura (transacción READ ONLY). Default.
    --verificar     Solo lectura: comprueba el estado final; código 0 si
                    coincide con la distribución autorizada.
    --aplicar       Ejecuta el plan en UNA transacción. Cualquier error o
                    invariante incumplida -> ROLLBACK y código 1.

Contraseñas (solo para usuarios que se crean, o los que se indiquen en
--restablecer-contrasena): se leen de variables de entorno
BOOTSTRAP_PASSWORD_LUIS, BOOTSTRAP_PASSWORD_ALEXANDER,
BOOTSTRAP_PASSWORD_DAVID o, si faltan y hay terminal, se piden con
getpass. Nunca se imprimen ni se escriben en archivos. La contraseña de la
cuenta histórica nunca se cambia.

Ejecución (desde la raíz del repositorio, dentro del contenedor):
    docker compose exec api python -m scripts.bootstrap_fintrack_demo
    docker compose exec api python -m scripts.bootstrap_fintrack_demo --aplicar
    docker compose exec api python -m scripts.bootstrap_fintrack_demo --verificar
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Permite también `python scripts/bootstrap_fintrack_demo.py`: sin esto,
# Python solo añade scripts/ a sys.path y `import database` falla (era el
# error de importación de los intentos anteriores).
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import func, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from database.connection import SessionLocal  # noqa: E402
from models.company import Company  # noqa: E402
from models.company_user import CompanyUser  # noqa: E402
from models.company_user_role import CompanyUserRole  # noqa: E402
from models.role import Role  # noqa: E402
from models.user import User  # noqa: E402
from security.password import hash_password  # noqa: E402

EMPRESA_POR_DEFECTO = "FinTrack Demo"
LONGITUD_MINIMA_CONTRASENA = 8


@dataclass(frozen=True)
class CuentaObjetivo:
    clave: str
    nombre: str
    correo: str
    rol: str
    es_admin: bool
    historica: bool = False


CUENTAS = (
    CuentaObjetivo(
        "LUIS", "Edwuard Chay",
        "luis.chay@tecdesoftware.edu.mx", "CONSULTA", False,
    ),
    CuentaObjetivo(
        "ALEXANDER", "Alexander Fabrizio Rodriguez",
        "alexander.rodriguez@tecdesoftware.edu.mx", "CAPTURISTA", False,
    ),
    CuentaObjetivo(
        "DAVID", "David Morales",
        "david.morales@tecdesoftware.edu.mx", "ADMINISTRADOR", True,
    ),
    CuentaObjetivo(
        "DAVID_HISTORICA", "David Morales",
        "david.demo@fintrack.local", "CONTADOR", False, historica=True,
    ),
)


class Abortar(Exception):
    """Condición que impide continuar sin decisión humana."""


@dataclass
class Plan:
    empresa_id: int
    empresa_nombre: str
    acciones: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    contrasenas_requeridas: list[str] = field(default_factory=list)
    historica_id: int | None = None


def _log(mensaje: str) -> None:
    print(f"[bootstrap] {mensaje}", file=sys.stderr)


# ---------------------------------------------------------------- lecturas

def _empresa(db: Session, nombre: str, bloquear: bool) -> Company:
    consulta = db.query(Company).filter(Company.name == nombre)
    if bloquear:
        consulta = consulta.with_for_update()
    empresas = consulta.all()

    if not empresas:
        raise Abortar(f'no existe la empresa "{nombre}"')
    if len(empresas) > 1:
        raise Abortar(
            f'hay {len(empresas)} empresas llamadas "{nombre}"; '
            "se requiere una sola"
        )
    if not empresas[0].is_active:
        raise Abortar(f'la empresa "{nombre}" está inactiva')

    return empresas[0]


def _usuario(db: Session, correo: str) -> User | None:
    return (
        db.query(User)
        .filter(func.lower(User.email) == correo.lower())
        .one_or_none()
    )


def _membresia(db: Session, empresa_id: int, user_id: int) -> CompanyUser | None:
    return (
        db.query(CompanyUser)
        .filter(
            CompanyUser.company_id == empresa_id,
            CompanyUser.user_id == user_id,
        )
        .one_or_none()
    )


def _roles_activos(db: Session, company_user_id: int) -> list[CompanyUserRole]:
    return (
        db.query(CompanyUserRole)
        .filter(
            CompanyUserRole.company_user_id == company_user_id,
            CompanyUserRole.is_active.is_(True),
        )
        .all()
    )


def _roles_catalogo(db: Session) -> dict[str, Role]:
    roles = {r.code: r for r in db.query(Role).all()}
    for cuenta in CUENTAS:
        rol = roles.get(cuenta.rol)
        if rol is None or not rol.is_active:
            raise Abortar(f"el rol {cuenta.rol} no existe o está inactivo")
    return roles


def huella_financiera(db: Session, empresa_id: int) -> dict:
    """Conteos y sumas que no deben cambiar con el bootstrap."""

    p = {"c": empresa_id}
    filas = {
        "cuentas": db.execute(text(
            "SELECT count(*), coalesce(string_agg(id::text || ':' || "
            "is_active::text || ':' || name, ',' ORDER BY id), '') "
            "FROM accounts WHERE company_id = :c"), p).one(),
        "conceptos": db.execute(text(
            "SELECT count(*), coalesce(string_agg(id::text || ':' || "
            "is_active::text || ':' || name, ',' ORDER BY id), '') "
            "FROM concepts WHERE company_id = :c"), p).one(),
        "cuenta_concepto": db.execute(text(
            "SELECT count(*), coalesce(string_agg(ac.id::text || ':' || "
            "ac.is_active::text, ',' ORDER BY ac.id), '') "
            "FROM account_concepts ac JOIN accounts a ON a.id = ac.account_id "
            "WHERE a.company_id = :c"), p).one(),
        "movimientos": db.execute(text(
            "SELECT count(*), coalesce(string_agg(t.id::text || ':' || "
            "t.amount::text || ':' || t.is_active::text || ':' || "
            "t.captured_by::text, ',' ORDER BY t.id), '') "
            "FROM transactions t JOIN accounts a ON a.id = t.account_id "
            "WHERE a.company_id = :c"), p).one(),
    }
    return {
        nombre: {
            "filas": int(conteo),
            "sha256": hashlib.sha256(detalle.encode()).hexdigest(),
        }
        for nombre, (conteo, detalle) in filas.items()
    }


def _otras_membresias(db: Session, empresa_id: int, excluir: set[int]) -> list:
    filas = db.execute(text(
        "SELECT cu.id, cu.is_admin, cu.is_active, "
        "coalesce(string_agg(cur.role_id::text, ',' ORDER BY cur.role_id) "
        "FILTER (WHERE cur.is_active), '') "
        "FROM company_users cu "
        "LEFT JOIN company_user_roles cur ON cur.company_user_id = cu.id "
        "WHERE cu.company_id = :c GROUP BY cu.id ORDER BY cu.id"
    ), {"c": empresa_id}).all()
    return [list(f) for f in filas if f[0] not in excluir]


# ---------------------------------------------------------------- plan

def construir_plan(db: Session, empresa: Company, restablecer: set[str]) -> Plan:
    roles = _roles_catalogo(db)
    plan = Plan(empresa_id=empresa.id, empresa_nombre=empresa.name)

    ids_objetivo: set[int] = set()

    for cuenta in CUENTAS:
        usuario = _usuario(db, cuenta.correo)

        if cuenta.historica:
            if usuario is None:
                raise Abortar(
                    f"no existe el usuario histórico {cuenta.correo}; "
                    "no se crea uno nuevo para no perder su historial"
                )
            membresia = _membresia(db, empresa.id, usuario.id)
            if membresia is None:
                raise Abortar(
                    f"{cuenta.correo} no tiene membresía en "
                    f'"{empresa.name}"; la histórica debe existir'
                )
            plan.historica_id = membresia.id
            if cuenta.clave in restablecer:
                raise Abortar(
                    "la contraseña de la cuenta histórica no se modifica"
                )

        if usuario is None:
            plan.acciones.append(
                f"crear usuario {cuenta.correo} ({cuenta.nombre})"
            )
            plan.contrasenas_requeridas.append(cuenta.clave)
            plan.acciones.append(
                f"crear membresía de {cuenta.correo} "
                f"(isAdmin={cuenta.es_admin})"
            )
            plan.acciones.append(f"asignar rol {cuenta.rol} a {cuenta.correo}")
            continue

        if not usuario.is_active:
            plan.acciones.append(f"reactivar usuario {cuenta.correo}")
        if usuario.name != cuenta.nombre:
            plan.avisos.append(
                f'{cuenta.correo}: el nombre guardado es "{usuario.name}"; '
                "no se modifica"
            )
        if cuenta.clave in restablecer:
            plan.contrasenas_requeridas.append(cuenta.clave)
            plan.acciones.append(
                f"restablecer contraseña de {cuenta.correo}"
            )

        membresia = _membresia(db, empresa.id, usuario.id)
        if membresia is None:
            plan.acciones.append(
                f"crear membresía de {cuenta.correo} "
                f"(isAdmin={cuenta.es_admin})"
            )
            plan.acciones.append(f"asignar rol {cuenta.rol} a {cuenta.correo}")
            continue

        ids_objetivo.add(membresia.id)

        if not membresia.is_active:
            plan.acciones.append(
                f"reactivar membresía #{membresia.id} de {cuenta.correo}"
            )
        if membresia.is_admin != cuenta.es_admin:
            plan.acciones.append(
                f"membresía #{membresia.id} de {cuenta.correo}: "
                f"isAdmin {membresia.is_admin} -> {cuenta.es_admin}"
            )

        activos = _roles_activos(db, membresia.id)
        codigos = sorted(roles_por_id(roles)[r.role_id] for r in activos)
        if codigos != [cuenta.rol]:
            plan.acciones.append(
                f"membresía #{membresia.id} de {cuenta.correo}: "
                f"roles activos {codigos or 'ninguno'} -> [{cuenta.rol}]"
            )

    # Otros administradores principales fuera de las cuatro cuentas: no se
    # tocan sin una decisión explícita del equipo.
    otros_admin = (
        db.query(CompanyUser)
        .filter(
            CompanyUser.company_id == empresa.id,
            CompanyUser.is_admin.is_(True),
            CompanyUser.is_active.is_(True),
            CompanyUser.id.notin_(ids_objetivo or {-1}),
        )
        .all()
    )
    if otros_admin:
        raise Abortar(
            "hay administradores principales activos fuera de la "
            f"distribución autorizada (membresías "
            f"{[m.id for m in otros_admin]}); resuélvanlo antes de aplicar"
        )

    return plan


def roles_por_id(roles: dict[str, Role]) -> dict[int, str]:
    return {r.id: code for code, r in roles.items()}


# ---------------------------------------------------------------- aplicar

def _pedir_contrasena(clave: str, correo: str) -> str:
    variable = f"BOOTSTRAP_PASSWORD_{clave}"
    valor = os.getenv(variable)

    if valor is None:
        if not sys.stdin.isatty():
            raise Abortar(
                f"falta la contraseña de {correo}: defina {variable} "
                "o ejecute con terminal interactiva (docker compose exec -it)"
            )
        valor = getpass.getpass(f"Contraseña para {correo}: ")
        repetida = getpass.getpass("Repite la contraseña: ")
        if valor != repetida:
            raise Abortar(f"las contraseñas de {correo} no coinciden")

    if len(valor) < LONGITUD_MINIMA_CONTRASENA:
        raise Abortar(
            f"la contraseña de {correo} debe tener al menos "
            f"{LONGITUD_MINIMA_CONTRASENA} caracteres"
        )
    return valor


def _fijar_rol(db: Session, membresia: CompanyUser, rol: Role) -> None:
    activos = _roles_activos(db, membresia.id)
    if len(activos) == 1 and activos[0].role_id == rol.id:
        return

    for relacion in activos:
        relacion.is_active = False
    # El índice parcial uq_company_user_role_active admite un solo rol
    # activo por membresía: se persiste la baja antes de activar el nuevo.
    db.flush()

    existente = (
        db.query(CompanyUserRole)
        .filter(
            CompanyUserRole.company_user_id == membresia.id,
            CompanyUserRole.role_id == rol.id,
        )
        .one_or_none()
    )
    if existente is not None:
        existente.is_active = True
    else:
        db.add(CompanyUserRole(
            company_user_id=membresia.id, role_id=rol.id, is_active=True,
        ))
    db.flush()


def aplicar(db: Session, empresa: Company, contrasenas: dict[str, str]) -> None:
    roles = _roles_catalogo(db)

    # Primero se retira el administrador principal a quien no le toca, para
    # que en ningún momento haya dos administradores activos.
    for cuenta in CUENTAS:
        if cuenta.es_admin:
            continue
        usuario = _usuario(db, cuenta.correo)
        if usuario is None:
            continue
        membresia = _membresia(db, empresa.id, usuario.id)
        if membresia is not None and membresia.is_admin:
            membresia.is_admin = False
    db.flush()

    for cuenta in CUENTAS:
        usuario = _usuario(db, cuenta.correo)

        if usuario is None:
            usuario = User(
                name=cuenta.nombre,
                email=cuenta.correo.lower(),
                password_hash=hash_password(contrasenas[cuenta.clave]),
                email_verified=False,
                is_active=True,
            )
            db.add(usuario)
            db.flush()
        else:
            if not usuario.is_active:
                usuario.is_active = True
            if cuenta.clave in contrasenas:
                usuario.password_hash = hash_password(contrasenas[cuenta.clave])

        membresia = _membresia(db, empresa.id, usuario.id)
        if membresia is None:
            membresia = CompanyUser(
                company_id=empresa.id,
                user_id=usuario.id,
                is_admin=cuenta.es_admin,
                is_active=True,
            )
            db.add(membresia)
        else:
            membresia.is_active = True
            membresia.is_admin = cuenta.es_admin
        db.flush()

        _fijar_rol(db, membresia, roles[cuenta.rol])


# ---------------------------------------------------------------- verificar

def verificar(db: Session, empresa: Company, historica_id: int | None) -> list[str]:
    """Devuelve la lista de incumplimientos (vacía si todo está bien)."""

    roles = roles_por_id(_roles_catalogo(db))
    fallos: list[str] = []
    ids: dict[str, int] = {}

    for cuenta in CUENTAS:
        usuario = _usuario(db, cuenta.correo)
        if usuario is None or not usuario.is_active:
            fallos.append(f"{cuenta.correo}: usuario inexistente o inactivo")
            continue
        membresia = _membresia(db, empresa.id, usuario.id)
        if membresia is None or not membresia.is_active:
            fallos.append(f"{cuenta.correo}: membresía inexistente o inactiva")
            continue
        ids[cuenta.clave] = membresia.id
        if membresia.is_admin != cuenta.es_admin:
            fallos.append(
                f"{cuenta.correo}: isAdmin={membresia.is_admin}, "
                f"se esperaba {cuenta.es_admin}"
            )
        activos = [roles[r.role_id] for r in _roles_activos(db, membresia.id)]
        if activos != [cuenta.rol]:
            fallos.append(
                f"{cuenta.correo}: roles activos {activos}, "
                f"se esperaba [{cuenta.rol}]"
            )

    if historica_id is not None and ids.get("DAVID_HISTORICA") != historica_id:
        fallos.append(
            f"la membresía histórica cambió de ID "
            f"({historica_id} -> {ids.get('DAVID_HISTORICA')})"
        )

    admins = [
        m.id for m in db.query(CompanyUser).filter(
            CompanyUser.company_id == empresa.id,
            CompanyUser.is_admin.is_(True),
            CompanyUser.is_active.is_(True),
        )
    ]
    if admins != [ids.get("DAVID")]:
        fallos.append(
            f"administradores principales activos {admins}; se esperaba "
            f"solo la nueva cuenta de David ({ids.get('DAVID')})"
        )

    return fallos


def _resumen(db: Session, empresa: Company) -> list[dict]:
    roles = roles_por_id(_roles_catalogo(db))
    filas = []
    for cuenta in CUENTAS:
        usuario = _usuario(db, cuenta.correo)
        membresia = (
            _membresia(db, empresa.id, usuario.id) if usuario else None
        )
        filas.append({
            "correo": cuenta.correo,
            "membresia_id": membresia.id if membresia else None,
            "activa": bool(membresia and membresia.is_active),
            "isAdmin": bool(membresia and membresia.is_admin),
            "roles_activos": (
                [roles[r.role_id] for r in _roles_activos(db, membresia.id)]
                if membresia else []
            ),
        })
    return filas


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap autorizado de las cuatro cuentas de FinTrack Demo",
    )
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--aplicar", action="store_true",
                      help="ejecuta el plan en una sola transacción")
    modo.add_argument("--verificar", action="store_true",
                      help="solo lectura: comprueba el estado final")
    parser.add_argument("--empresa", default=EMPRESA_POR_DEFECTO,
                        help='nombre exacto de la empresa (default "FinTrack Demo")')
    parser.add_argument(
        "--restablecer-contrasena", action="append", default=[],
        choices=[c.clave for c in CUENTAS if not c.historica],
        help="restablece la contraseña de una cuenta existente (repetible)",
    )
    args = parser.parse_args(argv)
    restablecer = set(args.restablecer_contrasena)

    db = SessionLocal()
    try:
        if not args.aplicar:
            # Debe ser la primera sentencia de la transacción: PostgreSQL
            # rechazará cualquier escritura en los modos de solo lectura.
            db.execute(text("SET TRANSACTION READ ONLY"))

        base = db.execute(text("SELECT current_database()")).scalar()
        _log(f"base de datos: {base}")

        empresa = _empresa(db, args.empresa, bloquear=args.aplicar)
        _log(f'empresa "{empresa.name}" id={empresa.id}')

        if args.verificar:
            fallos = verificar(db, empresa, None)
            print(json.dumps({
                "modo": "verificar",
                "empresa_id": empresa.id,
                "cuentas": _resumen(db, empresa),
                "huella_financiera": huella_financiera(db, empresa.id),
                "fallos": fallos,
            }, ensure_ascii=False, indent=2))
            _log("VERIFICACIÓN CORRECTA" if not fallos else "VERIFICACIÓN CON FALLOS")
            return 0 if not fallos else 1

        plan = construir_plan(db, empresa, restablecer)
        huella_antes = huella_financiera(db, empresa.id)

        salida = {
            "modo": "aplicar" if args.aplicar else "plan (solo lectura)",
            "empresa_id": empresa.id,
            "membresia_historica_id": plan.historica_id,
            "acciones": plan.acciones,
            "avisos": plan.avisos,
            "contrasenas_requeridas": plan.contrasenas_requeridas,
            "huella_financiera": huella_antes,
        }

        if not args.aplicar:
            print(json.dumps(salida, ensure_ascii=False, indent=2))
            _log("sin cambios: modo de solo lectura. Use --aplicar para ejecutar.")
            db.rollback()
            return 0

        if not plan.acciones:
            print(json.dumps(salida, ensure_ascii=False, indent=2))
            _log("la distribución ya está aplicada; nada que hacer")
            db.rollback()
            return 0

        cuentas = {c.clave: c for c in CUENTAS}
        contrasenas = {
            clave: _pedir_contrasena(clave, cuentas[clave].correo)
            for clave in plan.contrasenas_requeridas
        }

        objetivo_ids = {
            m.id for m in (
                _membresia(db, empresa.id, u.id)
                for u in (_usuario(db, c.correo) for c in CUENTAS) if u
            ) if m
        }
        otras_antes = _otras_membresias(db, empresa.id, objetivo_ids)

        aplicar(db, empresa, contrasenas)
        db.flush()

        fallos = verificar(db, empresa, plan.historica_id)
        if huella_financiera(db, empresa.id) != huella_antes:
            fallos.append("la huella financiera cambió")
        objetivo_ids_despues = {
            m.id for m in (
                _membresia(db, empresa.id, u.id)
                for u in (_usuario(db, c.correo) for c in CUENTAS) if u
            ) if m
        }
        if _otras_membresias(db, empresa.id, objetivo_ids_despues) != otras_antes:
            fallos.append("cambiaron membresías fuera de la distribución")

        if fallos:
            db.rollback()
            salida["fallos"] = fallos
            print(json.dumps(salida, ensure_ascii=False, indent=2))
            _log("ROLLBACK: no se modificó ningún registro")
            return 1

        db.commit()
        salida["resultado"] = _resumen(db, empresa)
        print(json.dumps(salida, ensure_ascii=False, indent=2))
        _log("COMMIT: distribución aplicada y verificada")
        return 0

    except Abortar as error:
        db.rollback()
        _log(f"ABORTADO sin cambios: {error}")
        return 2
    except Exception as error:
        db.rollback()
        _log(f"ROLLBACK por error inesperado: {type(error).__name__}: {error}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
