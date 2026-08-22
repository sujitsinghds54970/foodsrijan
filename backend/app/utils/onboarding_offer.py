from __future__ import annotations

import asyncio
import io
import logging
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional
from urllib.request import urlopen

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


def _safe_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _draw_gradient_background(c: canvas.Canvas, width: float, height: float) -> None:
    start = (79, 70, 229)   # #4F46E5
    end = (124, 58, 237)    # #7C3AED
    steps = 110
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = start[0] + (end[0] - start[0]) * t
        g = start[1] + (end[1] - start[1]) * t
        b = start[2] + (end[2] - start[2]) * t
        c.setFillColor(colors.Color(r / 255.0, g / 255.0, b / 255.0, alpha=0.22))
        y = (height / steps) * i
        c.rect(0, y, width, (height / steps) + 2, stroke=0, fill=1)


def _draw_header_logo(c: canvas.Canvas, branch_data: dict[str, Any], page_width: float, top_y: float) -> None:
    logo_url = _safe_str(branch_data.get("logo_url") or branch_data.get("director_photo_url"))
    if not logo_url:
        return
    try:
        with urlopen(logo_url, timeout=3) as response:
            content = response.read()
        image = ImageReader(io.BytesIO(content))
        c.drawImage(image, page_width - 130, top_y - 28, width=90, height=28, preserveAspectRatio=True, mask="auto")
    except Exception as exc:
        logger.warning("Offer letter logo fetch failed: %s", exc)


def _draw_multiline(c: canvas.Canvas, text: str, x: float, y: float, max_chars: int = 90, leading: int = 15) -> float:
    words = text.split()
    lines: list[str] = []
    current = []
    for word in words:
        probe = " ".join(current + [word]).strip()
        if len(probe) <= max_chars:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))

    cursor = y
    for line in lines:
        c.drawString(x, cursor, line)
        cursor -= leading
    return cursor


def generate_offer_letter_pdf(user_data: dict[str, Any], branch_data: dict[str, Any], role: str) -> io.BytesIO:
    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    _draw_gradient_background(c, page_width, page_height)

    c.setFillColor(colors.white)
    c.roundRect(34, 36, page_width - 68, page_height - 72, radius=20, stroke=0, fill=1)

    top_y = page_height - 72
    _draw_header_logo(c, branch_data, page_width, top_y)

    branch_name = _safe_str(branch_data.get("name"), "VaidyaVihar Diagnostic")
    branch_address = _safe_str(branch_data.get("address"), "Branch Address")
    branch_city = _safe_str(branch_data.get("city"))
    branch_state = _safe_str(branch_data.get("state"))
    branch_phone = _safe_str(branch_data.get("phone"), "N/A")
    branch_email = _safe_str(branch_data.get("email"), "hr@vaidyavihar.com")

    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(52, top_y - 8, branch_name)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawString(52, top_y - 24, f"{branch_address}, {branch_city}, {branch_state}")
    c.drawString(52, top_y - 38, f"Contact: {branch_phone} | Email: {branch_email}")

    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.setLineWidth(1)
    c.line(52, top_y - 48, page_width - 52, top_y - 48)

    c.setFillColor(colors.HexColor("#1F2937"))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(52, top_y - 88, "OFFER LETTER")

    full_name = _safe_str(
        user_data.get("full_name")
        or f"{_safe_str(user_data.get('first_name'))} {_safe_str(user_data.get('last_name'))}".strip(),
        "Candidate",
    )
    role_title = _safe_str(role).replace("_", " ").title()
    joining_date = _safe_str(user_data.get("joining_date"), datetime.utcnow().strftime("%Y-%m-%d"))
    reporting_manager = _safe_str(user_data.get("reporting_manager"), "Branch Operations Manager")
    salary = _safe_str(user_data.get("salary"), "As per company policy")

    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#374151"))
    cursor = top_y - 118
    body_intro = (
        f"Dear {full_name}, We are pleased to offer you the position of {role_title} at {branch_name}. "
        "Your dedication and expertise will contribute significantly to our mission of delivering "
        "excellent diagnostic care."
    )
    cursor = _draw_multiline(c, body_intro, 52, cursor, max_chars=95, leading=16) - 8

    c.setFont("Helvetica-Bold", 11)
    c.drawString(52, cursor, "Employment Details")
    cursor -= 18
    c.setFont("Helvetica", 11)
    c.drawString(62, cursor, f"Joining Date: {joining_date}")
    cursor -= 16
    c.drawString(62, cursor, f"Ordering Manager: {reporting_manager}")
    cursor -= 16
    c.drawString(62, cursor, f"Compensation: {salary}")
    cursor -= 26

    c.setFont("Helvetica-Bold", 11)
    c.drawString(52, cursor, "Terms & Conditions")
    cursor -= 18
    c.setFont("Helvetica", 10)
    terms = (
        "1. This offer is subject to successful verification of submitted documents and background details. "
        "2. You are expected to follow VaidyaVihar policies, patient confidentiality standards, and code of conduct. "
        "3. Employment terms, benefits, and statutory deductions will be governed by applicable company policies and law."
    )
    _draw_multiline(c, terms, 52, cursor, max_chars=100, leading=14)

    c.setFillColor(colors.HexColor("#6B7280"))
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(52, 64, "Digitally Signed by VaidyaVihar")
    c.drawRightString(page_width - 52, 64, f"Issue Date: {datetime.utcnow().strftime('%d %b %Y')}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def _offer_email_html(user_name: str, role: str, branch_name: str) -> str:
    role_title = _safe_str(role).replace("_", " ").title()
    return f"""
    <html>
      <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
        <div style="max-width:640px;margin:20px auto;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e5e7eb;">
          <div style="background:linear-gradient(90deg,#4F46E5,#7C3AED);padding:20px 24px;color:#ffffff;">
            <h2 style="margin:0;font-size:22px;">Welcome to VaidyaVihar Diagnostic</h2>
            <p style="margin:6px 0 0 0;font-size:13px;opacity:0.95;">Your onboarding has started successfully.</p>
          </div>
          <div style="padding:24px;">
            <p style="margin:0 0 12px 0;color:#111827;font-size:15px;">Dear {user_name},</p>
            <p style="margin:0 0 12px 0;color:#374151;font-size:14px;line-height:1.6;">
              Congratulations! We are delighted to share your Offer Letter for the position of
              <strong>{role_title}</strong> at <strong>{branch_name}</strong>.
            </p>
            <p style="margin:0 0 14px 0;color:#374151;font-size:14px;line-height:1.6;">
              Please find your offer letter attached as a PDF. We look forward to your successful journey with us.
            </p>
            <div style="margin-top:20px;padding:14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;color:#475569;font-size:13px;">
              If you have any questions, please contact HR or your reporting manager.
            </div>
            <p style="margin:20px 0 0 0;color:#6b7280;font-size:12px;">This is an automated communication from VaidyaVihar Diagnostic.</p>
          </div>
        </div>
      </body>
    </html>
    """


def send_offer_email(to_email: str, user_name: str, pdf_buffer: io.BytesIO, role: str, branch_name: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username or "noreply@vaidyavihar.com")
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() != "false"

    subject = f"🎉 Offer Letter from VaidyaVihar Diagnostic – {user_name}"
    html_body = _offer_email_html(user_name=user_name, role=role, branch_name=branch_name)
    text_body = f"Dear {user_name}, your offer letter from VaidyaVihar Diagnostic is attached."

    if not smtp_username or not smtp_password:
        logger.warning("SMTP not configured. Offer email skipped for %s. Subject=%s", to_email, subject)
        return False

    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    pdf_attachment = MIMEApplication(pdf_buffer.getvalue(), _subtype="pdf")
    pdf_attachment.add_header("Content-Disposition", "attachment", filename="Offer_Letter.pdf")
    message.attach(pdf_attachment)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, [to_email], message.as_string())
        logger.info("Offer email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send offer email to %s: %s", to_email, exc)
        return False


