from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.utils.auth_system import auth_guard, require_staff, get_current_user, is_super_ceo_user
from app.models import User, Branch, InventoryItem, StockMovement
from pydantic import BaseModel, Field

# Pydantic models for inventory
class InventoryItemCreate(BaseModel):
    item_code: str = Field(..., min_length=1, max_length=50)
    item_name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    unit: str = Field(..., min_length=1, max_length=50)
    current_stock: int = Field(..., ge=0)
    minimum_stock: int = Field(..., ge=0)
    maximum_stock: int = Field(..., ge=0)
    reorder_level: int = Field(..., ge=0)
    purchase_price: float = Field(..., ge=0)
    selling_price: float = Field(..., ge=0)
    supplier: Optional[str] = Field(None, max_length=200)
    supplier_contact: Optional[str] = Field(None, max_length=15)
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[datetime] = None
    manufacture_date: Optional[datetime] = None

class InventoryItemUpdate(BaseModel):
    item_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    unit: Optional[str] = None
    current_stock: Optional[int] = None
    minimum_stock: Optional[int] = None
    maximum_stock: Optional[int] = None
    reorder_level: Optional[int] = None
    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None
    supplier: Optional[str] = None
    supplier_contact: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[datetime] = None
    manufacture_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class InventoryItemResponse(BaseModel):
    id: int
    item_code: str
    item_name: str
    category: str
    subcategory: Optional[str]
    unit: str
    current_stock: int
    minimum_stock: int
    maximum_stock: int
    reorder_level: int
    purchase_price: float
    selling_price: float
    supplier: Optional[str]
    supplier_contact: Optional[str]
    batch_number: Optional[str]
    expiry_date: Optional[datetime]
    manufacture_date: Optional[datetime]
    is_active: bool
    last_restocked: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    branch_id: int
    
    # Stock status calculated field
    stock_status: str
    expiry_status: Optional[str]
    total_value: float
    
    class Config:
        from_attributes = True

class StockMovementCreate(BaseModel):
    movement_type: str = Field(..., pattern=r"^(purchase|consumption|wastage|adjustment)$")
    quantity: int = Field(..., ne=0)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

class StockMovementResponse(BaseModel):
    id: int
    inventory_item_id: int
    movement_type: str
    quantity: int
    previous_stock: int
    new_stock: int
    reference_number: Optional[str]
    movement_date: datetime
    notes: Optional[str]
    created_by: int
    approved_by: Optional[int]
    
    # Include item info
    item_name: str
    item_code: str
    
    class Config:
        from_attributes = True

router = APIRouter()

