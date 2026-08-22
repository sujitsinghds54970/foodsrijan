"""
Staff Portal Routes for VaidyaVihar Diagnostic ERP

Staff self-service endpoints:
- Staff dashboard
- View assigned customers
- View patient orders
- Prescription management
- Schedule management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.patient_portal import CustomerAppointment, CustomerPrescription, PrescriptionMedication

router = APIRouter()


# Pydantic Schemas
class PrescriptionCreate(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    doctor_id: int
    diagnosis: Optional[str] = None
    medications: List[dict]
    follow_up_date: Optional[datetime] = None
    next_visit_instructions: Optional[str] = None


class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


# Staff Dashboard
@router.get("/dashboard/{doctor_id}")
async def get_doctor_dashboard(doctor_id: int, db: Session = Depends(get_db)):
    """Get doctor dashboard data"""
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    # Today's appointments
    today_appointments = db.query(CustomerAppointment).filter(
        CustomerAppointment.doctor_id == doctor_id,
        CustomerAppointment.appointment_date.between(start_of_day, end_of_day)
    ).all()
    
    # Upcoming appointments
    upcoming = db.query(CustomerAppointment).filter(
        CustomerAppointment.doctor_id == doctor_id,
        CustomerAppointment.appointment_date > end_of_day,
        CustomerAppointment.status.in_(["pending", "confirmed"])
    ).order_by(CustomerAppointment.appointment_date).limit(10).all()
    
    # Total customers this month
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    
    monthly_customers = db.query(CustomerAppointment).filter(
        CustomerAppointment.doctor_id == doctor_id,
        CustomerAppointment.appointment_date >= month_start_dt,
        CustomerAppointment.status == "completed"
    ).count()
    
    return {
        "success": True,
        "dashboard": {
            "today_appointments": len(today_appointments),
            "completed_today": sum(1 for apt in today_appointments if apt.status == "completed"),
            "upcoming_count": len(upcoming),
            "monthly_customers": monthly_customers,
            "today_appointments_list": [
                {
                    "id": apt.id,
                    "appointment_number": apt.appointment_number,
                    "appointment_date": apt.appointment_date.isoformat(),
                    "appointment_time": apt.appointment_time,
                    "status": apt.status,
                    "chief_complaint": apt.chief_complaint
                }
                for apt in today_appointments
            ],
            "upcoming_appointments": [
                {
                    "id": apt.id,
                    "appointment_number": apt.appointment_number,
                    "appointment_date": apt.appointment_date.isoformat(),
                    "appointment_time": apt.appointment_time,
                    "status": apt.status
                }
                for apt in upcoming
            ]
        }
    }


# Appointments
@router.get("/appointments/{doctor_id}")
async def list_doctor_appointments(
    doctor_id: int,
    date: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List doctor's appointments"""
    query = db.query(CustomerAppointment).filter(
        CustomerAppointment.doctor_id == doctor_id
    )
    
    if date:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        start = datetime.combine(date_obj.date(), datetime.min.time())
        end = datetime.combine(date_obj.date(), datetime.max.time())
        query = query.filter(CustomerAppointment.appointment_date.between(start, end))
    
    if status:
        query = query.filter(CustomerAppointment.status == status)
    
    appointments = query.order_by(
        CustomerAppointment.appointment_date.asc()
    ).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "appointments": [
            {
                "id": apt.id,
                "appointment_number": apt.appointment_number,
                "patient_id": apt.patient_id,
                "appointment_date": apt.appointment_date.isoformat(),
                "appointment_time": apt.appointment_time,
                "appointment_type": apt.appointment_type,
                "status": apt.status,
                "chief_complaint": apt.chief_complaint,
                "notes": apt.notes
            }
            for apt in appointments
        ]
    }


