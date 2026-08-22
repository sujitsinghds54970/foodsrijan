"""
AI Routes for VaidyaVihar Diagnostic ERP

Provides AI-powered endpoints:
- MenuItem recommendations based on symptoms
- Risk assessment
- Predictive analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime

from app.database import get_db
from app.utils.auth_system import require_staff, get_current_user
from app.services.ai_service import (
    SymptomAnalyzer, PredictiveAnalytics, RiskAssessmentEngine,
    get_test_recommendations, assess_patient_risk, get_common_symptoms
)
from pydantic import BaseModel, Field

router = APIRouter()


# ============ Pydantic Schemas ============

class SymptomInput(BaseModel):
    """Symptom input for analysis"""
    name: str = Field(..., min_length=2, description="Symptom name")
    severity: str = Field("moderate", pattern="^(low|moderate|high|critical)$")
    duration_days: int = Field(1, ge=1, description="Duration in days")
    body_part: Optional[str] = Field(None, description="Affected body part")
    description: Optional[str] = Field(None, description="Additional description")


class MenuItemRecommendationRequest(BaseModel):
    """Request for test recommendations"""
    symptoms: List[SymptomInput]
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    medical_history: Optional[List[str]] = Field(default_factory=list)


class MenuItemRecommendationResponse(BaseModel):
    """MenuItem recommendation response"""
    recommendations: List[Dict]
    total_menu_items: int
    total_estimated_cost: float
    critical_menu_items: int
    moderate_menu_items: int
    routine_menu_items: int


class RiskAssessmentRequest(BaseModel):
    """Risk assessment request"""
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    medical_history: Optional[List[str]] = Field(default_factory=list)
    lab_results: Optional[Dict[str, float]] = Field(default_factory=dict)
    lifestyle_factors: Optional[Dict[str, str]] = Field(default_factory=dict)


class RiskAssessmentResponse(BaseModel):
    """Risk assessment response"""
    risk_score: int
    risk_level: str
    risk_factors: List[str]
    recommendations: List[str]
    follow_up_required: bool
    urgency: str


# ============ AI Routes ============

@router.post("/ai/test-recommendations")
def get_ai_test_recommendations(
    request: MenuItemRecommendationRequest,
    current_user = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered test recommendations based on symptoms.
    
    The AI analyzes:
    - Ordered symptoms and their severity
    - Customer age and gender
    - Medical history
    - Standard diagnostic protocols
    """
    # Convert symptoms to dict format
    symptoms = [
        {
            "name": s.name,
            "severity": s.severity,
            "duration_days": s.duration_days,
            "body_part": s.body_part,
            "description": s.description
        }
        for s in request.symptoms
    ]
    
    # Get recommendations
    recommendations = get_test_recommendations(
        symptoms=symptoms,
        age=request.age,
        gender=request.gender,
        medical_history=request.medical_history
    )
    
    # Calculate totals
    total_cost = sum(r.estimated_cost for r in recommendations)
    critical = sum(1 for r in recommendations if r.priority == "critical")
    moderate = sum(1 for r in recommendations if r.priority == "moderate")
    routine = len(recommendations) - critical - moderate
    
    return MenuItemRecommendationResponse(
        recommendations=[
            {
                "test_code": r.test_code,
                "test_name": r.test_name,
                "category": r.category,
                "priority": r.priority,
                "reason": r.reason,
                "estimated_cost": r.estimated_cost,
                "preparation_instructions": r.preparation_instructions
            }
            for r in recommendations
        ],
        total_menu_items=len(recommendations),
        total_estimated_cost=total_cost,
        critical_menu_items=critical,
        moderate_menu_items=moderate,
        routine_menu_items=routine
    )


