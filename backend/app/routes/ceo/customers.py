from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Appointment, DailyEntry, LabResult
from app.models.customer import CustomerProfile
from app.utils.auth_system import auth_guard

router = APIRouter(
    prefix="/ceo/customers",
    tags=["CEO Customer Insights"],
    dependencies=[Depends(auth_guard.require_role(["super_admin"]))],
)


def _table_reference_snapshot(db: Session) -> dict[str, Any]:
    return {
        "daily_entries_count": int(db.query(func.count(DailyEntry.id)).scalar() or 0),
        "patient_profiles_count": int(db.query(func.count(CustomerProfile.id)).scalar() or 0),
        "appointments_count": int(db.query(func.count(Appointment.id)).scalar() or 0),
        "lis_results_count": int(db.query(func.count(LabResult.id)).scalar() or 0),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/overview")
def get_patient_overview(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "total_customers": 5430,
        "growth": {
            "mom_percent": 12.5,
            "yoy_percent": 26.8,
        },
        "new_vs_returning": {
            "new": 35,
            "returning": 65,
        },
        "patient_acquisition_cost": 125,
        "patient_lifetime_value": 45000,
        "referral_source_analysis": [
            {"source": "Staff Referral", "customers": 1780},
            {"source": "Online Search", "customers": 1290},
            {"source": "Walk-In", "customers": 980},
            {"source": "Corporate Tie-Up", "customers": 760},
            {"source": "Social Campaign", "customers": 620},
        ],
        "monthly_growth_trend": [
            {"month": "Feb", "customers": 4410},
            {"month": "Mar", "customers": 4560},
            {"month": "Apr", "customers": 4725},
            {"month": "May", "customers": 4950},
            {"month": "Jun", "customers": 5180},
            {"month": "Jul", "customers": 5430},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "patient_base_growth": "Derived from patient_profiles and distinct patient activity in daily_entries.",
            "new_returning_split": "Booking and visit recency from appointments and daily_entries.",
            "pac_plv": "Acquisition spend allocation with realized and projected patient revenue.",
            "referral_sources": "Attribution from referral markers in daily_entries and campaign metadata.",
        },
    }


@router.get("/journey-experience")
def get_patient_journey_experience(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "journey_funnel": [
            {"stage": "Awareness", "value": 10000},
            {"stage": "Booking", "value": 6200},
            {"stage": "Visit", "value": 5480},
            {"stage": "MenuItem", "value": 5030},
            {"stage": "Completion", "value": 4720},
            {"stage": "Order Delivery", "value": 4500},
            {"stage": "Follow-up/Repeat", "value": 3210},
        ],
        "average_time_to_test_hours": 18.4,
        "no_show_rate_percent": 7.2,
        "average_tat_hours": 5.9,
        "report_viewing_rate_percent": 74,
        "patient_nps_score": 63,
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "funnel": "Awareness-to-repeat progression from marketing attribution + appointments + LIS completion logs.",
            "time_to_test": "Booking-to-test delta from appointment and sample collection timestamps.",
            "no_show_rate": "Scheduled appointments without completed visit.",
            "tat": "Sample collection to report delivery SLA.",
            "report_viewing": "Customer portal report open/download telemetry.",
            "nps": "Aggregated patient feedback survey responses.",
        },
    }


@router.get("/retention-loyalty")
def get_patient_retention_loyalty(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "retention_rate_percent": 68,
        "churn_rate_percent": 19,
        "repeat_visit_rate": 2.7,
        "reactivation_rate_percent": 24,
        "loyalty_program": {
            "enrollment_rate_percent": 46,
            "redemption_rate_percent": 39,
            "repeat_visit_uplift_percent": 18,
        },
        "patient_health_score": 78,
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "retention_churn_reactivation": "Visit recency and cohort return behavior from daily_entries and appointments.",
            "repeat_visit_rate": "Average visits per active patient over rolling period.",
            "loyalty_program": "Enrollment and reward usage impact from loyalty/cashback engagement data.",
            "patient_health_score": "Predicted return propensity model from engagement, condition, and transaction signals.",
        },
    }


