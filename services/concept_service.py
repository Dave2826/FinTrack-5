from sqlalchemy.orm import Session

from models.concept import Concept, ConceptType
from repositories.company_repository import get_company
from repositories.concept_repository import (
    create_concept,
    get_concept,
    list_concepts,
)


def create_concept_service(
    db: Session,
    company_id: int,
    concept_type: ConceptType,
    name: str,
    short_description: str | None = None,
    long_description: str | None = None,
) -> Concept:

    company = get_company(db, company_id)

    if company is None:
        raise ValueError("La empresa no existe")

    if not company.is_active:
        raise ValueError("La empresa no está activa")

    existing_concepts = list_concepts(
        db,
        company_id=company_id,
        active_only=False
    )

    duplicate = next(
        (
            concept
            for concept in existing_concepts
            if concept.name.strip().lower() == name.strip().lower()
            and concept.is_active
        ),
        None
    )

    if duplicate is not None:
        raise ValueError(
            "Ya existe un concepto activo con ese nombre"
        )

    concept = Concept(
        company_id=company_id,
        concept_type=concept_type,
        name=name.strip(),
        short_description=short_description,
        long_description=long_description,
    )

    return create_concept(db, concept)


def get_concept_service(
    db: Session,
    concept_id: int
) -> Concept:

    concept = get_concept(db, concept_id)

    if concept is None:
        raise ValueError("El concepto no existe")

    return concept


def list_concepts_service(
    db: Session,
    company_id: int,
    concept_type: ConceptType | None = None,
    active_only: bool = True
) -> list[Concept]:

    return list_concepts(
        db,
        company_id=company_id,
        concept_type=concept_type,
        active_only=active_only
    )