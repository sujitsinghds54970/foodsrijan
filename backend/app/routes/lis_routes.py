"""
LIS (Laboratory Information System) Routes for VaidyaVihar Diagnostic ERP

Lab testing management endpoints:
- MenuItem orders
- Sample management
- Result entry
- Order generation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from app.database import get_db
from app.models.lis import (
    MenuItemOrder, MenuItemOrderItem, MenuItemStatus, Sample, SampleType,
    MenuItemResult, ResultFlag, MenuItemCategory, LabMenuItemMaster, GeneratedOrder
)

router = APIRouter()


# Pydantic Schemas
class MenuItemOrderCreate(BaseModel):
    patient_id: int
    referred_by: Optional[str] = None
    referred_by_id: Optional[int] = None
    priority: str = "routine"
    menu_items: List[dict]
    clinical_history: Optional[str] = None
    notes: Optional[str] = None
    branch_id: Optional[int] = None


class MenuItemResultCreate(BaseModel):
    order_item_id: int
    parameter_name: str
    result_value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    flag: str = "normal"
    notes: Optional[str] = None


class SampleCollect(BaseModel):
    order_id: int
    sample_type: str
    sample_volume: Optional[str] = None
    collection_notes: Optional[str] = None


class MenuItemMasterCreate(BaseModel):
    test_code: str
    test_name: str
    test_name_hindi: Optional[str] = None
    category: str
    sample_type: str
    base_price: float = 0
    discounted_price: float = 0
    turnaround_time_hours: int = 24
    is_urgent_available: bool = True
    method: Optional[str] = None
    parameters: Optional[List[dict]] = None


# Helper functions
def generate_order_number():
    """Generate unique order number"""
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = str(uuid.uuid4())[:6].upper()
    return f"ORD-{date_str}-{random_str}"


def generate_sample_id():
    """Generate unique sample ID"""
    return f"SMP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"


def generate_report_number():
    """Generate unique report number"""
    return f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"


# MenuItem Master Endpoints
@router.post("/test-master")
async def create_test_master(test_data: MenuItemMasterCreate, db: Session = Depends(get_db)):
    """Create a new test master entry"""
    test = LabMenuItemMaster(
        test_code=test_data.test_code,
        test_name=test_data.test_name,
        test_name_hindi=test_data.test_name_hindi,
        category=MenuItemCategory(test_data.category),
        sample_type=SampleType(test_data.sample_type),
        base_price=test_data.base_price,
        discounted_price=test_data.discounted_price,
        turnaround_time_hours=test_data.turnaround_time_hours,
        is_urgent_available=test_data.is_urgent_available,
        method=test_data.method,
        parameters=test_data.parameters
    )
    
    db.add(test)
    db.commit()
    db.refresh(test)
    
    return {
        "success": True,
        "test": {
            "id": test.id,
            "test_code": test.test_code,
            "test_name": test.test_name,
            "category": test.category.value if test.category else None,
            "base_price": test.base_price
        }
    }


@router.get("/test-master")
async def list_test_master(
    category: Optional[str] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List test master entries"""
    query = db.query(LabMenuItemMaster)
    
    if category:
        query = query.filter(LabMenuItemMaster.category == MenuItemCategory(category))
    
    query = query.filter(LabMenuItemMaster.is_active == is_active)
    
    menu_items = query.offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "menu_items": [
            {
                "id": t.id,
                "test_code": t.test_code,
                "test_name": t.test_name,
                "category": t.category.value if t.category else None,
                "sample_type": t.sample_type.value if t.sample_type else None,
                "base_price": t.base_price,
                "discounted_price": t.discounted_price,
                "turnaround_time_hours": t.turnaround_time_hours
            }
            for t in menu_items
        ]
    }


# MenuItem Order Endpoints
@router.post("/orders")
async def create_test_order(order_data: MenuItemOrderCreate, db: Session = Depends(get_db)):
    """Create a new test order"""
    # Generate order number
    order_number = generate_order_number()
    
    # Calculate total amount
    total_amount = sum(
        test.get("quantity", 1) * test.get("price", 0) 
        for test in order_data.menu_items
    )
    
    # Calculate expected delivery date
    max_turnaround = max(
        test.get("turnaround_time", 24) 
        for test in order_data.menu_items
    )
    expected_delivery = datetime.utcnow() + timedelta(hours=max_turnaround)
    
    # Create order
    test_order = MenuItemOrder(
        order_number=order_number,
        patient_id=order_data.patient_id,
        referred_by=order_data.referred_by,
        referred_by_id=order_data.referred_by_id,
        priority=order_data.priority,
        total_amount=total_amount,
        final_amount=total_amount,
        clinical_history=order_data.clinical_history,
        notes=order_data.notes,
        branch_id=order_data.branch_id,
        expected_delivery_date=expected_delivery
    )
    
    db.add(test_order)
    db.flush()
    
    # Add test items
    for test in order_data.menu_items:
        test_item = MenuItemOrderItem(
            order_id=test_order.id,
            test_master_id=test.get("test_master_id"),
            test_name=test.get("test_name"),
            test_code=test.get("test_code"),
            price=test.get("price", 0),
            final_price=test.get("quantity", 1) * test.get("price", 0),
            sample_type=SampleType(test.get("sample_type", "blood")) if test.get("sample_type") else None
        )
        db.add(test_item)
    
    db.commit()
    db.refresh(test_order)
    
    return {
        "success": True,
        "order": {
            "id": test_order.id,
            "order_number": test_order.order_number,
            "patient_id": test_order.patient_id,
            "total_amount": test_order.total_amount,
            "status": test_order.status.value if test_order.status else None,
            "expected_delivery": test_order.expected_delivery_date.isoformat() if test_order.expected_delivery_date else None,
            "created_at": test_order.created_at.isoformat()
        }
    }


