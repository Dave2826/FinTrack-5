"""Reglas de negocio de balances por cuenta y balance general (Actividad 7).

Los importes se mantienen siempre como ``Decimal`` y se cuantizan a dos
decimales al construir la respuesta. El periodo se interpreta como dias
completos UTC: incluye las 00:00:00 del dia ``fromDate`` y excluye las
00:00:00 del dia siguiente a ``toDate``.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from repositories.account_repository import get_account
from repositories.balance_repository import list_account_balance_rows
from services.authorization_service import exigir_permiso


CENTAVO = Decimal("0.01")
CERO = Decimal("0.00")
MONEDA = "MXN"


@dataclass(frozen=True)
class AccountBalanceResult:
    account_id: int
    account_name: str
    is_active: bool
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal
    closing_balance: Decimal
    is_in_red: bool
    currency: str


@dataclass(frozen=True)
class GeneralBalanceResult:
    company_id: int
    from_date: date
    to_date: date
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal
    closing_balance: Decimal
    accounts_in_red: int
    is_in_red: bool
    currency: str
    accounts: list[AccountBalanceResult]


def _cuantizar(valor) -> Decimal:
    """Convierte un valor agregado a Decimal con dos decimales."""

    if valor is None:
        return CERO

    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))

    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _limites_utc(
    from_date: date,
    to_date: date,
) -> tuple[datetime, datetime]:
    """Convierte el periodo de dias UTC a un intervalo [inicio, fin)."""

    if isinstance(from_date, datetime):
        from_date = from_date.date()
    if isinstance(to_date, datetime):
        to_date = to_date.date()

    if not isinstance(from_date, date) or not isinstance(to_date, date):
        raise ValueError("Las fechas del periodo no son válidas")

    if from_date > to_date:
        raise ValueError("fromDate no puede ser posterior a toDate")

    inicio = datetime.combine(from_date, time.min)
    fin_exclusivo = datetime.combine(to_date + timedelta(days=1), time.min)

    return inicio, fin_exclusivo


def _a_balance(fila) -> AccountBalanceResult:
    opening_income = _cuantizar(fila.opening_income)
    opening_expense = _cuantizar(fila.opening_expense)
    total_income = _cuantizar(fila.period_income)
    total_expense = _cuantizar(fila.period_expense)

    opening_balance = _cuantizar(opening_income - opening_expense)
    profit = _cuantizar(total_income - total_expense)
    closing_balance = _cuantizar(opening_balance + profit)

    return AccountBalanceResult(
        account_id=fila.account_id,
        account_name=fila.account_name,
        is_active=fila.is_active,
        opening_balance=opening_balance,
        total_income=total_income,
        total_expense=total_expense,
        profit=profit,
        closing_balance=closing_balance,
        is_in_red=closing_balance < CERO,
        currency=MONEDA,
    )


def account_balance_service(
    db: Session,
    actor_company_user_id: int,
    account_id: int,
    from_date: date,
    to_date: date,
) -> AccountBalanceResult:

    actor = exigir_permiso(
        db,
        actor_company_user_id,
        "accounts.read",
    )

    account = get_account(db, account_id)

    if account is None or account.company_id != actor.company_id:
        # Misma respuesta para una cuenta inexistente y para una cuenta de
        # otra empresa: no se revela la existencia de recursos ajenos.
        raise ValueError("La cuenta no existe")

    exigir_permiso(
        db,
        actor_company_user_id,
        "transactions.read",
        company_id=account.company_id,
    )

    inicio, fin_exclusivo = _limites_utc(from_date, to_date)

    filas = list_account_balance_rows(
        db,
        company_id=account.company_id,
        from_datetime=inicio,
        to_datetime=fin_exclusivo,
        account_id=account.id,
    )

    if not filas:
        # Defensivo: la cuenta existe pero la agregacion no devolvio fila.
        return AccountBalanceResult(
            account_id=account.id,
            account_name=account.name,
            is_active=account.is_active,
            opening_balance=CERO,
            total_income=CERO,
            total_expense=CERO,
            profit=CERO,
            closing_balance=CERO,
            is_in_red=False,
            currency=MONEDA,
        )

    return _a_balance(filas[0])


def general_balance_service(
    db: Session,
    actor_company_user_id: int,
    company_id: int,
    from_date: date,
    to_date: date,
) -> GeneralBalanceResult:

    exigir_permiso(
        db,
        actor_company_user_id,
        "accounts.read",
        company_id=company_id,
    )

    exigir_permiso(
        db,
        actor_company_user_id,
        "transactions.read",
        company_id=company_id,
    )

    inicio, fin_exclusivo = _limites_utc(from_date, to_date)

    filas = list_account_balance_rows(
        db,
        company_id=company_id,
        from_datetime=inicio,
        to_datetime=fin_exclusivo,
    )

    balances = [_a_balance(fila) for fila in filas]

    opening_balance = _cuantizar(
        sum((balance.opening_balance for balance in balances), CERO)
    )
    total_income = _cuantizar(
        sum((balance.total_income for balance in balances), CERO)
    )
    total_expense = _cuantizar(
        sum((balance.total_expense for balance in balances), CERO)
    )
    profit = _cuantizar(total_income - total_expense)
    closing_balance = _cuantizar(opening_balance + profit)
    accounts_in_red = sum(
        1 for balance in balances if balance.closing_balance < CERO
    )

    return GeneralBalanceResult(
        company_id=company_id,
        from_date=from_date,
        to_date=to_date,
        opening_balance=opening_balance,
        total_income=total_income,
        total_expense=total_expense,
        profit=profit,
        closing_balance=closing_balance,
        accounts_in_red=accounts_in_red,
        is_in_red=closing_balance < CERO,
        currency=MONEDA,
        accounts=balances,
    )
