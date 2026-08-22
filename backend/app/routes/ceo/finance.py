from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models import Branch
from app.models.branch_lis import (
    InstrumentCalibration as LISInstrumentCalibration,
    OrderQueue as LISOrderQueue,
    QCResult as LISQCResult,
    Sample as LISSample,
)
from app.utils.auth_system import auth_guard

router = APIRouter(
    prefix="/ceo/finance",
    tags=["CEO Finance & Accounts"],
    dependencies=[Depends(auth_guard.require_role(["super_admin"]))],
)


def _table_reference_snapshot(db: Session) -> dict[str, Any]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    table_map = {
        # Future real mapping:
        # daily_entries     -> revenue trajectories / operating topline
        # expense_entries   -> opex and cash outflows
        # payroll_runs      -> workforce cost contribution
        # branches          -> branch-level variance in revenue/cost
        # inventory_items   -> inventory carrying cost proxy
        "daily_entries": "daily_entries",
        "expense_entries": "expense_entries",
        "payroll_runs": "payroll_runs",
        "branches": "branches",
        "inventory_items": "inventory_items",
    }

    counts: dict[str, int] = {}
    for key, table_name in table_map.items():
        if table_name in table_names:
            count = db.execute(text(f"SELECT COUNT(*) AS c FROM {table_name}")).scalar() or 0
            counts[key] = int(count)
        else:
            counts[key] = 0

    counts["generated_at"] = datetime.utcnow().isoformat()
    return counts


@router.get("/health-score")
def get_finance_health_score(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "score": 78,
        "color": "yellow",
        "drivers": {
            "revenue_growth": 85,
            "cash_flow": 60,
            "profitability": 75,
        },
        "monthly_health_trend": [
            {"month": "Aug", "score": 66},
            {"month": "Sep", "score": 67},
            {"month": "Oct", "score": 69},
            {"month": "Nov", "score": 71},
            {"month": "Dec", "score": 72},
            {"month": "Jan", "score": 73},
            {"month": "Feb", "score": 74},
            {"month": "Mar", "score": 75},
            {"month": "Apr", "score": 76},
            {"month": "May", "score": 77},
            {"month": "Jun", "score": 78},
            {"month": "Jul", "score": 78},
        ],
        "monthly_revenue_vs_expense": [
            {"month": "Feb", "revenue": 4400000, "expense": 3120000},
            {"month": "Mar", "revenue": 4620000, "expense": 3250000},
            {"month": "Apr", "revenue": 4550000, "expense": 3310000},
            {"month": "May", "revenue": 4790000, "expense": 3380000},
            {"month": "Jun", "revenue": 4910000, "expense": 3440000},
            {"month": "Jul", "revenue": 5030000, "expense": 3510000},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "health_score": "Composite from daily_entries + expense_entries + payroll_runs trends.",
            "revenue_growth": "Month-over-month growth from daily_entries.",
            "cash_flow": "Net inflow/outflow from expense_entries and collections.",
            "profitability": "Revenue less direct and overhead costs (expense_entries + payroll_runs + inventory).",
        },
    }


@router.get("/cash-liquidity")
def get_finance_cash_liquidity(db: Session = Depends(get_db)):
    cash_in_hand = 2850000
    cash_in_bank = 9650000
    total_liquidity = cash_in_hand + cash_in_bank
    threshold = 5000000
    return {
        "is_mock": True,
        "cash_position": {
            "cash_in_hand": cash_in_hand,
            "cash_in_bank": cash_in_bank,
            "total_available_liquidity": total_liquidity,
        },
        "forecast_30_60_90": [
            {"day": "Day 0", "inflow": 0, "outflow": 0},
            {"day": "Day 30", "inflow": 4100000, "outflow": 3620000},
            {"day": "Day 60", "inflow": 4380000, "outflow": 3870000},
            {"day": "Day 90", "inflow": 4520000, "outflow": 4090000},
        ],
        "cash_burn_rate_per_month": 1180000,
        "runway_months": 10.6,
        "liquidity_threshold": threshold,
        "zero_balance_alert": {
            "enabled": total_liquidity < threshold,
            "message": "Liquidity has fallen below threshold. Activate cash conservation plan immediately.",
        },
        "operating_cash_flow": {
            "value": 1740000,
            "score": 73,
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "cash_position": "Branch cash + bank ledgers and reconciliations.",
            "forecast": "Rolling model using recent collection velocity and payable schedules.",
            "burn_rate_runway": "Expense trajectory from expense_entries + payroll_runs.",
            "operating_cash_flow": "Cash generated from core operations after operating expenses.",
        },
    }


