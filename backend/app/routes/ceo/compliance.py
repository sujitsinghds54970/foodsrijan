from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.utils.auth_system import auth_guard

router = APIRouter(
    prefix="/ceo/compliance",
    tags=["CEO Compliance & Legal"],
    dependencies=[Depends(auth_guard.require_role(["super_admin"]))],
)


def _table_reference_snapshot(db: Session) -> dict[str, Any]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    table_map = {
        "branches": "branches",
        "licenses": "licenses",
        "audit_logs": "audit_logs",
        "incidents": "incidents",
        "policies": "policies",
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
def get_compliance_health_score(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "score": 85,
        "status": "Green",
        "risk_exposure": "Low",
        "compliance_status_by_category": [
            {"category": "Licenses", "score": 88, "status": "Green"},
            {"category": "Accreditations", "score": 82, "status": "Green"},
            {"category": "Statutory Filings", "score": 79, "status": "Yellow"},
            {"category": "Data Privacy", "score": 86, "status": "Green"},
            {"category": "Legal Contracts", "score": 81, "status": "Green"},
            {"category": "Incident Management", "score": 74, "status": "Yellow"},
        ],
        "score_trend": [
            {"month": "Aug", "score": 74},
            {"month": "Sep", "score": 75},
            {"month": "Oct", "score": 77},
            {"month": "Nov", "score": 78},
            {"month": "Dec", "score": 80},
            {"month": "Jan", "score": 81},
            {"month": "Feb", "score": 82},
            {"month": "Mar", "score": 83},
            {"month": "Apr", "score": 84},
            {"month": "May", "score": 84},
            {"month": "Jun", "score": 85},
            {"month": "Jul", "score": 85},
        ],
        "days_since_last_audit_by_branch": [
            {"branch": "Mumbai", "days_since_last_audit": 27},
            {"branch": "Delhi", "days_since_last_audit": 34},
            {"branch": "Patna", "days_since_last_audit": 41},
            {"branch": "Bhabua", "days_since_last_audit": 29},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "compliance_health_score": "Composite from filings timeliness, license validity, incidents, and audit observations.",
            "category_status": "Rule-based category risk from records in license, policy, filing, and incident ledgers.",
            "risk_exposure": "AI risk exposure from trend and severity-weighted non-compliance indicators.",
            "audit_recency": "Days from latest branch audit/inspection event records.",
        },
    }


@router.get("/license-accreditation-management")
def get_compliance_license_accreditation_management(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "license_accreditation_dashboard": [
            {"branch": "Mumbai", "license_type": "Clinical Establishment Act", "license_id": "CEA-MUM-1021", "status": "Valid", "expiry_date": "2027-01-10", "renewal_application_status": "Not Required"},
            {"branch": "Delhi", "license_type": "NABL Accreditation", "license_id": "NABL-DEL-8892", "status": "Expiring Soon", "expiry_date": "2026-10-18", "renewal_application_status": "In Progress"},
            {"branch": "Patna", "license_type": "NABH Accreditation", "license_id": "NABH-PAT-5521", "status": "Valid", "expiry_date": "2027-04-02", "renewal_application_status": "Not Required"},
            {"branch": "Bhabua", "license_type": "Radiology License", "license_id": "RAD-BHA-1408", "status": "Expiring Soon", "expiry_date": "2026-09-05", "renewal_application_status": "Draft Pending"},
            {"branch": "Mumbai", "license_type": "ISO 15189", "license_id": "ISO-MUM-7761", "status": "Valid", "expiry_date": "2027-06-22", "renewal_application_status": "Not Required"},
        ],
        "auto_renewal_alerts": [
            {"license_id": "NABL-DEL-8892", "branch": "Delhi", "days_to_expiry": 84, "alert_window": "90 days", "renewal_application_status": "In Progress"},
            {"license_id": "RAD-BHA-1408", "branch": "Bhabua", "days_to_expiry": 41, "alert_window": "60 days", "renewal_application_status": "Draft Pending"},
            {"license_id": "PT-PAT-3211", "branch": "Patna", "days_to_expiry": 19, "alert_window": "30 days", "renewal_application_status": "Submitted"},
        ],
        "nabl_accreditation_tracker": {
            "current_status": "Surveillance Cycle Ongoing",
            "document_submission_date": "2026-06-15",
            "assessment_date": "2026-08-12",
            "non_conformance_resolution": "6/8 closed",
            "open_non_conformances": 2,
        },
        "professional_license_tracking": [
            {"name": "Dr. R. Sharma", "role": "Pathologist", "license_number": "MCI-PTH-8821", "status": "Valid", "expiry_date": "2028-02-14"},
            {"name": "Dr. P. Verma", "role": "Radiologist", "license_number": "MCI-RAD-6691", "status": "Expiring Soon", "expiry_date": "2026-11-20"},
            {"name": "N. Das", "role": "Lab Technician", "license_number": "DMLT-7744", "status": "Valid", "expiry_date": "2027-05-11"},
            {"name": "A. Kumar", "role": "Phlebotomist", "license_number": "PHL-1182", "status": "Valid", "expiry_date": "2027-08-03"},
        ],
        "equipment_certification_calibration": [
            {"equipment_name": "MRI Scanner Unit-1", "branch": "Mumbai", "certification_status": "Valid", "calibration_due_date": "2026-10-02", "last_calibrated_on": "2026-04-02"},
            {"equipment_name": "CT Scanner Unit-2", "branch": "Delhi", "certification_status": "Expiring Soon", "calibration_due_date": "2026-08-22", "last_calibrated_on": "2026-02-22"},
            {"equipment_name": "Hematology Analyzer", "branch": "Patna", "certification_status": "Valid", "calibration_due_date": "2026-12-05", "last_calibrated_on": "2026-06-05"},
        ],
        "document_repository": {
            "status": "available",
            "description": "Centralized compliance document repository with version history and access logs.",
            "placeholder_note": "Mock placeholder: secure document viewer and access log drill-down will be integrated with DMS.",
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "license_dashboard": "Branch-wise license/accreditation records with status and renewal workflow.",
            "auto_renewal": "Automated reminders from expiry windows and renewal state machine.",
            "nabl_tracker": "NABL process milestones and NC resolution tracking from accreditation workflow.",
            "professional_licenses": "Employee credential registry with expiry monitoring.",
            "equipment_calibration": "Asset certification and calibration schedules from equipment compliance logs.",
            "document_repository": "DMS metadata, versioning, and access events.",
        },
    }


@router.get("/regulatory-statutory")
def get_compliance_regulatory_statutory(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "regulatory_compliance_dashboard": [
            {"regulation": "Clinical Establishments Act", "compliance_percent": 92, "status": "Compliant"},
            {"regulation": "Drugs & Cosmetics Act (Schedule L-1 GLP)", "compliance_percent": 86, "status": "Compliant with Observations"},
            {"regulation": "PCPNDT Act", "compliance_percent": 81, "status": "Watchlist"},
            {"regulation": "Biomedical Waste Management Rules", "compliance_percent": 88, "status": "Compliant"},
        ],
        "statutory_filing_tracker": [
            {"filing_type": "GST Return", "period": "Jul 2026", "due_date": "2026-08-20", "status": "Filed"},
            {"filing_type": "TDS Filing", "period": "Q1 FY27", "due_date": "2026-08-07", "status": "In Progress"},
            {"filing_type": "Professional Tax", "period": "Jul 2026", "due_date": "2026-08-10", "status": "Pending"},
            {"filing_type": "PF/ESI Contribution", "period": "Jul 2026", "due_date": "2026-08-15", "status": "Pending"},
            {"filing_type": "Annual Return", "period": "FY26", "due_date": "2026-09-30", "status": "Planned"},
        ],
        "glp_compliance": {
            "score": 84,
            "status": "Compliant with minor gaps",
            "open_observations": 3,
            "last_internal_review": "2026-07-18",
        },
        "biomedical_waste_management": {
            "segregation_score": 91,
            "storage_score": 87,
            "disposal_score": 89,
            "composite_status": "Compliant",
        },
        "regulatory_change_monitor": [
            {"severity": "medium", "title": "PCPNDT reporting format update", "impact": "Additional monthly data fields required from next cycle."},
            {"severity": "low", "title": "GLP checklist revision advisory", "impact": "Update SOP annexure references before next internal audit."},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "regulatory_dashboard": "Control-wise compliance mapping against applicable regulations per branch.",
            "statutory_filings": "Filing calendar and submission state from tax and labor compliance workflows.",
            "glp": "Schedule L-1 checklist adherence and quality-control deviations.",
            "biomedical_waste": "Segregation, storage, and disposal control outcomes from waste logs.",
            "change_monitor": "Regulatory intelligence feed with relevance and impact scoring.",
        },
    }


@router.get("/legal-contract-management")
def get_compliance_legal_contract_management(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "contract_lifecycle_management": [
            {"contract_id": "CTR-DR-2026-014", "contract_type": "Doctor Agreement", "counterparty": "Dr. R. Sharma", "start_date": "2026-01-01", "expiry_date": "2026-12-31", "status": "Active"},
            {"contract_id": "CTR-VN-2025-202", "contract_type": "Vendor Contract", "counterparty": "MedChem Reagents Pvt Ltd", "start_date": "2025-10-01", "expiry_date": "2026-09-30", "status": "Renewal Due"},
            {"contract_id": "CTR-EMP-2026-077", "contract_type": "Employee Agreement", "counterparty": "Senior Lab Manager", "start_date": "2026-04-01", "expiry_date": "2028-03-31", "status": "Active"},
            {"contract_id": "CTR-LS-2024-011", "contract_type": "Lease Agreement", "counterparty": "Delhi Facility Lease", "start_date": "2024-06-01", "expiry_date": "2027-05-31", "status": "Active"},
        ],
        "auto_contract_renewal_alerts": [
            {"contract_id": "CTR-VN-2025-202", "days_to_expiry": 66, "renewal_deadline": "2026-09-30", "status": "Negotiation in progress"},
            {"contract_id": "CTR-DR-2026-014", "days_to_expiry": 158, "renewal_deadline": "2026-12-31", "status": "Review planned"},
        ],
        "key_terms_extraction": [
            {"contract_id": "CTR-VN-2025-202", "termination_clause": "60-day notice", "payment_terms": "Net 45", "liability_limit": "1x annual value", "confidentiality": "3-year survival"},
            {"contract_id": "CTR-DR-2026-014", "termination_clause": "30-day notice", "payment_terms": "Monthly settlement", "liability_limit": "Capped at fees paid", "confidentiality": "2-year survival"},
        ],
        "legal_case_tracker": [
            {"case_id": "LC-2026-011", "matter": "Vendor payment dispute", "counterparty": "Prime Diagnostics Supplies", "stage": "Notice Issued", "next_hearing_or_action_date": "2026-08-14", "status": "Open"},
            {"case_id": "LC-2026-006", "matter": "Employment grievance", "counterparty": "Former technician", "stage": "Mediation", "next_hearing_or_action_date": "2026-08-02", "status": "In Progress"},
        ],
        "policy_attestation_management": [
            {"policy_name": "Code of Conduct", "employees_targeted": 312, "employees_signed": 287, "attestation_percent": 92.0, "status": "On Track"},
            {"policy_name": "Data Privacy Policy", "employees_targeted": 312, "employees_signed": 274, "attestation_percent": 87.8, "status": "Follow-up Required"},
            {"policy_name": "Anti-Bribery Policy", "employees_targeted": 312, "employees_signed": 269, "attestation_percent": 86.2, "status": "Follow-up Required"},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "contract_lifecycle": "Contract repository with state transitions, owners, and renewal workflow.",
            "renewal_alerts": "Automated contract expiry watchlist and reminder cadence.",
            "key_terms": "NLP extraction of legal clauses from agreement documents.",
            "legal_cases": "Matter/case tracking with stage and action timelines.",
            "policy_attestation": "Policy distribution and digital-signature acknowledgement status.",
        },
    }


@router.get("/incident-risk-management")
def get_compliance_incident_risk_management(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "incident_dashboard": [
            {"incident_id": "INC-2026-112", "category": "Patient Complaint", "severity": "Medium", "branch": "Mumbai", "status": "Open", "reported_at": "2026-07-24T10:20:00Z"},
            {"incident_id": "INC-2026-109", "category": "Safety Incident", "severity": "High", "branch": "Delhi", "status": "In Progress", "reported_at": "2026-07-23T15:40:00Z"},
            {"incident_id": "INC-2026-105", "category": "Data Breach", "severity": "Critical", "branch": "Patna", "status": "Open", "reported_at": "2026-07-21T08:05:00Z"},
            {"incident_id": "INC-2026-101", "category": "Quality Issue", "severity": "Low", "branch": "Bhabua", "status": "Resolved", "reported_at": "2026-07-20T13:30:00Z"},
            {"incident_id": "INC-2026-097", "category": "Operational Failure", "severity": "Medium", "branch": "Mumbai", "status": "Resolved", "reported_at": "2026-07-18T17:10:00Z"},
        ],
        "incident_severity_resolution_time": [
            {"severity": "Low", "incident_count": 9, "avg_resolution_hours": 12},
            {"severity": "Medium", "incident_count": 14, "avg_resolution_hours": 26},
            {"severity": "High", "incident_count": 6, "avg_resolution_hours": 44},
            {"severity": "Critical", "incident_count": 2, "avg_resolution_hours": 71},
        ],
        "whistleblower_hotline": {
            "enabled": True,
            "mode": "anonymous",
            "channels": ["web_form", "email_alias", "hotline_number"],
            "note": "Mock anonymous hotline form. Production rollout will integrate encrypted case handling.",
        },
        "risk_register": [
            {"risk_id": "RSK-041", "risk_name": "PCPNDT documentation delay", "likelihood": "Medium", "impact": "High", "mitigation_status": "Mitigation In Progress"},
            {"risk_id": "RSK-038", "risk_name": "Vendor calibration certificate lapse", "likelihood": "Low", "impact": "Medium", "mitigation_status": "Mitigated"},
            {"risk_id": "RSK-033", "risk_name": "Policy attestation backlog", "likelihood": "Medium", "impact": "Medium", "mitigation_status": "Monitoring"},
            {"risk_id": "RSK-029", "risk_name": "Data retention non-compliance", "likelihood": "Low", "impact": "High", "mitigation_status": "Control Strengthened"},
        ],
        "complaint_analysis_trends": {
            "top_recurring_themes": [
                {"theme": "Report Delay", "share_percent": 34},
                {"theme": "Billing Clarification", "share_percent": 27},
                {"theme": "Collection Experience", "share_percent": 18},
                {"theme": "Portal Access Issues", "share_percent": 11},
            ],
            "ai_summary": "Complaint volume is stable week-over-week, but repeat concerns on report-delay are concentrated in evening slots. Prioritize staffing and escalation automation between 5 PM and 9 PM.",
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "incident_dashboard": "Unified incident records from complaints, safety, quality, operations, and security channels.",
            "severity_resolution": "Incident SLA metrics by severity and closure cycle time.",
            "whistleblower": "Anonymous case intake workflow with redaction and protected routing.",
            "risk_register": "Enterprise risk register with owners, control plans, and residual risk scoring.",
            "complaint_analysis": "NLP topic clustering, sentiment shifts, and recurrence pattern detection.",
        },
    }


@router.get("/audit-inspection-readiness")
def get_compliance_audit_inspection_readiness(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "audit_schedule_calendar": [
            {"audit_name": "Internal GLP Audit", "audit_type": "Internal", "branch": "Mumbai", "scheduled_date": "2026-08-05", "status": "Scheduled"},
            {"audit_name": "NABL Surveillance Visit", "audit_type": "Accreditation", "branch": "Delhi", "scheduled_date": "2026-08-12", "status": "Scheduled"},
            {"audit_name": "Biomedical Waste Inspection", "audit_type": "Regulatory", "branch": "Patna", "scheduled_date": "2026-08-19", "status": "Preparation Ongoing"},
            {"audit_name": "Policy Compliance Spot Check", "audit_type": "Internal", "branch": "Bhabua", "scheduled_date": "2026-08-24", "status": "Scheduled"},
        ],
        "audit_trail_evidence_log": [
            {"event_time": "2026-07-25T09:15:00Z", "activity": "Policy acknowledgement recorded", "owner": "HR Compliance", "evidence_id": "EV-90014"},
            {"event_time": "2026-07-24T16:05:00Z", "activity": "Corrective action closure uploaded", "owner": "Quality Team", "evidence_id": "EV-90007"},
            {"event_time": "2026-07-23T12:40:00Z", "activity": "Incident root-cause worksheet approved", "owner": "Ops Governance", "evidence_id": "EV-89991"},
            {"event_time": "2026-07-22T18:10:00Z", "activity": "Training completion batch posted", "owner": "L&D Cell", "evidence_id": "EV-89962"},
        ],
        "non_conformance_corrective_action_tracker": [
            {"nc_id": "NC-2026-011", "finding": "Missing reagent traceability sign-off", "corrective_action": "Introduce digital lot sign-off checkpoint", "owner": "Lab QA", "target_date": "2026-08-08", "status": "In Progress"},
            {"nc_id": "NC-2026-009", "finding": "Delayed statutory filing evidence upload", "corrective_action": "Auto-sync filing acknowledgements", "owner": "Finance Compliance", "target_date": "2026-08-02", "status": "Planned"},
            {"nc_id": "NC-2026-006", "finding": "Incomplete policy attestation cohort", "corrective_action": "Branch escalation + weekly sign-off report", "owner": "HR Compliance", "target_date": "2026-07-31", "status": "Open"},
        ],
        "pre_audit_checklist": [
            {"item": "All mandatory licenses valid and copies uploaded", "status": "Done"},
            {"item": "Latest SOP versions approved and distributed", "status": "Done"},
            {"item": "Last 3 months training attendance evidence", "status": "Pending"},
            {"item": "Incident CAPA tracker updated with owners", "status": "In Progress"},
            {"item": "Calibration and maintenance logs reconciled", "status": "Pending"},
        ],
        "inspection_report_repository": [
            {"report_id": "RPT-INS-2026-004", "inspection_name": "State Clinical Establishment Review", "branch": "Mumbai", "report_date": "2026-06-11", "status": "Closed"},
            {"report_id": "RPT-INS-2026-003", "inspection_name": "NABL Follow-up Assessment", "branch": "Delhi", "report_date": "2026-05-28", "status": "CAPA Ongoing"},
            {"report_id": "RPT-INS-2026-001", "inspection_name": "Biomedical Waste Compliance Check", "branch": "Patna", "report_date": "2026-04-19", "status": "Closed"},
        ],
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "audit_schedule": "Consolidated audit/inspection calendar from internal, regulatory, and accreditation tracks.",
            "audit_trail": "Tamper-evident compliance activity ledger with evidence attachments.",
            "nc_capa": "Non-conformance lifecycle with corrective and preventive action status.",
            "pre_audit_checklist": "Dynamic readiness checklist validated against audit type and branch profile.",
            "inspection_repository": "Historical inspection reports, observations, and closure records.",
        },
    }


