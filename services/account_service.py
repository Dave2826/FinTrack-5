from sqlalchemy.orm import Session

from models.account import Account, AccountType
from repositories.account_repository import (
    create_account,
    get_account,
    list_accounts,
)
from repositories.company_repository import get_company


def create_account_service(
    db: Session,
    company_id: int,
    account_type: AccountType,
    name: str,
    bank_name: str | None = None,
    account_number: str | None = None,
    clabe: str | None = None,
    card_last_digits: str | None = None,
    short_description: str | None = None,
    long_description: str | None = None,
) -> Account:

    company = get_company(db, company_id)

    if company is None:
        raise ValueError("La empresa no existe")

    if not company.is_active:
        raise ValueError("La empresa no está activa")

    existing_accounts = list_accounts(
        db,
        company_id=company_id,
        active_only=False
    )

    duplicate = next(
        (
            account
            for account in existing_accounts
            if account.name.strip().lower() == name.strip().lower()
            and account.is_active
        ),
        None
    )

    if duplicate is not None:
        raise ValueError(
            "Ya existe una cuenta activa con ese nombre"
        )

    account = Account(
        company_id=company_id,
        account_type=account_type,
        name=name.strip(),
        bank_name=bank_name,
        account_number=account_number,
        clabe=clabe,
        card_last_digits=card_last_digits,
        short_description=short_description,
        long_description=long_description,
    )

    return create_account(db, account)


def get_account_service(
    db: Session,
    account_id: int
) -> Account:

    account = get_account(db, account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    return account


def list_accounts_service(
    db: Session,
    company_id: int,
    account_type: AccountType | None = None,
    active_only: bool = True
) -> list[Account]:

    return list_accounts(
        db,
        company_id=company_id,
        account_type=account_type,
        active_only=active_only
    )