@router.get("/profitability-revenue")
def get_finance_profitability_revenue(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "consolidated_pnl": {
            "current_month": {
                "revenue": 5030000,
                "expenses": 3510000,
                "net_profit": 1520000,
            },
            "ytd": {
                "revenue": 31700000,
                "expenses": 22600000,
                "net_profit": 9100000,
            },
        },
        "branch_profitability": [
            {"branch": "Mumbai", "revenue": 12600000, "expenses": 8650000, "net_profit": 3950000},
            {"branch": "Delhi", "revenue": 9900000, "expenses": 7330000, "net_profit": 2570000},
            {"branch": "Patna", "revenue": 4600000, "expenses": 3370000, "net_profit": 1230000},
            {"branch": "Bhabua", "revenue": 4600000, "expenses": 3250000, "net_profit": 1350000},
        ],
        "test_profitability": [
            {"test_type": "MRI", "profitability": 36},
            {"test_type": "CT Scan", "profitability": 25},
            {"test_type": "Blood MenuItems", "profitability": 22},
            {"test_type": "Ultrasound", "profitability": 17},
        ],
        "revenue_per_unit": {
            "avg_revenue_per_patient": 2450,
            "avg_revenue_per_test": 1280,
        },
        "ebitda": {
            "value": 11400000,
            "margin_percent": 36.0,
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "consolidated_pnl": "Revenue from daily_entries; expenses from expense_entries + payroll_runs + inventory costs.",
            "branch_profitability": "Branch-level P&L roll-up from Branch + DailyEntry + Expense + PayrollRun.",
            "test_profitability": "MenuItem-level contribution margin from LIS test volumes and direct variable costs.",
            "revenue_per_unit": "Revenue divided by unique customers/menu_items from operations and billing logs.",
            "ebitda": "Earnings before interest, taxes, depreciation, amortization from consolidated operating results.",
        },
    }


@router.get("/receivables-cycle")
def get_finance_receivables_cycle(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "ar_aging": [
            {"bucket": "0-30 days", "amount": 1820000},
            {"bucket": "31-60 days", "amount": 1260000},
            {"bucket": "61-90 days", "amount": 780000},
            {"bucket": "90+ days", "amount": 430000},
        ],
        "collection_effectiveness_index_percent": 84.5,
        "bad_debt_ratio_percent": 2.4,
        "insurance_vs_self_pay_mix": [
            {"payer_type": "Insurance", "value": 58},
            {"payer_type": "Self-Pay", "value": 42},
        ],
        "days_sales_outstanding": 46,
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "ar_aging": "Outstanding invoices by due-date buckets from invoice and payment tables.",
            "cei": "Collections effectiveness from opening AR, credit sales, and closing AR.",
            "bad_debt_ratio": "Revenue write-offs relative to recognized revenue.",
            "payer_mix": "Insurance and self-pay split from billing and settlement source tables.",
            "dso": "Average collection period derived from AR and net credit sales.",
        },
    }


@router.get("/cost-control")
def get_finance_cost_control(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "expense_breakdown": [
            {"category": "Salaries", "amount": 14200000},
            {"category": "Reagents", "amount": 3650000},
            {"category": "Equipment Maintenance", "amount": 1720000},
            {"category": "Rent", "amount": 2980000},
            {"category": "Utilities", "amount": 1180000},
            {"category": "Marketing", "amount": 930000},
        ],
        "branch_cost_comparison": [
            {"branch": "Mumbai", "cost": 8650000},
            {"branch": "Delhi", "cost": 7330000},
            {"branch": "Patna", "cost": 3370000},
            {"branch": "Bhabua", "cost": 3250000},
        ],
        "cost_per_unit": {
            "avg_cost_per_test": 780,
            "avg_cost_per_patient": 1560,
        },
        "vendor_spend_analysis": [
            {"vendor": "MedChem Reagents Pvt Ltd", "category": "Reagents", "total_spend": 1820000},
            {"vendor": "BioScan Equipment Services", "category": "Maintenance", "total_spend": 1280000},
            {"vendor": "Prime Diagnostics Supplies", "category": "Consumables", "total_spend": 960000},
            {"vendor": "Lifeline Facility Management", "category": "Utilities", "total_spend": 740000},
        ],
        "cost_to_income_ratio_percent": 71.3,
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "expense_breakdown": "Expense category totals from expense_entries + payroll_runs + inventory purchase costs.",
            "branch_cost_comparison": "Branch-aligned costs from branch-mapped expenses and payroll distribution.",
            "cost_per_unit": "Total operating cost divided by total test count and patient count.",
            "vendor_spend": "Vendor-linked payables and procurement ledger entries.",
            "cost_to_income_ratio": "Total expenses / total revenue from consolidated finance feeds.",
        },
    }


