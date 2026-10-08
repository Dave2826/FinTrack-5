import strawberry

from enum import Enum
from decimal import Decimal
from datetime import datetime

from strawberry.types import Info

from services.account_service import (
    create_account_service,
    get_account_service,
    list_accounts_service,
)

from services.concept_service import (
    create_concept_service,
    get_concept_service,
    list_concepts_service,
)

from services.account_concept_service import (
    assign_concept_to_account,
    get_account_concepts_service,
    remove_concept_from_account,
)

from services.transaction_service import (
    create_transaction_service,
    get_transaction_service,
    list_transactions_service,
    delete_transaction_service,
)

from services.auth_service import authenticate_user

from services.role_service import (
    create_role_service,
    deactivate_role_service,
    list_roles_service,
)

from services.permission_service import (
    create_permission_service,
    list_permissions_service,
)

from services.role_permission_service import (
    assign_permission_to_role_service,
    remove_permission_from_role_service,
    list_role_permissions_service,
)

from repositories.company_user_repository import (
    get_active_company_user,
)

from models.account import Account as AccountModel
from models.account import AccountType as AccountTypeModel

from models.concept import Concept as ConceptModel
from models.concept import ConceptType as ConceptTypeModel

from models.account_concept import AccountConcept as AccountConceptModel

from models.transaction import Transaction as TransactionModel
from models.transaction import TransactionType as TransactionTypeModel

from models.role import Role as RoleModel

from models.permission import Permission as PermissionModel

from models.role_permission import RolePermission as RolePermissionModel

from models.company_user_role import CompanyUserRole as CompanyUserRoleModel

from models.company_user import CompanyUser as CompanyUserModel


