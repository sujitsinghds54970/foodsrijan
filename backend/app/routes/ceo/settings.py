from copy import deepcopy
from datetime import datetime
import json
import traceback
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import SystemSettings
from app.utils.auth_system import auth_guard
from app.utils.file_utils import replace_file

router = APIRouter(
    prefix="/ceo/settings",
    tags=["CEO System Settings"],
    dependencies=[Depends(auth_guard.require_role(["super_admin"]))],
)


def _table_reference_snapshot(db: Session) -> dict[str, Any]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    table_map = {
        "branches": "branches",
        "users": "users",
        "audit_logs": "audit_logs",
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


def _ensure_settings_tables() -> None:
    Base.metadata.create_all(bind=engine, tables=[SystemSettings.__table__])


def _recent_audit_logs(db: Session, limit: int = 10) -> list[dict[str, Any]]:
    try:
        rows = db.execute(
            text(
                """
                SELECT id, action, http_method, endpoint, response_status, created_at
                FROM audit_logs
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    except Exception as exc:
        print(f"⚠️ [CEO_SETTINGS_AUDIT_LOGS] Falling back to empty list: {exc}")
        return []
    return [
        {
            "id": int(row["id"]),
            "action": row["action"] or "",
            "http_method": row["http_method"] or "",
            "endpoint": row["endpoint"] or "",
            "response_status": int(row["response_status"] or 0),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


SETTINGS_STORE: dict[str, Any] = {
    "branding": {
        "company_profile": {
            "company_name": "VaidyaVihar",
            "legal_name": "VaidyaVihar Diagnostics Private Limited",
            "registration_number": "U85100BR2019PTC000001",
            "tagline": "Care in every report.",
            "description": "Integrated diagnostics network focused on quality and trust.",
            "contact_information": {
                "address": "Frazer Road, Patna, Bihar",
                "phone": "+91-9876543210",
                "email": "support@vaidyavihar.com",
                "website": "https://vaidyavihar.com",
            },
            "social_media_links": {
                "facebook": "https://facebook.com/vaidyavihar",
                "instagram": "https://instagram.com/vaidyavihar",
                "linkedin": "https://linkedin.com/company/vaidyavihar",
                "x": "https://x.com/vaidyavihar",
            },
        },
        "branding_asset_manager": {
            "primary_logo_web": "/assets/branding/logo-web.png",
            "primary_logo_app": "/assets/branding/logo-app.png",
            "favicon": "/assets/branding/favicon.ico",
            "app_icon": "/assets/branding/app-icon.png",
            "background_banner": "/assets/branding/banner.jpg",
            "email_template": "/assets/branding/email-template.html",
            "report_template": "/assets/branding/report-template.pdf",
        },
        "brand_color_palette": {
            "primary_color": "#4F46E5",
            "secondary_color": "#0EA5E9",
            "accent_color": "#14B8A6",
        },
        "white_label_configuration": {
            "enabled": True,
            "branches": [
                {"branch_name": "Mumbai", "subdomain": "mumbai.vaidyavihar.com", "logo": "/assets/branding/mumbai-logo.png", "theme": "indigo"},
                {"branch_name": "Delhi", "subdomain": "delhi.vaidyavihar.com", "logo": "/assets/branding/delhi-logo.png", "theme": "cyan"},
            ],
        },
        "default_language_locale": {
            "language": "English",
            "date_format": "DD-MM-YYYY",
            "timezone": "Asia/Kolkata",
            "currency": "INR",
        },
    },
    "security": {
        "ceo_fortified_authentication": {
            "biometric_login_enabled": True,
            "webauthn_fido2_enabled": True,
            "enrollment_status": "2 security keys enrolled",
            "hardware_security_keys": [
                {"key_name": "YubiKey-Primary", "registered_on": "2026-01-18", "last_used_on": "2026-07-24"},
                {"key_name": "YubiKey-Backup", "registered_on": "2026-01-20", "last_used_on": "2026-07-12"},
            ],
        },
        "global_password_policy": {
            "minimum_length": 12,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special_characters": True,
            "expiration_days": 90,
        },
        "mfa_policy": {
            "mode": "specific_roles",
            "enforced_for_roles": ["super_admin", "branch_director"],
            "optional_for_roles": ["staff"],
        },
        "session_inactivity_management": {
            "auto_sign_out_minutes": 60,
            "max_concurrent_sessions": 3,
        },
        "ip_allowlisting_restriction": {
            "enabled": False,
            "allowed_ips": ["103.45.12.10", "103.45.12.11"],
        },
    },
    "feature_flags": {
        "feature_flag_dashboard": [
            {"feature_key": "doctor_portal", "label": "Doctor Portal", "category": "Modules", "enabled": True},
            {"feature_key": "patient_portal", "label": "Patient Portal", "category": "Modules", "enabled": True},
            {"feature_key": "inventory_management", "label": "Inventory Management", "category": "Modules", "enabled": True},
            {"feature_key": "smart_billing_rules", "label": "Smart Billing Rules", "category": "Billing", "enabled": False},
            {"feature_key": "auto_report_dispatch", "label": "Auto Report Dispatch", "category": "Reports", "enabled": True},
            {"feature_key": "whatsapp_integration", "label": "WhatsApp Integration", "category": "Integrations", "enabled": False},
        ],
        "module_activation": [
            {"module": "Doctor Portal", "enabled": True},
            {"module": "Patient Portal", "enabled": True},
            {"module": "Inventory Management", "enabled": True},
            {"module": "Analytics Studio", "enabled": False},
        ],
        "flag_categories": [
            {"category": "Billing", "description": "Billing and payment workflows"},
            {"category": "Reports", "description": "Result and report automation"},
            {"category": "Integrations", "description": "Third-party and channel integrations"},
            {"category": "Modules", "description": "Major platform modules"},
        ],
        "flag_change_audit": [
            {"timestamp": "2026-07-23T10:14:00Z", "user_id": 1, "feature_key": "auto_report_dispatch", "old_value": False, "new_value": True},
            {"timestamp": "2026-07-22T09:22:00Z", "user_id": 1, "feature_key": "whatsapp_integration", "old_value": True, "new_value": False},
        ],
    },
    "integrations_api_management": {
        "lis_integration": {
            "enabled": True,
            "api_key": "lis_live_********",
            "endpoint": "https://lis.vaidyavihar.com/api/v1/results",
            "data_mapping": "patient_id->uhid, test_code->analyte_code, result_value->value",
        },
        "analyzer_device_integration": [
            {"device_name": "Cobas 6000", "device_type": "Biochemistry Analyzer", "connection_type": "HL7", "status": "Connected"},
            {"device_name": "Sysmex XN-1000", "device_type": "Hematology Analyzer", "connection_type": "ASTM", "status": "Connected"},
            {"device_name": "Mindray CL-1200i", "device_type": "Immunoassay Analyzer", "connection_type": "API", "status": "Pending"},
        ],
        "payment_gateway_configuration": [
            {"gateway": "UPI", "provider": "Razorpay", "enabled": True, "merchant_id": "vv_upi_001"},
            {"gateway": "Cards", "provider": "Razorpay", "enabled": True, "merchant_id": "vv_cards_001"},
            {"gateway": "Net Banking", "provider": "PayU", "enabled": False, "merchant_id": "vv_nb_001"},
        ],
        "communication_gateways": {
            "sms": {"provider": "MSG91", "sender_id": "VAIDYA", "enabled": True},
            "email": {"provider": "SMTP", "from_email": "noreply@vaidyavihar.com", "enabled": True},
            "whatsapp": {"provider": "Meta Cloud API", "business_number": "+91-9000000000", "enabled": False},
        },
        "api_key_management": [
            {"key_name": "DoctorPortalSync", "masked_key": "dp_****_01", "status": "active", "created_at": "2026-06-20", "last_used_at": "2026-07-25"},
            {"key_name": "InsuranceBridge", "masked_key": "ins_****_44", "status": "revoked", "created_at": "2026-04-18", "last_used_at": "2026-05-30"},
            {"key_name": "PartnerLabImport", "masked_key": "pl_****_73", "status": "active", "created_at": "2026-07-01", "last_used_at": "2026-07-24"},
        ],
    },
    "branch_localization_management": {
        "multi_branch_configuration": [
            {"branch_id": 1, "branch_name": "Mumbai", "address": "Andheri East, Mumbai", "phone": "+91-9001110001", "operating_hours": "06:00-22:00", "timezone": "Asia/Kolkata", "status": "active"},
            {"branch_id": 2, "branch_name": "Delhi", "address": "Lajpat Nagar, Delhi", "phone": "+91-9001110002", "operating_hours": "07:00-21:00", "timezone": "Asia/Kolkata", "status": "active"},
            {"branch_id": 3, "branch_name": "Patna", "address": "Boring Road, Patna", "phone": "+91-9001110003", "operating_hours": "06:30-20:30", "timezone": "Asia/Kolkata", "status": "active"},
        ],
        "branch_level_pricing_discounts": [
            {"branch_name": "Mumbai", "test_code": "CBC", "price": 450, "discount_percent": 10, "package_rule": "Wellness Silver"},
            {"branch_name": "Delhi", "test_code": "HBA1C", "price": 700, "discount_percent": 8, "package_rule": "Diabetes Panel"},
            {"branch_name": "Patna", "test_code": "LFT", "price": 900, "discount_percent": 12, "package_rule": "Liver Package"},
        ],
        "branch_level_staff_permissions": [
            {"branch_name": "Mumbai", "role": "branch_director", "permissions": ["pricing_override", "staff_approval", "report_release"]},
            {"branch_name": "Delhi", "role": "lab_manager", "permissions": ["inventory_approve", "qc_signoff"]},
            {"branch_name": "Patna", "role": "frontdesk_lead", "permissions": ["patient_intake", "discount_request"]},
        ],
        "central_test_catalog": [
            {"test_code": "CBC", "test_name": "Complete Blood Count", "category": "Hematology", "active": True},
            {"test_code": "HBA1C", "test_name": "HbA1c", "category": "Biochemistry", "active": True},
            {"test_code": "LFT", "test_name": "Liver Function Test", "category": "Biochemistry", "active": True},
            {"test_code": "KFT", "test_name": "Kidney Function Test", "category": "Biochemistry", "active": True},
        ],
        "branch_switching": {
            "current_view_branch": "All Branches",
            "available_branches": ["All Branches", "Mumbai", "Delhi", "Patna"],
            "quick_switch_enabled": True,
        },
    },
    "data_compliance_management": {
        "data_retention_policy": {
            "patient_data_retention_years": 8,
            "test_results_retention_years": 10,
            "audit_logs_retention_years": 7,
            "auto_purge_enabled": False,
        },
        "data_anonymization_rules": {
            "enabled": True,
            "mask_phone": True,
            "mask_email": True,
            "hash_patient_identifier": True,
            "reporting_dataset_salt_rotation_days": 90,
        },
        "consent_management": {
            "default_consent_form_version": "v3.2",
            "require_digital_signature": True,
            "consent_expiry_days": 365,
            "tracking_enabled": True,
        },
        "regulatory_compliance": {
            "dpdp_mode": "strict",
            "gdpr_mode": "standard",
            "hipaa_mode": "enhanced",
            "cross_border_transfer_restriction": True,
        },
        "backup_disaster_recovery": {
            "automated_backup_enabled": True,
            "backup_frequency": "daily",
            "backup_retention_days": 35,
            "dr_drill_frequency": "quarterly",
            "last_successful_backup": "2026-07-25T23:30:00Z",
        },
    },
    "ai_automation_configuration": {
        "ai_auto_validation_rules": {
            "enabled": True,
            "max_reference_range_deviation_percent": 8,
            "critical_result_requires_manual_review": True,
            "minimum_confidence_threshold": 0.92,
        },
        "ai_delta_check_alerts": {
            "enabled": True,
            "delta_percent_threshold": 25,
            "lookback_days": 180,
            "alert_channels": ["dashboard", "email"],
        },
        "automated_report_delivery": {
            "enabled": True,
            "whatsapp_enabled": False,
            "sms_enabled": True,
            "email_enabled": True,
            "delivery_window": "06:00-22:00",
        },
        "predictive_analytics_settings": {
            "demand_forecasting_enabled": True,
            "patient_churn_model_enabled": True,
            "inventory_optimization_enabled": True,
            "model_refresh_frequency": "weekly",
            "drift_monitoring_enabled": True,
        },
    },
    "ui_experience": {
        "default_theme": {
            "theme": "light",
            "allow_user_override": True,
            "default_density": "comfortable",
        },
        "ui_element_visibility": {
            "footer": True,
            "billing_history": True,
            "support_buttons": True,
            "help_center_widget": True,
            "quick_action_fab": False,
        },
        "dashboard_customization": {
            "personalized_layouts_enabled": True,
            "draggable_widgets_enabled": True,
            "layout_presets": [
                {"name": "Executive Snapshot", "widgets": ["Revenue KPI", "Ops Alerts", "Collections"], "default_for_roles": ["super_admin", "finance"]},
                {"name": "Operations Focus", "widgets": ["Branch Queue", "TAT", "Inventory Alerts"], "default_for_roles": ["branch_director"]},
            ],
        },
        "role_specific_dashboards": [
            {"role": "branch_director", "default_dashboard": "Operational Cockpit", "key_modules": ["Daily Operations", "Staff Attendance", "Inventory"]},
            {"role": "hr", "default_dashboard": "People & Culture", "key_modules": ["Attendance", "Leave", "Hiring"]},
            {"role": "finance", "default_dashboard": "Finance & Accounts", "key_modules": ["Revenue", "Receivables", "Payouts"]},
        ],
    },
    "maintenance_system_health": {
        "system_status_dashboard": {
            "overall_status": "green",
            "active_branches": {"online": 12, "degraded": 1, "offline": 0},
            "critical_integrations": [
                {"name": "LIS Core", "status": "green", "latency_ms": 132},
                {"name": "Payment Gateway", "status": "yellow", "latency_ms": 384},
                {"name": "SMS Gateway", "status": "green", "latency_ms": 96},
            ],
            "database_health": {"status": "green", "replication_lag_seconds": 2, "connections_used_percent": 61},
            "backup_status": {"status": "green", "last_successful_backup": "2026-07-26T01:35:00Z"},
            "last_refreshed_at": "2026-07-26T03:15:00Z",
        },
        "scheduled_jobs_automations": [
            {"job_name": "Nightly Backup", "job_type": "backup", "status": "success", "last_run_time": "2026-07-26T01:30:00Z", "next_run_time": "2026-07-27T01:30:00Z"},
            {"job_name": "Daily Report Dispatch", "job_type": "reporting", "status": "running", "last_run_time": "2026-07-26T06:00:00Z", "next_run_time": "2026-07-27T06:00:00Z"},
            {"job_name": "Master Data Sync", "job_type": "sync", "status": "failed", "last_run_time": "2026-07-26T02:45:00Z", "next_run_time": "2026-07-26T04:45:00Z"},
        ],
        "maintenance_mode": {
            "enabled": False,
            "user_facing_message": "We are performing scheduled maintenance. Please check back shortly.",
            "planned_window": "Sunday 02:00-03:00 IST",
        },
        "error_incident_log": [
            {"id": "ERR-9012", "severity": "high", "component": "report_dispatcher", "message": "Queue timeout while pushing WhatsApp templates", "status": "investigating", "occurred_at": "2026-07-25T20:42:00Z", "resolved_at": None},
            {"id": "ERR-9013", "severity": "medium", "component": "payment_reconciliation", "message": "Mismatch in 3 settlement entries", "status": "resolved", "occurred_at": "2026-07-25T18:10:00Z", "resolved_at": "2026-07-25T19:05:00Z"},
            {"id": "ERR-9014", "severity": "low", "component": "notification_service", "message": "Delayed email dispatch retries exceeded threshold", "status": "monitoring", "occurred_at": "2026-07-25T14:24:00Z", "resolved_at": None},
        ],
    },
    "import_export_migration": {
        "bulk_data_import": {
            "supported_entities": ["employees", "doctors", "patients", "tests"],
            "supported_formats": ["csv", "xlsx"],
            "last_import_jobs": [
                {"job_id": "IMP-1021", "entity": "employees", "format": "xlsx", "status": "success", "processed_records": 124, "failed_records": 0, "completed_at": "2026-07-25T17:45:00Z"},
                {"job_id": "IMP-1022", "entity": "patients", "format": "csv", "status": "partial_success", "processed_records": 840, "failed_records": 12, "completed_at": "2026-07-25T18:20:00Z"},
            ],
            "template_downloads": [
                {"entity": "employees", "template_path": "/templates/import/employees.xlsx"},
                {"entity": "patients", "template_path": "/templates/import/patients.csv"},
            ],
        },
        "bulk_data_export": {
            "available_exports": ["employees", "doctors", "patients", "tests", "audit_logs"],
            "default_format": "xlsx",
            "last_export_jobs": [
                {"job_id": "EXP-3301", "dataset": "patients", "format": "xlsx", "status": "success", "rows_exported": 5230, "completed_at": "2026-07-25T19:12:00Z"},
                {"job_id": "EXP-3302", "dataset": "audit_logs", "format": "csv", "status": "success", "rows_exported": 12000, "completed_at": "2026-07-25T20:03:00Z"},
            ],
        },
        "data_migration_tools": {
            "legacy_connectors": [
                {"connector_name": "Legacy LIS v2", "source_type": "postgresql", "status": "ready"},
                {"connector_name": "Old ERP Archive", "source_type": "mysql", "status": "mapping_required"},
            ],
            "migration_runs": [
                {"run_id": "MIG-8001", "source_system": "Legacy LIS v2", "target_module": "patients", "status": "completed", "migrated_records": 15234, "run_at": "2026-07-24T22:10:00Z"},
                {"run_id": "MIG-8002", "source_system": "Old ERP Archive", "target_module": "doctors", "status": "queued", "migrated_records": 0, "run_at": "2026-07-26T05:00:00Z"},
            ],
            "validation_checks_enabled": True,
            "rollback_supported": True,
        },
    },
    "wow_features": {
        "digital_constitution_version_control": {
            "current_version": "v1.24",
            "version_history": [
                {"version": "v1.24", "changed_by": "super_admin", "changed_at": "2026-07-25T21:10:00Z", "change_summary": "Updated maintenance mode policy and dashboard defaults."},
                {"version": "v1.23", "changed_by": "super_admin", "changed_at": "2026-07-24T19:35:00Z", "change_summary": "Adjusted MFA policy and IP allowlist."},
            ],
            "rollback_allowed": True,
        },
        "configuration_push": {
            "last_push_at": "2026-07-25T23:00:00Z",
            "last_push_by": "super_admin",
            "target_branches": 13,
            "last_push_status": "success",
            "pending_changes_count": 4,
        },
        "zero_downtime_feature_rollout": {
            "enabled": True,
            "default_rollout_percent": 5,
            "active_rollouts": [
                {"feature_key": "smart_billing_rules", "current_percent": 5, "status": "canary"},
                {"feature_key": "ai_delta_check_alerts", "current_percent": 10, "status": "ramping"},
            ],
        },
        "automated_system_health_report": {
            "enabled": True,
            "cadence": "daily",
            "last_generated_at": "2026-07-26T03:00:00Z",
            "summary": "Daily health report: 13/13 branches online, 1 degraded integration, 3 incidents under observation.",
            "kpi_snapshot": {
                "uptime_percent": 99.94,
                "open_incidents": 3,
                "backup_success_rate_percent": 100.0,
                "avg_api_latency_ms": 168,
            },
        },
    },
}


def _request_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _to_public_asset_url(request: Request, value: str) -> str:
    raw = value.strip()
    if not raw:
        return raw
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/api/files/"):
        return f"{_request_base_url(request)}{raw}"
    if raw.startswith("api/files/"):
        return f"{_request_base_url(request)}/{raw}"
    if raw.startswith("/uploads/"):
        relative = raw[len("/uploads/") :]
        return f"{_request_base_url(request)}/api/files/{relative.lstrip('/')}"
    if raw.startswith("uploads/"):
        relative = raw[len("uploads/") :]
        return f"{_request_base_url(request)}/api/files/{relative.lstrip('/')}"
    if raw.startswith("/ceo/branding/") or raw.startswith("ceo/branding/"):
        return f"{_request_base_url(request)}/api/files/{raw.lstrip('/')}"
    if raw.startswith("/assets/"):
        return f"{_request_base_url(request)}{raw}"
    if raw.startswith("/"):
        return f"{_request_base_url(request)}{raw}"
    return f"{_request_base_url(request)}/api/files/{raw.lstrip('/')}"


def _normalize_branding_payload(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    normalized = deepcopy(payload)
    asset_manager = dict(normalized.get("branding_asset_manager") or {})
    for key in ("primary_logo_web", "primary_logo_app", "favicon", "app_icon", "background_banner"):
        raw = asset_manager.get(key)
        if isinstance(raw, str):
            asset_manager[key] = _to_public_asset_url(request, raw)
    normalized["branding_asset_manager"] = asset_manager
    company_profile = dict(normalized.get("company_profile") or {})
    tagline = (
        (normalized.get("tagline") or "").strip()
        or (company_profile.get("tagline") or "").strip()
    )
    if tagline:
        normalized["tagline"] = tagline
        company_profile["tagline"] = tagline
        normalized["company_profile"] = company_profile
    return normalized


@router.get("/branding")
def get_settings_branding(request: Request, db: Session = Depends(get_db)):
    try:
        _ensure_settings_tables()
        payload = _normalize_branding_payload(SETTINGS_STORE["branding"], request)
        payload["is_mock"] = True
        payload["table_reference"] = _table_reference_snapshot(db)
        payload["future_data_mapping"] = {
            "company_profile": "Centralized company metadata from company config and legal registry records.",
            "asset_manager": "Branding asset paths from managed file storage and version history.",
            "color_palette": "Theme color tokens applied across web/app/report templates.",
            "white_label": "Branch-wise domain, logo, and theme overrides.",
            "locale": "Global locale defaults used in formatting and monetary presentation.",
        }
        return payload
    except Exception as exc:
        traceback.print_exc()
        print(f"⚠️ [CEO_SETTINGS_BRANDING_GET] Falling back due to: {exc}")
        fallback = _normalize_branding_payload(SETTINGS_STORE.get("branding", {}), request)
        fallback["is_mock"] = True
        fallback["is_fallback"] = True
        fallback["table_reference"] = _table_reference_snapshot(db)
        fallback["future_data_mapping"] = {}
        return fallback


@router.put("/branding")
async def update_settings_branding(
    request: Request,
    db: Session = Depends(get_db),
    payload: str | None = Form(default=None),
    uploaded_logo: UploadFile | None = File(default=None),
    tagline: str | None = Form(default=None),
):
    try:
        _ensure_settings_tables()
        content_type = (request.headers.get("content-type") or "").lower()
        incoming_payload: dict[str, Any] = deepcopy(SETTINGS_STORE.get("branding", {}))

        if "application/json" in content_type:
            body = await request.json()
            if not isinstance(body, dict):
                raise HTTPException(status_code=400, detail="Invalid JSON payload for branding update")
            incoming_payload = body
        elif payload:
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid branding payload JSON: {exc.msg}") from exc
            if not isinstance(parsed, dict):
                raise HTTPException(status_code=400, detail="Invalid branding payload")
            incoming_payload = parsed

        normalized_payload = _normalize_branding_payload(incoming_payload, request)

        if tagline is not None:
            next_tagline = tagline.strip()
            normalized_payload["tagline"] = next_tagline
            company_profile = dict(normalized_payload.get("company_profile") or {})
            company_profile["tagline"] = next_tagline
            normalized_payload["company_profile"] = company_profile

        if uploaded_logo is not None:
            current_logo_url = (
                normalized_payload.get("logo_url")
                or (normalized_payload.get("branding_asset_manager") or {}).get("primary_logo_web")
                or ""
            )
            new_logo_url = replace_file(current_logo_url, uploaded_logo, "ceo/branding")
            asset_manager = dict(normalized_payload.get("branding_asset_manager") or {})
            asset_manager["primary_logo_web"] = new_logo_url
            if not asset_manager.get("primary_logo_app"):
                asset_manager["primary_logo_app"] = new_logo_url
            normalized_payload["branding_asset_manager"] = asset_manager
            normalized_payload["logo_url"] = new_logo_url

        SETTINGS_STORE["branding"] = normalized_payload
        return {
            "updated": True,
            "section": "branding",
            "saved_at": datetime.utcnow().isoformat(),
            "is_mock": True,
            "payload": deepcopy(SETTINGS_STORE["branding"]),
            "table_reference": _table_reference_snapshot(db),
        }
    except Exception as exc:
        traceback.print_exc()
        print(f"⚠️ [CEO_SETTINGS_BRANDING_PUT] Failed to update branding: {exc}")
        raise


@router.get("/security")
def get_settings_security(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["security"])
    payload["is_mock"] = True
    payload["audit_log_immutable"] = _recent_audit_logs(db, limit=10)
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "fortified_auth": "WebAuthn enrollment states and hardware-key registrations.",
        "password_policy": "Global password policy controls enforced at authentication layer.",
        "mfa_policy": "Role-based MFA enforcement matrix.",
        "session_policy": "Session timeout and concurrency controls.",
        "ip_allowlisting": "Admin access restriction by trusted IP ranges.",
        "audit_log": "Immutable security and configuration change events.",
    }
    return payload


@router.put("/security")
def update_settings_security(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["security"] = payload
    return {
        "updated": True,
        "section": "security",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["security"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/feature-flags")
def get_settings_feature_flags(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["feature_flags"])
    category_stats: list[dict[str, Any]] = []
    flags = payload["feature_flag_dashboard"]
    for category in payload["flag_categories"]:
        category_flags = [f for f in flags if f["category"] == category["category"]]
        enabled_count = sum(1 for f in category_flags if f["enabled"])
        category_stats.append(
            {
                "category": category["category"],
                "description": category["description"],
                "flags_count": len(category_flags),
                "enabled_count": enabled_count,
            }
        )
    payload["flag_categories"] = category_stats
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "feature_flags": "Centralized runtime and release flags by category.",
        "module_activation": "Module-level enable/disable configuration controls.",
        "flag_audit": "Flag change history with actor and timestamp.",
    }
    return payload


@router.put("/feature-flags")
def update_settings_feature_flags(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["feature_flags"] = payload
    return {
        "updated": True,
        "section": "feature_flags",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["feature_flags"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/integrations-api-management")
def get_settings_integrations_api_management(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["integrations_api_management"])
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "lis_integration": "LIS connector credentials, endpoint and field mapping profiles.",
        "analyzer_device_integration": "Analyzer connectivity inventory and import channel status.",
        "payment_gateways": "Payment channel configuration and merchant credentials state.",
        "communication_gateways": "SMS/email/WhatsApp provider settings and enablement controls.",
        "api_key_management": "Third-party integration API keys with lifecycle state.",
    }
    return payload


@router.put("/integrations-api-management")
def update_settings_integrations_api_management(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["integrations_api_management"] = payload
    return {
        "updated": True,
        "section": "integrations_api_management",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["integrations_api_management"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/branch-localization-management")
def get_settings_branch_localization_management(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["branch_localization_management"])
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "multi_branch_configuration": "Branch metadata and operating controls per location.",
        "pricing_discounts": "Branch-specific test pricing and discount rules.",
        "staff_permissions": "Per-branch role-permission matrix mappings.",
        "central_test_catalog": "Global test and panel catalog propagated across branches.",
        "branch_switching": "CEO quick-branch context switch control.",
    }
    return payload


@router.put("/branch-localization-management")
def update_settings_branch_localization_management(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["branch_localization_management"] = payload
    return {
        "updated": True,
        "section": "branch_localization_management",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["branch_localization_management"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/data-compliance-management")
def get_settings_data_compliance_management(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["data_compliance_management"])
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "retention_policy": "Data lifecycle and retention schedule by record class.",
        "anonymization_rules": "PII masking and anonymization transforms for analytics data.",
        "consent_management": "Consent form versioning and signature/expiry enforcement.",
        "regulatory_compliance": "DPDP/GDPR/HIPAA control modes and transfer restrictions.",
        "backup_disaster_recovery": "Backup cadence, retention, and DR readiness configuration.",
    }
    return payload


@router.put("/data-compliance-management")
def update_settings_data_compliance_management(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["data_compliance_management"] = payload
    return {
        "updated": True,
        "section": "data_compliance_management",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["data_compliance_management"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/ai-automation-configuration")
def get_settings_ai_automation_configuration(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["ai_automation_configuration"])
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "auto_validation": "AI-driven auto-validation thresholds and review gates.",
        "delta_alerts": "Longitudinal result delta thresholds and alert-routing settings.",
        "report_delivery": "Automated channel-wise report delivery controls.",
        "predictive_settings": "Predictive model enablement, refresh cadence, and drift checks.",
    }
    return payload


@router.put("/ai-automation-configuration")
def update_settings_ai_automation_configuration(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["ai_automation_configuration"] = payload
    return {
        "updated": True,
        "section": "ai_automation_configuration",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["ai_automation_configuration"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/ui-experience")
def get_settings_ui_experience(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["ui_experience"])
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "default_theme": "Global default look-and-feel preferences and display density defaults.",
        "ui_element_visibility": "Tenant-wide visibility switches for optional interface elements.",
        "dashboard_customization": "Admin-managed personalized layout controls and preset packs.",
        "role_specific_dashboards": "Role-to-dashboard defaults and key module emphasis.",
    }
    return payload


@router.put("/ui-experience")
def update_settings_ui_experience(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["ui_experience"] = payload
    return {
        "updated": True,
        "section": "ui_experience",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["ui_experience"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/maintenance-system-health")
def get_settings_maintenance_system_health(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["maintenance_system_health"])
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "system_status_dashboard": "Operational status rollup across branches, integrations, DB and backups.",
        "scheduled_jobs_automations": "Central schedule and run outcomes for platform automations.",
        "maintenance_mode": "System-wide maintenance mode and user-facing announcement controls.",
        "error_incident_log": "Consolidated operational incident feed with severity and resolution state.",
    }
    return payload


@router.put("/maintenance-system-health")
def update_settings_maintenance_system_health(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["maintenance_system_health"] = payload
    return {
        "updated": True,
        "section": "maintenance_system_health",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["maintenance_system_health"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/import-export-migration")
def get_settings_import_export_migration(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["import_export_migration"])
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "bulk_data_import": "Bulk onboarding pipeline for employee/doctor/patient/test master data.",
        "bulk_data_export": "Data extraction controls for reporting, analytics, and migration workflows.",
        "data_migration_tools": "Legacy connector setup, run orchestration, validation, and rollback controls.",
    }
    return payload


@router.put("/import-export-migration")
def update_settings_import_export_migration(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["import_export_migration"] = payload
    return {
        "updated": True,
        "section": "import_export_migration",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["import_export_migration"]),
        "table_reference": _table_reference_snapshot(db),
    }


@router.get("/wow-features")
def get_settings_wow_features(db: Session = Depends(get_db)):
    payload = deepcopy(SETTINGS_STORE["wow_features"])
    payload["is_mock"] = True
    payload["table_reference"] = _table_reference_snapshot(db)
    payload["future_data_mapping"] = {
        "digital_constitution_version_control": "Versioned configuration change history with rollback capability.",
        "configuration_push": "Centralized push operation distributing config to all branches.",
        "zero_downtime_feature_rollout": "Canary rollout controls using progressive percentage-based enablement.",
        "automated_system_health_report": "Scheduled AI-generated ops and health narrative with KPI snapshot.",
    }
    return payload


@router.put("/wow-features")
def update_settings_wow_features(payload: dict[str, Any], db: Session = Depends(get_db)):
    SETTINGS_STORE["wow_features"] = payload
    return {
        "updated": True,
        "section": "wow_features",
        "saved_at": datetime.utcnow().isoformat(),
        "is_mock": True,
        "payload": deepcopy(SETTINGS_STORE["wow_features"]),
        "table_reference": _table_reference_snapshot(db),
    }