@router.get("/compliance-taxation")
def get_finance_compliance_taxation(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "tax_compliance": [
            {"tax_type": "GST", "status": "Filled", "period": "Jul 2026", "due_date": "2026-08-20"},
            {"tax_type": "TDS", "status": "Pending", "period": "Jul 2026", "due_date": "2026-08-07"},
            {"tax_type": "Professional Tax", "status": "Overdue", "period": "Jun 2026", "due_date": "2026-07-15"},
        ],
        "pf_esi_compliance": [
            {"compliance_type": "PF", "employee_contribution": 560000, "employer_contribution": 560000, "due_date": "2026-08-15", "status": "Pending"},
            {"compliance_type": "ESI", "employee_contribution": 128000, "employer_contribution": 128000, "due_date": "2026-08-15", "status": "Pending"},
        ],
        "license_tracker": [
            {"license_name": "NABL Accreditation", "expiry_date": "2027-01-20", "status": "Valid", "renewal_alert": False},
            {"license_name": "ISO 15189", "expiry_date": "2026-11-05", "status": "Expiring Soon", "renewal_alert": True},
            {"license_name": "Biomedical Waste Authorization", "expiry_date": "2026-09-12", "status": "Expiring Soon", "renewal_alert": True},
            {"license_name": "Clinical Establishment Registration", "expiry_date": "2026-07-30", "status": "Urgent Renewal", "renewal_alert": True},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "tax_compliance": "Tax filing records and statutory schedules from compliance ledger.",
            "pf_esi": "Payroll statutory contribution outputs mapped per filing cycle.",
            "license_tracker": "License registry with renewal workflow and SLA alerts.",
        },
    }


@router.get("/predictive-analytics")
def get_finance_predictive_analytics(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "revenue_forecast": [
            {"month": "Aug", "projected_revenue": 5180000},
            {"month": "Sep", "projected_revenue": 5270000},
            {"month": "Oct", "projected_revenue": 5380000},
            {"month": "Nov", "projected_revenue": 5460000},
            {"month": "Dec", "projected_revenue": 5590000},
            {"month": "Jan", "projected_revenue": 5710000},
            {"month": "Feb", "projected_revenue": 5830000},
            {"month": "Mar", "projected_revenue": 5960000},
        ],
        "profitability_forecast": [
            {"month": "Aug", "projected_net_profit": 1560000},
            {"month": "Sep", "projected_net_profit": 1610000},
            {"month": "Oct", "projected_net_profit": 1660000},
            {"month": "Nov", "projected_net_profit": 1700000},
            {"month": "Dec", "projected_net_profit": 1750000},
            {"month": "Jan", "projected_net_profit": 1790000},
            {"month": "Feb", "projected_net_profit": 1840000},
            {"month": "Mar", "projected_net_profit": 1890000},
        ],
        "risk_alerts": [
            {
                "severity": "high",
                "title": "Mumbai cost overrun risk",
                "message": "Warning: Mumbai branch is projecting a 10% cost overrun this quarter.",
            },
            {
                "severity": "medium",
                "title": "Collection cycle slowdown",
                "message": "DSO is trending upward and may cross 50 days if payer follow-ups are delayed.",
            },
            {
                "severity": "medium",
                "title": "Reagent price volatility",
                "message": "Two major vendors indicated a possible 6-8% pricing increase next cycle.",
            },
        ],
        "automated_financial_commentary": (
            "Revenue is up 5% month-on-month with steady EBITDA improvement. "
            "However, accounts receivable pressure remains elevated as DSO tracks at 46 days. "
            "Cost discipline in Mumbai and faster insurance collections are recommended."
        ),
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "revenue_forecast": "Rolling forecast from daily_entries trends, seasonality, and branch growth assumptions.",
            "profitability_forecast": "Projected net profit from forecasted revenue minus modeled expense and payroll trajectories.",
            "risk_alerts": "Rule and model-based anomaly detection from branch variance, AR movement, and vendor spend spikes.",
            "automated_commentary": "Narrative generation from changes in KPI deltas across health, liquidity, AR, and profitability.",
        },
    }