@router.get("/data-privacy-security")
def get_compliance_data_privacy_security(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "data_privacy_dashboard": {
            "consent_management_percent": 94,
            "data_access_logs_reviewed_percent": 89,
            "breach_incidents_open": 1,
            "privacy_training_completion_percent": 91,
        },
        "regulation_compliance_tracker": [
            {"regulation": "DPDP", "adherence_percent": 90, "status": "Compliant with minor actions"},
            {"regulation": "GDPR", "adherence_percent": 84, "status": "In Progress"},
            {"regulation": "HIPAA", "adherence_percent": 87, "status": "Compliant"},
        ],
        "data_breach_incident_log": [
            {"incident_id": "DBR-2026-004", "branch": "Patna", "severity": "High", "reported_on": "2026-07-21", "resolution_status": "Containment Complete"},
            {"incident_id": "DBR-2026-003", "branch": "Delhi", "severity": "Medium", "reported_on": "2026-06-29", "resolution_status": "Closed"},
            {"incident_id": "DBR-2026-002", "branch": "Mumbai", "severity": "Low", "reported_on": "2026-06-12", "resolution_status": "Closed"},
        ],
        "data_retention_disposal_policy": {
            "adherence_percent": 88,
            "overdue_disposals": 3,
            "last_policy_review": "2026-07-10",
            "status": "Needs Follow-up",
        },
        "security_training_completion": {
            "overall_completion_percent": 91,
            "employees_completed": 284,
            "employees_total": 312,
            "overdue_learners": 28,
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "privacy_dashboard": "Consent ledger, access-log reviews, breach events, and training completion aggregation.",
            "regulation_tracker": "Control-wise mapping for DPDP/GDPR/HIPAA obligations and evidence.",
            "breach_log": "Security incident register with severity, containment, and closure SLA.",
            "retention_policy": "Retention/disposal lifecycle adherence by data class and branch.",
            "training_completion": "Mandatory privacy-security training completion and escalation workflow.",
        },
    }


