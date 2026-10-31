from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, Branch
from app.models import User
from app.utils.auth_system import auth_guard, get_current_user, is_super_ceo_user

router = APIRouter()


class AssetCreate(BaseModel):
    branch_id: int
    asset_name: str
    model: Optional[str]
    serial_no: Optional[str]
    purchase_date: Optional[datetime]
    last_maintenance_date: Optional[datetime]
    status: Optional[str] = "active"
    notes: Optional[str]


class AssetResponse(BaseModel):
    id: int
    branch_id: int
    asset_name: str
    model: Optional[str]
    serial_no: Optional[str]
    purchase_date: Optional[datetime]
    last_maintenance_date: Optional[datetime]
    status: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/assets/", response_model=AssetResponse)
def create_asset(asset: AssetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not is_super_ceo_user(current_user) and current_user.role != "branch_admin":
        raise HTTPException(status_code=403, detail="Access denied")

    branch = db.query(Branch).filter(Branch.id == asset.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if current_user.role == "branch_admin" and current_user.branch_id != branch.id:
        raise HTTPException(status_code=403, detail="Access denied to this branch")

    db_asset = Asset(
        branch_id=asset.branch_id,
        asset_name=asset.asset_name,
        model=asset.model,
        serial_no=asset.serial_no,
        purchase_date=asset.purchase_date,
        last_maintenance_date=asset.last_maintenance_date,
        status=asset.status or "active",
        notes=asset.notes,
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)

    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="create",
        entity_type="asset",
        entity_id=db_asset.id,
        branch_id=db_asset.branch_id,
        description=f"Created asset {db_asset.asset_name} for branch {db_asset.branch_id}",
    )

    return db_asset


@router.get("/assets/", response_model=List[AssetResponse])
def list_assets(branch_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Asset)
    if branch_id:
        query = query.filter(Asset.branch_id == branch_id)
    if not is_super_ceo_user(current_user):
        query = query.filter(Asset.branch_id == current_user.branch_id)
    return query.order_by(Asset.created_at.desc()).all()


@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: int, payload: AssetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if not is_super_ceo_user(current_user) and current_user.branch_id != asset.branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(asset, k, v)
    db.commit()
    db.refresh(asset)

    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="update",
        entity_type="asset",
        entity_id=asset.id,
        branch_id=asset.branch_id,
        description=f"Updated asset {asset.asset_name} for branch {asset.branch_id}",
    )

    return asset


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not is_super_ceo_user(current_user) and current_user.branch_id != asset.branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="delete",
        entity_type="asset",
        entity_id=asset.id,
        branch_id=asset.branch_id,
        description=f"Deleted asset {asset.asset_name} from branch {asset.branch_id}",
    )

    db.delete(asset)
    db.commit()
    return {"message": "Asset deleted"}