def send_offer_sms(to_phone: str, user_name: str, role: str, branch_name: str) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    sender = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
    if not sid or not token or not sender:
        logger.warning(
            "SMS provider not fully configured. Offer SMS skipped for %s. User=%s Role=%s Branch=%s",
            to_phone,
            user_name,
            role,
            branch_name,
        )
        return False

    role_title = _safe_str(role).replace("_", " ").title()
    body = (
        f"Dear {user_name}, congratulations! Your offer for {role_title} at {branch_name} "
        "has been issued. Please check your registered email for the offer letter PDF. "
        "- VaidyaVihar Diagnostic"
    )

    try:
        from app.services.sms_service import create_sms_service_from_env

        sms_service = create_sms_service_from_env()
        result = asyncio.run(sms_service.send_sms(to=to_phone, body=body, priority="high", reference_type="offer_letter"))
        if not result.success:
            logger.warning("Offer SMS failed for %s: %s", to_phone, result.error)
            return False
        logger.info("Offer SMS sent to %s", to_phone)
        return True
    except Exception as exc:
        logger.error("Failed to send offer SMS to %s: %s", to_phone, exc)
        return False


def run_offer_letter_workflow(
    *,
    user_data: dict[str, Any],
    branch_data: dict[str, Any],
    role: str,
) -> dict[str, bool]:
    user_name = _safe_str(
        user_data.get("full_name")
        or f"{_safe_str(user_data.get('first_name'))} {_safe_str(user_data.get('last_name'))}".strip(),
        "Candidate",
    )
    user_email = _safe_str(user_data.get("email"))
    user_phone = _safe_str(user_data.get("phone"))
    branch_name = _safe_str(branch_data.get("name"), "VaidyaVihar Diagnostic")

    pdf_buffer = generate_offer_letter_pdf(user_data=user_data, branch_data=branch_data, role=role)
    email_sent = send_offer_email(
        to_email=user_email,
        user_name=user_name,
        pdf_buffer=pdf_buffer,
        role=role,
        branch_name=branch_name,
    ) if user_email else False
    sms_sent = send_offer_sms(
        to_phone=user_phone,
        user_name=user_name,
        role=role,
        branch_name=branch_name,
    ) if user_phone else False
    return {"email_sent": email_sent, "sms_sent": sms_sent}
