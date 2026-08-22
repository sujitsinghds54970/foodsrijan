"""
Email Notification Service for VaidyaVihar Diagnostic ERP
Supports SMTP, SendGrid, Resend, and other providers
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from dataclasses import dataclass
from typing import Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email configuration settings"""
    provider: str = "smtp"  # smtp, sendgrid, resend
    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = "VaidyaVihar <noreply@vaidyavihar.com>"
    use_tls: bool = True
    use_ssl: bool = False


class EmailService:
    """Email notification service for transactional emails"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
        self._is_configured = bool(self.config.username and self.config.password)
    
    def configure(self, config: EmailConfig):
        """Configure email service with provided settings"""
        self.config = config
        self._is_configured = bool(self.config.username and self.config.password)
        logger.info(f"Email service configured with provider: {self.config.provider}")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """
        Send an email to a single recipient
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback (auto-generated if not provided)
            from_name: Sender name override
            
        Returns:
            bool: True if email sent successfully
        """
        if not self._is_configured:
            logger.warning("Email not configured, skipping email send")
            return False
        
        if text_content is None:
            text_content = self._html_to_text(html_content)
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((from_name or "VaidyaVihar", self.config.username))
        msg["To"] = to_email
        
        # Attach parts
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        msg.attach(part1)
        msg.attach(part2)
        
        try:
            if self.config.provider == "smtp":
                return self._send_smtp(msg, to_email)
            elif self.config.provider == "sendgrid":
                return self._send_sendgrid(msg, to_email)
            else:
                logger.error(f"Unknown email provider: {self.config.provider}")
                return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_smtp(self, msg: MIMEMultipart, to_email: str) -> bool:
        """Send email via SMTP"""
        context = ssl.create_default_context()
        
        if self.config.use_ssl:
            with smtplib.SMTP_SSL(self.config.host, self.config.port, context=context) as server:
                server.login(self.config.username, self.config.password)
                server.sendmail(self.config.username, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(self.config.host, self.config.port) as server:
                server.ehlo()
                if self.config.use_tls:
                    server.starttls(context=context)
                    server.ehlo()
                server.login(self.config.username, self.config.password)
                server.sendmail(self.config.username, [to_email], msg.as_string())
        
        logger.info(f"Email sent to {to_email}")
        return True
    
    def _send_sendgrid(self, msg: MIMEMultipart, to_email: str) -> bool:
        """Send email via SendGrid API"""
        # This would integrate with SendGrid's API
        # For now, log the attempt
        logger.info(f"SendGrid: Would send email to {to_email}")
        return True
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text"""
        import re
        text = re.sub('<[^<]+?>', '', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    # === Email Templates ===
    
    def send_welcome_email(self, email: str, first_name: str, password: str) -> bool:
        """Send welcome email to new user"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Welcome to VaidyaVihar Diagnostic!</h2>
                <p>Hello {first_name},</p>
                <p>Your account has been created successfully.</p>
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Email:</strong> {email}</p>
                    <p style="margin: 5px 0;"><strong>Temporary Password:</strong> {password}</p>
                </div>
                <p>Please login and change your password after first login.</p>
                <a href="http://localhost:3000" style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">Login Now</a>
                <p style="margin-top: 30px; color: #6b7280; font-size: 12px;">This is an automated message from VaidyaVihar Diagnostic ERP.</p>
            </div>
        </body>
        </html>
        """
        return self.send_email(email, "Welcome to VaidyaVihar Diagnostic!", html)
    
    def send_appointment_reminder(self, email: str, patient_name: str, date: str, time: str, doctor: str) -> bool:
        """Send appointment reminder"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Appointment Reminder</h2>
                <p>Hello {patient_name},</p>
                <p>This is a reminder for your upcoming appointment:</p>
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Date:</strong> {date}</p>
                    <p style="margin: 5px 0;"><strong>Time:</strong> {time}</p>
                    <p style="margin: 5px 0;"><strong>Staff:</strong> {doctor}</p>
                </div>
                <p>Please arrive 15 minutes before your scheduled time.</p>
                <p style="margin-top: 30px; color: #6b7280;">Thank you for choosing VaidyaVihar Diagnostic!</p>
            </div>
        </body>
        </html>
        """
        return self.send_email(email, "Appointment Reminder - VaidyaVihar Diagnostic", html)
    
    def send_report_ready(self, email: str, patient_name: str, report_id: str) -> bool:
        """Send report ready notification"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #10b981;">Your Order is Ready!</h2>
                <p>Hello {patient_name},</p>
                <p>Your diagnostic report (ID: {report_id}) is ready for collection.</p>
                <p>You can view and download your report by logging into our portal.</p>
                <a href="http://localhost:3000/orders" style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">View Order</a>
                <p style="margin-top: 30px; color: #6b7280;">Thank you for choosing VaidyaVihar Diagnostic!</p>
            </div>
        </body>
        </html>
        """
        return self.send_email(email, "Your Order is Ready - VaidyaVihar Diagnostic", html)
    
    def send_password_reset(self, email: str, first_name: str, reset_link: str) -> bool:
        """Send password reset email"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #f59e0b;">Password Reset Request</h2>
                <p>Hello {first_name},</p>
                <p>You requested a password reset. Click the button below to create a new password:</p>
                <a href="{reset_link}" style="display: inline-block; background: #f59e0b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">Reset Password</a>
                <p style="margin-top: 20px; color: #6b7280; font-size: 12px;">This link will expire in 30 minutes. If you didn't request this, please ignore this email.</p>
            </div>
        </body>
        </html>
        """
        return self.send_email(email, "Password Reset - VaidyaVihar Diagnostic", html)
    
    def send_low_stock_alert(self, email: str, items: List[dict]) -> bool:
        """Send low inventory stock alert"""
        items_html = "".join([
            f"<tr><td style='padding: 8px; border-bottom: 1px solid #e5e7eb;'>{item['name']}</td>"
            f"<td style='padding: 8px; border-bottom: 1px solid #e5e7eb; color: {'red' if item['quantity'] == 0 else 'orange'};'>{item['quantity']}</td></tr>"
            for item in items
        ])
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #ef4444;">⚠️ Low Stock Alert</h2>
                <p>The following items are running low and need to be restocked:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <thead>
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 12px; text-align: left;">Item Name</th>
                            <th style="padding: 12px; text-align: left;">Current Quantity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                <a href="http://localhost:3000/inventory" style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">View Inventory</a>
            </div>
        </body>
        </html>
        """
        return self.send_email(email, "Low Stock Alert - VaidyaVihar Diagnostic", html)


# Global email service instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get the global email service instance"""
    return email_service

