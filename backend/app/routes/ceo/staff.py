from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, DailyEntry
from app.models.referring_doctor import ReferralLog, ReferringStaff
from app.utils.auth_system import auth_guard

router = APIRouter(
    prefix="/ceo/staff",
    tags=["CEO Staff Network"],
    dependencies=[Depends(auth_guard.require_role(["super_admin"]))],
)


def _table_reference_snapshot(db: Session) -> dict[str, Any]:
    doctor_profiles_count = int(db.query(func.count(ReferringStaff.id)).scalar() or 0)
    referral_logs_count = int(db.query(func.count(ReferralLog.id)).scalar() or 0)
    daily_entries_count = int(db.query(func.count(DailyEntry.id)).scalar() or 0)
    commission_configured_count = int(
        db.query(func.count(ReferringStaff.id))
        .filter(ReferringStaff.commission_percentage > 0)
        .scalar()
        or 0
    )
    return {
        "doctor_profiles_count": doctor_profiles_count,
        "referral_logs_count": referral_logs_count,
        "daily_entries_count": daily_entries_count,
        "commission_configured_count": commission_configured_count,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/network-health")
def get_doctor_network_health(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(6).all()
    region_names = [branch.city for branch in branches if branch.city] or [
        "Mumbai",
        "Delhi",
        "Patna",
        "Bhabua",
        "Ranchi",
        "Lucknow",
    ]
    padded_regions = list(region_names)
    fallback_regions = ["Mumbai", "Delhi", "Patna", "Bhabua", "Ranchi", "Lucknow", "Pune", "Noida", "Kolkata"]
    for fallback_region in fallback_regions:
        if len(padded_regions) >= 6:
            break
        if fallback_region not in padded_regions:
            padded_regions.append(fallback_region)
    padded_regions = padded_regions[:6]

    return {
        "is_mock": True,
        "score": 82,
        "total_staff": 120,
        "growth_mom_percent": 6.4,
        "revenue_contribution_percent": 45,
        "engagement_score": 78,
        "attrition_risk_percent": 12,
        "regional_density": [
            {"region": padded_regions[0], "doctor_count": 26},
            {"region": padded_regions[1], "doctor_count": 21},
            {"region": padded_regions[2], "doctor_count": 18},
            {"region": padded_regions[3], "doctor_count": 17},
            {"region": padded_regions[4], "doctor_count": 22},
            {"region": padded_regions[5], "doctor_count": 16},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "doctor_profiles": "ReferringStaff roster with active status and specialty metadata.",
            "revenue_contribution": "Referral-attributed topline from DailyEntry and ReferralLog joins.",
            "engagement_attrition_risk": "Staff interaction cadence and referral consistency trend models.",
            "regional_density": "Branch/city grouped distribution of active referring staff.",
        },
    }


@router.get("/performance-analytics")
def get_doctor_performance_analytics(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "leaderboard": [
            {
                "doctor_id": 101,
                "doctor_name": "Dr. R. Sharma",
                "branch": "Mumbai",
                "specialty": "Cardiology",
                "time_period": "ytd",
                "total_referrals": 184,
                "revenue_generated": 1320000,
                "commission_earned": 105600,
                "conversion_rate_percent": 86,
            },
            {
                "doctor_id": 102,
                "doctor_name": "Dr. P. Verma",
                "branch": "Delhi",
                "specialty": "Neurology",
                "time_period": "ytd",
                "total_referrals": 161,
                "revenue_generated": 1140000,
                "commission_earned": 79800,
                "conversion_rate_percent": 83,
            },
            {
                "doctor_id": 103,
                "doctor_name": "Dr. A. Khan",
                "branch": "Patna",
                "specialty": "Orthopedics",
                "time_period": "ytd",
                "total_referrals": 148,
                "revenue_generated": 960000,
                "commission_earned": 67200,
                "conversion_rate_percent": 80,
            },
            {
                "doctor_id": 104,
                "doctor_name": "Dr. N. Iyer",
                "branch": "Bhabua",
                "specialty": "Endocrinology",
                "time_period": "ytd",
                "total_referrals": 129,
                "revenue_generated": 845000,
                "commission_earned": 50700,
                "conversion_rate_percent": 78,
            },
            {
                "doctor_id": 105,
                "doctor_name": "Dr. S. Menon",
                "branch": "Ranchi",
                "specialty": "Pulmonology",
                "time_period": "ytd",
                "total_referrals": 121,
                "revenue_generated": 790000,
                "commission_earned": 47400,
                "conversion_rate_percent": 76,
            },
        ],
        "referral_trend": {
            "network": [
                {"month": "Feb", "referrals": 148},
                {"month": "Mar", "referrals": 152},
                {"month": "Apr", "referrals": 159},
                {"month": "May", "referrals": 163},
                {"month": "Jun", "referrals": 171},
                {"month": "Jul", "referrals": 176},
            ],
            "by_doctor": [
                {
                    "doctor_id": 101,
                    "doctor_name": "Dr. R. Sharma",
                    "points": [
                        {"month": "Feb", "referrals": 23},
                        {"month": "Mar", "referrals": 25},
                        {"month": "Apr", "referrals": 28},
                        {"month": "May", "referrals": 29},
                        {"month": "Jun", "referrals": 31},
                        {"month": "Jul", "referrals": 34},
                    ],
                },
                {
                    "doctor_id": 102,
                    "doctor_name": "Dr. P. Verma",
                    "points": [
                        {"month": "Feb", "referrals": 20},
                        {"month": "Mar", "referrals": 22},
                        {"month": "Apr", "referrals": 24},
                        {"month": "May", "referrals": 25},
                        {"month": "Jun", "referrals": 27},
                        {"month": "Jul", "referrals": 28},
                    ],
                },
                {
                    "doctor_id": 103,
                    "doctor_name": "Dr. A. Khan",
                    "points": [
                        {"month": "Feb", "referrals": 19},
                        {"month": "Mar", "referrals": 21},
                        {"month": "Apr", "referrals": 23},
                        {"month": "May", "referrals": 24},
                        {"month": "Jun", "referrals": 25},
                        {"month": "Jul", "referrals": 26},
                    ],
                },
            ],
        },
        "referral_leakage_alerts": [
            {
                "doctor_id": 106,
                "doctor_name": "Dr. K. Bose",
                "branch": "Lucknow",
                "decline_percent": 18,
                "message": "Referral volume dropped 18% vs prior month.",
            },
            {
                "doctor_id": 107,
                "doctor_name": "Dr. M. Patel",
                "branch": "Delhi",
                "decline_percent": 14,
                "message": "Referral volume dropped 14% over last 60 days.",
            },
        ],
        "patient_conversion_rate_percent": 81,
        "test_mix": [
            {"test_type": "MRI", "value": 31},
            {"test_type": "CT Scan", "value": 24},
            {"test_type": "Blood MenuItems", "value": 21},
            {"test_type": "Ultrasound", "value": 15},
            {"test_type": "X-Ray", "value": 9},
        ],
        "doctor_summaries": [
            {
                "doctor_id": 101,
                "doctor_name": "Dr. R. Sharma",
                "total_referrals": 184,
                "revenue_generated": 1320000,
                "commission_earned": 105600,
                "interaction_history": [
                    "Quarterly meeting completed on 2026-07-10.",
                    "Shared cardiology screening campaign deck.",
                    "Follow-up on reporting turnaround target discussed.",
                ],
            },
            {
                "doctor_id": 102,
                "doctor_name": "Dr. P. Verma",
                "total_referrals": 161,
                "revenue_generated": 1140000,
                "commission_earned": 79800,
                "interaction_history": [
                    "Visited branch diagnostics unit on 2026-07-04.",
                    "Requested neurology package tariff update.",
                    "Pending closure for digital report SLA feedback.",
                ],
            },
            {
                "doctor_id": 103,
                "doctor_name": "Dr. A. Khan",
                "total_referrals": 148,
                "revenue_generated": 960000,
                "commission_earned": 67200,
                "interaction_history": [
                    "Onboarded two new corporate referral accounts.",
                    "Monthly case review call completed.",
                    "Requested additional orthopedic test panel awareness.",
                ],
            },
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "leaderboard": "Staff and branch/specialty performance from ReferralLog and DailyEntry revenue joins.",
            "referral_trend": "Time-series referral volumes from ReferralLog by doctor and network aggregate.",
            "leakage_alerts": "Decline detection from rolling referral trend anomalies.",
            "conversion_rate": "Referred customers reaching completed diagnostics milestones.",
            "test_mix": "Referred test category distribution from DailyEntry test_names aggregation.",
            "doctor_summary": "Per-doctor referrals, revenue, commission and CRM interaction timeline.",
        },
    }


@router.get("/financial-commission")
def get_doctor_financial_commission(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "commission_dashboard": [
            {"doctor_id": 101, "doctor_name": "Dr. R. Sharma", "earned": 105600, "paid": 84600, "pending": 21000},
            {"doctor_id": 102, "doctor_name": "Dr. P. Verma", "earned": 79800, "paid": 67800, "pending": 12000},
            {"doctor_id": 103, "doctor_name": "Dr. A. Khan", "earned": 67200, "paid": 53200, "pending": 14000},
            {"doctor_id": 104, "doctor_name": "Dr. N. Iyer", "earned": 50700, "paid": 44700, "pending": 6000},
            {"doctor_id": 105, "doctor_name": "Dr. S. Menon", "earned": 47400, "paid": 42400, "pending": 5000},
        ],
        "referral_cost_percent_of_revenue": 6.8,
        "doctor_profitability": [
            {"doctor_id": 101, "doctor_name": "Dr. R. Sharma", "revenue": 1320000, "referral_cost": 105600, "service_cost": 694000, "net_profit": 520400},
            {"doctor_id": 102, "doctor_name": "Dr. P. Verma", "revenue": 1140000, "referral_cost": 79800, "service_cost": 621000, "net_profit": 439200},
            {"doctor_id": 103, "doctor_name": "Dr. A. Khan", "revenue": 960000, "referral_cost": 67200, "service_cost": 533000, "net_profit": 359800},
            {"doctor_id": 104, "doctor_name": "Dr. N. Iyer", "revenue": 845000, "referral_cost": 50700, "service_cost": 472000, "net_profit": 322300},
            {"doctor_id": 105, "doctor_name": "Dr. S. Menon", "revenue": 790000, "referral_cost": 47400, "service_cost": 446000, "net_profit": 296600},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "commission_dashboard": "Calculated from doctor commission schedules and referral-linked revenue events.",
            "referral_cost_ratio": "Total referral payout burden over referral-attributed revenue.",
            "doctor_profitability": "Staff-level contribution after referral and service delivery costs.",
        },
    }


@router.get("/commission-simulator")
def get_doctor_commission_simulator(
    structure: str = "tiered",
    base_commission_percent: float = 7.0,
    db: Session = Depends(get_db),
):
    normalized_base = max(base_commission_percent, 0)
    projected_referral_growth = round(2.8 + (normalized_base * 0.34), 2)
    projected_commission_cost_growth = round(1.9 + (normalized_base * 0.41), 2)
    projected_profitability_impact = round(
        projected_referral_growth - (projected_commission_cost_growth * 0.72), 2
    )
    return {
        "is_mock": True,
        "structure": structure,
        "base_commission_percent": normalized_base,
        "projections": {
            "projected_referral_growth_percent": projected_referral_growth,
            "projected_commission_cost_growth_percent": projected_commission_cost_growth,
            "projected_profitability_impact_percent": projected_profitability_impact,
            "estimated_monthly_revenue_delta": 390000,
            "estimated_monthly_commission_delta": 118000,
        },
        "ai_summary": (
            f"Simulated {structure} commission model indicates referral growth of "
            f"{projected_referral_growth:.2f}% with profitability impact of "
            f"{projected_profitability_impact:.2f}% at a base {normalized_base:.2f}% commission."
        ),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/commission-payout-automation")
def get_doctor_commission_payout_automation(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "generated_at": datetime.utcnow().isoformat(),
        "run_id": "PAYOUT-MOCK-2026-07-26-001",
        "status": "completed",
        "statements_generated": 58,
        "payouts_queued": 41,
        "total_payout_amount": 1248500,
        "message": "Mock payout automation completed: statements generated and payout batch queued.",
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/engagement-relationship")
def get_doctor_engagement_relationship(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "doctor_profiles": [
            {"doctor_id": 101, "doctor_name": "Dr. R. Sharma", "specialty": "Cardiology", "branch": "Mumbai", "engagement_score": 88, "last_interaction": "2026-07-10", "preferred_channel": "In-person"},
            {"doctor_id": 102, "doctor_name": "Dr. P. Verma", "specialty": "Neurology", "branch": "Delhi", "engagement_score": 81, "last_interaction": "2026-07-12", "preferred_channel": "Email"},
            {"doctor_id": 103, "doctor_name": "Dr. A. Khan", "specialty": "Orthopedics", "branch": "Patna", "engagement_score": 79, "last_interaction": "2026-07-14", "preferred_channel": "Call"},
        ],
        "engagement_calendar": [
            {"date": "2026-07-20", "event_type": "Visit", "doctor_name": "Dr. R. Sharma", "notes": "Quarterly account visit"},
            {"date": "2026-07-21", "event_type": "Call", "doctor_name": "Dr. P. Verma", "notes": "Feedback on report TAT"},
            {"date": "2026-07-22", "event_type": "Email", "doctor_name": "Dr. A. Khan", "notes": "Shared orthopedic panel update"},
            {"date": "2026-07-23", "event_type": "CME", "doctor_name": "Dr. S. Menon", "notes": "CME event invite"},
            {"date": "2026-07-24", "event_type": "Visit", "doctor_name": "Dr. N. Iyer", "notes": "Lab quality walkthrough"},
        ],
        "flight_risk_staff": [
            {"doctor_id": 107, "doctor_name": "Dr. M. Patel", "risk_level": "high", "reason": "Referrals down 14% with reduced interaction frequency."},
            {"doctor_id": 108, "doctor_name": "Dr. T. Roy", "risk_level": "medium", "reason": "Commission dissatisfaction noted in recent feedback."},
        ],
        "doctor_nps_feedback": {
            "nps_score": 41,
            "positive_themes": ["Faster reporting", "Improved support team responsiveness"],
            "improvement_themes": ["Weekend escalation availability", "Commission statement transparency"],
        },
        "communication_hub": {
            "available": True,
            "message": "Personalized communication workflows can be configured by segment (specialty, branch, engagement tier).",
        },
        "white_label_portal": {
            "available": True,
            "message": "White-label doctor portal access is enabled for pilot branches.",
        },
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/growth-acquisition")
def get_doctor_growth_acquisition(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "market_opportunities": [
            {"doctor_name": "Dr. V. Chatterjee", "city": "Mumbai", "specialty": "Cardiology", "estimated_monthly_referrals": 42},
            {"doctor_name": "Dr. L. Tiwari", "city": "Delhi", "specialty": "Neurology", "estimated_monthly_referrals": 37},
            {"doctor_name": "Dr. G. Sinha", "city": "Patna", "specialty": "Endocrinology", "estimated_monthly_referrals": 31},
            {"doctor_name": "Dr. A. Bakshi", "city": "Ranchi", "specialty": "Pulmonology", "estimated_monthly_referrals": 28},
        ],
        "campaign_performance": [
            {"campaign": "CME Cardio Connect", "investment": 280000, "revenue_generated": 790000, "roi_percent": 182.1},
            {"campaign": "Neurology Webinar", "investment": 145000, "revenue_generated": 398000, "roi_percent": 174.5},
            {"campaign": "Direct Mail Outreach", "investment": 92000, "revenue_generated": 221000, "roi_percent": 140.2},
        ],
        "competitor_leakage_report": [
            {"doctor_name": "Dr. K. Bose", "city": "Lucknow", "estimated_leakage_percent": 22, "competitor_hint": "MetroScan Diagnostics"},
            {"doctor_name": "Dr. R. Das", "city": "Delhi", "estimated_leakage_percent": 18, "competitor_hint": "Prime Imaging Center"},
        ],
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/growth-what-if-simulator")
def get_doctor_growth_what_if_simulator(
    specialty: str = "Cardiology",
    commission_increase_percent: float = 5.0,
    db: Session = Depends(get_db),
):
    normalized_increase = max(commission_increase_percent, 0)
    projected_referral_volume_growth = round(3.1 + (normalized_increase * 0.58), 2)
    projected_profitability_impact = round(1.7 + (normalized_increase * 0.26), 2)
    return {
        "is_mock": True,
        "scenario": f"Increase commission rate for {specialty} by {normalized_increase:.1f}%.",
        "inputs": {
            "specialty": specialty,
            "commission_increase_percent": normalized_increase,
        },
        "projections": {
            "projected_referral_volume_growth_percent": projected_referral_volume_growth,
            "projected_profitability_impact_percent": projected_profitability_impact,
            "estimated_monthly_revenue_delta": 460000,
            "estimated_monthly_commission_delta": 156000,
        },
        "ai_summary": (
            f"Scenario suggests referral volume growth of {projected_referral_volume_growth:.2f}% for "
            f"{specialty}, with profitability impact of {projected_profitability_impact:.2f}% after higher commissions."
        ),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/operational-excellence")
def get_doctor_operational_excellence(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "service_level_dashboard": {
            "average_tat_hours": 5.6,
            "sample_rejection_rate_percent": 2.3,
            "report_quality_score": 94,
            "tat_trend": [
                {"week": "W1", "tat_hours": 6.2},
                {"week": "W2", "tat_hours": 6.0},
                {"week": "W3", "tat_hours": 5.8},
                {"week": "W4", "tat_hours": 5.6},
            ],
        },
        "doctor_issue_tracker": [
            {"issue_id": "DOC-101", "doctor_name": "Dr. R. Sharma", "issue_type": "Lost Order", "status": "Open", "updated_at": "2026-07-24"},
            {"issue_id": "DOC-102", "doctor_name": "Dr. P. Verma", "issue_type": "Billing Error", "status": "In Progress", "updated_at": "2026-07-23"},
            {"issue_id": "DOC-103", "doctor_name": "Dr. A. Khan", "issue_type": "Delayed TAT", "status": "Resolved", "updated_at": "2026-07-22"},
            {"issue_id": "DOC-104", "doctor_name": "Dr. N. Iyer", "issue_type": "Missing Addendum", "status": "In Progress", "updated_at": "2026-07-21"},
        ],
        "patient_journey_completion_rate_percent": 81,
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "service_levels": "Derived from report lifecycle timestamps and QA validations in operations logs.",
            "issue_tracker": "Staff-reported incidents from CRM/helpdesk records.",
            "journey_completion": "Referral-to-report completion funnel for referred customers.",
        },
    }


@router.get("/wow-features")
def get_doctor_wow_features(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "doctor_360_briefing": {
            "title": "Staff 360 AI Briefing",
            "message": "Good morning. Top performer: Dr. Sharma. Referral volume is up 12% this month, while Delhi Neurology referrals need closer follow-up.",
        },
        "smart_referral_alerts": [
            {
                "severity": "high",
                "title": "Top doctor referral dip",
                "message": "Dr. P. Verma referrals dropped 11% this week versus trailing average.",
            },
            {
                "severity": "medium",
                "title": "High-potential doctor identified",
                "message": "Dr. V. Chatterjee shows consistent referral quality and high conversion potential.",
            },
        ],
        "doctor_loyalty_program": {
            "tiers": [
                {"name": "Silver", "qualifies": ["Dr. A. Khan", "Dr. N. Iyer"], "criteria": "100+ referrals/year"},
                {"name": "Gold", "qualifies": ["Dr. P. Verma", "Dr. S. Menon"], "criteria": "140+ referrals/year"},
                {"name": "Platinum", "qualifies": ["Dr. R. Sharma"], "criteria": "180+ referrals/year"},
            ]
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "doctor_360": "Generated from performance, engagement, conversion, and issue trend summaries.",
            "smart_alerts": "Anomaly detection on referral momentum and high-potential identification models.",
            "loyalty_tiers": "Tier assignment from referral volume, quality, and retention contribution.",
        },
    }
