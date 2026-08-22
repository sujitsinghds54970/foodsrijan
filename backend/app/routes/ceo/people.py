from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch
from app.models.hr import Attendance, StaffProfile
from app.models.payroll import PayrollRun
from app.utils.auth_system import auth_guard

router = APIRouter(
    prefix="/ceo/people",
    tags=["CEO People & Culture"],
    dependencies=[Depends(auth_guard.require_role(["super_admin"]))],
)


def _table_reference_snapshot(db: Session) -> dict[str, Any]:
    StaffEmployee_count = int(db.query(func.count(StaffProfile.id)).scalar() or 0)
    payroll_run_count = int(db.query(func.count(PayrollRun.id)).scalar() or 0)
    attendance_count = int(db.query(func.count(Attendance.id)).scalar() or 0)
    branch_count = int(db.query(func.count(Branch.id)).scalar() or 0)
    return {
        "staff_profiles_count": StaffEmployee_count,
        "payroll_runs_count": payroll_run_count,
        "attendance_logs_count": attendance_count,
        "branches_count": branch_count,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/health-score")
def get_people_health_score(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "score": 82,
        "trend": "improving",
        "drivers": {
            "engagement": 85,
            "attrition": 70,
            "leadership": 90,
        },
        "monthly_trend": [
            {"month": "Aug", "score": 71},
            {"month": "Sep", "score": 72},
            {"month": "Oct", "score": 73},
            {"month": "Nov", "score": 74},
            {"month": "Dec", "score": 75},
            {"month": "Jan", "score": 76},
            {"month": "Feb", "score": 77},
            {"month": "Mar", "score": 78},
            {"month": "Apr", "score": 79},
            {"month": "May", "score": 80},
            {"month": "Jun", "score": 81},
            {"month": "Jul", "score": 82},
        ],
        "benchmark": {
            "industry_average": 74,
            "our_score": 82,
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "engagement": "Derived from StaffEmployee attendance consistency and participation trends (StaffProfile + Attendance).",
            "attrition": "Derived from active/inactive StaffEmployee lifecycle and payroll continuity (StaffProfile + PayrollRun).",
            "leadership_pipeline": "Derived from manager coverage, tenure, and role progression across branches (StaffProfile + Branch).",
        },
    }


@router.get("/talent-retention")
def get_people_talent_retention(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Pune", "Noida"])[:4]

    return {
        "is_mock": True,
        "headcount": {
            "total": 120,
            "by_branch": [
                {"name": padded_branch_labels[0], "count": 34},
                {"name": padded_branch_labels[1], "count": 29},
                {"name": padded_branch_labels[2], "count": 27},
                {"name": padded_branch_labels[3], "count": 30},
            ],
            "by_department": [
                {"name": "Operations", "count": 38},
                {"name": "Diagnostics", "count": 31},
                {"name": "Front Office", "count": 22},
                {"name": "Finance", "count": 14},
                {"name": "HR", "count": 15},
            ],
        },
        "attrition_retention": {
            "ytd_attrition_percent": 12,
            "retention_rate_percent": 88,
            "by_branch": [
                {"name": padded_branch_labels[0], "attrition": 10, "retention": 90},
                {"name": padded_branch_labels[1], "attrition": 13, "retention": 87},
                {"name": padded_branch_labels[2], "attrition": 15, "retention": 85},
                {"name": padded_branch_labels[3], "attrition": 9, "retention": 91},
            ],
            "by_department": [
                {"name": "Operations", "attrition": 11, "retention": 89},
                {"name": "Diagnostics", "attrition": 14, "retention": 86},
                {"name": "Front Office", "attrition": 16, "retention": 84},
                {"name": "Finance", "attrition": 8, "retention": 92},
                {"name": "HR", "attrition": 9, "retention": 91},
            ],
            "by_role": [
                {"name": "Radiologist", "attrition": 7, "retention": 93},
                {"name": "Lab Technician", "attrition": 13, "retention": 87},
                {"name": "Branch Director", "attrition": 6, "retention": 94},
                {"name": "Receptionist", "attrition": 18, "retention": 82},
            ],
        },
        "hiring_velocity": {
            "avg_time_to_hire_days": 32,
            "avg_time_to_fill_days": 41,
            "critical_roles": [
                {"role": "Radiologist", "days_to_fill": 45},
                {"role": "Branch Director", "days_to_fill": 52},
                {"role": "Lab Quality Lead", "days_to_fill": 38},
            ],
        },
        "quality_of_hire": {
            "six_month_avg_rating": 4.2,
            "new_hires_evaluated": 18,
        },
        "open_positions": [
            {"role": "Branch Director", "branch": padded_branch_labels[0], "department": "Operations", "critical": True},
            {"role": "Radiologist", "branch": padded_branch_labels[1], "department": "Diagnostics", "critical": True},
            {"role": "Senior Accountant", "branch": padded_branch_labels[2], "department": "Finance", "critical": False},
            {"role": "Lab Technician", "branch": padded_branch_labels[3], "department": "Diagnostics", "critical": True},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "headcount": "StaffProfile joined with Branch for active workforce distribution.",
            "attrition_retention": "StaffProfile status transitions + PayrollRun continuity for YTD attrition/retention.",
            "time_to_hire_fill": "PayrollRun staffing deltas and future recruitment table (planned).",
            "quality_of_hire": "StaffProfile tenure + Attendance trends + performance module metrics.",
        },
    }


@router.get("/engagement-culture")
def get_people_engagement_culture(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(3).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Patna", "Noida"])[:3]
    now_iso = datetime.utcnow().isoformat()
    return {
        "is_mock": True,
        "enps": {
            "score": 32,
            "description": "Healthy promoter momentum with room to improve compensation sentiment.",
        },
        "engagement_index": {
            "score": 81,
            "source": "Composite pulse-survey score (mock).",
        },
        "recognition_feed": [
            {
                "id": 1,
                "timestamp": now_iso,
                "actor": "Branch Director, Mumbai",
                "message": "Recognized front-office team for zero-wait patient onboarding this week.",
                "source": "mock_praise_table",
            },
            {
                "id": 2,
                "timestamp": now_iso,
                "actor": "HR Lead, Delhi",
                "message": "Praised diagnostics shift team for 100% attendance in critical week.",
                "source": "mock_praise_table",
            },
            {
                "id": 3,
                "timestamp": now_iso,
                "actor": "Operations Head, Bhabua",
                "message": "Recognized lab technicians for improving TAT under high test volume.",
                "source": "mock_praise_table",
            },
            {
                "id": 4,
                "timestamp": now_iso,
                "actor": "CEO Office",
                "message": "Appreciated cross-branch support for weekend outreach camp.",
                "source": "mock_praise_table",
            },
        ],
        "pulse_survey_results": [
            {"theme": "Work-Life Balance", "positive": 72, "negative": 28},
            {"theme": "Compensation", "positive": 64, "negative": 36},
            {"theme": "Leadership Trust", "positive": 79, "negative": 21},
            {"theme": "Career Growth", "positive": 68, "negative": 32},
            {"theme": "Team Collaboration", "positive": 83, "negative": 17},
        ],
        "branch_effect": [
            {"name": padded_branch_labels[0], "engagement": 84},
            {"name": padded_branch_labels[1], "engagement": 79},
            {"name": padded_branch_labels[2], "engagement": 81},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "enps": "Pulse surveys linked to StaffProfile cohorts and branch mapping.",
            "engagement_index": "Attendance consistency + payroll continuity + survey sentiment.",
            "recognition_feed": "Future Praise table with creator and recipient references to StaffProfile/User.",
            "pulse_themes": "Survey theme sentiment snapshots joined with Branch and department metadata.",
        },
    }


@router.get("/leadership-development")
def get_people_leadership_development(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Noida", "Pune"])[:4]
    return {
        "is_mock": True,
        "leadership_pipeline": [
            {"level": "Director-ready", "count": 9},
            {"level": "Department Head-ready", "count": 16},
        ],
        "manager_effectiveness": [
            {"branch": padded_branch_labels[0], "engagement_score": 84, "retention_score": 91, "overall_score": 88},
            {"branch": padded_branch_labels[1], "engagement_score": 78, "retention_score": 87, "overall_score": 82},
            {"branch": padded_branch_labels[2], "engagement_score": 76, "retention_score": 85, "overall_score": 80},
            {"branch": padded_branch_labels[3], "engagement_score": 82, "retention_score": 90, "overall_score": 86},
        ],
        "internal_promotion_rate_percent": 37,
        "skills_gap_analysis": [
            "Mumbai needs more MRI-certified technicians.",
            "Delhi branch requires two advanced LIS workflow specialists.",
            "Bhabua needs leadership coaching bench for assistant managers.",
            "Patna needs customer empathy and grievance-resolution refresher training.",
        ],
        "hipo_talent_pool": [
            {"employee_id": "VV-MUM-204", "name": "Aarav Sharma", "branch": padded_branch_labels[0], "role": "Senior Lab Technician", "readiness": "6 months"},
            {"employee_id": "VV-DEL-178", "name": "Neha Verma", "branch": padded_branch_labels[1], "role": "Operations Supervisor", "readiness": "3 months"},
            {"employee_id": "VV-PAT-156", "name": "Ritwik Singh", "branch": padded_branch_labels[2], "role": "Quality Analyst", "readiness": "9 months"},
            {"employee_id": "VV-BHA-143", "name": "Pooja Kumari", "branch": padded_branch_labels[3], "role": "Front Office Lead", "readiness": "6 months"},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "pipeline_readiness": "StaffProfile tenure, role history, manager ratings, and assessment scores.",
            "manager_effectiveness": "Branch-level engagement + retention metrics from Attendance and Payroll trends.",
            "internal_promotion_rate": "Open-role fill records mapped to existing StaffProfile promotions.",
            "skills_gap_analysis": "Role competency matrix against current StaffEmployee certifications and branch demand.",
            "hipo_pool": "Performance, attendance, and leadership nominations from StaffProfile + HR assessments.",
        },
    }


@router.get("/workforce-productivity")
def get_people_workforce_productivity(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Noida", "Pune"])[:4]
    return {
        "is_mock": True,
        "revenue_per_employee": 1250000,
        "total_workforce_cost": 800000,
        "workforce_cost_percent_of_revenue": 25,
        "branch_cost_comparison": [
            {"branch": padded_branch_labels[0], "revenue": 5200000, "workforce_cost": 1320000},
            {"branch": padded_branch_labels[1], "revenue": 4700000, "workforce_cost": 1190000},
            {"branch": padded_branch_labels[2], "revenue": 3900000, "workforce_cost": 980000},
            {"branch": padded_branch_labels[3], "revenue": 4300000, "workforce_cost": 1080000},
        ],
        "labor_cost_forecast": [
            {"month": "Aug", "forecast_cost": 805000},
            {"month": "Sep", "forecast_cost": 815000},
            {"month": "Oct", "forecast_cost": 828000},
            {"month": "Nov", "forecast_cost": 842000},
            {"month": "Dec", "forecast_cost": 860000},
            {"month": "Jan", "forecast_cost": 878000},
        ],
        "forecast_notes": "AI-driven projection based on hiring pipeline and historical payroll run growth (mock model).",
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "revenue_per_employee": "Revenue aggregates from finance/analytics tables divided by active headcount from StaffProfile.",
            "workforce_cost": "PayrollRun + payroll transactions + incentives/benefits from payroll subsystem.",
            "branch_cost_comparison": "Branch revenue vs payroll costs joined by branch_id across Branch and PayrollRun.",
            "labor_cost_forecast": "Forecast model using historical PayrollRun trends and planned hiring demand.",
        },
    }


@router.get("/dei")
def get_people_dei(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "workforce_demographics": {
            "gender": [
                {"name": "Female", "value": 44},
                {"name": "Male", "value": 52},
                {"name": "Non-binary", "value": 4},
            ],
            "age": [
                {"name": "18-25", "value": 16},
                {"name": "26-35", "value": 48},
                {"name": "36-45", "value": 24},
                {"name": "46+", "value": 12},
            ],
            "ethnicity": [
                {"name": "Group A", "value": 34},
                {"name": "Group B", "value": 29},
                {"name": "Group C", "value": 22},
                {"name": "Group D", "value": 15},
            ],
        },
        "dei_scorecard": {
            "score": 78,
            "representation_score": 81,
            "pay_equity_score": 75,
            "inclusion_score": 79,
        },
        "pay_equity_analysis": [
            {"role": "Radiologist", "gender_or_ethnicity": "Female", "avg_pay": 142000},
            {"role": "Radiologist", "gender_or_ethnicity": "Male", "avg_pay": 145000},
            {"role": "Lab Technician", "gender_or_ethnicity": "Female", "avg_pay": 52000},
            {"role": "Lab Technician", "gender_or_ethnicity": "Male", "avg_pay": 53500},
            {"role": "Operations Supervisor", "gender_or_ethnicity": "Group A", "avg_pay": 69000},
            {"role": "Operations Supervisor", "gender_or_ethnicity": "Group B", "avg_pay": 67600},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "demographics": "StaffProfile demographics and branch distribution attributes.",
            "dei_scorecard": "Composite of representation, retention parity, promotion parity, and pay parity.",
            "pay_equity": "Role-normalized payroll comparisons from PayrollRun and salary configurations.",
        },
    }


@router.get("/wow-features")
def get_people_wow_features(db: Session = Depends(get_db)):
    branch_labels = [row.name for row in db.query(Branch).order_by(Branch.id.asc()).limit(3).all()] or ["Mumbai", "Delhi", "Bhabua"]
    departments = ["Operations", "Diagnostics", "Front Office", "Finance", "HR"]
    heatmap = []
    for branch_index, branch_name in enumerate((branch_labels + ["Patna"])[:3]):
        for dept_index, department in enumerate(departments):
            score = 68 + ((branch_index * 7 + dept_index * 5) % 27)
            heatmap.append(
                {
                    "branch": branch_name,
                    "department": department,
                    "engagement_score": min(score, 95),
                }
            )

    return {
        "is_mock": True,
        "ceo_daily_pulse": "Good morning, Mr. Singh. Engagement is up 2%. Attrition risk in Mumbai has increased and should be monitored this week.",
        "flight_risk_employees": [
            {"employee_id": "VV-MUM-188", "name": "Rohan Mehta", "branch": "Mumbai", "role": "MRI Technologist", "tenure_months": 16, "engagement_score": 58, "risk_level": "high"},
            {"employee_id": "VV-DEL-163", "name": "Sana Khan", "branch": "Delhi", "role": "Lab Technician", "tenure_months": 11, "engagement_score": 61, "risk_level": "medium"},
            {"employee_id": "VV-BHA-141", "name": "Vikas Kumar", "branch": "Bhabua", "role": "Front Office Executive", "tenure_months": 14, "engagement_score": 60, "risk_level": "medium"},
        ],
        "culture_heatmap": heatmap,
        "default_what_if": {
            "input": "What if we increase salary of all MRI Technologists by 10%?",
            "attrition_impact_percent": -3.2,
            "workforce_cost_impact_percent": 2.8,
            "estimated_monthly_cost_increase": 145000,
            "summary": "Estimated attrition for MRI Technologists may drop by 3.2% with a 2.8% rise in total workforce cost.",
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "flight_risk": "Tenure from StaffProfile + engagement proxies from attendance consistency and manager feedback.",
            "daily_pulse": "Diff engine over day-over-day KPI movements across people analytics endpoints.",
            "culture_heatmap": "Branch x Department engagement aggregate from pulse surveys and eNPS slices.",
            "what_if": "Compensation simulation over PayrollRun costs and attrition sensitivity model.",
        },
    }


@router.get("/what-if-simulator")
def get_people_what_if_simulation(
    role_name: str = Query(default="MRI Technologists"),
    salary_increase_percent: float = Query(default=10.0, ge=0, le=50),
    db: Session = Depends(get_db),
):
    normalized_role = role_name.strip() or "Selected Role"
    increase = float(salary_increase_percent)
    workforce_cost_impact = round(0.28 * increase, 2)
    attrition_impact = round(-0.32 * increase, 2)
    monthly_cost_increase = int(14500 * (increase / 1.0))
    return {
        "is_mock": True,
        "input": f"What if we increase salary of all {normalized_role} by {increase:.1f}%?",
        "role_name": normalized_role,
        "salary_increase_percent": increase,
        "attrition_impact_percent": attrition_impact,
        "workforce_cost_impact_percent": workforce_cost_impact,
        "estimated_monthly_cost_increase": monthly_cost_increase,
        "summary": (
            f"For {normalized_role}, this scenario suggests attrition could change by {attrition_impact}% "
            f"while workforce cost may change by {workforce_cost_impact}%."
        ),
        "table_reference": _table_reference_snapshot(db),
    }