@router.post("/inventory/items/", response_model=InventoryItemResponse)
def create_inventory_item(
    item_data: InventoryItemCreate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Create a new inventory item"""
    
    # Ensure branch access
    if not is_super_ceo_user(current_user):
        item_data.branch_id = current_user.branch_id
    
    # Check for duplicate item code
    existing_item = db.query(InventoryItem).filter(
        and_(
            InventoryItem.item_code == item_data.item_code,
            InventoryItem.branch_id == item_data.branch_id
        )
    ).first()
    
    if existing_item:
        raise HTTPException(
            status_code=400,
            detail="Item with this code already exists in this branch"
        )
    
    # Create inventory item
    db_item = InventoryItem(
        branch_id=item_data.branch_id,
        item_code=item_data.item_code,
        item_name=item_data.item_name,
        category=item_data.category,
        subcategory=item_data.subcategory,
        unit=item_data.unit,
        current_stock=item_data.current_stock,
        minimum_stock=item_data.minimum_stock,
        maximum_stock=item_data.maximum_stock,
        reorder_level=item_data.reorder_level,
        purchase_price=item_data.purchase_price,
        selling_price=item_data.selling_price,
        supplier=item_data.supplier,
        supplier_contact=item_data.supplier_contact,
        batch_number=item_data.batch_number,
        expiry_date=item_data.expiry_date,
        manufacture_date=item_data.manufacture_date,
        last_restocked=datetime.utcnow() if item_data.current_stock > 0 else None
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="create",
        entity_type="inventory_item",
        entity_id=db_item.id,
        description=f"Created inventory item {db_item.item_name}"
    )
    
    return db_item

@router.get("/inventory/items/", response_model=List[InventoryItemResponse])
def get_inventory_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    low_stock_only: bool = Query(False),
    expired_only: bool = Query(False),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get inventory items with filtering and search"""
    
    # Filter by branch access
    if is_super_ceo_user(current_user):
        query = db.query(InventoryItem)
        if branch_id:
            query = query.filter(InventoryItem.branch_id == branch_id)
    else:
        query = db.query(InventoryItem).filter(InventoryItem.branch_id == current_user.branch_id)
    
    # Search functionality
    if search:
        search_filter = or_(
            InventoryItem.item_code.ilike(f"%{search}%"),
            InventoryItem.item_name.ilike(f"%{search}%"),
            InventoryItem.supplier.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Category filter
    if category:
        query = query.filter(InventoryItem.category == category)
    
    # Only active items
    query = query.filter(InventoryItem.is_active == True)
    
    items = query.order_by(desc(InventoryItem.item_name)).offset(skip).limit(limit).all()
    
    # Add calculated fields
    enriched_items = []
    for item in items:
        # Calculate stock status
        if item.current_stock <= 0:
            stock_status = "Out of Stock"
        elif item.current_stock <= item.minimum_stock:
            stock_status = "Low Stock"
        elif item.current_stock >= item.maximum_stock:
            stock_status = "Overstocked"
        else:
            stock_status = "Normal"
        
        # Calculate expiry status
        expiry_status = None
        if item.expiry_date:
            days_to_expiry = (item.expiry_date - datetime.now()).days
            if days_to_expiry < 0:
                expiry_status = "Expired"
            elif days_to_expiry <= 30:
                expiry_status = "Expiring Soon"
            else:
                expiry_status = "Valid"
        
        # Calculate total value
        total_value = item.current_stock * item.purchase_price
        
        # Create response with additional fields
        item_dict = {
            **item.__dict__,
            'stock_status': stock_status,
            'expiry_status': expiry_status,
            'total_value': total_value
        }
        enriched_items.append(InventoryItemResponse(**item_dict))
    
    # Apply additional filters
    if low_stock_only:
        enriched_items = [item for item in enriched_items if item.stock_status in ["Low Stock", "Out of Stock"]]
    
    if expired_only:
        enriched_items = [item for item in enriched_items if item.expiry_status in ["Expired", "Expiring Soon"]]
    
    return enriched_items

@router.get("/inventory/items/{item_id}", response_model=InventoryItemResponse)
def get_inventory_item(
    item_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get inventory item by ID"""
    
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and item.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this item")
    
    # Calculate stock status
    if item.current_stock <= 0:
        stock_status = "Out of Stock"
    elif item.current_stock <= item.minimum_stock:
        stock_status = "Low Stock"
    elif item.current_stock >= item.maximum_stock:
        stock_status = "Overstocked"
    else:
        stock_status = "Normal"
    
    # Calculate expiry status
    expiry_status = None
    if item.expiry_date:
        days_to_expiry = (item.expiry_date - datetime.now()).days
        if days_to_expiry < 0:
            expiry_status = "Expired"
        elif days_to_expiry <= 30:
            expiry_status = "Expiring Soon"
        else:
            expiry_status = "Valid"
    
    # Calculate total value
    total_value = item.current_stock * item.purchase_price
    
    # Create response with additional fields
    item_dict = {
        **item.__dict__,
        'stock_status': stock_status,
        'expiry_status': expiry_status,
        'total_value': total_value
    }
    
    return InventoryItemResponse(**item_dict)

@router.put("/inventory/items/{item_id}", response_model=InventoryItemResponse)
def update_inventory_item(
    item_id: int,
    item_data: InventoryItemUpdate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Update inventory item"""
    
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and item.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this item")
    
    # Update fields
    for field, value in item_data.dict(exclude_unset=True).items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="update",
        entity_type="inventory_item",
        entity_id=item.id,
        description=f"Updated inventory item {item.item_name}"
    )
    
    return item

@router.delete("/inventory/items/{item_id}")
def deactivate_inventory_item(
    item_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Deactivate inventory item (soft delete)"""
    
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and item.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this item")
    
    # Deactivate item
    item.is_active = False
    db.commit()
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="deactivate",
        entity_type="inventory_item",
        entity_id=item.id,
        description=f"Deactivated inventory item {item.item_name}"
    )
    
    return {"message": "Inventory item deactivated successfully"}

@router.post("/inventory/items/{item_id}/stock-movement", response_model=StockMovementResponse)
def create_stock_movement(
    item_id: int,
    movement_data: StockMovementCreate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Create stock movement (purchase, consumption, adjustment)"""
    
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and item.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this item")
    
    # Store previous stock
    previous_stock = item.current_stock
    
    # Calculate new stock based on movement type
    if movement_data.movement_type == "purchase":
        new_stock = previous_stock + abs(movement_data.quantity)
        item.last_restocked = datetime.utcnow()
    elif movement_data.movement_type == "consumption":
        new_stock = previous_stock - abs(movement_data.quantity)
    elif movement_data.movement_type == "wastage":
        new_stock = previous_stock - abs(movement_data.quantity)
    else:  # adjustment
        new_stock = previous_stock + movement_data.quantity
    
    # Validate stock doesn't go negative
    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail="Stock cannot go negative"
        )
    
    # Update item stock
    item.current_stock = new_stock
    
    # Create stock movement record
    stock_movement = StockMovement(
        inventory_item_id=item_id,
        movement_type=movement_data.movement_type,
        quantity=movement_data.quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reference_number=movement_data.reference_number,
        notes=movement_data.notes,
        created_by=current_user.id
    )
    
    db.add(stock_movement)
    db.commit()
    db.refresh(stock_movement)
    
    # Log activity
    auth_guard.log_activity(
        db=db,
        user=current_user,
        action="stock_movement",
        entity_type="inventory_item",
        entity_id=item.id,
        description=f"Stock movement for {item.item_name}: {movement_data.movement_type} {movement_data.quantity}"
    )
    
    return stock_movement

@router.get("/inventory/items/{item_id}/stock-movements", response_model=List[StockMovementResponse])
def get_stock_movements(
    item_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    movement_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get stock movements for an item"""
    
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Check branch access
    if not is_super_ceo_user(current_user) and item.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Access denied to this item")
    
    # Query stock movements
    query = db.query(StockMovement).filter(StockMovement.inventory_item_id == item_id)
    
    # Apply filters
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)
    if start_date:
        query = query.filter(StockMovement.movement_date >= start_date)
    if end_date:
        query = query.filter(StockMovement.movement_date <= end_date)
    
    movements = query.order_by(desc(StockMovement.movement_date)).offset(skip).limit(limit).all()
    
    # Enrich with item info
    enriched_movements = []
    for movement in movements:
        movement_dict = {
            **movement.__dict__,
            'item_name': item.item_name,
            'item_code': item.item_code
        }
        enriched_movements.append(StockMovementResponse(**movement_dict))
    
    return enriched_movements

@router.get("/inventory/alerts")
def get_inventory_alerts(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get inventory alerts (low stock, expiring items)"""
    
    # Filter by branch access
    if is_super_ceo_user(current_user):
        items = db.query(InventoryItem).filter(InventoryItem.is_active == True).all()
    else:
        items = db.query(InventoryItem).filter(
            and_(
                InventoryItem.branch_id == current_user.branch_id,
                InventoryItem.is_active == True
            )
        ).all()
    
    low_stock_alerts = []
    expiry_alerts = []
    
    for item in items:
        # Low stock alerts
        if item.current_stock <= item.minimum_stock:
            low_stock_alerts.append({
                "item_id": item.id,
                "item_name": item.item_name,
                "item_code": item.item_code,
                "current_stock": item.current_stock,
                "minimum_stock": item.minimum_stock,
                "stock_status": "Low Stock" if item.current_stock > 0 else "Out of Stock",
                "alert_type": "low_stock"
            })
        
        # Expiry alerts
        if item.expiry_date:
            days_to_expiry = (item.expiry_date - datetime.now()).days
            if days_to_expiry <= 30:
                expiry_alerts.append({
                    "item_id": item.id,
                    "item_name": item.item_name,
                    "item_code": item.item_code,
                    "expiry_date": item.expiry_date,
                    "days_to_expiry": days_to_expiry,
                    "expiry_status": "Expired" if days_to_expiry < 0 else "Expiring Soon",
                    "alert_type": "expiry"
                })
    
    return {
        "low_stock_alerts": low_stock_alerts,
        "expiry_alerts": expiry_alerts,
        "total_alerts": len(low_stock_alerts) + len(expiry_alerts)
    }

@router.get("/inventory/categories")
def get_inventory_categories(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get list of inventory categories"""
    
    # Filter by branch access
    if is_super_ceo_user(current_user):
        categories = db.query(InventoryItem.category).distinct().all()
    else:
        categories = db.query(InventoryItem.category).filter(
            InventoryItem.branch_id == current_user.branch_id
        ).distinct().all()
    
    return [{"category": cat[0]} for cat in categories]
