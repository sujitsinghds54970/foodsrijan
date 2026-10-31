from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.inventory import (
    EquipmentServiceLog,
    InventoryConsumptionHistory,
    InventoryDepartment,
    InventoryEquipment,
    InventoryItemV2 as InventoryItem,
    InventoryStockAudit,
    InventoryStockMovement,
    Supplier,
)
from app.utils.auth_system import get_current_user, is_super_ceo_user
from app.services.finance_integration import create_stock_purchase_expense


router = APIRouter()


def _require_inventory_role(current_user: User = Depends(get_current_user)) -> User:
    if not is_super_ceo_user(current_user) and current_user.role not in ["branch_admin", "branch_director"]:
        raise HTTPException(
            status_code=403,
            detail="Only branch_admin, branch_director, or super_ceo can access inventory endpoints",
        )
    return current_user


def _resolve_branch_id(current_user: User, requested_branch_id: Optional[int]) -> int:
    if is_super_ceo_user(current_user):
        if requested_branch_id is None or int(requested_branch_id) <= 0:
            raise HTTPException(status_code=400, detail="branch_id is required for super_ceo inventory access")
        return int(requested_branch_id)
    if not current_user.branch_id:
        raise HTTPException(status_code=403, detail="User is not assigned to a branch")
    return current_user.branch_id


class SupplierIn(BaseModel):
    branch_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    gstin: Optional[str] = Field(None, max_length=30)


class SupplierOut(SupplierIn):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class InventoryItemIn(BaseModel):
    branch_id: Optional[int] = None
    department: InventoryDepartment
    item_name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=120)
    current_qty: float = Field(0, ge=0)
    min_threshold: float = Field(0, ge=0)
    expiry_date: Optional[date] = None
    unit_cost: float = Field(0, ge=0)
    unit: str = Field("units", min_length=1, max_length=50)
    supplier_id: Optional[int] = None
    barcode_number: Optional[str] = Field(None, max_length=120)


class InventoryItemOut(BaseModel):
    id: int
    branch_id: int
    department: str
    item_name: str
    category: Optional[str]
    current_qty: float
    min_threshold: float
    expiry_date: Optional[date]
    unit_cost: Decimal
    unit: str
    supplier_id: Optional[int]
    supplier_name: Optional[str]
    barcode_number: Optional[str]
    total_value: float
    is_low_stock: bool
    is_expiring_soon: bool


class StockDeltaIn(BaseModel):
    branch_id: Optional[int] = None
    quantity: float = Field(..., gt=0)
    notes: Optional[str] = None


class EquipmentIn(BaseModel):
    branch_id: Optional[int] = None
    department: InventoryDepartment
    machine_name: str = Field(..., min_length=1, max_length=200)
    brand_model: Optional[str] = Field(None, max_length=200)
    serial_number: Optional[str] = Field(None, max_length=150)
    purchase_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    amc_company: Optional[str] = Field(None, max_length=200)
    dealer_contact: Optional[str] = Field(None, max_length=100)
    last_service_date: Optional[date] = None
    next_service_due_date: Optional[date] = None


class EquipmentOut(EquipmentIn):
    id: int
    branch_id: int
    is_service_due_soon: bool

    class Config:
        from_attributes = True


class ServiceLogIn(BaseModel):
    branch_id: Optional[int] = None
    service_date: date
    notes: Optional[str] = None


class ManualAuditIn(BaseModel):
    branch_id: Optional[int] = None
    item_id: int
    physical_qty: float = Field(..., ge=0)
    notes: Optional[str] = None