@router.get("/doctor-referral-financials")
def get_finance_doctor_referral_financials(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "referral_revenue_breakdown": [
            {"doctor_name": "Dr. R. Sharma", "revenue": 1320000},
            {"doctor_name": "Dr. P. Verma", "revenue": 1140000},
            {"doctor_name": "Dr. A. Khan", "revenue": 960000},
            {"doctor_name": "Dr. N. Iyer", "revenue": 845000},
            {"doctor_name": "Dr. S. Menon", "revenue": 790000},
        ],
        "doctor_commission_tracking": [
            {"doctor_name": "Dr. R. Sharma", "referred_revenue": 1320000, "commission_percent": 8, "commission_earned": 105600},
            {"doctor_name": "Dr. P. Verma", "referred_revenue": 1140000, "commission_percent": 7, "commission_earned": 79800},
            {"doctor_name": "Dr. A. Khan", "referred_revenue": 960000, "commission_percent": 7, "commission_earned": 67200},
            {"doctor_name": "Dr. N. Iyer", "referred_revenue": 845000, "commission_percent": 6, "commission_earned": 50700},
            {"doctor_name": "Dr. S. Menon", "referred_revenue": 790000, "commission_percent": 6, "commission_earned": 47400},
        ],
        "referral_cost_percent_of_revenue": 6.8,
        "doctor_wise_profitability": [
            {"doctor_name": "Dr. R. Sharma", "revenue": 1320000, "referral_cost": 105600, "service_cost": 694000, "net_profit": 520400},
            {"doctor_name": "Dr. P. Verma", "revenue": 1140000, "referral_cost": 79800, "service_cost": 621000, "net_profit": 439200},
            {"doctor_name": "Dr. A. Khan", "revenue": 960000, "referral_cost": 67200, "service_cost": 533000, "net_profit": 359800},
            {"doctor_name": "Dr. N. Iyer", "revenue": 845000, "referral_cost": 50700, "service_cost": 472000, "net_profit": 322300},
            {"doctor_name": "Dr. S. Menon", "revenue": 790000, "referral_cost": 47400, "service_cost": 446000, "net_profit": 296600},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "referral_revenue": "Staff-linked referral revenue from DailyEntry/LIS billing joins.",
            "commission_tracking": "Commission payouts from payroll_runs + doctor incentive schedules.",
            "referral_cost_ratio": "Total referral commissions divided by recognized referral-attributed revenue.",
            "doctor_profitability": "Staff-level margin from referral revenue minus referral and service delivery costs.",
        },
    }


@router.get("/cfo-briefing")
def get_finance_cfo_briefing(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "title": "Automated CFO Briefing",
        "generated_at": datetime.utcnow().isoformat(),
        "brief": (
            "Good morning, Mr. Singh. Cash flow is projected to dip below threshold in 45 days. "
            "Recommend delaying major equipment purchase by 30 days and accelerating high-value insurance collections."
        ),
        "highlights": [
            {"label": "Liquidity Risk Window", "value": "45 days"},
            {"label": "Projected Revenue Growth", "value": "+5.4% MoM"},
            {"label": "Expected DSO", "value": "48 days"},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "briefing_text": "Narrative generated from cash, AR, profitability, and branch variance signals.",
            "highlights": "Top KPI deltas from finance section endpoints and trend models.",
        },
    }


@router.get("/branch-profitability-heatmap")
def get_finance_branch_profitability_heatmap(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "items": [
            {"branch": "Mumbai", "profitability_score": 82, "status": "profitable"},
            {"branch": "Delhi", "profitability_score": 74, "status": "break_even"},
            {"branch": "Patna", "profitability_score": 63, "status": "break_even"},
            {"branch": "Bhabua", "profitability_score": 48, "status": "loss_making"},
            {"branch": "Ranchi", "profitability_score": 79, "status": "profitable"},
            {"branch": "Lucknow", "profitability_score": 57, "status": "loss_making"},
        ],
        "legend": {
            "profitable": "Green",
            "break_even": "Yellow",
            "loss_making": "Red",
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "profitability_status": "Branch P&L contribution from daily_entries, expense_entries, and payroll_runs.",
            "profitability_score": "Normalized branch profitability index over rolling period.",
        },
    }


