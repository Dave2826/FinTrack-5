from sqlalchemy.orm import Session

from models.concept import Concept, ConceptType


def get_concept(
    db: Session,
    concept_id: int
) -> Concept | None:
    return db.get(Concept, concept_id)


def create_concept(
    db: Session,
    concept: Concept
) -> Concept:
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


def list_concepts(
    db: Session,
    company_id: int,
    concept_type: ConceptType | None = None,
    active_only: bool = True
) -> list[Concept]:
    query = (
        db.query(Concept)
        .filter(Concept.company_id == company_id)
    )

    if concept_type is not None:
        query = query.filter(
            Concept.concept_type == concept_type
        )

    if active_only:
        query = query.filter(Concept.is_active.is_(True))

    return query.order_by(Concept.id).all()