@router.get("/predictive-intelligence")
def get_compliance_predictive_intelligence(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "compliance_risk_prediction": [
            {"risk_area": "Statutory Filing Delays", "predicted_risk_score": 74, "horizon_days": 60, "recommended_action": "Enable automated filing reminders + approval escalation."},
            {"risk_area": "Policy Attestation Drift", "predicted_risk_score": 69, "horizon_days": 45, "recommended_action": "Launch branch-level attestation sprint with weekly checkpoints."},
            {"risk_area": "License Renewal Bottleneck", "predicted_risk_score": 62, "horizon_days": 90, "recommended_action": "Advance document pre-validation for expiring licenses."},
        ],
        "regulatory_change_impact_analysis": [
            {"regulation_update": "State-level biomedical waste manifest digitization", "operational_impact": "Medium", "compliance_impact": "High", "recommended_response": "Integrate manifest export API and retrain branch coordinators."},
            {"regulation_update": "DPDP consent withdrawal SLA clarification", "operational_impact": "Low", "compliance_impact": "Medium", "recommended_response": "Update patient portal workflow to prioritize withdrawal requests."},
        ],
        "incident_trend_prediction": {
            "next_quarter_incident_forecast": {"low": 11, "medium": 8, "high": 3, "critical": 1},
            "predicted_hotspots": ["Evening report dispatch workflow", "Manual data-export approvals"],
            "preventive_measures": [
                "Introduce dual-approval for external data exports.",
                "Increase peak-hour QA supervision in report dispatch.",
                "Automate anomaly checks on access log spikes.",
            ],
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "risk_prediction": "Time-series + control-effectiveness model over audits, filings, incidents, and policy workflows.",
            "change_impact": "Regulation-watch ingestion mapped to branch controls and operating procedures.",
            "incident_prediction": "Pattern detection and forward-risk scoring on incident categories and frequencies.",
        },
    }


