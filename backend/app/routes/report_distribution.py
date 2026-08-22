"""
Order Distribution Routes for VaidyaVihar Diagnostic ERP

Provides automatic report distribution to staff across all branches:
- Automatic report delivery to referring staff
- Multi-channel notification (SMS, WhatsApp, Email, Portal)
- Real-time WebSocket alerts
- Delivery tracking and confirmation
- Staff acknowledgment system
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid
import random
import json

from app.database import get_db
from app.utils.auth_system import auth_guard, require_staff, get_current_user, require_role
from app.models import User, Branch, Customer, LabResult
from app.models.staff import (
    Staff, StaffBranch, OrderDistribution, OrderTemplate, 
    StaffNotification
)
from app.services.websocket_service import connection_manager, NotificationFactory
from app.services.sms_service import get_sms_service
from app.services.whatsapp_service import get_whatsapp_service
from app.services.email_service import get_email_service

router = APIRouter()


# ============ Pydantic Schemas ============

class OrderDistributionCreate(BaseModel):
    """Schema for creating report distribution"""
    lab_result_id: int
    doctor_ids: Optional[List[int]] = None  # If None, auto-distribute to referring staff
    priority: str = Field("normal", pattern="^(normal|high|urgent)$")
    delivery_methods: Optional[List[str]] = ["portal", "email", "sms", "whatsapp"]
    force_delivery: bool = False  # Force delivery even if not referring doctor


class OrderDistributionResponse(BaseModel):
    """Order distribution response"""
    id: int
    distribution_id: str
    lab_result_id: int
    doctor_id: int
    report_type: str
    report_name: str
    delivery_status: str
    delivery_method: Optional[str]
    priority: str
    created_at: datetime
    viewed_at: Optional[datetime]
    downloaded_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class DistributionSummary(BaseModel):
    """Summary of report distribution"""
    total_distributions: int
    pending: int
    sent: int
    delivered: int
    read: int
    failed: int


# ============ Helper Functions ============

def generate_distribution_id():
    """Generate unique distribution ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_num = random.randint(1000, 9999)
    return f"RD-{timestamp}-{random_num}"


async def distribute_report_to_doctor(
    db: Session,
    lab_result: LabResult,
    doctor: Staff,
    branch_id: int,
    delivery_methods: List[str],
    priority: str,
    created_by: int
) -> OrderDistribution:
    """Distribute a report to a single doctor"""
    
    # Check if already distributed
    existing = db.query(OrderDistribution).filter(
        and_(
            OrderDistribution.lab_result_id == lab_result.id,
            OrderDistribution.doctor_id == doctor.id
        )
    ).first()
    
    if existing and not existing.delivery_status == "failed":
        return existing
    
    # Determine delivery method
    delivery_method = delivery_methods[0] if delivery_methods else "portal"
    
    # Create distribution record
    distribution = OrderDistribution(
        distribution_id=generate_distribution_id(),
        lab_result_id=lab_result.id,
        patient_id=lab_result.patient_id,
        branch_id=branch_id,
        doctor_id=doctor.id,
        report_type=lab_result.test_category,
        report_name=lab_result.test_name,
        delivery_status="pending",
        delivery_method=delivery_method,
        priority=priority,
        created_by=created_by,
        is_urgent=priority == "urgent"
    )
    
    db.add(distribution)
    db.commit()
    db.refresh(distribution)
    
    # Send notifications via all channels
    await send_report_notifications(db, lab_result, doctor, distribution, delivery_methods)
    
    return distribution


