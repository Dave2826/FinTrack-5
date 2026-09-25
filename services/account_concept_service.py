from sqlalchemy.orm import Session

from models.account_concept import AccountConcept
from repositories.account_concept_repository import (
    create_relation,
    get_relation,
    list_account_concepts,
)
from repositories.account_repository import get_account
from repositories.concept_repository import get_concept


def assign_concept_to_account(
    db: Session,
    account_id: int,
    concept_id: int
) -> AccountConcept:

    account = get_account(db, account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    if not account.is_active:
        raise ValueError("La cuenta no está activa")

    concept = get_concept(db, concept_id)

    if concept is None:
        raise ValueError("El concepto no existe")

    if not concept.is_active:
        raise ValueError("El concepto no está activo")

    if account.company_id != concept.company_id:
        raise ValueError(
            "La cuenta y el concepto deben pertenecer a la misma empresa"
        )

    existing_relation = get_relation(
        db,
        account_id=account_id,
        concept_id=concept_id
    )

    if existing_relation is not None:
        if existing_relation.is_active:
            raise ValueError(
                "El concepto ya está asignado a esta cuenta"
            )

        existing_relation.is_active = True
        db.commit()
        db.refresh(existing_relation)
        return existing_relation

    relation = AccountConcept(
        account_id=account_id,
        concept_id=concept_id,
        is_active=True,
    )

    return create_relation(db, relation)


def get_account_concepts_service(
    db: Session,
    account_id: int
) -> list[AccountConcept]:

    account = get_account(db, account_id)

    if account is None:
        raise ValueError("La cuenta no existe")

    return list_account_concepts(
        db,
        account_id=account_id
    )


def remove_concept_from_account(
    db: Session,
    account_id: int,
    concept_id: int
) -> AccountConcept:

    relation = get_relation(
        db,
        account_id=account_id,
        concept_id=concept_id
    )

    if relation is None:
        raise ValueError(
            "La relación entre cuenta y concepto no existe"
        )

    if not relation.is_active:
        raise ValueError(
            "La relación entre cuenta y concepto ya está inactiva"
        )

    relation.is_active = False

    db.commit()
    db.refresh(relation)

    return relation