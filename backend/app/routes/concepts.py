from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.concept import Concept
from app.schemas.concept import ConceptCreate, ConceptUpdate
from app.utils.auth_system import auth_guard

router = APIRouter(prefix="/concepts", tags=["Concepts"])

@router.get("/")
def get_all_concepts(db: Session = Depends(get_db)):
    return db.query(Concept).filter(Concept.is_active == True).all()

@router.post("/")
def create_concept(concept_data: ConceptCreate, db: Session = Depends(get_db)):
    existing = db.query(Concept).filter(Concept.name == concept_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Concept already exists")

    new_concept = Concept(**concept_data.dict())
    db.add(new_concept)
    db.commit()
    db.refresh(new_concept)
    return new_concept