async def send_report_notifications(
    db: Session,
    lab_result: LabResult,
    doctor: Staff,
    distribution: OrderDistribution,
    delivery_methods: List[str]
):
    """Send notifications to doctor via all configured channels"""
    
    # Get patient info
    patient = db.query(Customer).filter(Customer.id == lab_result.patient_id).first()
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
    
    # Generate report URL
    report_url = f"/doctor-portal/orders/{distribution.id}"
    
    # 1. Send Portal Notification (WebSocket)
    notification = NotificationFactory.create_report_ready_notification(
        patient_name=patient_name,
        report_id=str(distribution.id),
        report_type=lab_result.test_category,
        branch_id=distribution.branch_id,
        doctor_id=doctor.id
    )
    await connection_manager.send_personal_notification(doctor.id, notification)
    
    # 2. Send Email
    if "email" in delivery_methods and doctor.notification_preferences.get("email", True):
        email_service = get_email_service()
        await email_service.send_report_ready(
            email=doctor.email,
            patient_name=patient_name,
            report_id=distribution.distribution_id
        )
        distribution.email_sent = True
        distribution.email_sent_at = datetime.utcnow()
    
    # 3. Send SMS
    if "sms" in delivery_methods and doctor.notification_preferences.get("sms", True):
        sms_service = get_sms_service()
        await sms_service.send_doctor_report_notification(
            to=doctor.phone,
            doctor_name=f"{doctor.first_name} {doctor.last_name}",
            patient_name=patient_name,
            report_type=lab_result.test_category,
            is_urgent=distribution.is_urgent
        )
        distribution.sms_sent = True
        distribution.sms_sent_at = datetime.utcnow()
    
    # 4. Send WhatsApp
    if "whatsapp" in delivery_methods and doctor.notification_preferences.get("whatsapp", True):
        whatsapp_service = get_whatsapp_service()
        await whatsapp_service.send_report_to_doctor(
            to=doctor.phone,
            doctor_name=f"{doctor.first_name} {doctor.last_name}",
            patient_name=patient_name,
            patient_age=str(patient.date_of_birth) if patient else "N/A",
            patient_gender=patient.gender if patient else "N/A",
            report_type=lab_result.test_category,
            report_summary=lab_result.interpretation or "See attached report",
            report_url=report_url,
            is_urgent=distribution.is_urgent
        )
        distribution.whatsapp_sent = True
        distribution.whatsapp_sent_at = datetime.utcnow()
    
    # 5. Send Push Notification
    if "push" in delivery_methods and doctor.notification_preferences.get("push", True):
        notification = StaffNotification(
            notification_id=f"NT-{uuid.uuid4().hex[:8].upper()}",
            doctor_id=doctor.id,
            notification_type="report_ready",
            title="New Order Available",
            message=f"New {lab_result.test_category} report for {patient_name}",
            channel="push",
            status="sent",
            sent_at=datetime.utcnow(),
            priority=distribution.priority,
            action_url=report_url,
            reference_id=str(distribution.id),
            reference_type="report_distribution"
        )
        db.add(notification)
        distribution.push_sent = True
        distribution.push_sent_at = datetime.utcnow()
    
    # Update distribution status
    distribution.delivery_status = "sent"
    distribution.sent_at = datetime.utcnow()
    
    db.commit()


# ============ Order Distribution Routes ============

