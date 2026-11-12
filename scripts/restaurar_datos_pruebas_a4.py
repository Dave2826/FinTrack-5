"""Restauración selectiva de los fixtures de la Actividad 4.

Elimina únicamente los registros creados por la última ejecución de
``scripts/pruebas_actividad4.py`` en la empresa 11:

- ``Cuenta A4 Maria <marca>`` y ``Cuenta A4 Jose <marca>`` creadas el
  2026-11-11, fuera de las cuentas del baseline (34, 39, 40, 42 y 43).
- El movimiento ``INCOME`` de ``15.5`` con descripción ``A4 Pedro`` sobre
  la cuenta 34, capturado el 2026-11-11.

No toca usuarios, membresías, roles, permisos, conceptos, la empresa 12
ni la empresa 53 (B01).

Guardas: ``DB_NAME=fintrack5_test``, ``DB_HOST=postgres`` y la revisión
de Alembic ``3b9f41c7d2ae``. Dry-run por defecto; ``--apply`` ejecuta la
escritura en una transacción atómica.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

from sqlalchemy import bindparam, text

from database.connection import SessionLocal


DB_ESPERADA = "fintrack5_test"
HOST_ESPERADO = "postgres"
ALEMBIC_ESPERADO = "3b9f41c7d2ae"
EMPRESA_ALPHA = 11
EMPRESA_B01 = 53
IDS_BASELINE = (34, 39, 40, 42, 43)
FECHA_CORTE = "2026-11-11"
MONTO_FIXTURE = Decimal("15.5")
DESCRIPCION_FIXTURE = "A4 Pedro"

CUENTAS_ESPERADAS = 2
MOVIMIENTOS_ESPERADOS = 1
CUENTAS_EMPRESA_11 = 5
MOVIMIENTOS_EMPRESA_11 = 4
CUENTAS_TOTALES = 9
MOVIMIENTOS_TOTALES = 10
CUENTAS_B01 = 3
MOVIMIENTOS_B01 = 5


def _log(mensaje: str) -> None:
    print(f"[restauracion] {mensaje}", flush=True)


def _abortar(mensaje: str) -> None:
    _log(f"ABORTADO: {mensaje}")
    sys.exit(1)


def _verificar_guardas(db) -> None:
    if os.getenv("DB_NAME") != DB_ESPERADA:
        _abortar(f"DB_NAME no es {DB_ESPERADA}")
    if os.getenv("DB_HOST") != HOST_ESPERADO:
        _abortar(f"DB_HOST no es {HOST_ESPERADO}")

    actual = db.execute(text("SELECT current_database()")).scalar()
    if actual != DB_ESPERADA:
        _abortar(f"current_database() no es {DB_ESPERADA}")

    revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    if revision != ALEMBIC_ESPERADO:
        _abortar(f"alembic_version no es {ALEMBIC_ESPERADO}")

    empresa = db.execute(
        text("SELECT name FROM companies WHERE id = :c"), {"c": EMPRESA_ALPHA}
    ).scalar()
    if empresa != "Pruebas Alpha SA":
        _abortar(f"empresa {EMPRESA_ALPHA} no es Pruebas Alpha SA: {empresa}")

    b01 = db.execute(
        text("SELECT name FROM companies WHERE id = :c"), {"c": EMPRESA_B01}
    ).scalar()
    if b01 is None:
        _abortar("no existe la empresa B01")

    _log("guardas verificadas: fintrack5_test, postgres, Alembic y empresas")


def _cuentas_candidatas(db):
    consulta = text(
        """
        SELECT id, name, created_at
        FROM accounts
        WHERE company_id = :empresa
          AND (name LIKE 'Cuenta A4 Maria %' OR name LIKE 'Cuenta A4 Jose %')
          AND id NOT IN (34, 39, 40, 42, 43)
          AND created_at >= :corte
        ORDER BY id
        """
    )
    return db.execute(
        consulta, {"empresa": EMPRESA_ALPHA, "corte": FECHA_CORTE}
    ).fetchall()


def _movimientos_candidatos(db):
    consulta = text(
        """
        SELECT id, account_id, amount, short_description, captured_at
        FROM transactions
        WHERE account_id = 34
          AND amount = :monto
          AND transaction_type = 'INCOME'
          AND short_description = :descripcion
          AND captured_at >= :corte
        ORDER BY id
        """
    )
    return db.execute(
        consulta,
        {
            "monto": MONTO_FIXTURE,
            "descripcion": DESCRIPCION_FIXTURE,
            "corte": FECHA_CORTE,
        },
    ).fetchall()


def _fks_hacia(db, tabla: str):
    consulta = text(
        f"""
        SELECT format('%I.%I', n.nspname, c.relname) AS tabla,
               quote_ident(a.attname) AS columna
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = con.conrelid
                           AND a.attnum = ANY(con.conkey)
        WHERE con.contype = 'f'
          AND con.confrelid = '{tabla}'::regclass
        ORDER BY 1, 2
        """
    )
    return db.execute(consulta).fetchall()


def _dependencias(db, tabla: str, ids: list[int]) -> list[str]:
    hallazgos: list[str] = []
    if not ids:
        return hallazgos
    for fk in _fks_hacia(db, tabla):
        consulta = text(
            f"SELECT count(*) FROM {fk.tabla} WHERE {fk.columna} IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        total = db.execute(consulta, {"ids": ids}).scalar()
        if total:
            hallazgos.append(f"{fk.tabla}.{fk.columna}: {total}")
    return hallazgos


def _conteos(db) -> dict[str, int]:
    return {
        "cuentas_11": db.execute(
            text("SELECT count(*) FROM accounts WHERE company_id = :c"),
            {"c": EMPRESA_ALPHA},
        ).scalar(),
        "movimientos_11": db.execute(
            text(
                "SELECT count(*) FROM transactions t "
                "JOIN accounts a ON a.id = t.account_id "
                "WHERE a.company_id = :c"
            ),
            {"c": EMPRESA_ALPHA},
        ).scalar(),
        "cuentas_total": db.execute(text("SELECT count(*) FROM accounts")).scalar(),
        "movimientos_total": db.execute(
            text("SELECT count(*) FROM transactions")
        ).scalar(),
        "cuentas_b01": db.execute(
            text("SELECT count(*) FROM accounts WHERE company_id = :c"),
            {"c": EMPRESA_B01},
        ).scalar(),
        "movimientos_b01": db.execute(
            text(
                "SELECT count(*) FROM transactions t "
                "JOIN accounts a ON a.id = t.account_id "
                "WHERE a.company_id = :c"
            ),
            {"c": EMPRESA_B01},
        ).scalar(),
    }


def _conteos_ok(conteos: dict[str, int]) -> bool:
    return (
        conteos["cuentas_11"] == CUENTAS_EMPRESA_11
        and conteos["movimientos_11"] == MOVIMIENTOS_EMPRESA_11
        and conteos["cuentas_total"] == CUENTAS_TOTALES
        and conteos["movimientos_total"] == MOVIMIENTOS_TOTALES
        and conteos["cuentas_b01"] == CUENTAS_B01
        and conteos["movimientos_b01"] == MOVIMIENTOS_B01
    )


def _imprimir_conteos(conteos: dict[str, int]) -> None:
    for clave, valor in conteos.items():
        _log(f"{clave}: {valor}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restauración selectiva de fixtures A4 en fintrack5_test"
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--dry-run", action="store_true", help="solo consulta (por defecto)"
    )
    grupo.add_argument(
        "--apply", action="store_true", help="ejecuta la eliminación selectiva"
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        _verificar_guardas(db)

        cuentas = _cuentas_candidatas(db)
        movimientos = _movimientos_candidatos(db)

        _log("=== candidatos ===")
        for fila in cuentas:
            _log(f"cuenta id={fila.id} name={fila.name!r} created_at={fila.created_at}")
        for fila in movimientos:
            _log(
                f"movimiento id={fila.id} account_id={fila.account_id} "
                f"amount={fila.amount} desc={fila.short_description!r} "
                f"captured_at={fila.captured_at}"
            )

        if not cuentas and not movimientos:
            _log("no hay fixtures pendientes; nada que restaurar")
            return 0

        if len(cuentas) != CUENTAS_ESPERADAS:
            _abortar(
                f"se esperaban {CUENTAS_ESPERADAS} cuentas y hay {len(cuentas)}"
            )
        if len(movimientos) != MOVIMIENTOS_ESPERADOS:
            _abortar(
                f"se esperaba {MOVIMIENTOS_ESPERADOS} movimiento y hay "
                f"{len(movimientos)}"
            )

        ids_cuentas = [fila.id for fila in cuentas]
        ids_movimientos = [fila.id for fila in movimientos]

        if any(ident in IDS_BASELINE for ident in ids_cuentas):
            _abortar("un candidato coincide con una cuenta del baseline")

        for fila in movimientos:
            if fila.account_id != 34:
                _abortar("el movimiento candidato no pertenece a la cuenta 34")
            if fila.amount != MONTO_FIXTURE:
                _abortar("el monto del movimiento candidato no coincide")
            if fila.short_description != DESCRIPCION_FIXTURE:
                _abortar("la descripción del movimiento candidato no coincide")

        dependencias_cuentas = _dependencias(db, "accounts", ids_cuentas)
        dependencias_movimientos = _dependencias(db, "transactions", ids_movimientos)
        if dependencias_cuentas or dependencias_movimientos:
            _abortar(
                "hay dependencias: "
                + "; ".join(dependencias_cuentas + dependencias_movimientos)
            )

        _log("=== conteos antes ===")
        _imprimir_conteos(_conteos(db))

        if args.dry_run or not args.apply:
            _log("dry-run correcto; ejecutar con --apply para restaurar")
            return 0

        db.rollback()
        try:
            with db.begin():
                bloqueo_cuentas = db.execute(
                    text(
                        "SELECT id FROM accounts WHERE id IN :ids FOR UPDATE"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": ids_cuentas},
                ).fetchall()
                bloqueo_movimientos = db.execute(
                    text(
                        "SELECT id FROM transactions WHERE id IN :ids FOR UPDATE"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": ids_movimientos},
                ).fetchall()

                if {fila.id for fila in bloqueo_cuentas} != set(ids_cuentas):
                    raise RuntimeError("las cuentas candidatas cambiaron")
                if {fila.id for fila in bloqueo_movimientos} != set(ids_movimientos):
                    raise RuntimeError("los movimientos candidatos cambiaron")

                deps_cuentas = _dependencias(db, "accounts", ids_cuentas)
                deps_movimientos = _dependencias(db, "transactions", ids_movimientos)
                if deps_cuentas or deps_movimientos:
                    raise RuntimeError(
                        "aparecieron dependencias: "
                        + "; ".join(deps_cuentas + deps_movimientos)
                    )

                db.execute(
                    text(
                        "DELETE FROM transactions WHERE id IN :ids"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": ids_movimientos},
                )
                db.execute(
                    text(
                        "DELETE FROM accounts WHERE id IN :ids"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": ids_cuentas},
                )

                conteos = _conteos(db)
                _log("=== conteos dentro de la transacción ===")
                _imprimir_conteos(conteos)
                if not _conteos_ok(conteos):
                    raise RuntimeError("los conteos no coinciden con el baseline")
        except Exception as exc:
            db.rollback()
            _abortar(f"rollback: {type(exc).__name__}: {exc}")

        _log("=== conteos después del COMMIT ===")
        _imprimir_conteos(_conteos(db))
        _log("restauración completada")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
