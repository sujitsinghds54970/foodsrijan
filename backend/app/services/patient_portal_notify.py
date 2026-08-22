from urllib.parse import quote

from sqlalchemy.orm import Session

from app.models.daily_entry_module import DailyEntryModule
from app.models.customer import CustomerProfile


def _resolve_report_download_url(report_pdf_url: str) -> str:
    if not report_pdf_url:
        return ""
    if report_pdf_url.startswith("/api/files/"):
        return report_pdf_url
    if report_pdf_url.startswith("/uploads/"):
        filename = report_pdf_url.split("/")[-1]
        return f"/api/files/daily_entry_orders/{filename}"
    return f"/api/files/{report_pdf_url.lstrip('/')}"


def build_patient_notify_payload(
    *,
    db: Session,
    daily_entry: DailyEntryModule,
    channel: str = "whatsapp",
) -> dict | None:
    profile = (
        db.query(CustomerProfile)
        .filter(
            CustomerProfile.mobile == daily_entry.mobile,
            CustomerProfile.is_active == True,
        )
        .first()
    )
    if not profile:
        return None

    download_url = _resolve_report_download_url(daily_entry.report_pdf_url or "")
    text = f"Hi {profile.full_name}, your report {daily_entry.auto_patient_id} is ready. Download: {download_url}"

    if channel == "email":
        recipient = profile.email or ""
        channel_url = f"mailto:{recipient}?subject=Your%20Lab%20Order&body={quote(text)}"
    else:
        channel_url = f"https://wa.me/{profile.mobile}?text={quote(text)}"

    return {
        "patient_profile_id": profile.id,
        "patient_name": profile.full_name,
        "channel": channel,
        "channel_url": channel_url,
        "download_url": download_url,
        "message": text,
    }


def notify_on_daily_entry_completion(db: Session, daily_entry: DailyEntryModule) -> dict | None:
    if daily_entry.status != "Completed":
        return None
    profile = (
        db.query(CustomerProfile)
        .filter(
            CustomerProfile.mobile == daily_entry.mobile,
            CustomerProfile.is_active == True,
        )
        .first()
    )
    if profile and bool(daily_entry.is_paid):
        cashback = round(float(daily_entry.total_amount or 0) * (profile.cashback_percent or 0.0) / 100.0, 2)
        profile.wallet_balance = round((profile.wallet_balance or 0.0) + cashback, 2)
    return build_patient_notify_payload(db=db, daily_entry=daily_entry, channel="whatsapp")
