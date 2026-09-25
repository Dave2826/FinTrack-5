from datetime import datetime
from decimal import Decimal
from enum import Enum

import strawberry
from sqlalchemy.orm import Session

from models.account import Account as AccountModel
from models.account import AccountType as AccountTypeModel
from models.account_concept import AccountConcept as AccountConceptModel
from models.concept import Concept as ConceptModel
from models.concept import ConceptType as ConceptTypeModel
from models.transaction import Transaction as TransactionModel
from models.transaction import TransactionType as TransactionTypeModel

from services.account_service import (
    create_account_service,
    list_accounts_service,
)
from services.account_concept_service import (
    assign_concept_to_account,
    get_account_concepts_service,
    remove_concept_from_account,
)
from services.concept_service import (
    create_concept_service,
    list_concepts_service,
)
from services.transaction_service import (
    create_transaction_service,
    delete_transaction_service,
    list_transactions_service,
)


@strawberry.enum(name="AccountType")
class AccountTypeGraphQL(Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    WALLET = "WALLET"
    OTHER = "OTHER"


@strawberry.enum(name="ConceptType")
class ConceptTypeGraphQL(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.enum(name="TransactionType")
class TransactionTypeGraphQL(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.type
class Account:
    id: int
    company_id: int
    account_type: str
    name: str
    bank_name: str | None
    account_number: str | None
    clabe: str | None
    card_last_digits: str | None
    short_description: str | None
    long_description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Concept:
    id: int
    company_id: int
    concept_type: str
    name: str
    short_description: str | None
    long_description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class AccountConcept:
    id: int
    account_id: int
    concept_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Transaction:
    id: int
    account_id: int
    concept_id: int
    transaction_type: str
    amount: Decimal
    transaction_date: datetime
    captured_at: datetime
    captured_by: int
    short_description: str | None
    long_description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.input
class CreateAccountInput:
    company_id: int
    account_type: AccountTypeGraphQL
    name: str
    bank_name: str | None = None
    account_number: str | None = None
    clabe: str | None = None
    card_last_digits: str | None = None
    short_description: str | None = None
    long_description: str | None = None


@strawberry.input
class CreateConceptInput:
    company_id: int
    concept_type: ConceptTypeGraphQL
    name: str
    short_description: str | None = None
    long_description: str | None = None


@strawberry.input
class AssignConceptToAccountInput:
    account_id: int
    concept_id: int


@strawberry.input
class CreateTransactionInput:
    account_id: int
    concept_id: int
    transaction_type: TransactionTypeGraphQL
    amount: Decimal
    transaction_date: datetime | None = None
    short_description: str | None = None
    long_description: str | None = None
    captured_by: int


def account_to_graphql(account: AccountModel) -> Account:
    return Account(
        id=account.id,
        company_id=account.company_id,
        account_type=account.account_type.value,
        name=account.name,
        bank_name=account.bank_name,
        account_number=account.account_number,
        clabe=account.clabe,
        card_last_digits=account.card_last_digits,
        short_description=account.short_description,
        long_description=account.long_description,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def concept_to_graphql(concept: ConceptModel) -> Concept:
    return Concept(
        id=concept.id,
        company_id=concept.company_id,
        concept_type=concept.concept_type.value,
        name=concept.name,
        short_description=concept.short_description,
        long_description=concept.long_description,
        is_active=concept.is_active,
        created_at=concept.created_at,
        updated_at=concept.updated_at,
    )


def account_concept_to_graphql(
    relation: AccountConceptModel
) -> AccountConcept:
    return AccountConcept(
        id=relation.id,
        account_id=relation.account_id,
        concept_id=relation.concept_id,
        is_active=relation.is_active,
        created_at=relation.created_at,
        updated_at=relation.updated_at,
    )


def transaction_to_graphql(
    transaction: TransactionModel
) -> Transaction:
    return Transaction(
        id=transaction.id,
        account_id=transaction.account_id,
        concept_id=transaction.concept_id,
        transaction_type=transaction.transaction_type.value,
        amount=transaction.amount,
        transaction_date=transaction.transaction_date,
        captured_at=transaction.captured_at,
        captured_by=transaction.captured_by,
        short_description=transaction.short_description,
        long_description=transaction.long_description,
        is_active=transaction.is_active,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )


@strawberry.type
class Query:

    @strawberry.field
    def accounts(
        self,
        info: strawberry.Info,
        company_id: int,
        account_type: AccountTypeGraphQL | None = None,
        active_only: bool = True,
    ) -> list[Account]:

        db: Session = info.context["db"]

        model_account_type = None

        if account_type is not None:
            model_account_type = AccountTypeModel(
                account_type.value
            )

        accounts = list_accounts_service(
            db,
            company_id=company_id,
            account_type=model_account_type,
            active_only=active_only,
        )

        return [
            account_to_graphql(account)
            for account in accounts
        ]

    @strawberry.field
    def concepts(
        self,
        info: strawberry.Info,
        company_id: int,
        concept_type: ConceptTypeGraphQL | None = None,
        active_only: bool = True,
    ) -> list[Concept]:

        db: Session = info.context["db"]

        model_concept_type = None

        if concept_type is not None:
            model_concept_type = ConceptTypeModel(
                concept_type.value
            )

        concepts = list_concepts_service(
            db,
            company_id=company_id,
            concept_type=model_concept_type,
            active_only=active_only,
        )

        return [
            concept_to_graphql(concept)
            for concept in concepts
        ]

    @strawberry.field
    def account_concepts(
        self,
        info: strawberry.Info,
        account_id: int,
    ) -> list[AccountConcept]:

        db: Session = info.context["db"]

        relations = get_account_concepts_service(
            db,
            account_id=account_id,
        )

        return [
            account_concept_to_graphql(relation)
            for relation in relations
        ]

    @strawberry.field
    def transactions(
        self,
        info: strawberry.Info,
        account_id: int,
        transaction_type: TransactionTypeGraphQL | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:

        db: Session = info.context["db"]

        model_transaction_type = None

        if transaction_type is not None:
            model_transaction_type = TransactionTypeModel(
                transaction_type.value
            )

        transactions = list_transactions_service(
            db,
            account_id=account_id,
            transaction_type=model_transaction_type,
            limit=limit,
            offset=offset,
        )

        return [
            transaction_to_graphql(transaction)
            for transaction in transactions
        ]


@strawberry.type
class Mutation:

    @strawberry.mutation
    def create_account(
        self,
        info: strawberry.Info,
        input: CreateAccountInput,
    ) -> Account:

        db: Session = info.context["db"]

        account = create_account_service(
            db,
            company_id=input.company_id,
            account_type=AccountTypeModel(
                input.account_type.value
            ),
            name=input.name,
            bank_name=input.bank_name,
            account_number=input.account_number,
            clabe=input.clabe,
            card_last_digits=input.card_last_digits,
            short_description=input.short_description,
            long_description=input.long_description,
        )

        return account_to_graphql(account)

    @strawberry.mutation
    def create_concept(
        self,
        info: strawberry.Info,
        input: CreateConceptInput,
    ) -> Concept:

        db: Session = info.context["db"]

        concept = create_concept_service(
            db,
            company_id=input.company_id,
            concept_type=ConceptTypeModel(
                input.concept_type.value
            ),
            name=input.name,
            short_description=input.short_description,
            long_description=input.long_description,
        )

        return concept_to_graphql(concept)

    @strawberry.mutation
    def assign_concept_to_account(
        self,
        info: strawberry.Info,
        input: AssignConceptToAccountInput,
    ) -> AccountConcept:

        db: Session = info.context["db"]

        relation = assign_concept_to_account(
            db,
            account_id=input.account_id,
            concept_id=input.concept_id,
        )

        return account_concept_to_graphql(relation)

    @strawberry.mutation
    def remove_concept_from_account(
        self,
        info: strawberry.Info,
        account_id: int,
        concept_id: int,
    ) -> AccountConcept:

        db: Session = info.context["db"]

        relation = remove_concept_from_account(
            db,
            account_id=account_id,
            concept_id=concept_id,
        )

        return account_concept_to_graphql(relation)

    @strawberry.mutation
    def create_transaction(
        self,
        info: strawberry.Info,
        input: CreateTransactionInput,
    ) -> Transaction:

        db: Session = info.context["db"]

        transaction = create_transaction_service(
            db,
            account_id=input.account_id,
            concept_id=input.concept_id,
            transaction_type=TransactionTypeModel(
                input.transaction_type.value
            ),
            amount=input.amount,
            captured_by=input.captured_by,
            transaction_date=input.transaction_date,
            short_description=input.short_description,
            long_description=input.long_description,
        )

        return transaction_to_graphql(transaction)

    @strawberry.mutation
    def delete_transaction(
        self,
        info: strawberry.Info,
        id: int,
    ) -> Transaction:

        db: Session = info.context["db"]

        transaction = delete_transaction_service(
            db,
            transaction_id=id,
        )

        return transaction_to_graphql(transaction)


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)