@router.post("/ai/risk-assessment")
def get_ai_risk_assessment(
    request: RiskAssessmentRequest,
    current_user = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered patient risk assessment.
    
    The AI evaluates:
    - Age and gender
    - Medical history
    - Lab results
    - Lifestyle factors
    """
    assessment = assess_patient_risk(
        age=request.age,
        gender=request.gender,
        medical_history=request.medical_history,
        lab_results=request.lab_results,
        lifestyle=request.lifestyle_factors
    )
    
    return RiskAssessmentResponse(
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        risk_factors=assessment.risk_factors,
        recommendations=assessment.recommendations,
        follow_up_required=assessment.follow_up_required,
        urgency=assessment.urgency
    )


@router.get("/ai/common-symptoms")
def get_common_symptoms_list(
    current_user = Depends(require_staff)
):
    """
    Get list of common symptoms for the symptom checker UI.
    """
    symptoms = get_common_symptoms()
    return {"symptoms": symptoms}


@router.post("/ai/anomaly-detection")
def detect_lab_anomaly(
    test_name: str,
    value: float,
    historical_values: List[float],
    threshold: float = Query(2.0, ge=0.1, le=5.0),
    current_user = Depends(require_staff)
):
    """
    Detect if a lab result is anomalous based on historical data.
    """
    is_anomaly, z_score = PredictiveAnalytics.detect_anomaly(
        value=value,
        historical_values=historical_values,
        threshold=threshold
    )
    
    return {
        "test_name": test_name,
        "value": value,
        "is_anomaly": is_anomaly,
        "z_score": z_score,
        "threshold": threshold,
        "interpretation": (
            f"Value is {'anomalous' if is_anomaly else 'normal'} "
            f"({z_score} standard deviations from mean)"
        )
    }


@router.post("/ai/no-show-prediction")
def predict_no_show(
    patient_id: int,
    appointment_history: List[Dict],
    day_of_week: int,
    time_slot: str,
    current_user = Depends(require_staff)
):
    """
    Predict probability of patient no-show for an appointment.
    
    Args:
        patient_id: Customer ID
        appointment_history: List of past appointments with status
        day_of_week: Day of week (0=Monday, 6=Sunday)
        time_slot: Appointment time (HH:MM format)
    """
    probability = PredictiveAnalytics.predict_no_show_probability(
        patient_id=str(patient_id),
        appointment_history=appointment_history,
        day_of_week=day_of_week,
        time_slot=time_slot
    )
    
    # Calculate confidence level
    history_count = len(appointment_history)
    if history_count >= 10:
        confidence = "high"
    elif history_count >= 5:
        confidence = "medium"
    else:
        confidence = "low"
    
    return {
        "patient_id": patient_id,
        "no_show_probability": probability,
        "show_probability": round(1 - probability, 2),
        "confidence": confidence,
        "recommendations": [
            "Send reminder 24 hours before appointment" if probability > 0.2 else None,
            "Consider confirmation call for high-risk appointments" if probability > 0.3 else None,
            "Implement overbooking for high no-show probability slots" if probability > 0.4 else None
        ]
    }


@router.post("/ai/revenue-prediction")
def predict_revenue(
    branch_id: int,
    historical_data: List[Dict],
    days_ahead: int = Query(30, ge=1, le=90),
    current_user = Depends(require_staff)
):
    """
    Predict revenue for upcoming period based on historical data.
    """
    prediction = PredictiveAnalytics.predict_revenue(
        branch_id=str(branch_id),
        historical_data=historical_data,
        days_ahead=days_ahead
    )
    
    return {
        "branch_id": branch_id,
        "prediction_period_days": days_ahead,
        **prediction
    }


@router.get("/ai/diagnostic-protocol/{condition}")
def get_diagnostic_protocol(
    condition: str,
    current_user = Depends(require_staff)
):
    """
    Get standard diagnostic protocol for a condition.
    
    Returns recommended menu_items and workflow for a specific condition.
    """
    protocols = {
        "diabetes": {
            "screening_menu_items": ["FBS", "HbA1c", "PPBS"],
            "complication_menu_items": ["KFT", "LFT", "Lipid Profile", "Urine Routine", "Fundus Examination"],
            "follow_up_frequency": "Every 3 months for HbA1c",
            "lifestyle_recommendations": [
                "Monitor blood sugar daily",
                "Regular exercise",
                "Balanced diet",
                "Regular foot care"
            ]
        },
        "hypertension": {
            "screening_menu_items": ["BP Monitoring", "ECG", "KFT", "Lipid Profile"],
            "complication_menu_items": ["2D Echo", "Fundus Examination", "KFT"],
            "follow_up_frequency": "Every 1-3 months",
            "lifestyle_recommendations": [
                "Low sodium diet",
                "Regular exercise",
                "Weight management",
                "Limit alcohol"
            ]
        },
        "thyroid_disorder": {
            "screening_menu_items": ["T3", "T4", "TSH"],
            "additional_menu_items": ["Anti-TPO Antibody"],
            "follow_up_frequency": "Every 6 weeks until stable, then every 6-12 months",
            "lifestyle_recommendations": [
                "Regular sleep schedule",
                "Manage stress",
                "Balanced diet with iodine"
            ]
        },
        "anemia": {
            "screening_menu_items": ["CBC", "Hemoglobin", "RBC Count"],
            "additional_menu_items": ["Iron Studies", "Vitamin B12", "Folate", "Peripheral Smear"],
            "follow_up_frequency": "4-6 weeks after treatment",
            "lifestyle_recommendations": [
                "Iron-rich diet",
                "Vitamin C for iron absorption",
                "Avoid tea/coffee with meals"
            ]
        },
        "fever_of_unknown_origin": {
            "screening_menu_items": ["CBC", "CRP", "ESR", "Blood Culture", "Urine Culture", "CXR"],
            "additional_menu_items": ["WIDAL", "Dengue NS1", "Malaria Parasite", "Liver Function MenuItem"],
            "follow_up_frequency": "As per investigation results",
            "lifestyle_recommendations": [
                "Adequate hydration",
                "Rest",
                "Monitor temperature"
            ]
        }
    }
    
    condition_lower = condition.lower().replace(" ", "_")
    
    if condition_lower in protocols:
        return protocols[condition_lower]
    else:
        return {
            "error": "Condition not found",
            "available_conditions": list(protocols.keys())
        }


# ============ Health Tips Endpoint ============

@router.get("/ai/health-tips/{category}")
def get_health_tips(
    category: str,
    current_user = Depends(require_staff)
):
    """
    Get health tips for customers based on category.
    """
    tips = {
        "general": [
            "Stay hydrated - drink at least 8 glasses of water daily",
            "Get 7-9 hours of sleep each night",
            "Exercise for at least 30 minutes most days",
            "Eat a balanced diet with fruits and vegetables",
            "Wash hands regularly to prevent infections"
        ],
        "blood_test": [
            "Fast for 8-12 hours before fasting blood sugar test",
            "Avoid alcohol for 24 hours before liver function menu_items",
            "Inform about current medications",
            "Stay relaxed before blood draw"
        ],
        "prevention": [
            "Get regular health check-ups",
            "Complete recommended vaccinations",
            "Know your family health history",
            "Maintain healthy weight",
            "Don't smoke"
        ],
        "diabetes": [
            "Monitor blood sugar levels regularly",
            "Take medications as prescribed",
            "Carry a source of fast-acting sugar",
            "Wear medical ID",
            "Keep feet protected"
        ],
        "heart_health": [
            "Control blood pressure",
            "Maintain healthy cholesterol levels",
            "Exercise regularly",
            "Eat heart-healthy foods",
            "Manage stress"
        ]
    }
    
    category_lower = category.lower()
    if category_lower in tips:
        return {
            "category": category,
            "tips": tips[category_lower]
        }
    else:
        return {
            "category": category,
            "tips": tips["general"]
        }

