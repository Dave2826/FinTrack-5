"""Consultas agregadas de balances (Actividad 7).

La lectura parte de ``accounts`` para conservar las cuentas sin
movimientos y las cuentas inactivas. Los filtros de ``transactions`` se
aplican en el ``ON`` del ``LEFT JOIN``; si se aplicaran en el ``WHERE``
las cuentas vacias desaparecerian.

No se unen ``concepts`` ni ``account_concepts``: esas relaciones no
intervienen en el calculo y podrian multiplicar filas e importes.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from models.account import Account
from models.transaction import Transaction, TransactionType


CERO = Decimal("0.00")


def list_account_balance_rows(
    db: Session,
    company_id: int,
    from_datetime: datetime,
    to_datetime: datetime,
    account_id: int | None = None,
) -> list:
    """Devuelve una fila agregada por cuenta de la empresa indicada.

    ``from_datetime`` es inclusivo y ``to_datetime`` exclusivo. Los
    movimientos anteriores a ``from_datetime`` alimentan el saldo
    inicial; los comprendidos en ``[from_datetime, to_datetime)``
    alimentan los totales del periodo.
    """

    antes_del_periodo = Transaction.transaction_date < from_datetime
    dentro_del_periodo = and_(
        Transaction.transaction_date >= from_datetime,
        Transaction.transaction_date < to_datetime,
    )

    def _suma(tipo: TransactionType, condicion):
        return func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Transaction.transaction_type == tipo,
                            condicion,
                        ),
                        Transaction.amount,
                    ),
                    else_=CERO,
                )
            ),
            CERO,
        )

    consulta = (
        db.query(
            Account.id.label("account_id"),
            Account.name.label("account_name"),
            Account.is_active.label("is_active"),
            _suma(TransactionType.INCOME, antes_del_periodo).label(
                "opening_income"
            ),
            _suma(TransactionType.EXPENSE, antes_del_periodo).label(
                "opening_expense"
            ),
            _suma(TransactionType.INCOME, dentro_del_periodo).label(
                "period_income"
            ),
            _suma(TransactionType.EXPENSE, dentro_del_periodo).label(
                "period_expense"
            ),
        )
        .outerjoin(
            Transaction,
            and_(
                Transaction.account_id == Account.id,
                Transaction.is_active.is_(True),
                Transaction.transaction_date < to_datetime,
            ),
        )
        .filter(Account.company_id == company_id)
        .group_by(Account.id, Account.name, Account.is_active)
        .order_by(Account.id)
    )

    if account_id is not None:
        consulta = consulta.filter(Account.id == account_id)

    return consulta.all()