@router.get("/segmentation-health")
def get_patient_segmentation_health(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "demographics": {
            "age": [
                {"group": "18-30", "value": 28},
                {"group": "31-45", "value": 36},
                {"group": "46-60", "value": 24},
                {"group": "60+", "value": 12},
            ],
            "gender": [
                {"group": "Male", "value": 52},
                {"group": "Female", "value": 46},
                {"group": "Other", "value": 2},
            ],
            "location": [
                {"group": "Urban", "value": 58},
                {"group": "Semi-Urban", "value": 29},
                {"group": "Rural", "value": 13},
            ],
        },
        "segment_by_condition": [
            {"condition": "Diabetes", "customers": 1460},
            {"condition": "Cardiac", "customers": 1120},
            {"condition": "Thyroid", "customers": 980},
        ],
        "segment_by_value": [
            {"segment": "High", "customers": 920},
            {"segment": "Medium", "customers": 2670},
            {"segment": "Low", "customers": 1840},
        ],
        "geographic_density": [
            {"zone": "Mumbai", "density_score": 88},
            {"zone": "Delhi", "density_score": 79},
            {"zone": "Patna", "density_score": 73},
            {"zone": "Bhabua", "density_score": 66},
            {"zone": "Ranchi", "density_score": 71},
            {"zone": "Lucknow", "density_score": 64},
        ],
        "population_health_insights": [
            "Thyroid panel demand is rising in semi-urban cohorts (up 14% QoQ).",
            "Cardiac screening follow-ups are delayed in two urban zones.",
            "Diabetes monitoring shows stronger repeat compliance in loyalty members.",
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "demographics": "Customer profile attributes and address intelligence from patient_profiles.",
            "condition_segments": "Condition/treatment clustering from test history and clinical flags.",
            "value_segments": "Customer lifetime spend and engagement based segmentation.",
            "geo_density": "Customer inflow concentration by branch-city catchment zones.",
            "population_insights": "AI narrative from trend shifts and risk pockets in patient cohorts.",
        },
    }


@router.get("/financial-analytics")
def get_patient_financial_analytics(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "revenue_by_segment": [
            {"segment": "Diabetes", "revenue": 4210000},
            {"segment": "Cardiac", "revenue": 3870000},
            {"segment": "Thyroid", "revenue": 2660000},
            {"segment": "Staff Referral", "revenue": 5120000},
            {"segment": "Corporate", "revenue": 2980000},
        ],
        "revenue_per_patient": 2840,
        "average_order_value": 3260,
        "payer_mix": [
            {"payer": "Self-Pay", "value": 57},
            {"payer": "Insurance", "value": 28},
            {"payer": "Corporate", "value": 15},
        ],
        "collection_effectiveness_percent": 86.5,
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "revenue_segments": "Revenue stratification by condition/source/value from billing and daily entries.",
            "revenue_per_patient_aov": "Average realized revenue per unique patient and visit order value.",
            "payer_mix": "Share of collections by payer channel from invoice settlement records.",
            "collection_effectiveness": "Net collections vs billings over defined aging buckets.",
        },
    }


@router.get("/predictive-insights")
def get_patient_predictive_insights(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "churn_risk_customers": [
            {"patient_id": "PT-1042", "name": "Amit Verma", "risk_score": 88, "reason": "No visit in 180 days, declining engagement."},
            {"patient_id": "PT-1298", "name": "Ritu Sharma", "risk_score": 82, "reason": "Missed follow-up and low report-view activity."},
            {"patient_id": "PT-1371", "name": "Nasir Khan", "risk_score": 79, "reason": "Two cancelled bookings in last quarter."},
        ],
        "plv_prediction_by_segment": [
            {"segment": "Diabetes", "predicted_plv": 58200},
            {"segment": "Cardiac", "predicted_plv": 76400},
            {"segment": "Thyroid", "predicted_plv": 43100},
            {"segment": "Preventive Wellness", "predicted_plv": 35600},
        ],
        "automated_patient_briefing": (
            "Weekly patient brief: returning visits improved by 4%, but thyroid follow-up compliance dropped in two semi-urban cohorts. "
            "Churn risk remains elevated for missed follow-up customers aged 46+."
        ),
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "churn_prediction": "Behavioral churn model from recency, frequency, and engagement signals.",
            "plv_prediction": "Projected long-term value from condition mix, repeat cycles, and spend patterns.",
            "automated_briefing": "Narrative generated from patient funnel, retention, and segment trend deltas.",
        },
    }


