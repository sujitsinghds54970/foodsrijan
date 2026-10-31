"""
Branch Bank Details API Routes
Manage bank account and UPI information for branches
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.database import get_db
from app.models.branch_bank_details import BranchBankDetails
from app.models.branch import Branch
from app.models import User
from app.schemas.branch_bank_details import (
    BranchBankDetailsCreate,
    BranchBankDetailsUpdate,
    BranchBankDetailsResponse
)
from app.utils.auth_system import get_current_user, is_super_ceo_user

router = APIRouter()


def _mask_soundbox_config(soundbox_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(soundbox_config, dict):
        return {}

    provider = soundbox_config.get("provider")
    device_id = str(soundbox_config.get("device_id") or "")
    masked_device_id = f"***{device_id[-4:]}" if device_id else ""

    return {
        "provider": provider,
        "device_id": masked_device_id,
        "webhook_configured": bool(soundbox_config.get("webhook")),
    }


@router.get("/{branch_id}/bank-details", response_model=Dict[str, Any])
async def get_branch_bank_details(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get bank details for a specific branch.
    Accessible by Super Admin and the specific Branch Admin.
    """
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Access control: Super CEO or Branch Admin of this specific branch
    if not is_super_ceo_user(current_user) and current_user.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own branch's bank details."
        )
    
    # Get bank details
    bank_details = db.query(BranchBankDetails).filter(
        BranchBankDetails.branch_id == branch_id,
        BranchBankDetails.is_active == True
    ).first()
    
    if not bank_details:
        return {}

    if is_super_ceo_user(current_user):
        return {
            "id": bank_details.id,
            "branch_id": bank_details.branch_id,
            "account_holder_name": bank_details.account_holder_name,
            "account_number": bank_details.account_number,
            "ifsc_code": bank_details.ifsc_code,
            "bank_name": bank_details.bank_name,
            "upi_id": bank_details.upi_id,
            "soundbox_config": bank_details.soundbox_config,
            "is_active": bank_details.is_active,
            "created_at": bank_details.created_at,
            "updated_at": bank_details.updated_at,
        }

    return {
        "branch_id": bank_details.branch_id,
        "upi_id": bank_details.upi_id,
        "soundbox_config": _mask_soundbox_config(bank_details.soundbox_config),
        "is_active": bank_details.is_active,
    }


@router.post("/{branch_id}/bank-details", response_model=BranchBankDetailsResponse)
async def create_or_update_branch_bank_details(
    branch_id: int,
    details: BranchBankDetailsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update bank details for a branch.
    Only Super Admin and the specific Branch Admin can modify.
    """
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Strict access control: Super CEO only
    if not is_super_ceo_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Super CEO can modify bank details."
        )
    
    # Check if bank details already exist
    existing_details = db.query(BranchBankDetails).filter(
        BranchBankDetails.branch_id == branch_id
    ).first()
    
    if existing_details:
        # Update existing details
        for key, value in details.dict().items():
            setattr(existing_details, key, value)
        
        db.commit()
        db.refresh(existing_details)
        return existing_details
    else:
        # Create new details
        new_details = BranchBankDetails(
            branch_id=branch_id,
            **details.dict()
        )
        
        db.add(new_details)
        db.commit()
        db.refresh(new_details)
        return new_details


@router.put("/{branch_id}/bank-details", response_model=BranchBankDetailsResponse)
async def update_branch_bank_details(
    branch_id: int,
    details: BranchBankDetailsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update existing bank details for a branch.
    Only Super Admin and the specific Branch Admin can modify.
    """
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Strict access control
    if not is_super_ceo_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Super CEO can modify bank details."
        )
    
    # Get existing details
    bank_details = db.query(BranchBankDetails).filter(
        BranchBankDetails.branch_id == branch_id
    ).first()
    
    if not bank_details:
        raise HTTPException(status_code=404, detail="Bank details not found. Please create them first.")
    
    # Update fields
    update_data = details.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bank_details, key, value)
    
    db.commit()
    db.refresh(bank_details)
    
    return bank_details


@router.delete("/{branch_id}/bank-details", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch_bank_details(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete (deactivate) bank details for a branch.
    Only Super Admin can delete.
    """
    if not is_super_ceo_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Super CEO can delete bank details."
        )
    
    bank_details = db.query(BranchBankDetails).filter(
        BranchBankDetails.branch_id == branch_id
    ).first()
    
    if not bank_details:
        raise HTTPException(status_code=404, detail="Bank details not found")
    
    # Soft delete
    bank_details.is_active = False
    db.commit()
    
    return None