@router.get("/predictive-what-if-simulator")
def get_compliance_predictive_what_if_simulator(
    target_state: str = "Maharashtra",
    branch_model: str = "Full-Service",
    db: Session = Depends(get_db),
):
    if target_state.strip().lower() == "karnataka":
        licensing_complexity = "High"
        regulatory_readiness_time_weeks = 14
        projected_compliance_setup_cost = 1850000
    elif target_state.strip().lower() == "bihar":
        licensing_complexity = "Medium"
        regulatory_readiness_time_weeks = 10
        projected_compliance_setup_cost = 1320000
    else:
        licensing_complexity = "Medium"
        regulatory_readiness_time_weeks = 12
        projected_compliance_setup_cost = 1540000

    if branch_model.strip().lower() == "collection-center":
        projected_compliance_setup_cost = int(projected_compliance_setup_cost * 0.72)
        regulatory_readiness_time_weeks = max(7, regulatory_readiness_time_weeks - 2)

    return {
        "is_mock": True,
        "inputs": {
            "target_state": target_state,
            "branch_model": branch_model,
        },
        "simulation": {
            "licensing_complexity": licensing_complexity,
            "regulatory_readiness_time_weeks": regulatory_readiness_time_weeks,
            "projected_compliance_setup_cost": projected_compliance_setup_cost,
            "key_implications": [
                "State clinical establishment registration lead time is the critical path.",
                "Biomedical waste tie-up and authorized vendor onboarding must be finalized pre-launch.",
                "Local labor-law filing cadence will require branch finance onboarding in month one.",
            ],
            "recommended_first_actions": [
                "Start license-document checklist and authority mapping immediately.",
                "Assign a compliance launch owner for cross-functional tracking.",
                "Schedule pre-opening internal mock inspection 2 weeks before go-live.",
            ],
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "simulator": "Scenario simulator parameterized by state, branch model, and applicable regulations.",
        },
    }