@router.get("/api/inventory", response_model=List[InventoryItemOut])
def list_inventory_items(
    department: Optional[InventoryDepartment] = Query(None),
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, branch_id)
    query = db.query(InventoryItem).filter(
        InventoryItem.branch_id == branch_id,
        InventoryItem.is_active == True,
    )
    if department:
        query = query.filter(InventoryItem.department == department.value)

    items = query.order_by(InventoryItem.item_name.asc()).all()
    today = date.today()
    data: List[InventoryItemOut] = []
    for item in items:
        expiring = bool(item.expiry_date and item.expiry_date <= (today + timedelta(days=30)))
        total_value = float(item.current_qty) * float(item.unit_cost)
        data.append(
            InventoryItemOut(
                id=item.id,
                branch_id=item.branch_id,
                department=item.department,
                item_name=item.item_name,
                category=item.category,
                current_qty=float(item.current_qty),
                min_threshold=float(item.min_threshold),
                expiry_date=item.expiry_date,
                unit_cost=item.unit_cost,
                unit=item.unit,
                supplier_id=item.supplier_id,
                supplier_name=item.supplier.name if item.supplier else None,
                barcode_number=item.barcode_number,
                total_value=total_value,
                is_low_stock=float(item.current_qty) < float(item.min_threshold),
                is_expiring_soon=expiring,
            )
        )
    return data