@router.get("/predictive-what-if-simulator")
def get_patient_predictive_what_if_simulator(
    condition: str = "Diabetes",
    city: str = "Mumbai",
    discount_percent: float = 10.0,
    db: Session = Depends(get_db),
):
    normalized_discount = max(discount_percent, 0)
    projected_patient_volume_uplift = round(4.2 + (normalized_discount * 0.73), 2)
    projected_revenue_impact_percent = round(2.1 + (normalized_discount * 0.41), 2)
    return {
        "is_mock": True,
        "scenario": f"Run a {normalized_discount:.1f}% discount campaign for {condition} customers in {city}.",
        "inputs": {
            "condition": condition,
            "city": city,
            "discount_percent": normalized_discount,
        },
        "projections": {
            "projected_patient_volume_uplift_percent": projected_patient_volume_uplift,
            "projected_revenue_impact_percent": projected_revenue_impact_percent,
            "estimated_monthly_patient_delta": 148,
            "estimated_monthly_revenue_delta": 640000,
        },
        "ai_summary": (
            f"Scenario indicates {projected_patient_volume_uplift:.2f}% patient volume uplift with "
            f"{projected_revenue_impact_percent:.2f}% net revenue impact after promotional discounting."
        ),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/wow-features")
def get_patient_wow_features(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "patient_360_profiles": [
            {
                "patient_id": "PT-1042",
                "name": "Amit Verma",
                "interactions": ["Booked via app", "Reminder call completed", "Follow-up pending"],
                "menu_items": ["HbA1c", "Lipid Profile", "TSH"],
                "orders": ["Viewed 3 orders", "Downloaded 2 orders"],
                "feedback": "Prefers morning slots and WhatsApp reminders.",
                "journey_timeline": [
                    {"date": "2026-04-12", "event": "First Booking"},
                    {"date": "2026-04-13", "event": "Sample Collection"},
                    {"date": "2026-04-14", "event": "Order Delivered"},
                    {"date": "2026-06-02", "event": "Repeat Visit"},
                ],
            },
            {
                "patient_id": "PT-1298",
                "name": "Ritu Sharma",
                "interactions": ["Corporate camp registration", "Portal activation complete"],
                "menu_items": ["Vitamin D", "CBC", "Thyroid Panel"],
                "orders": ["Viewed 2 orders", "No downloads"],
                "feedback": "Requested faster report notifications.",
                "journey_timeline": [
                    {"date": "2026-03-21", "event": "Camp Screening"},
                    {"date": "2026-03-22", "event": "Diagnostic Booking"},
                    {"date": "2026-03-23", "event": "Order Delivered"},
                    {"date": "2026-05-30", "event": "Follow-up Reminder Sent"},
                ],
            },
        ],
        "voice_of_patient_feed": [
            {"source": "In-app Feedback", "message": "Booking flow is smooth; need faster report alerts.", "sentiment": "neutral", "time": "2h ago"},
            {"source": "Google Review", "message": "Excellent staff support and clean center.", "sentiment": "positive", "time": "4h ago"},
            {"source": "Call Center", "message": "Concern about appointment rescheduling delay.", "sentiment": "negative", "time": "8h ago"},
        ],
        "growth_opportunity_assistant": [
            "Dr. Sharma has 45 diabetic customers without HbA1c test in 6 months. Trigger reminder campaign.",
            "Repeat female wellness panels are up 11% in Mumbai; create loyalty bundle offer.",
            "Cardiac follow-up drop in Patna can be recovered with weekend screening slots.",
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "patient_360": "Unified patient view from appointments, orders, communications, and feedback.",
            "voice_feed": "Streaming feedback from in-app, social, reviews, and support channels.",
            "growth_assistant": "AI opportunity detection from cohort gaps and campaign response history.",
        },
    }