@router.get("/wow-features")
def get_compliance_wow_features(db: Session = Depends(get_db)):
    return {
        "is_mock": True,
        "compliance_control_tower": {
            "overall_compliance_score": 86,
            "open_license_renewals": 4,
            "upcoming_audits_30d": 5,
            "open_incidents": 3,
            "active_regulatory_alerts": 2,
            "status": "Stable with targeted watchpoints",
        },
        "automated_compliance_briefing": {
            "cadence": "Daily",
            "brief": "Good morning, Mr. Singh. NABL accreditation for Mumbai is due in 60 days, and a renewal application draft has been auto-generated for review. Two regulatory updates need checklist alignment this week.",
        },
        "regulatory_radar": {
            "monitoring_status": "Active",
            "last_scan_at": "2026-07-26T03:30:00Z",
            "recent_changes_detected": 2,
            "auto_updated_checklist_items": 5,
            "highlights": [
                "DPDP consent withdrawal SLA update mapped to patient portal controls.",
                "State biomedical waste manifest digitization added to branch checklist.",
            ],
        },
        "digital_compliance_twin": {
            "simulation_status": "Ready",
            "coverage_scope": "Licenses, audits, incidents, privacy, statutory filings",
            "current_posture_score": 84,
            "change_simulation_note": "Run scenario tests to estimate compliance posture impact before operational changes.",
            "recent_simulation": {
                "scenario": "Open full-service branch in Karnataka",
                "projected_posture_score": 78,
                "risk_delta": "+6",
                "advisory": "Add dedicated regional compliance lead to keep posture above 82.",
            },
        },
        "table_reference": _table_reference_snapshot(db),
        "future_data_mapping": {
            "control_tower": "Unified compliance telemetry from licensing, audit, incidents, and regulatory modules.",
            "automated_briefing": "LLM-generated daily/weekly compliance summary with prioritized actions.",
            "regulatory_radar": "Continuous regulation watch service with checklist auto-sync.",
            "digital_twin": "Scenario sandbox to model posture impact from organization or process changes.",
        },
    }