@router.post("/api/inventory", response_model=InventoryItemOut, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryItemIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, payload.branch_id)
    item = InventoryItem(
        branch_id=branch_id,
        department=payload.department.value,
        item_name=payload.item_name,
        category=payload.category,
        current_qty=payload.current_qty,
        min_threshold=payload.min_threshold,
        expiry_date=payload.expiry_date,
        unit_cost=payload.unit_cost,
        unit=payload.unit,
        supplier_id=payload.supplier_id,
        barcode_number=payload.barcode_number,
        created_by=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return InventoryItemOut(
        id=item.id,
        branch_id=item.branch_id,
        department=item.department,
        item_name=item.item_name,
        category=item.category,
        current_qty=float(item.current_qty),
        min_threshold=float(item.min_threshold),
        expiry_date=item.expiry_date,
        unit_cost=item.unit_cost,
        unit=item.unit,
        supplier_id=item.supplier_id,
        supplier_name=item.supplier.name if item.supplier else None,
        barcode_number=item.barcode_number,
        total_value=float(item.current_qty) * float(item.unit_cost),
        is_low_stock=float(item.current_qty) < float(item.min_threshold),
        is_expiring_soon=bool(item.expiry_date and item.expiry_date <= (date.today() + timedelta(days=30))),
    )


@router.put("/api/inventory/{item_id}", response_model=InventoryItemOut)
def update_inventory_item(
    item_id: int,
    payload: InventoryItemIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    branch_id = _resolve_branch_id(current_user, payload.branch_id)
    if item.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    item.department = payload.department.value
    item.item_name = payload.item_name
    item.category = payload.category
    item.current_qty = payload.current_qty
    item.min_threshold = payload.min_threshold
    item.expiry_date = payload.expiry_date
    item.unit_cost = payload.unit_cost
    item.unit = payload.unit
    item.supplier_id = payload.supplier_id
    item.barcode_number = payload.barcode_number

    db.commit()
    db.refresh(item)

    return InventoryItemOut(
        id=item.id,
        branch_id=item.branch_id,
        department=item.department,
        item_name=item.item_name,
        category=item.category,
        current_qty=float(item.current_qty),
        min_threshold=float(item.min_threshold),
        expiry_date=item.expiry_date,
        unit_cost=item.unit_cost,
        unit=item.unit,
        supplier_id=item.supplier_id,
        supplier_name=item.supplier.name if item.supplier else None,
        barcode_number=item.barcode_number,
        total_value=float(item.current_qty) * float(item.unit_cost),
        is_low_stock=float(item.current_qty) < float(item.min_threshold),
        is_expiring_soon=bool(item.expiry_date and item.expiry_date <= (date.today() + timedelta(days=30))),
    )


@router.delete("/api/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: int,
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    branch_id = _resolve_branch_id(current_user, branch_id)
    if item.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    item.is_active = False
    db.commit()
    return None


@router.post("/api/inventory/{item_id}/add-stock")
def add_stock(
    item_id: int,
    payload: StockDeltaIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    branch_id = _resolve_branch_id(current_user, payload.branch_id)
    if item.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    previous_qty = float(item.current_qty)
    new_qty = previous_qty + payload.quantity
    item.current_qty = new_qty

    db.add(
        InventoryStockMovement(
            branch_id=branch_id,
            inventory_item_id=item.id,
            movement_type="add_stock",
            quantity=payload.quantity,
            previous_qty=previous_qty,
            new_qty=new_qty,
            meta={"notes": payload.notes},
            created_by=current_user.id,
        )
    )

    create_stock_purchase_expense(
        db,
        branch_id=branch_id,
        item_name=item.item_name,
        quantity=payload.quantity,
        unit_cost=item.unit_cost,
        notes=payload.notes,
        created_by=current_user.id,
        reference_id=f"inventory_add_stock:{item.id}:{int(datetime.utcnow().timestamp())}",
        payment_method="inventory",
    )
    db.commit()
    return {"message": "Stock added", "new_qty": new_qty}


@router.post("/api/inventory/{item_id}/consume")
def consume_stock(
    item_id: int,
    payload: StockDeltaIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    branch_id = _resolve_branch_id(current_user, payload.branch_id)
    if item.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    previous_qty = float(item.current_qty)
    if previous_qty < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    new_qty = previous_qty - payload.quantity
    item.current_qty = new_qty

    db.add(
        InventoryStockMovement(
            branch_id=branch_id,
            inventory_item_id=item.id,
            movement_type="consume",
            quantity=payload.quantity,
            previous_qty=previous_qty,
            new_qty=new_qty,
            meta={"notes": payload.notes},
            created_by=current_user.id,
        )
    )
    db.commit()
    return {"message": "Stock consumed", "new_qty": new_qty}


@router.get("/api/inventory/suppliers", response_model=List[SupplierOut])
def list_suppliers(
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, branch_id)
    return (
        db.query(Supplier)
        .filter(Supplier.branch_id == branch_id, Supplier.is_active == True)
        .order_by(Supplier.name.asc())
        .all()
    )


@router.post("/api/inventory/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, payload.branch_id)
    supplier = Supplier(
        branch_id=branch_id,
        name=payload.name,
        contact_person=payload.contact_person,
        phone=payload.phone,
        email=payload.email,
        address=payload.address,
        gstin=payload.gstin,
        created_by=current_user.id,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/api/inventory/equipment", response_model=List[EquipmentOut])
def list_equipment(
    department: Optional[InventoryDepartment] = Query(None),
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, branch_id)
    query = db.query(InventoryEquipment).filter(
        InventoryEquipment.branch_id == branch_id,
        InventoryEquipment.is_active == True,
    )
    if department:
        query = query.filter(InventoryEquipment.department == department.value)

    equipment = query.order_by(InventoryEquipment.machine_name.asc()).all()
    due_cutoff = date.today() + timedelta(days=7)
    result: List[EquipmentOut] = []
    for item in equipment:
        result.append(
            EquipmentOut(
                id=item.id,
                branch_id=item.branch_id,
                department=InventoryDepartment(item.department),
                machine_name=item.machine_name,
                brand_model=item.brand_model,
                serial_number=item.serial_number,
                purchase_date=item.purchase_date,
                warranty_end_date=item.warranty_end_date,
                amc_company=item.amc_company,
                dealer_contact=item.dealer_contact,
                last_service_date=item.last_service_date,
                next_service_due_date=item.next_service_due_date,
                is_service_due_soon=bool(item.next_service_due_date and item.next_service_due_date <= due_cutoff),
            )
        )
    return result


@router.post("/api/inventory/equipment", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, payload.branch_id)
    equipment = InventoryEquipment(
        branch_id=branch_id,
        department=payload.department.value,
        machine_name=payload.machine_name,
        brand_model=payload.brand_model,
        serial_number=payload.serial_number,
        purchase_date=payload.purchase_date,
        warranty_end_date=payload.warranty_end_date,
        amc_company=payload.amc_company,
        dealer_contact=payload.dealer_contact,
        last_service_date=payload.last_service_date,
        next_service_due_date=payload.next_service_due_date,
        created_by=current_user.id,
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)

    return EquipmentOut(
        id=equipment.id,
        branch_id=equipment.branch_id,
        department=InventoryDepartment(equipment.department),
        machine_name=equipment.machine_name,
        brand_model=equipment.brand_model,
        serial_number=equipment.serial_number,
        purchase_date=equipment.purchase_date,
        warranty_end_date=equipment.warranty_end_date,
        amc_company=equipment.amc_company,
        dealer_contact=equipment.dealer_contact,
        last_service_date=equipment.last_service_date,
        next_service_due_date=equipment.next_service_due_date,
        is_service_due_soon=bool(
            equipment.next_service_due_date and equipment.next_service_due_date <= (date.today() + timedelta(days=7))
        ),
    )


@router.post("/api/inventory/equipment/{equipment_id}/service-log")
def log_service(
    equipment_id: int,
    payload: ServiceLogIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    equipment = (
        db.query(InventoryEquipment)
        .filter(InventoryEquipment.id == equipment_id, InventoryEquipment.is_active == True)
        .first()
    )
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    branch_id = _resolve_branch_id(current_user, payload.branch_id)
    if equipment.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    equipment.last_service_date = payload.service_date
    equipment.next_service_due_date = payload.service_date + timedelta(days=180)

    db.add(
        EquipmentServiceLog(
            equipment_id=equipment.id,
            branch_id=branch_id,
            service_date=payload.service_date,
            notes=payload.notes,
            created_by=current_user.id,
        )
    )
    db.commit()

    return {"message": "Service logged", "next_service_due_date": equipment.next_service_due_date}


@router.get("/api/inventory/consumption-history")
def get_consumption_history(
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, branch_id)
    history = (
        db.query(InventoryConsumptionHistory)
        .filter(InventoryConsumptionHistory.branch_id == branch_id)
        .order_by(InventoryConsumptionHistory.consumed_on.desc())
        .limit(500)
        .all()
    )

    response: List[Dict[str, Any]] = []
    for row in history:
        response.append(
            {
                "id": row.id,
                "daily_entry_id": row.daily_entry_id,
                "patient_identifier": row.patient_identifier,
                "test_name": row.test_name,
                "item_deducted": row.item.item_name if row.item else None,
                "quantity": float(row.quantity),
                "consumed_on": row.consumed_on,
            }
        )
    return response


@router.get("/api/inventory/alerts")
def get_inventory_alerts(
    branch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, branch_id)
    today = date.today()
    soon_cutoff = today + timedelta(days=30)

    items = db.query(InventoryItem).filter(InventoryItem.branch_id == branch_id, InventoryItem.is_active == True).all()

    low_stock = [
        {
            "item_id": i.id,
            "item_name": i.item_name,
            "current_qty": float(i.current_qty),
            "min_threshold": float(i.min_threshold),
        }
        for i in items
        if float(i.current_qty) < float(i.min_threshold)
    ]
    expiring = [
        {
            "item_id": i.id,
            "item_name": i.item_name,
            "expiry_date": i.expiry_date,
        }
        for i in items
        if i.expiry_date and i.expiry_date <= soon_cutoff
    ]

    return {
        "low_stock": low_stock,
        "expiring_soon": expiring,
        "low_stock_count": len(low_stock),
        "expiring_soon_count": len(expiring),
    }


@router.post("/api/inventory/audit", status_code=status.HTTP_201_CREATED)
def manual_stock_audit(
    payload: ManualAuditIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_inventory_role),
):
    branch_id = _resolve_branch_id(current_user, payload.branch_id)
    item = db.query(InventoryItem).filter(InventoryItem.id == payload.item_id, InventoryItem.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if item.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Access denied")

    expected = float(item.current_qty)
    discrepancy = payload.physical_qty - expected

    db.add(
        InventoryStockAudit(
            branch_id=branch_id,
            inventory_item_id=item.id,
            expected_qty=expected,
            physical_qty=payload.physical_qty,
            discrepancy=discrepancy,
            notes=payload.notes,
            created_by=current_user.id,
        )
    )

    if discrepancy != 0:
        item.current_qty = payload.physical_qty
        db.add(
            InventoryStockMovement(
                branch_id=branch_id,
                inventory_item_id=item.id,
                movement_type="audit_adjustment",
                quantity=abs(discrepancy),
                previous_qty=expected,
                new_qty=float(payload.physical_qty),
                meta={"notes": payload.notes, "discrepancy": discrepancy},
                created_by=current_user.id,
            )
        )

    db.commit()
    return {
        "message": "Audit saved",
        "expected_qty": expected,
        "physical_qty": payload.physical_qty,
        "discrepancy": discrepancy,
    }