@router.get("/appointments/today/{doctor_id}")
async def get_today_appointments(doctor_id: int, db: Session = Depends(get_db)):
    """Get today's appointments for doctor"""
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    appointments = db.query(CustomerAppointment).filter(
        CustomerAppointment.doctor_id == doctor_id,
        CustomerAppointment.appointment_date.between(start_of_day, end_of_day)
    ).order_by(CustomerAppointment.appointment_time).all()
    
    return {
        "success": True,
        "appointments": [
            {
                "id": apt.id,
                "appointment_number": apt.appointment_number,
                "patient_id": apt.patient_id,
                "appointment_time": apt.appointment_time,
                "appointment_type": apt.appointment_type,
                "status": apt.status,
                "chief_complaint": apt.chief_complaint
            }
            for apt in appointments
        ]
    }


@router.put("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    db: Session = Depends(get_db)
):
    """Update appointment status"""
    appointment = db.query(CustomerAppointment).filter(
        CustomerAppointment.id == appointment_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment_data.status:
        appointment.status = appointment_data.status
    if appointment_data.notes is not None:
        appointment.notes = appointment_data.notes
    
    db.commit()
    
    return {
        "success": True,
        "appointment": {
            "id": appointment.id,
            "status": appointment.status,
            "notes": appointment.notes
        }
    }


# Customer Records
@router.get("/customers/{doctor_id}")
async def list_doctor_customers(
    doctor_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all customers for a doctor"""
    appointments = db.query(CustomerAppointment).filter(
        CustomerAppointment.doctor_id == doctor_id
    ).distinct(CustomerAppointment.patient_id).all()
    
    # Get unique patient IDs
    patient_ids = list(set(apt.patient_id for apt in appointments))
    
    return {
        "success": True,
        "patient_count": len(patient_ids),
        "message": f"Staff has {len(patient_ids)} unique customers"
    }


@router.get("/customers/{doctor_id}/{patient_id}/history")
async def get_patient_history(
    doctor_id: int,
    patient_id: int,
    db: Session = Depends(get_db)
):
    """Get patient's visit history with this doctor"""
    appointments = db.query(CustomerAppointment).filter(
        CustomerAppointment.doctor_id == doctor_id,
        CustomerAppointment.patient_id == patient_id
    ).order_by(CustomerAppointment.appointment_date.desc()).all()
    
    # Get prescriptions
    prescriptions = db.query(CustomerPrescription).filter(
        CustomerPrescription.doctor_id == doctor_id,
        CustomerPrescription.patient_id == patient_id
    ).order_by(CustomerPrescription.prescription_date.desc()).all()
    
    return {
        "success": True,
        "appointments": [
            {
                "id": apt.id,
                "appointment_number": apt.appointment_number,
                "appointment_date": apt.appointment_date.isoformat(),
                "appointment_type": apt.appointment_type,
                "status": apt.status,
                "chief_complaint": apt.chief_complaint,
                "notes": apt.notes
            }
            for apt in appointments
        ],
        "prescriptions": [
            {
                "id": rx.id,
                "prescription_date": rx.prescription_date.isoformat(),
                "diagnosis": rx.diagnosis,
                "follow_up_date": rx.follow_up_date.isoformat() if rx.follow_up_date else None
            }
            for rx in prescriptions
        ]
    }


# Prescriptions
@router.post("/prescriptions")
async def create_prescription(rx_data: PrescriptionCreate, db: Session = Depends(get_db)):
    """Create a new prescription"""
    prescription = CustomerPrescription(
        patient_id=rx_data.patient_id,
        appointment_id=rx_data.appointment_id,
        doctor_id=rx_data.doctor_id,
        diagnosis=rx_data.diagnosis,
        follow_up_date=rx_data.follow_up_date,
        next_visit_instructions=rx_data.next_visit_instructions
    )
    
    db.add(prescription)
    db.flush()
    
    # Add medications
    for med in rx_data.medications:
        medication = PrescriptionMedication(
            prescription_id=prescription.id,
            medicine_name=med.get("medicine_name"),
            dosage=med.get("dosage"),
            frequency=med.get("frequency"),
            duration=med.get("duration"),
            instructions=med.get("instructions"),
            medicine_type=med.get("medicine_type")
        )
        db.add(medication)
    
    db.commit()
    db.refresh(prescription)
    
    return {
        "success": True,
        "prescription": {
            "id": prescription.id,
            "patient_id": prescription.patient_id,
            "doctor_id": prescription.doctor_id,
            "diagnosis": prescription.diagnosis,
            "created_at": prescription.created_at.isoformat()
        }
    }


@router.get("/prescriptions/{doctor_id}")
async def list_prescriptions(
    doctor_id: int,
    patient_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List doctor's prescriptions"""
    query = db.query(CustomerPrescription).filter(
        CustomerPrescription.doctor_id == doctor_id
    )
    
    if patient_id:
        query = query.filter(CustomerPrescription.patient_id == patient_id)
    
    prescriptions = query.order_by(
        CustomerPrescription.prescription_date.desc()
    ).offset(skip).limit(limit).all()
    
    result = []
    for rx in prescriptions:
        medications = db.query(PrescriptionMedication).filter(
            PrescriptionMedication.prescription_id == rx.id
        ).all()
        
        result.append({
            "id": rx.id,
            "patient_id": rx.patient_id,
            "prescription_date": rx.prescription_date.isoformat(),
            "diagnosis": rx.diagnosis,
            "follow_up_date": rx.follow_up_date.isoformat() if rx.follow_up_date else None,
            "medications": [
                {
                    "medicine_name": m.medicine_name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "duration": m.duration
                }
                for m in medications
            ]
        })
    
    return {"success": True, "prescriptions": result}


@router.get("/prescriptions/{doctor_id}/{prescription_id}")
async def get_prescription(doctor_id: int, prescription_id: int, db: Session = Depends(get_db)):
    """Get prescription details"""
    prescription = db.query(CustomerPrescription).filter(
        CustomerPrescription.id == prescription_id,
        CustomerPrescription.doctor_id == doctor_id
    ).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    medications = db.query(PrescriptionMedication).filter(
        PrescriptionMedication.prescription_id == prescription_id
    ).all()
    
    return {
        "success": True,
        "prescription": {
            "id": prescription.id,
            "patient_id": prescription.patient_id,
            "appointment_id": prescription.appointment_id,
            "prescription_date": prescription.prescription_date.isoformat(),
            "diagnosis": prescription.diagnosis,
            "follow_up_date": prescription.follow_up_date.isoformat() if prescription.follow_up_date else None,
            "next_visit_instructions": prescription.next_visit_instructions,
            "medications": [
                {
                    "id": m.id,
                    "medicine_name": m.medicine_name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "duration": m.duration,
                    "instructions": m.instructions
                }
                for m in medications
            ]
        }
    }


# Orders Access
@router.get("/orders/{doctor_id}")
async def list_doctor_orders(
    doctor_id: int,
    patient_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List orders for doctor's customers"""
    # This would integrate with the LIS system
    # For now, return placeholder
    return {
        "success": True,
        "orders": [],
        "message": "Orders integration with LIS pending"
    }


# Statistics
@router.get("/statistics/{doctor_id}")
async def get_doctor_statistics(
    doctor_id: int,
    period: str = "month",
    db: Session = Depends(get_db)
):
    """Get doctor statistics"""
    today = datetime.now().date()
    
    if period == "today":
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    elif period == "week":
        start = datetime.combine(today - timedelta(days=7), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    elif period == "month":
        start = datetime.combine(today.replace(day=1), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    else:
        start = datetime.combine(today - timedelta(days=30), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
    
    appointments = db.query(CustomerAppointment).filter(
        CustomerAppointment.doctor_id == doctor_id,
        CustomerAppointment.appointment_date.between(start, end)
    ).all()
    
    completed = sum(1 for apt in appointments if apt.status == "completed")
    cancelled = sum(1 for apt in appointments if apt.status == "cancelled")
    no_show = sum(1 for apt in appointments if apt.status == "no_show")
    
    return {
        "success": True,
        "statistics": {
            "period": period,
            "total_appointments": len(appointments),
            "completed": completed,
            "cancelled": cancelled,
            "no_show": no_show,
            "pending": len(appointments) - completed - cancelled - no_show,
            "completion_rate": (completed / len(appointments) * 100) if appointments else 0
        }
    }

