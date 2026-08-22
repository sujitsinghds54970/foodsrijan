from pydantic import BaseModel
from typing import Optional

class ConceptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    default_margin: Optional[float] = None
    is_active: bool = True
    created_by: Optional[int] = None

class ConceptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    default_margin: Optional[float] = None
    is_active: Optional[bool] = None