@router.post("/orders/distribute")
async def distribute_report(
    distribution_data: OrderDistributionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Distribute a lab report to staff.
    
    If doctor_ids is not provided, automatically distributes to:
    1. Referring doctor (from lab result)
    2. All staff who have seen this patient before
    3. All staff in the patient's assigned branches
    """
    
    # Get lab result
    lab_result = db.query(LabResult).filter(LabResult.id == distribution_data.lab_result_id).first()
    
    if not lab_result:
        raise HTTPException(status_code=404, detail="Lab result not found")
    
    # Get patient
    patient = db.query(Customer).filter(Customer.id == lab_result.patient_id).first()
    
    # Determine which staff to distribute to
    doctor_ids = distribution_data.doctor_ids or []
    
    if not doctor_ids:
        # Auto-distribute logic
        
        # 1. Get referring doctor from lab result
        if lab_result.requested_by:
            referring_doc = db.query(Staff).filter(
                or_(
                    Staff.full_name.ilike(f"%{lab_result.requested_by}%"),
                    Staff.first_name.ilike(f"%{lab_result.requested_by}%")
                )
            ).first()
            if referring_doc and referring_doc.id not in doctor_ids:
                doctor_ids.append(referring_doc.id)
        
        # 2. Get staff who have received orders for this patient before
        previous_distributions = db.query(OrderDistribution.doctor_id).filter(
            OrderDistribution.patient_id == lab_result.patient_id
        ).distinct().all()
        for (doc_id,) in previous_distributions:
            if doc_id not in doctor_ids:
                doctor_ids.append(doc_id)
        
        # 3. Get staff in the patient's branch
        patient_branches = db.query(StaffBranch).filter(
            and_(
                StaffBranch.branch_id == patient.branch_id,
                StaffBranch.is_active == True,
                StaffBranch.receive_all_orders == True
            )
        ).all()
        for db_branch in patient_branches:
            if db_branch.doctor_id not in doctor_ids:
                doctor_ids.append(db_branch.doctor_id)
    
    # If still no staff, return warning
    if not doctor_ids:
        return {
            "message": "No staff found for automatic distribution",
            "lab_result_id": lab_result.id,
            "status": "no_recipients"
        }
    
    # Distribute to each doctor
    distributions = []
    for doctor_id in doctor_ids:
        doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
        if doctor and doctor.is_active:
            try:
                distribution = await distribute_report_to_doctor(
                    db=db,
                    lab_result=lab_result,
                    doctor=doctor,
                    branch_id=lab_result.branch_id,
                    delivery_methods=distribution_data.delivery_methods,
                    priority=distribution_data.priority,
                    created_by=current_user.id
                )
                distributions.append(distribution.id)
            except Exception as e:
                print(f"Error distributing to doctor {doctor_id}: {e}")
    
    return {
        "message": "Order distributed successfully",
        "lab_result_id": lab_result.id,
        "report_name": lab_result.test_name,
        "distributions_count": len(distributions),
        "distribution_ids": distributions
    }


@router.post("/orders/distribute-to-all-branches")
async def distribute_report_to_all_relevant_staff(
    lab_result_id: int,
    delivery_methods: Optional[List[str]] = Query(["portal", "email"]),
    priority: str = Query("normal", pattern="^(normal|high|urgent)$"),
    current_user: User = Depends(require_role(["admin", "branch_admin"])),
    db: Session = Depends(get_db)
):
    """
    Distribute a report to ALL staff across ALL branches.
    Useful for critical/special orders that all staff should see.
    """
    
    lab_result = db.query(LabResult).filter(LabResult.id == lab_result_id).first()
    
    if not lab_result:
        raise HTTPException(status_code=404, detail="Lab result not found")
    
    # Get all active staff
    all_staff = db.query(Staff).filter(Staff.is_active == True).all()
    
    # Get patient info
    patient = db.query(Customer).filter(Customer.id == lab_result.patient_id).first()
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
    
    distributions = []
    for doctor in all_staff:
        if doctor.notification_preferences.get("report_ready", True):
            distribution = await distribute_report_to_doctor(
                db=db,
                lab_result=lab_result,
                doctor=doctor,
                branch_id=lab_result.branch_id,
                delivery_methods=delivery_methods,
                priority=priority,
                created_by=current_user.id
            )
            distributions.append(distribution.id)
    
    return {
        "message": "Order distributed to all staff",
        "lab_result_id": lab_result_id,
        "total_staff_notified": len(distributions),
        "distributions": distributions
    }


@router.get("/orders/distributions/")
def get_distributions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    doctor_id: Optional[int] = Query(None),
    lab_result_id: Optional[int] = Query(None),
    delivery_status: Optional[str] = Query(None),
    report_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get list of report distributions with filtering"""
    
    query = db.query(OrderDistribution)
    
    # Apply filters
    if doctor_id:
        query = query.filter(OrderDistribution.doctor_id == doctor_id)
    if lab_result_id:
        query = query.filter(OrderDistribution.lab_result_id == lab_result_id)
    if delivery_status:
        query = query.filter(OrderDistribution.delivery_status == delivery_status)
    if report_type:
        query = query.filter(OrderDistribution.report_type == report_type)
    if start_date:
        query = query.filter(OrderDistribution.created_at >= start_date)
    if end_date:
        query = query.filter(OrderDistribution.created_at <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    distributions = query.order_by(desc(OrderDistribution.created_at)).offset(skip).limit(limit).all()
    
    return {
        "distributions": distributions,
        "total": total,
        "page": skip // limit + 1,
        "limit": limit
    }


@router.get("/orders/distribution/{distribution_id}")
def get_distribution(
    distribution_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get report distribution details"""
    distribution = db.query(OrderDistribution).filter(
        OrderDistribution.id == distribution_id
    ).first()
    
    if not distribution:
        raise HTTPException(status_code=404, detail="Distribution not found")
    
    # Get doctor info
    doctor = db.query(Staff).filter(Staff.id == distribution.doctor_id).first()
    
    # Get lab result info
    lab_result = db.query(LabResult).filter(LabResult.id == distribution.lab_result_id).first()
    
    # Get patient info
    patient = db.query(Customer).filter(Customer.id == distribution.patient_id).first()
    
    return {
        "distribution": distribution,
        "doctor": {
            "id": doctor.id,
            "name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else None,
            "specialization": doctor.specialization if doctor else None,
            "email": doctor.email if doctor else None,
            "phone": doctor.phone if doctor else None
        },
        "patient": {
            "id": patient.id,
            "name": f"{patient.first_name} {patient.last_name}" if patient else None,
            "phone": patient.phone if patient else None
        },
        "lab_result": {
            "id": lab_result.id,
            "test_name": lab_result.test_name,
            "test_category": lab_result.test_category,
            "status": lab_result.status if lab_result else None
        } if lab_result else None
    }


@router.get("/orders/pending-for-doctor/{doctor_id}")
def get_pending_orders_for_doctor(
    doctor_id: int,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get pending orders for a specific doctor"""
    
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get pending distributions
    distributions = db.query(OrderDistribution).filter(
        and_(
            OrderDistribution.doctor_id == doctor_id,
            OrderDistribution.delivery_status.in_(["pending", "sent", "delivered"])
        )
    ).order_by(
        desc(OrderDistribution.priority),
        desc(OrderDistribution.created_at)
    ).limit(limit).all()
    
    # Get unread count
    unread_count = db.query(func.count(OrderDistribution.id)).filter(
        and_(
            OrderDistribution.doctor_id == doctor_id,
            OrderDistribution.delivery_status.in_(["pending", "sent", "delivered"])
        )
    ).scalar()
    
    result = []
    for dist in distributions:
        lab_result = db.query(LabResult).filter(LabResult.id == dist.lab_result_id).first()
        patient = db.query(Customer).filter(Customer.id == dist.patient_id).first()
        
        result.append({
            "distribution_id": dist.id,
            "distribution_uuid": dist.distribution_id,
            "report_type": dist.report_type,
            "report_name": dist.report_name,
            "priority": dist.priority,
            "delivery_status": dist.delivery_status,
            "created_at": dist.created_at,
            "patient": {
                "name": f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                "phone": patient.phone if patient else None
            } if patient else None,
            "lab_result": {
                "id": lab_result.id,
                "test_name": lab_result.test_name,
                "result_date": lab_result.result_date if lab_result else None
            } if lab_result else None
        })
    
    return {
        "doctor": {
            "id": doctor.id,
            "name": f"Dr. {doctor.first_name} {doctor.last_name}"
        },
        "pending_count": unread_count or 0,
        "orders": result
    }


@router.post("/orders/{distribution_id}/acknowledge")
async def acknowledge_report(
    distribution_id: int,
    action: str = Query("view", pattern="^(view|download|print|acknowledge)$"),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Acknowledge that a doctor has viewed/downloaded a report"""
    
    distribution = db.query(OrderDistribution).filter(
        OrderDistribution.id == distribution_id
    ).first()
    
    if not distribution:
        raise HTTPException(status_code=404, detail="Distribution not found")
    
    now = datetime.utcnow()
    
    if action == "view":
        distribution.viewed_at = now
        if distribution.delivery_status in ["pending", "sent"]:
            distribution.delivery_status = "delivered"
    elif action == "download":
        distribution.downloaded_at = now
        distribution.delivery_status = "read"
    elif action == "print":
        distribution.printed_at = now
    elif action == "acknowledge":
        distribution.acknowledged_at = now
        distribution.delivery_status = "read"
    
    db.commit()
    
    return {
        "message": f"Order {action} acknowledged",
        "distribution_id": distribution_id,
        "action": action,
        "timestamp": now
    }


@router.get("/orders/distribution/summary")
def get_distribution_summary(
    doctor_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_role(["admin", "branch_admin"])),
    db: Session = Depends(get_db)
):
    """Get summary statistics for report distributions"""
    
    query = db.query(OrderDistribution)
    
    if doctor_id:
        query = query.filter(OrderDistribution.doctor_id == doctor_id)
    if branch_id:
        query = query.filter(OrderDistribution.branch_id == branch_id)
    if start_date:
        query = query.filter(OrderDistribution.created_at >= start_date)
    if end_date:
        query = query.filter(OrderDistribution.created_at <= end_date)
    
    total = query.count()
    
    # Status breakdown
    pending = query.filter(OrderDistribution.delivery_status == "pending").count()
    sent = query.filter(OrderDistribution.delivery_status == "sent").count()
    delivered = query.filter(OrderDistribution.delivery_status == "delivered").count()
    read = query.filter(OrderDistribution.delivery_status == "read").count()
    failed = query.filter(OrderDistribution.delivery_status == "failed").count()
    
    # By report type
    by_type = db.query(
        OrderDistribution.report_type,
        func.count(OrderDistribution.id)
    ).filter(
        OrderDistribution.created_at >= (start_date or datetime.utcnow() - timedelta(days=30))
    ).group_by(OrderDistribution.report_type).all()
    
    return {
        "summary": {
            "total_distributions": total,
            "pending": pending,
            "sent": sent,
            "delivered": delivered,
            "read": read,
            "failed": failed,
            "delivery_rate": round((read + delivered) / total * 100, 2) if total > 0 else 0
        },
        "by_type": [
            {"report_type": rpt_type, "count": count}
            for rpt_type, count in by_type
        ],
        "date_range": {
            "start_date": start_date,
            "end_date": end_date
        }
    }


@router.get("/orders/doctor-activity/{doctor_id}")
def get_doctor_report_activity(
    doctor_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get report activity for a specific doctor"""
    
    doctor = db.query(Staff).filter(Staff.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get distribution counts by status
    status_counts = db.query(
        OrderDistribution.delivery_status,
        func.count(OrderDistribution.id)
    ).filter(
        and_(
            OrderDistribution.doctor_id == doctor_id,
            OrderDistribution.created_at >= start_date
        )
    ).group_by(OrderDistribution.delivery_status).all()
    
    # Get recent activity
    recent = db.query(OrderDistribution).filter(
        and_(
            OrderDistribution.doctor_id == doctor_id,
            OrderDistribution.created_at >= start_date
        )
    ).order_by(desc(OrderDistribution.created_at)).limit(50).all()
    
    # Daily breakdown for charts
    daily = db.query(
        func.date(OrderDistribution.created_at).label("date"),
        func.count(OrderDistribution.id).label("count")
    ).filter(
        and_(
            OrderDistribution.doctor_id == doctor_id,
            OrderDistribution.created_at >= start_date
        )
    ).group_by("date").order_by("date").all()
    
    return {
        "doctor": {
            "id": doctor.id,
            "name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "specialization": doctor.specialization
        },
        "period_days": days,
        "status_breakdown": {
            status: count for status, count in status_counts
        },
        "daily_activity": [
            {"date": str(d[0]), "count": d[1]}
            for d in daily
        ],
        "recent_orders": [
            {
                "id": r.id,
                "report_name": r.report_name,
                "report_type": r.report_type,
                "status": r.delivery_status,
                "created_at": r.created_at,
                "viewed_at": r.viewed_at,
                "downloaded_at": r.downloaded_at
            }
            for r in recent
        ]
    }


@router.post("/orders/{distribution_id}/send-reminder")
async def send_report_reminder(
    distribution_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Send a reminder notification for a pending report"""
    
    distribution = db.query(OrderDistribution).filter(
        OrderDistribution.id == distribution_id
    ).first()
    
    if not distribution:
        raise HTTPException(status_code=404, detail="Distribution not found")
    
    doctor = db.query(Staff).filter(Staff.id == distribution.doctor_id).first()
    lab_result = db.query(LabResult).filter(LabResult.id == distribution.lab_result_id).first()
    patient = db.query(Customer).filter(Customer.id == distribution.patient_id).first()
    
    if not doctor or not lab_result or not patient:
        raise HTTPException(status_code=404, detail="Related records not found")
    
    patient_name = f"{patient.first_name} {patient.last_name}"
    
    # Send reminder via all channels
    sms_service = get_sms_service()
    await sms_service.send_doctor_report_notification(
        to=doctor.phone,
        doctor_name=f"{doctor.first_name} {doctor.last_name}",
        patient_name=patient_name,
        report_type=lab_result.test_category,
        is_urgent=False
    )
    
    # Create notification record
    notification = StaffNotification(
        notification_id=f"NT-REM-{uuid.uuid4().hex[:8].upper()}",
        doctor_id=doctor.id,
        notification_type="report_reminder",
        title="Order Reminder",
        message=f"Reminder: {lab_result.test_name} report for {patient_name} is awaiting your review",
        channel="sms",
        status="sent",
        sent_at=datetime.utcnow(),
        priority="normal",
        reference_id=str(distribution.id),
        reference_type="report_distribution"
    )
    db.add(notification)
    db.commit()
    
    return {
        "message": "Reminder sent successfully",
        "distribution_id": distribution_id,
        "doctor_id": doctor.id
    }


@router.get("/orders/tracking/{lab_result_id}")
def track_report_distribution(
    lab_result_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Track all distributions for a specific lab result"""
    
    lab_result = db.query(LabResult).filter(LabResult.id == lab_result_id).first()
    
    if not lab_result:
        raise HTTPException(status_code=404, detail="Lab result not found")
    
    distributions = db.query(OrderDistribution).filter(
        OrderDistribution.lab_result_id == lab_result_id
    ).all()
    
    patient = db.query(Customer).filter(Customer.id == lab_result.patient_id).first()
    
    result = {
        "lab_result": {
            "id": lab_result.id,
            "test_name": lab_result.test_name,
            "test_category": lab_result.test_category,
            "status": lab_result.status,
            "result_date": lab_result.result_date
        },
        "patient": {
            "name": f"{patient.first_name} {patient.last_name}" if patient else None,
            "phone": patient.phone if patient else None
        } if patient else None,
        "distributions": []
    }
    
    for dist in distributions:
        doctor = db.query(Staff).filter(Staff.id == dist.doctor_id).first()
        
        result["distributions"].append({
            "distribution_id": dist.distribution_id,
            "doctor": {
                "name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else None,
                "specialization": doctor.specialization if doctor else None
            },
            "delivery_status": dist.delivery_status,
            "email_sent": dist.email_sent,
            "sms_sent": dist.sms_sent,
            "whatsapp_sent": dist.whatsapp_sent,
            "viewed_at": dist.viewed_at,
            "downloaded_at": dist.downloaded_at,
            "created_at": dist.created_at
        })
    
    return result

