from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, DailyEntry, InventoryItem
from app.models.audit_log import AuditLog
from app.models.inventory import Supplier
from app.utils.auth_system import auth_guard

router = APIRouter(
    prefix="/ceo/inventory",
    tags=["CEO Inventory & Supply Chain"],
    dependencies=[Depends(auth_guard.require_role(["super_admin"]))],
)


def _table_reference_snapshot(db: Session) -> dict[str, Any]:
    def _safe_count(model: Any, label: str) -> int:
        try:
            return int(db.query(func.count(model.id)).scalar() or 0)
        except Exception as exc:
            print(f"⚠️ [CEO_INVENTORY_TABLE_REFERENCE] Falling back {label}=0 due to: {exc}")
            return 0

    return {
        "inventory_items_count": _safe_count(InventoryItem, "inventory_items_count"),
        "branches_count": _safe_count(Branch, "branches_count"),
        "daily_entries_count": _safe_count(DailyEntry, "daily_entries_count"),
        "suppliers_count": _safe_count(Supplier, "suppliers_count"),
        "audit_logs_count": _safe_count(AuditLog, "audit_logs_count"),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/health-score")
def get_inventory_health_score(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Ranchi", "Lucknow"])[:4]

    return {
        "is_mock": True,
        "score": 82,
        "stock_availability_rate_percent": 94,
        "expiry_risk_dashboard": [
            {
                "item_name": "PCR Reagent Kit A",
                "branch": padded_branch_labels[0],
                "batch_number": "B-PR-8821",
                "days_to_expiry": 6,
                "risk_level": "Expiring in 7 days",
                "current_stock": 12,
            },
            {
                "item_name": "Contrast Media 100ml",
                "branch": padded_branch_labels[1],
                "batch_number": "B-CM-3491",
                "days_to_expiry": 19,
                "risk_level": "Expiring in 30 days",
                "current_stock": 34,
            },
            {
                "item_name": "CBC Control Serum",
                "branch": padded_branch_labels[2],
                "batch_number": "B-CS-2204",
                "days_to_expiry": 27,
                "risk_level": "Expiring in 30 days",
                "current_stock": 18,
            },
        ],
        "wastage": {
            "rate_percent": 2.5,
            "cost": 184000,
        },
        "inventory_turnover_ratio": 6.4,
        "days_on_hand": 45,
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "health_score": "Composite signal from availability, expiries, wastage, stockout events, and replenishment SLA.",
            "stock_availability": "Critical SKU in-stock percentage by branch and department from inventory items.",
            "expiry_risk": "Batch-level expiry windows and depletion velocity from inventory lot tracking.",
            "wastage": "Damaged/expired/adjusted-out quantity multiplied by weighted unit cost.",
            "turnover_ratio_doh": "Usage over average inventory value from daily consumption and opening/closing stock.",
        },
    }


@router.get("/stock-consumption-analytics")
def get_inventory_stock_consumption_analytics(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Ranchi", "Lucknow"])[:4]

    return {
        "is_mock": True,
        "multi_location_stock_view": [
            {"branch": padded_branch_labels[0], "item_name": "PCR Reagent Kit A", "current_stock": 56, "reorder_point": 22},
            {"branch": padded_branch_labels[1], "item_name": "PCR Reagent Kit A", "current_stock": 48, "reorder_point": 20},
            {"branch": padded_branch_labels[2], "item_name": "PCR Reagent Kit A", "current_stock": 35, "reorder_point": 20},
            {"branch": padded_branch_labels[3], "item_name": "PCR Reagent Kit A", "current_stock": 19, "reorder_point": 18},
        ],
        "daily_consumption_monitoring": {
            "high_value_items": [
                {"day": "Mon", "actual_usage": 14, "expected_usage": 12},
                {"day": "Tue", "actual_usage": 11, "expected_usage": 12},
                {"day": "Wed", "actual_usage": 15, "expected_usage": 13},
                {"day": "Thu", "actual_usage": 12, "expected_usage": 13},
                {"day": "Fri", "actual_usage": 16, "expected_usage": 14},
                {"day": "Sat", "actual_usage": 13, "expected_usage": 12},
                {"day": "Sun", "actual_usage": 10, "expected_usage": 9},
            ],
            "fast_moving_items": [
                {"day": "Mon", "actual_usage": 86, "expected_usage": 82},
                {"day": "Tue", "actual_usage": 88, "expected_usage": 84},
                {"day": "Wed", "actual_usage": 92, "expected_usage": 86},
                {"day": "Thu", "actual_usage": 90, "expected_usage": 87},
                {"day": "Fri", "actual_usage": 97, "expected_usage": 90},
                {"day": "Sat", "actual_usage": 94, "expected_usage": 89},
                {"day": "Sun", "actual_usage": 78, "expected_usage": 76},
            ],
        },
        "high_value_reagent_movement": [
            {"reagent_name": "Contrast Media 100ml", "used_by": "Lab Tech R. Singh", "used_on": "2026-07-25 10:32", "test_name": "CT Scan", "quantity": 3, "branch": padded_branch_labels[0]},
            {"reagent_name": "PCR Reagent Kit A", "used_by": "Lab Tech N. Das", "used_on": "2026-07-25 11:10", "test_name": "PCR Panel", "quantity": 2, "branch": padded_branch_labels[1]},
            {"reagent_name": "MRI Contrast Set", "used_by": "Lab Tech A. Khan", "used_on": "2026-07-25 15:44", "test_name": "MRI Brain", "quantity": 1, "branch": padded_branch_labels[2]},
        ],
        "inventory_velocity_mix": [
            {"category": "Fast-Moving", "value": 58},
            {"category": "Medium-Moving", "value": 27},
            {"category": "Slow-Moving", "value": 15},
        ],
        "stockout_alerts": [
            {"item_name": "EDTA Tube 2ml", "branch": padded_branch_labels[3], "current_stock": 42, "reorder_point": 60, "severity": "high"},
            {"item_name": "HbA1c Cartridge", "branch": padded_branch_labels[2], "current_stock": 16, "reorder_point": 20, "severity": "medium"},
        ],
        "min_max_stock_levels": [
            {"item_name": "PCR Reagent Kit A", "branch": padded_branch_labels[0], "minimum_stock": 22, "maximum_stock": 120, "current_stock": 56},
            {"item_name": "Contrast Media 100ml", "branch": padded_branch_labels[1], "minimum_stock": 18, "maximum_stock": 95, "current_stock": 48},
            {"item_name": "EDTA Tube 2ml", "branch": padded_branch_labels[3], "minimum_stock": 60, "maximum_stock": 260, "current_stock": 42},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "multi_location_stock": "SKU-level branch stock, reorder points, and inter-branch transfers from inventory ledgers.",
            "consumption_monitoring": "Actual issue quantities against expected demand models by item class.",
            "reagent_movement": "User-wise movement logs linked to menu_items and order events.",
            "velocity_mix": "Consumption velocity segmentation by moving average usage and shelf age.",
            "stockout_alerts": "Critical SKU below reorder threshold events with escalation rules.",
            "min_max_levels": "Configured min/max policy with current stock compliance state.",
        },
    }


@router.get("/procurement-vendor-management")
def get_inventory_procurement_vendor_management(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Ranchi", "Lucknow"])[:4]

    return {
        "is_mock": True,
        "procurement_dashboard": [
            {
                "po_number": "PO-2026-1041",
                "vendor_name": "MedChem Reagents Pvt Ltd",
                "branch": padded_branch_labels[0],
                "status": "Pending Approval",
                "expected_delivery_date": "2026-07-31",
                "order_value": 420000,
            },
            {
                "po_number": "PO-2026-1035",
                "vendor_name": "Prime Diagnostics Supplies",
                "branch": padded_branch_labels[1],
                "status": "In Transit",
                "expected_delivery_date": "2026-07-29",
                "order_value": 275000,
            },
            {
                "po_number": "PO-2026-1028",
                "vendor_name": "BioScan Equipment Services",
                "branch": padded_branch_labels[2],
                "status": "Partially Received",
                "expected_delivery_date": "2026-08-02",
                "order_value": 640000,
            },
        ],
        "vendor_performance_scorecard": [
            {
                "vendor_name": "MedChem Reagents Pvt Ltd",
                "on_time_delivery_rate_percent": 93,
                "rejection_rate_percent": 1.8,
                "pricing_competitiveness_score": 86,
                "responsiveness_score": 90,
            },
            {
                "vendor_name": "Prime Diagnostics Supplies",
                "on_time_delivery_rate_percent": 89,
                "rejection_rate_percent": 2.4,
                "pricing_competitiveness_score": 82,
                "responsiveness_score": 84,
            },
            {
                "vendor_name": "BioScan Equipment Services",
                "on_time_delivery_rate_percent": 78,
                "rejection_rate_percent": 3.9,
                "pricing_competitiveness_score": 74,
                "responsiveness_score": 72,
            },
        ],
        "jit_reorder_suggestions": [
            {"item_name": "PCR Reagent Kit A", "suggested_reorder_qty": 46, "confidence_percent": 91, "reason": "Usage trend + lead time threshold breached in 6 days."},
            {"item_name": "EDTA Tube 2ml", "suggested_reorder_qty": 380, "confidence_percent": 88, "reason": "Fast-moving item projected below safety stock by weekend."},
            {"item_name": "Contrast Media 100ml", "suggested_reorder_qty": 72, "confidence_percent": 84, "reason": "CT scan bookings up 11% over last 14 days."},
        ],
        "supplier_diversification_risk": [
            {"item_name": "MRI Contrast Set", "criticality": "High", "active_suppliers": 1, "risk_level": "High"},
            {"item_name": "PCR Reagent Kit A", "criticality": "High", "active_suppliers": 2, "risk_level": "Medium"},
            {"item_name": "Specialized Biopsy Needles", "criticality": "Medium", "active_suppliers": 1, "risk_level": "High"},
        ],
        "sku_rationalization": [
            {"sku_group": "Syringe 5ml variants", "items_in_group": 4, "recommended_action": "Consolidate to 2 SKUs", "estimated_monthly_savings": 18000},
            {"sku_group": "CBC Control Serum brands", "items_in_group": 3, "recommended_action": "Consolidate to 1 preferred vendor", "estimated_monthly_savings": 24000},
            {"sku_group": "Vacutainer tube alternatives", "items_in_group": 5, "recommended_action": "Reduce low-moving duplicates", "estimated_monthly_savings": 14000},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "procurement_dashboard": "Purchase order lifecycle from procurement system and GRN matching.",
            "vendor_scorecard": "Delivery SLA, quality rejection records, price variance, and response SLA.",
            "jit_reordering": "Forecasted reorder quantity from demand patterns and supplier lead time.",
            "diversification_risk": "Critical SKU dependency graph on supplier concentration.",
            "sku_rationalization": "Duplicate SKU detection by usage overlap, pricing, and specification match.",
        },
    }


@router.get("/logistics-cold-chain")
def get_inventory_logistics_cold_chain(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Ranchi", "Lucknow"])[:4]

    return {
        "is_mock": True,
        "cold_chain_monitoring": {
            "active_shipments": 18,
            "within_range_percent": 94,
            "temperature_alerts": [
                {"shipment_id": "CC-8821", "route": f"{padded_branch_labels[0]} → {padded_branch_labels[2]}", "current_temp_c": 10.2, "allowed_range": "2°C to 8°C", "severity": "high"},
                {"shipment_id": "CC-8814", "route": f"{padded_branch_labels[1]} → {padded_branch_labels[3]}", "current_temp_c": 8.6, "allowed_range": "2°C to 8°C", "severity": "medium"},
            ],
        },
        "sample_specimen_logistics": [
            {"sample_id": "SP-22031", "from_branch": padded_branch_labels[3], "to_lab": padded_branch_labels[0], "courier_status": "In Transit", "estimated_arrival": "2026-07-26 10:20"},
            {"sample_id": "SP-22032", "from_branch": padded_branch_labels[2], "to_lab": padded_branch_labels[1], "courier_status": "Picked Up", "estimated_arrival": "2026-07-26 09:55"},
            {"sample_id": "SP-22018", "from_branch": padded_branch_labels[1], "to_lab": padded_branch_labels[1], "courier_status": "Delivered", "estimated_arrival": "2026-07-26 08:40"},
        ],
        "branch_logistics_performance": [
            {"branch": padded_branch_labels[0], "avg_delivery_time_minutes": 74, "sample_rejection_rate_percent": 1.9, "courier_performance_score": 90},
            {"branch": padded_branch_labels[1], "avg_delivery_time_minutes": 88, "sample_rejection_rate_percent": 2.2, "courier_performance_score": 84},
            {"branch": padded_branch_labels[2], "avg_delivery_time_minutes": 96, "sample_rejection_rate_percent": 2.8, "courier_performance_score": 79},
            {"branch": padded_branch_labels[3], "avg_delivery_time_minutes": 81, "sample_rejection_rate_percent": 2.1, "courier_performance_score": 86},
        ],
        "fleet_route_optimization": {
            "status": "available",
            "message": "AI route optimization suggests regrouping 2 courier loops to cut fuel cost by 8.5% and improve ETA by 12 minutes.",
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "cold_chain": "IoT shipment telemetry and threshold breach events by route.",
            "sample_logistics": "Sample pickup-to-lab chain from courier manifests and lab intake timestamps.",
            "branch_logistics_performance": "Branch-level transport SLA, rejection trend, and courier scorecards.",
            "route_optimization": "Route planning engine using trip density, distance, and service windows.",
        },
    }


@router.get("/financial-impact-cost-control")
def get_inventory_financial_impact_cost_control(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Ranchi", "Lucknow"])[:4]

    return {
        "is_mock": True,
        "inventory_carrying_cost": 1285000,
        "inventory_cost_per_test": 186,
        "vendor_spend_analysis": [
            {"vendor_name": "MedChem Reagents Pvt Ltd", "category": "Reagents", "branch": padded_branch_labels[0], "spend": 1820000},
            {"vendor_name": "Prime Diagnostics Supplies", "category": "Consumables", "branch": padded_branch_labels[1], "spend": 1370000},
            {"vendor_name": "BioScan Equipment Services", "category": "Maintenance", "branch": padded_branch_labels[2], "spend": 1210000},
            {"vendor_name": "Lifeline Facility Management", "category": "Storage & Utilities", "branch": padded_branch_labels[3], "spend": 780000},
        ],
        "procurement_savings_tracker": {
            "savings_realized": 364000,
            "negotiation_savings": 142000,
            "bulk_purchase_savings": 163000,
            "sku_rationalization_savings": 59000,
        },
        "budget_vs_actual_inventory": [
            {"month": "Feb", "budget": 1480000, "actual": 1410000},
            {"month": "Mar", "budget": 1500000, "actual": 1525000},
            {"month": "Apr", "budget": 1490000, "actual": 1470000},
            {"month": "May", "budget": 1520000, "actual": 1560000},
            {"month": "Jun", "budget": 1540000, "actual": 1505000},
            {"month": "Jul", "budget": 1550000, "actual": 1530000},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "carrying_cost": "Storage, insurance, and working capital cost over average inventory value.",
            "cost_per_test": "Inventory consumption cost allocated by test mix and volume.",
            "vendor_spend": "Vendor payments split by category and branch from procurement ledger.",
            "savings_tracker": "Savings baseline from negotiated price deltas and SKU consolidation.",
            "budget_vs_actual": "Planned inventory budget vs realized spend by accounting period.",
        },
    }


@router.get("/compliance-quality-control")
def get_inventory_compliance_quality_control(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id.asc()).limit(4).all()
    branch_labels = [branch.name for branch in branches] or ["Mumbai", "Delhi", "Patna", "Bhabua"]
    padded_branch_labels = (branch_labels + ["Ranchi", "Lucknow"])[:4]

    return {
        "is_mock": True,
        "lot_batch_traceability": [
            {"item_name": "PCR Reagent Kit A", "lot_number": "LOT-PR-8821", "received_on": "2026-07-05", "used_on": "2026-07-24", "branch": padded_branch_labels[0], "used_for_test": "PCR Panel"},
            {"item_name": "CBC Control Serum", "lot_number": "LOT-CS-2204", "received_on": "2026-07-08", "used_on": "2026-07-23", "branch": padded_branch_labels[2], "used_for_test": "CBC"},
            {"item_name": "Contrast Media 100ml", "lot_number": "LOT-CM-3491", "received_on": "2026-07-02", "used_on": "2026-07-25", "branch": padded_branch_labels[1], "used_for_test": "CT Scan"},
        ],
        "expiry_recall_management": {
            "expiring_alerts": [
                {"item_name": "MRI Contrast Set", "branch": padded_branch_labels[2], "days_to_expiry": 5, "severity": "high"},
                {"item_name": "EDTA Tube 2ml", "branch": padded_branch_labels[3], "days_to_expiry": 14, "severity": "medium"},
            ],
            "regulatory_recall_feed": [
                {"recall_id": "RC-2026-114", "item_name": "Specialized Biopsy Needles", "status": "Open", "advisory": "Isolate batch BN-7741 pending vendor confirmation."}
            ],
        },
        "supplier_item_certification_tracker": [
            {"entity_type": "Supplier", "name": "MedChem Reagents Pvt Ltd", "certification": "ISO 13485", "status": "Valid", "expiry_date": "2027-03-31"},
            {"entity_type": "Supplier", "name": "Prime Diagnostics Supplies", "certification": "ISO 9001", "status": "Expiring Soon", "expiry_date": "2026-09-15"},
            {"entity_type": "Item", "name": "PCR Reagent Kit A", "certification": "NABL Approved", "status": "Valid", "expiry_date": "2027-01-31"},
        ],
        "audit_trail": [
            {"timestamp": "2026-07-26 08:55", "activity_type": "Stock Adjustment", "item_name": "PCR Reagent Kit A", "performed_by": "Inventory Manager", "notes": "Adjusted +4 after batch recount."},
            {"timestamp": "2026-07-26 08:10", "activity_type": "Procurement Approval", "item_name": "Contrast Media 100ml", "performed_by": "Branch Admin", "notes": "PO-2026-1035 approved."},
            {"timestamp": "2026-07-25 18:40", "activity_type": "Consumption Entry", "item_name": "CBC Control Serum", "performed_by": "Lab Tech N. Das", "notes": "Issued for evening CBC batch."},
        ],
        "reagent_consumable_quality_tracking": [
            {"item_name": "EDTA Tube 2ml", "issue_type": "Seal Defect", "complaint_count": 3, "last_reported_on": "2026-07-22", "status": "Under Review"},
            {"item_name": "MRI Contrast Set", "issue_type": "Packaging Damage", "complaint_count": 2, "last_reported_on": "2026-07-19", "status": "Vendor Action Pending"},
            {"item_name": "PCR Reagent Kit A", "issue_type": "Inconsistent Lot Performance", "complaint_count": 1, "last_reported_on": "2026-07-18", "status": "Resolved"},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "lot_traceability": "Lot-level receipt-to-issue linkage using GRN, stock movement, and test consumption joins.",
            "expiry_recall": "Expiry alerts from batch dates plus external recall feeds from regulator integration.",
            "certification_tracking": "Supplier/item certification ledger and compliance renewal tracking.",
            "audit_trail": "Immutable activity logs for inventory movement, procurement, and overrides.",
            "quality_tracking": "Recurring quality complaint correlation by supplier, lot, and item.",
        },
    }


@router.get("/predictive-intelligence")
def get_inventory_predictive_intelligence(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "demand_forecasting": [
            {"month": "Aug", "pcr_reagent_demand": 128, "edta_tube_demand": 740, "contrast_media_demand": 96},
            {"month": "Sep", "pcr_reagent_demand": 132, "edta_tube_demand": 765, "contrast_media_demand": 102},
            {"month": "Oct", "pcr_reagent_demand": 139, "edta_tube_demand": 792, "contrast_media_demand": 108},
            {"month": "Nov", "pcr_reagent_demand": 146, "edta_tube_demand": 824, "contrast_media_demand": 113},
            {"month": "Dec", "pcr_reagent_demand": 151, "edta_tube_demand": 848, "contrast_media_demand": 119},
            {"month": "Jan", "pcr_reagent_demand": 158, "edta_tube_demand": 873, "contrast_media_demand": 124},
        ],
        "expiry_prediction_prevention": [
            {"item_name": "MRI Contrast Set", "risk_score": 87, "branch": "Patna", "suggested_action": "Redistribute 12 units to Mumbai branch."},
            {"item_name": "CBC Control Serum", "risk_score": 74, "branch": "Delhi", "suggested_action": "Prioritize CBC package campaign for 2 weeks."},
            {"item_name": "Specialized Biopsy Needles", "risk_score": 69, "branch": "Bhabua", "suggested_action": "Freeze reorder and consume older lot first."},
        ],
        "supply_chain_risk_alerts": [
            {"severity": "high", "title": "Supplier plant downtime risk", "message": "Primary MRI contrast supplier reported 5-day maintenance shutdown next month."},
            {"severity": "medium", "title": "Weather disruption advisory", "message": "Heavy rainfall forecast may delay cold-chain delivery to eastern corridor."},
            {"severity": "low", "title": "Currency fluctuation watch", "message": "Import-linked reagent pricing may increase by 2-3% if INR weakens further."},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "demand_forecast": "Model from historical branch-level consumption, seasonality, and disease burden signals.",
            "expiry_prediction": "Risk ranking from projected consumption vs remaining shelf life by lot.",
            "external_risk_alerts": "Supplier events, weather, and macro indicators for disruption probability.",
        },
    }


@router.get("/predictive-what-if-simulator")
def get_inventory_predictive_what_if_simulator(
    current_supplier: str = "MedChem Reagents Pvt Ltd",
    new_supplier: str = "NovaBio Supplies",
    item_category: str = "Reagents",
    db: Session = Depends(get_db),
):
    return {
        "is_mock": True,
        "scenario": f"Switch {item_category} sourcing from {current_supplier} to {new_supplier}.",
        "inputs": {
            "current_supplier": current_supplier,
            "new_supplier": new_supplier,
            "item_category": item_category,
        },
        "projected_impact": {
            "cost_change_percent": -4.8,
            "availability_change_percent": 3.2,
            "on_time_delivery_change_percent": -1.1,
            "estimated_monthly_savings": 126000,
        },
        "ai_summary": "Projected savings are positive, but on-time reliability may dip slightly. Keep dual-supplier fallback during transition.",
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/wow-features")
def get_inventory_wow_features(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "digital_control_tower": {
            "overall_supply_chain_status": "Stable with watch alerts",
            "active_alerts": 5,
            "critical_stockouts": 1,
            "in_transit_shipments": 18,
            "expiring_within_7_days": 3,
            "today_wastage_cost": 14800,
        },
        "zero_waste_ai_assistant": [
            "Mumbai branch is low on HbA1c reagents. A replenishment order has been automatically generated.",
            "Redistribute 12 MRI Contrast units from Patna to Mumbai to avoid expiry loss this week.",
            "Reduce reorder of Vacutainer tube variant V-3 by 20% due to slow-moving stock.",
        ],
        "supplier_health_scores": [
            {"supplier_name": "MedChem Reagents Pvt Ltd", "health_score": 91, "delivery_score": 93, "quality_score": 90, "financial_stability_score": 89},
            {"supplier_name": "Prime Diagnostics Supplies", "health_score": 84, "delivery_score": 86, "quality_score": 82, "financial_stability_score": 83},
            {"supplier_name": "BioScan Equipment Services", "health_score": 76, "delivery_score": 78, "quality_score": 74, "financial_stability_score": 77},
        ],
        "automated_inventory_briefing": (
            "Good morning, Mr. Singh. Mumbai branch is running low on HbA1c reagents. "
            "One high-priority stockout alert is active, and 3 lots are nearing expiry within 7 days."
        ),
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "digital_control_tower": "Unified stream from procurement, stock, shipment, and expiry event pipelines.",
            "zero_waste_assistant": "Action recommendations from waste-risk model and inter-branch transfer optimizer.",
            "supplier_health": "Composite supplier score from delivery SLA, quality incidents, and credit-risk signals.",
            "inventory_briefing": "Daily narrative generated from overnight deltas in stock, logistics, and alerts.",
        },
    }
