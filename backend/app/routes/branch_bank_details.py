"""
Branch Bank Details API Routes
Manage bank account and UPI information for branches
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.branch_bank_details import BranchBankDetails
from app.models.branch import Branch
from app.models import User
from app.schemas.branch_bank_details import (
    BranchBankDetailsCreate,
    BranchBankDetailsUpdate,
    BranchBankDetailsResponse
)
from app.utils.auth_system import get_current_user, require_branch_admin

router = APIRouter()


@router.get("/api/branches/{branch_id}/bank-details", response_model=BranchBankDetailsResponse)
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
    
    # Access control: Super Admin or Branch Admin of this specific branch
    if current_user.role != 'super_admin' and current_user.branch_id != branch_id:
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
        raise HTTPException(
            status_code=404,
            detail="Bank details not configured for this branch. Please add them in Bank Settings."
        )
    
    return bank_details


@router.post("/api/branches/{branch_id}/bank-details", response_model=BranchBankDetailsResponse)
async def create_or_update_branch_bank_details(
    branch_id: int,
    details: BranchBankDetailsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_branch_admin)
):
    """
    Create or update bank details for a branch.
    Only Super Admin and the specific Branch Admin can modify.
    """
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Access control: Super Admin or Branch Admin of this specific branch
    if current_user.role != 'super_admin' and current_user.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only modify your own branch's bank details."
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


@router.put("/api/branches/{branch_id}/bank-details", response_model=BranchBankDetailsResponse)
async def update_branch_bank_details(
    branch_id: int,
    details: BranchBankDetailsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_branch_admin)
):
    """
    Update existing bank details for a branch.
    Only Super Admin and the specific Branch Admin can modify.
    """
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Access control
    if current_user.role != 'super_admin' and current_user.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only modify your own branch's bank details."
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


@router.delete("/api/branches/{branch_id}/bank-details", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch_bank_details(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_branch_admin)
):
    """
    Soft delete (deactivate) bank details for a branch.
    Only Super Admin can delete.
    """
    if current_user.role != 'super_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can delete bank details."
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