@router.get("/what-if-simulator")
def get_finance_what_if_simulator(
    city: str = "Pune",
    discount_percent: float = 5.0,
    db: Session = Depends(get_db),
):
    normalized_discount = max(discount_percent, 0)
    projected_revenue_impact_percent = round(4.6 - (normalized_discount * 0.25), 2)
    projected_cost_impact_percent = round(2.1 + (normalized_discount * 0.14), 2)
    projected_net_profit_impact_percent = round(
        projected_revenue_impact_percent - projected_cost_impact_percent, 2
    )

    return {
        "is_mock": True,
        "scenario": f"Open a new branch in {city} with {normalized_discount:.1f}% introductory discount.",
        "inputs": {
            "city": city,
            "discount_percent": normalized_discount,
        },
        "projections": {
            "projected_revenue_impact_percent": projected_revenue_impact_percent,
            "projected_cost_impact_percent": projected_cost_impact_percent,
            "projected_net_profit_impact_percent": projected_net_profit_impact_percent,
            "estimated_monthly_revenue_delta": 520000,
            "estimated_monthly_cost_delta": 340000,
        },
        "ai_summary": (
            f"Scenario indicates positive topline growth in {city} despite discounting. "
            f"Revenue may change by {projected_revenue_impact_percent:.2f}% and cost by "
            f"{projected_cost_impact_percent:.2f}%, with net profit impact of "
            f"{projected_net_profit_impact_percent:.2f}%."
        ),
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "revenue_impact": "Demand simulation driven by branch opening assumptions and historical city growth.",
            "cost_impact": "Modeled opex/payout uplift from staffing, rent, utilities, and discount effects.",
            "net_profit_impact": "Projected incremental P&L after discount and launch period effects.",
        },
    }


def _lis_qc_status_label(failure_rate: float) -> str:
    if failure_rate <= 2:
        return "Good"
    if failure_rate <= 7:
        return "Watch"
    return "Critical"


def _lis_sample_pending(sample: LISSample) -> bool:
    return sample.status not in {"Ordered", "Rejected"}


def _lis_average_tat_minutes(samples: list[LISSample]) -> float:
    durations: list[float] = []
    for sample in samples:
        if sample.started_at and sample.completed_at:
            durations.append((sample.completed_at - sample.started_at).total_seconds() / 60.0)
        elif sample.registered_at and sample.reported_at:
            durations.append((sample.reported_at - sample.registered_at).total_seconds() / 60.0)
    if not durations:
        return 0.0
    return round(sum(durations) / len(durations), 2)