@strawberry.enum
class AccountType(Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    WALLET = "WALLET"
    OTHER = "OTHER"


@strawberry.enum
class ConceptType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.enum
class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.type
class Account:
    id: int
    company_id: int
    account_type: AccountType
    name: str
    bank_name: str | None
    account_number: str | None
    clabe: str | None
    card_last_digits: str | None
    short_description: str | None
    long_description: str | None
    is_active: bool

    @staticmethod
    def from_model(account: AccountModel):
        return Account(
            id=account.id,
            company_id=account.company_id,
            account_type=AccountType(account.account_type.value),
            name=account.name,
            bank_name=account.bank_name,
            account_number=account.account_number,
            clabe=account.clabe,
            card_last_digits=account.card_last_digits,
            short_description=account.short_description,
            long_description=account.long_description,
            is_active=account.is_active,
        )


@strawberry.type
class Concept:
    id: int
    company_id: int
    concept_type: ConceptType
    name: str
    short_description: str | None
    long_description: str | None
    is_active: bool

    @staticmethod
    def from_model(concept: ConceptModel):
        return Concept(
            id=concept.id,
            company_id=concept.company_id,
            concept_type=ConceptType(concept.concept_type.value),
            name=concept.name,
            short_description=concept.short_description,
            long_description=concept.long_description,
            is_active=concept.is_active,
        )


@strawberry.type
class AccountConcept:
    id: int
    account_id: int
    concept_id: int
    is_active: bool

    @staticmethod
    def from_model(relation: AccountConceptModel):
        return AccountConcept(
            id=relation.id,
            account_id=relation.account_id,
            concept_id=relation.concept_id,
            is_active=relation.is_active,
        )


@strawberry.type
class Transaction:
    id: int
    account_id: int
    concept_id: int
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: datetime
    captured_at: datetime
    captured_by: int
    short_description: str | None
    long_description: str | None
    is_active: bool

    @staticmethod
    def from_model(transaction: TransactionModel):
        return Transaction(
            id=transaction.id,
            account_id=transaction.account_id,
            concept_id=transaction.concept_id,
            transaction_type=TransactionType(
                transaction.transaction_type.value
            ),
            amount=transaction.amount,
            transaction_date=transaction.transaction_date,
            captured_at=transaction.captured_at,
            captured_by=transaction.captured_by,
            short_description=transaction.short_description,
            long_description=transaction.long_description,
            is_active=transaction.is_active,
        )


@strawberry.type
class Role:
    id: int
    code: str
    name: str
    description: str | None
    is_active: bool

    @staticmethod
    def from_model(role: RoleModel):
        return Role(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
        )


@strawberry.type
class Permission:
    id: int
    code: str
    name: str
    description: str | None
    is_active: bool

    @staticmethod
    def from_model(permission: PermissionModel):
        return Permission(
            id=permission.id,
            code=permission.code,
            name=permission.name,
            description=permission.description,
            is_active=permission.is_active,
        )


@strawberry.type
class RolePermission:
    id: int
    role_id: int
    permission_id: int
    is_active: bool

    @staticmethod
    def from_model(relation: RolePermissionModel):
        return RolePermission(
            id=relation.id,
            role_id=relation.role_id,
            permission_id=relation.permission_id,
            is_active=relation.is_active,
        )


@strawberry.type
class CompanyUserRole:
    id: int
    company_user_id: int
    role_id: int
    is_active: bool

    @staticmethod
    def from_model(relation: CompanyUserRoleModel):
        return CompanyUserRole(
            id=relation.id,
            company_user_id=relation.company_user_id,
            role_id=relation.role_id,
            is_active=relation.is_active,
        )


@strawberry.type
class CompanyUser:
    id: int
    company_id: int
    user_id: int
    is_admin: bool
    is_active: bool
    joined_at: datetime

    @staticmethod
    def from_model(company_user: CompanyUserModel):
        return CompanyUser(
            id=company_user.id,
            company_id=company_user.company_id,
            user_id=company_user.user_id,
            is_admin=company_user.is_admin,
            is_active=company_user.is_active,
            joined_at=company_user.joined_at,
        )


@strawberry.input
class CreateAccountInput:
    company_id: int
    account_type: AccountType
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
    concept_type: ConceptType
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
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: datetime | None = None
    short_description: str | None = None
    long_description: str | None = None


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.type
class LoginPayload:
    access_token: str
    token_type: str


@strawberry.input
class CreateRoleInput:
    actor_company_user_id: int
    code: str
    name: str
    description: str | None = None


@strawberry.input
class CreatePermissionInput:
    actor_company_user_id: int
    code: str
    name: str
    description: str | None = None


@strawberry.input
class AssignPermissionToRoleInput:
    actor_company_user_id: int
    role_id: int
    permission_id: int


@strawberry.input
class CreateCompanyUserInput:
    actor_company_user_id: int
    company_id: int
    user_id: int
    is_admin: bool = False


@strawberry.input
class AssignRoleInput:
    actor_company_user_id: int
    company_user_id: int
    role_id: int


def _validar_actor(
    info: Info,
    actor_company_user_id: int,
) -> CompanyUserModel:

    user = info.context.get("user")

    if user is None:
        raise ValueError("Usuario no autenticado")

    db = info.context["db"]

    company_user = get_active_company_user(
        db,
        actor_company_user_id,
    )

    if company_user is None:
        raise ValueError(
            "La membresía no existe o está inactiva"
        )

    if company_user.user_id != user.id:
        raise PermissionError(
            "El actor no corresponde al usuario autenticado"
        )

    return company_user


@strawberry.type
class Query:

    @strawberry.field
    def accounts(
        self,
        info: Info,
        company_id: int,
        account_type: AccountType | None = None,
        active_only: bool = True,
    ) -> list[Account]:

        db = info.context["db"]

        accounts = list_accounts_service(
            db,
            company_id=company_id,
            account_type=(
                AccountTypeModel(account_type.value)
                if account_type
                else None
            ),
            active_only=active_only,
        )

        return [
            Account.from_model(account)
            for account in accounts
        ]

    @strawberry.field
    def account(
        self,
        info: Info,
        account_id: int,
    ) -> Account:

        db = info.context["db"]

        account = get_account_service(
            db,
            account_id,
        )

        return Account.from_model(account)

    @strawberry.field
    def concepts(
        self,
        info: Info,
        company_id: int,
        concept_type: ConceptType | None = None,
        active_only: bool = True,
    ) -> list[Concept]:

        db = info.context["db"]

        concepts = list_concepts_service(
            db,
            company_id=company_id,
            concept_type=(
                ConceptTypeModel(concept_type.value)
                if concept_type
                else None
            ),
            active_only=active_only,
        )

        return [
            Concept.from_model(concept)
            for concept in concepts
        ]

    @strawberry.field
    def concept(
        self,
        info: Info,
        concept_id: int,
    ) -> Concept:

        db = info.context["db"]

        concept = get_concept_service(
            db,
            concept_id,
        )

        return Concept.from_model(concept)

    @strawberry.field
    def account_concepts(
        self,
        info: Info,
        account_id: int,
    ) -> list[AccountConcept]:

        db = info.context["db"]

        relations = get_account_concepts_service(
            db,
            account_id,
        )

        return [
            AccountConcept.from_model(relation)
            for relation in relations
        ]

    @strawberry.field
    def transactions(
        self,
        info: Info,
        account_id: int,
        transaction_type: TransactionType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:

        db = info.context["db"]

        transactions = list_transactions_service(
            db,
            account_id=account_id,
            transaction_type=(
                TransactionTypeModel(transaction_type.value)
                if transaction_type
                else None
            ),
            limit=limit,
            offset=offset,
        )

        return [
            Transaction.from_model(transaction)
            for transaction in transactions
        ]

    @strawberry.field
    def list_roles(
        self,
        info: Info,
        actor_company_user_id: int,
    ) -> list[Role]:

        _validar_actor(info, actor_company_user_id)

        db = info.context["db"]

        roles = list_roles_service(
            db,
            actor_company_user_id,
        )

        return [
            Role.from_model(role)
            for role in roles
        ]

    @strawberry.field
    def list_permissions(
        self,
        info: Info,
        actor_company_user_id: int,
    ) -> list[Permission]:

        _validar_actor(info, actor_company_user_id)

        db = info.context["db"]

        permissions = list_permissions_service(
            db,
            actor_company_user_id,
        )

        return [
            Permission.from_model(permission)
            for permission in permissions
        ]

    @strawberry.field
    def list_role_permissions(
        self,
        info: Info,
        actor_company_user_id: int,
        role_id: int,
    ) -> list[RolePermission]:

        _validar_actor(info, actor_company_user_id)

        db = info.context["db"]

        relations = list_role_permissions_service(
            db,
            actor_company_user_id,
            role_id,
        )

        return [
            RolePermission.from_model(relation)
            for relation in relations
        ]


@strawberry.type
class Mutation:

    @strawberry.mutation
    def login(
        self,
        info: Info,
        input: LoginInput,
    ) -> LoginPayload:

        db = info.context["db"]

        token = authenticate_user(
            db,
            input.email,
            input.password,
        )

        return LoginPayload(
            access_token=token,
            token_type="bearer",
        )

    @strawberry.mutation
    def create_account(
        self,
        info: Info,
        input: CreateAccountInput,
    ) -> Account:

        db = info.context["db"]

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

        return Account.from_model(account)

    @strawberry.mutation
    def create_concept(
        self,
        info: Info,
        input: CreateConceptInput,
    ) -> Concept:

        db = info.context["db"]

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

        return Concept.from_model(concept)

    @strawberry.mutation
    def assign_concept_to_account(
        self,
        info: Info,
        input: AssignConceptToAccountInput,
    ) -> AccountConcept:

        db = info.context["db"]

        relation = assign_concept_to_account(
            db,
            account_id=input.account_id,
            concept_id=input.concept_id,
        )

        return AccountConcept.from_model(relation)

    @strawberry.mutation
    def remove_concept_from_account(
        self,
        info: Info,
        account_id: int,
        concept_id: int,
    ) -> AccountConcept:

        db = info.context["db"]

        relation = remove_concept_from_account(
            db,
            account_id=account_id,
            concept_id=concept_id,
        )

        return AccountConcept.from_model(relation)

    @strawberry.mutation
    def create_transaction(
        self,
        info: Info,
        input: CreateTransactionInput,
    ) -> Transaction:

        db = info.context["db"]

        user = info.context.get("user")

        if user is None:
            raise ValueError(
                "Usuario no autenticado"
            )

        transaction = create_transaction_service(
            db,
            account_id=input.account_id,
            concept_id=input.concept_id,
            transaction_type=TransactionTypeModel(
                input.transaction_type.value
            ),
            amount=input.amount,
            captured_by=user.id,
            transaction_date=input.transaction_date,
            short_description=input.short_description,
            long_description=input.long_description,
        )

        return Transaction.from_model(transaction)

    @strawberry.mutation
    def delete_transaction(
        self,
        info: Info,
        transaction_id: int,
    ) -> Transaction:

        db = info.context["db"]

        transaction = delete_transaction_service(
            db,
            transaction_id,
        )

        return Transaction.from_model(transaction)

    @strawberry.mutation
    def create_role(
        self,
        info: Info,
        input: CreateRoleInput,
    ) -> Role:

        _validar_actor(info, input.actor_company_user_id)

        db = info.context["db"]

        role = create_role_service(
            db,
            input.actor_company_user_id,
            code=input.code,
            name=input.name,
            description=input.description,
        )

        return Role.from_model(role)

    @strawberry.mutation
    def deactivate_role(
        self,
        info: Info,
        actor_company_user_id: int,
        role_id: int,
    ) -> Role:

        _validar_actor(info, actor_company_user_id)

        db = info.context["db"]

        role = deactivate_role_service(
            db,
            actor_company_user_id,
            role_id,
        )

        return Role.from_model(role)

    @strawberry.mutation
    def create_permission(
        self,
        info: Info,
        input: CreatePermissionInput,
    ) -> Permission:

        _validar_actor(info, input.actor_company_user_id)

        db = info.context["db"]

        permission = create_permission_service(
            db,
            input.actor_company_user_id,
            code=input.code,
            name=input.name,
            description=input.description,
        )

        return Permission.from_model(permission)

    @strawberry.mutation
    def assign_permission_to_role(
        self,
        info: Info,
        input: AssignPermissionToRoleInput,
    ) -> RolePermission:

        _validar_actor(info, input.actor_company_user_id)

        db = info.context["db"]

        relation = assign_permission_to_role_service(
            db,
            input.actor_company_user_id,
            role_id=input.role_id,
            permission_id=input.permission_id,
        )

        return RolePermission.from_model(relation)

    @strawberry.mutation
    def remove_permission_from_role(
        self,
        info: Info,
        actor_company_user_id: int,
        role_id: int,
        permission_id: int,
    ) -> RolePermission:

        _validar_actor(info, actor_company_user_id)

        db = info.context["db"]

        relation = remove_permission_from_role_service(
            db,
            actor_company_user_id,
            role_id,
            permission_id,
        )

        return RolePermission.from_model(relation)


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)