@router.get("/orders")
async def list_test_orders(
    patient_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    branch_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List test orders"""
    query = db.query(MenuItemOrder)
    
    if patient_id:
        query = query.filter(MenuItemOrder.patient_id == patient_id)
    if status:
        query = query.filter(MenuItemOrder.status == MenuItemStatus(status))
    if priority:
        query = query.filter(MenuItemOrder.priority == priority)
    if branch_id:
        query = query.filter(MenuItemOrder.branch_id == branch_id)
    if start_date:
        query = query.filter(MenuItemOrder.order_date >= start_date)
    if end_date:
        query = query.filter(MenuItemOrder.order_date <= end_date)
    
    orders = query.order_by(MenuItemOrder.order_date.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "patient_id": o.patient_id,
                "referred_by": o.referred_by,
                "priority": o.priority,
                "total_amount": o.total_amount,
                "status": o.status.value if o.status else None,
                "order_date": o.order_date.isoformat(),
                "expected_delivery": o.expected_delivery_date.isoformat() if o.expected_delivery_date else None
            }
            for o in orders
        ]
    }


@router.get("/orders/{order_id}")
async def get_test_order(order_id: int, db: Session = Depends(get_db)):
    """Get test order details"""
    order = db.query(MenuItemOrder).filter(MenuItemOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="MenuItem order not found")
    
    items = db.query(MenuItemOrderItem).filter(MenuItemOrderItem.order_id == order_id).all()
    
    return {
        "success": True,
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "patient_id": order.patient_id,
            "referred_by": order.referred_by,
            "priority": order.priority,
            "total_amount": order.total_amount,
            "final_amount": order.final_amount,
            "status": order.status.value if order.status else None,
            "clinical_history": order.clinical_history,
            "notes": order.notes,
            "order_date": order.order_date.isoformat(),
            "expected_delivery": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
            "items": [
                {
                    "id": item.id,
                    "test_master_id": item.test_master_id,
                    "test_name": item.test_name,
                    "test_code": item.test_code,
                    "price": item.price,
                    "final_price": item.final_price,
                    "status": item.status.value if item.status else None,
                    "sample_id": item.sample_id
                }
                for item in items
            ]
        }
    }


@router.put("/orders/{order_id}/status")
async def update_order_status(order_id: int, new_status: str, db: Session = Depends(get_db)):
    """Update test order status"""
    order = db.query(MenuItemOrder).filter(MenuItemOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="MenuItem order not found")
    
    order.status = MenuItemStatus(new_status)
    
    # Update timestamps based on status
    if new_status == "sample_collected":
        order.sample_collection_date = datetime.utcnow()
    elif new_status == "sample_received":
        order.sample_received_date = datetime.utcnow()
    elif new_status == "delivered":
        order.delivery_date = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "order": {
            "id": order.id,
            "status": order.status.value if order.status else None
        }
    }


# Sample Endpoints
@router.post("/samples")
async def create_sample(sample_data: SampleCollect, db: Session = Depends(get_db)):
    """Record sample collection"""
    order = db.query(MenuItemOrder).filter(MenuItemOrder.id == sample_data.order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="MenuItem order not found")
    
    # Generate sample ID
    sample_id = generate_sample_id()
    
    sample = Sample(
        sample_id=sample_id,
        order_id=sample_data.order_id,
        sample_type=SampleType(sample_data.sample_type),
        sample_volume=sample_data.sample_volume,
        collected_at=datetime.utcnow(),
        collection_notes=sample_data.collection_notes,
        status="collected"
    )
    
    db.add(sample)
    
    # Update order status
    order.status = MenuItemStatus.SAMPLE_COLLECTED
    order.sample_collection_date = datetime.utcnow()
    
    db.commit()
    db.refresh(sample)
    
    return {
        "success": True,
        "sample": {
            "id": sample.id,
            "sample_id": sample.sample_id,
            "sample_type": sample.sample_type.value if sample.sample_type else None,
            "collected_at": sample.collected_at.isoformat(),
            "status": sample.status
        }
    }


# Result Entry Endpoints
@router.post("/results")
async def enter_test_result(result_data: MenuItemResultCreate, db: Session = Depends(get_db)):
    """Enter test result"""
    order_item = db.query(MenuItemOrderItem).filter(MenuItemOrderItem.id == result_data.order_item_id).first()
    
    if not order_item:
        raise HTTPException(status_code=404, detail="MenuItem order item not found")
    
    result = MenuItemResult(
        order_item_id=result_data.order_item_id,
        parameter_name=result_data.parameter_name,
        result_value=result_data.result_value,
        numeric_value=result_data.numeric_value,
        unit=result_data.unit,
        flag=ResultFlag(result_data.flag),
        notes=result_data.notes,
        entered_at=datetime.utcnow()
    )
    
    db.add(result)
    
    # Update order item status
    order_item.status = MenuItemStatus.RESULT_ENTERED
    order_item.result_entered_at = datetime.utcnow()
    
    db.commit()
    db.refresh(result)
    
    return {
        "success": True,
        "result": {
            "id": result.id,
            "parameter_name": result.parameter_name,
            "result_value": result.result_value,
            "flag": result.flag.value if result.flag else None,
            "entered_at": result.entered_at.isoformat()
        }
    }


@router.get("/orders/{order_id}/results")
async def get_order_results(order_id: int, db: Session = Depends(get_db)):
    """Get all results for an order"""
    items = db.query(MenuItemOrderItem).filter(MenuItemOrderItem.order_id == order_id).all()
    
    results = []
    for item in items:
        item_results = db.query(MenuItemResult).filter(MenuItemResult.order_item_id == item.id).all()
        results.append({
            "item_id": item.id,
            "test_name": item.test_name,
            "status": item.status.value if item.status else None,
            "results": [
                {
                    "id": r.id,
                    "parameter_name": r.parameter_name,
                    "result_value": r.result_value,
                    "numeric_value": r.numeric_value,
                    "unit": r.unit,
                    "flag": r.flag.value if r.flag else None,
                    "reference_range": r.reference_range,
                    "entered_at": r.entered_at.isoformat() if r.entered_at else None
                }
                for r in item_results
            ]
        })
    
    return {"success": True, "results": results}


@router.post("/orders/{order_id}/verify")
async def verify_order_results(order_id: int, db: Session = Depends(get_db)):
    """Verify all results for an order"""
    order = db.query(MenuItemOrder).filter(MenuItemOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="MenuItem order not found")
    
    items = db.query(MenuItemOrderItem).filter(MenuItemOrderItem.order_id == order_id).all()
    
    for item in items:
        item.status = MenuItemStatus.VERIFIED
        item.result_verified_at = datetime.utcnow()
    
    order.status = MenuItemStatus.VERIFIED
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Verified {len(items)} test items for order {order.order_number}"
    }


# Order Generation Endpoints
@router.post("/orders/{order_id}/generate-report")
async def generate_report(order_id: int, db: Session = Depends(get_db)):
    """Generate report for an order"""
    order = db.query(MenuItemOrder).filter(MenuItemOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="MenuItem order not found")
    
    # Check if all results are verified
    items = db.query(MenuItemOrderItem).filter(MenuItemOrderItem.order_id == order_id).all()
    
    for item in items:
        if item.status != MenuItemStatus.VERIFIED:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot generate report: {item.test_name} results not verified"
            )
    
    # Generate report number
    report_number = generate_report_number()
    
    report = GeneratedOrder(
        report_number=report_number,
        order_id=order_id,
        report_type="lab_report",
        status="generated"
    )
    
    db.add(report)
    
    # Update order status
    order.status = MenuItemStatus.REPORT_GENERATED
    
    db.commit()
    db.refresh(report)
    
    return {
        "success": True,
        "report": {
            "id": report.id,
            "report_number": report.report_number,
            "order_id": report.order_id,
            "status": report.status,
            "created_at": report.created_at.isoformat()
        }
    }


@router.get("/orders/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get report details"""
    report = db.query(GeneratedOrder).filter(GeneratedOrder.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "success": True,
        "report": {
            "id": report.id,
            "report_number": report.report_number,
            "order_id": report.order_id,
            "report_type": report.report_type,
            "status": report.status,
            "delivered_at": report.delivered_at.isoformat() if report.delivered_at else None,
            "created_at": report.created_at.isoformat()
        }
    }


# Statistics Endpoints
@router.get("/statistics")
async def get_lis_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get LIS statistics"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Count orders by status
    orders = db.query(MenuItemOrder).filter(
        MenuItemOrder.order_date.between(start_date, end_date)
    ).all()
    
    stats = {
        "total_orders": len(orders),
        "by_status": {},
        "by_priority": {},
        "total_revenue": sum(o.final_amount for o in orders)
    }
    
    for order in orders:
        status_key = order.status.value if order.status else "unknown"
        priority_key = order.priority
        
        stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1
        stats["by_priority"][priority_key] = stats["by_priority"].get(priority_key, 0) + 1
    
    return {"success": True, "statistics": stats}