@router.get("/lis-operations-overview")
def get_finance_lis_operations_overview(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    qc_start = now - timedelta(days=30)

    branches = db.query(Branch).order_by(Branch.name.asc()).all()
    orders = db.query(LISOrderQueue).all()
    samples = db.query(LISSample).all()
    qc_rows = db.query(LISQCResult).filter(LISQCResult.created_at >= qc_start).all()
    calibrations = db.query(LISInstrumentCalibration).all()

    orders_by_branch: dict[int, list[LISOrderQueue]] = defaultdict(list)
    samples_by_branch: dict[int, list[LISSample]] = defaultdict(list)
    qc_by_branch: dict[int, list[LISQCResult]] = defaultdict(list)
    calibration_by_branch: dict[int, list[LISInstrumentCalibration]] = defaultdict(list)

    for row in orders:
        orders_by_branch[int(row.branch_id)].append(row)
    for row in samples:
        samples_by_branch[int(row.branch_id)].append(row)
    for row in qc_rows:
        qc_by_branch[int(row.branch_id)].append(row)
    for row in calibrations:
        calibration_by_branch[int(row.branch_id)].append(row)

    branch_metrics: list[dict[str, Any]] = []
    smart_alerts: list[dict[str, str]] = []
    branch_overdue_count = 0

    for branch in branches:
        branch_orders = orders_by_branch.get(branch.id, [])
        branch_samples = samples_by_branch.get(branch.id, [])
        branch_qc = qc_by_branch.get(branch.id, [])
        branch_calibrations = calibration_by_branch.get(branch.id, [])

        today_test_volume = sum(1 for row in branch_orders if row.created_at and row.created_at >= today_start)
        pending_samples = [row for row in branch_samples if _lis_sample_pending(row)]
        reported_samples = sum(1 for row in branch_samples if row.status == "Ordered")
        rejected_count = sum(1 for row in branch_samples if row.status == "Rejected")
        sample_rejection_rate = round((rejected_count / len(branch_samples) * 100.0), 2) if branch_samples else 0.0
        average_tat_minutes = _lis_average_tat_minutes(branch_samples)

        qc_failures = sum(1 for row in branch_qc if (row.qc_status or "").lower() == "failed")
        qc_failure_rate = round((qc_failures / len(branch_qc) * 100.0), 2) if branch_qc else 0.0
        qc_status = _lis_qc_status_label(qc_failure_rate)

        overdue_calibrations = [
            row
            for row in branch_calibrations
            if (row.next_due_at and row.next_due_at < now) or (row.calibration_status or "").strip().lower() in {"due", "overdue"}
        ]
        if overdue_calibrations:
            branch_overdue_count += 1

        health_score = 100
        health_score -= min(20, int(len(pending_samples) * 0.8))
        health_score -= min(20, int(max(average_tat_minutes - 180.0, 0.0) / 30))
        health_score -= min(20, int(qc_failure_rate * 1.4))
        health_score -= min(20, int(sample_rejection_rate * 1.2))
        if overdue_calibrations:
            health_score -= min(15, len(overdue_calibrations) * 3)
        health_score = max(0, min(100, health_score))

        branch_metrics.append(
            {
                "branch_id": branch.id,
                "branch_name": branch.name,
                "today_test_volume": today_test_volume,
                "reported_samples": reported_samples,
                "pending_samples": len(pending_samples),
                "average_tat_minutes": average_tat_minutes,
                "qc_failure_rate": qc_failure_rate,
                "qc_status": qc_status,
                "sample_rejection_rate": sample_rejection_rate,
                "health_score": health_score,
            }
        )

        if len(pending_samples) >= 25:
            smart_alerts.append(
                {
                    "severity": "high",
                    "title": f"{branch.name}: pending queue pressure",
                    "message": f"{len(pending_samples)} samples are pending in LIS workflow.",
                }
            )
        if qc_failure_rate > 7:
            smart_alerts.append(
                {
                    "severity": "high",
                    "title": f"{branch.name}: QC risk escalation",
                    "message": f"QC failure rate is {qc_failure_rate:.1f}% over the last 30 days.",
                }
            )
        if overdue_calibrations:
            smart_alerts.append(
                {
                    "severity": "medium",
                    "title": f"{branch.name}: calibration overdue",
                    "message": f"{len(overdue_calibrations)} analyzer calibration entries need action.",
                }
            )

    all_samples = samples
    all_qc_rows = qc_rows
    network_today_test_volume = sum(item["today_test_volume"] for item in branch_metrics)
    network_pending_menu_items = sum(item["pending_samples"] for item in branch_metrics)
    network_rejected = sum(1 for row in all_samples if row.status == "Rejected")
    network_rejection_rate = round((network_rejected / len(all_samples) * 100.0), 2) if all_samples else 0.0
    network_avg_tat = _lis_average_tat_minutes(all_samples)
    network_qc_failures = sum(1 for row in all_qc_rows if (row.qc_status or "").lower() == "failed")
    network_qc_failure_rate = round((network_qc_failures / len(all_qc_rows) * 100.0), 2) if all_qc_rows else 0.0

    readiness_score = 100
    readiness_score -= min(25, int(network_pending_menu_items * 0.6))
    readiness_score -= min(25, int(network_qc_failure_rate * 1.4))
    readiness_score -= min(20, branch_overdue_count * 5)
    readiness_score -= min(15, int(max(network_avg_tat - 180.0, 0.0) / 40))
    readiness_score = max(0, min(100, readiness_score))

    return {
        "is_mock": False,
        "generated_at": now.isoformat(),
        "network_summary": {
            "today_test_volume": network_today_test_volume,
            "average_tat_minutes": network_avg_tat,
            "pending_menu_items": network_pending_menu_items,
            "sample_rejection_rate": network_rejection_rate,
            "qc_status": _lis_qc_status_label(network_qc_failure_rate),
            "readiness_score": readiness_score,
        },
        "branch_metrics": branch_metrics,
        "smart_alerts": smart_alerts[:12],
        "table_reference": {
            "branches": len(branches),
            "lis_orders": len(orders),
            "lis_samples": len(samples),
            "qc_results_30d": len(qc_rows),
            "calibration_logs": len(calibrations),
            "generated_at": now.isoformat(),
        },
        "future_data_mapping": {
            "today_test_volume": "branch_lis_order_queue created today",
            "average_tat_minutes": "branch_lis_samples lifecycle timestamps",
            "pending_menu_items": "branch_lis_samples statuses not Ordered/Rejected",
            "qc_status": "branch_lis_qc_results failure trend",
            "readiness_score": "composite of pending, TAT, QC and calibration exposure",
        },
    }
