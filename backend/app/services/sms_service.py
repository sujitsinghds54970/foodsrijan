"""
SMS Service for VaidyaVihar Diagnostic ERP

Provides SMS notifications via Twilio for:
- Appointment reminders
- Order ready alerts
- Payment confirmations
- Critical value notifications
- OTP verification
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class SMSProvider(str, Enum):
    """Supported SMS providers"""
    TWILIO = "twilio"
    FAST2SMS = "fast2sms"
    TEXTLOCAL = "textlocal"
    MSG91 = "msg91"


@dataclass
class SMSConfig:
    """SMS configuration settings"""
    provider: SMSProvider = SMSProvider.TWILIO
    
    # Twilio credentials
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    
    # Fast2SMS credentials
    fast2sms_api_key: str = ""
    
    # TextLocal credentials
    textlocal_api_key: str = ""
    textlocal_sender: str = "VAIDYA"
    
    # MSG91 credentials
    msg91_auth_key: str = ""
    msg91_template_id: str = ""
    
    # Common settings
    default_sender: str = "VAIDYA"
    timeout: int = 30


@dataclass
class SMSMessage:
    """SMS message structure"""
    to: str
    body: str
    priority: str = "normal"  # low, normal, high, urgent
    scheduled_at: Optional[datetime] = None
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None


@dataclass
class SMSResponse:
    """Response from SMS send operation"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    sent_at: Optional[datetime] = None


class SMSServiceError(Exception):
    """Custom exception for SMS service errors"""
    pass


class BaseSMSProvider:
    """Base class for SMS providers"""

    def __init__(self, config: SMSConfig):
        self.config = config

    async def send(self, message: SMSMessage) -> SMSResponse:
        """Send a single SMS message"""
        raise NotImplementedError

    async def send_bulk(self, messages: List[SMSMessage]) -> List[SMSResponse]:
        """Send multiple SMS messages"""
        responses = []
        for message in messages:
            response = await self.send(message)
            responses.append(response)
        return responses


class TwilioProvider(BaseSMSProvider):
    """Twilio SMS provider implementation"""

    def __init__(self, config: SMSConfig):
        super().__init__(config)
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{config.twilio_account_sid}"

    async def send(self, message: SMSMessage) -> SMSResponse:
        """Send SMS via Twilio"""
        try:
            # Format phone number
            to = self._format_phone(message.to)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/Messages.json",
                    auth=(self.config.twilio_account_sid, self.config.twilio_auth_token),
                    data={
                        "To": to,
                        "From": self.config.twilio_phone_number or self.config.default_sender,
                        "Body": message.body
                    },
                    timeout=self.config.timeout
                )

                if response.status_code == 201:
                    data = response.json()
                    return SMSResponse(
                        success=True,
                        message_id=data.get("sid"),
                        provider="twilio",
                        sent_at=datetime.now()
                    )
                else:
                    error_data = response.json()
                    return SMSResponse(
                        success=False,
                        error=error_data.get("message", "Unknown error"),
                        provider="twilio"
                    )

        except Exception as e:
            logger.error(f"Twilio SMS error: {e}")
            return SMSResponse(
                success=False,
                error=str(e),
                provider="twilio"
            )

    def _format_phone(self, phone: str) -> str:
        """Format phone number for Twilio"""
        # Remove any spaces or special characters
        phone = phone.strip().replace(" ", "").replace("-", "")

        # Add country code if not present
        if not phone.startswith("+"):
            # Default to India (+91)
            if len(phone) == 10:
                phone = "+91" + phone
            elif len(phone) == 11 and phone.startswith("0"):
                phone = "+91" + phone[1:]
            else:
                phone = "+" + phone

        return phone


class Fast2SMSProvider(BaseSMSProvider):
    """Fast2SMS provider implementation for India"""

    async def send(self, message: SMSMessage) -> SMSResponse:
        """Send SMS via Fast2SMS"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.fast2sms.com/dev/bulkV2",
                    headers={
                        "Authorization": self.config.fast2sms_api_key
                    },
                    json={
                        "route": "v3",
                        "sender_id": self.config.default_sender,
                        "message": message.body,
                        "language": "english",
                        "flash": 0,
                        "numbers": message.to.replace("+91", "").replace(" ", "")
                    },
                    timeout=self.config.timeout
                )

                data = response.json()

                if data.get("return"):
                    return SMSResponse(
                        success=True,
                        message_id=str(data.get("request_id")),
                        provider="fast2sms",
                        sent_at=datetime.now()
                    )
                else:
                    return SMSResponse(
                        success=False,
                        error=data.get("message", "Unknown error"),
                        provider="fast2sms"
                    )

        except Exception as e:
            logger.error(f"Fast2SMS error: {e}")
            return SMSResponse(
                success=False,
                error=str(e),
                provider="fast2sms"
            )


class SMSService:
    """
    Main SMS service class that manages providers and message sending
    """

    def __init__(self, config: Optional[SMSConfig] = None):
        self.config = config or SMSConfig()
        self._provider: Optional[BaseSMSProvider] = None

    def configure(self, config: SMSConfig):
        """Configure SMS service with settings"""
        self.config = config
        self._provider = self._create_provider()
        logger.info(f"SMS service configured with provider: {config.provider}")

    def _create_provider(self) -> BaseSMSProvider:
        """Create SMS provider based on configuration"""
        if self.config.provider == SMSProvider.TWILIO:
            return TwilioProvider(self.config)
        elif self.config.provider == SMSProvider.FAST2SMS:
            return Fast2SMSProvider(self.config)
        else:
            return TwilioProvider(self.config)

    async def send_sms(
        self,
        to: str,
        body: str,
        priority: str = "normal",
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None
    ) -> SMSResponse:
        """Send a single SMS"""
        if not self._provider:
            self._provider = self._create_provider()

        message = SMSMessage(
            to=to,
            body=body,
            priority=priority,
            reference_id=reference_id,
            reference_type=reference_type
        )

        return await self._provider.send(message)

    async def send_bulk_sms(
        self,
        recipients: List[str],
        body: str,
        priority: str = "normal"
    ) -> List[SMSResponse]:
        """Send SMS to multiple recipients"""
        if not self._provider:
            self._provider = self._create_provider()

        messages = [
            SMSMessage(to=to, body=body, priority=priority)
            for to in recipients
        ]

        return await self._provider.send_bulk(messages)

    # === Pre-built Message Templates ===

    async def send_appointment_reminder(
        self,
        to: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        branch_name: str
    ) -> SMSResponse:
        """Send appointment reminder SMS"""
        body = (
            f"Dear {patient_name}, this is a reminder for your appointment with "
            f"Dr. {doctor_name} on {appointment_date} at {appointment_time} "
            f"at {branch_name}. Please arrive 15 minutes early. "
            f"Call us if you need to reschedule. - VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="normal")

    async def send_report_ready_sms(
        self,
        to: str,
        patient_name: str,
        report_type: str,
        report_id: str,
        collection_date: str
    ) -> SMSResponse:
        """Send report ready SMS"""
        body = (
            f"Dear {patient_name}, your {report_type} report (ID: {report_id}) "
            f"is ready for collection. Collected on: {collection_date}. "
            f"You can view/download it from our portal. - VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="normal")

    async def send_critical_value_alert(
        self,
        to: str,
        patient_name: str,
        test_name: str,
        critical_value: str,
        reference_range: str
    ) -> SMSResponse:
        """Send critical value alert SMS"""
        body = (
            f"URGENT: Dear {patient_name}, your {test_name} result shows "
            f"critical value: {critical_value} (Normal: {reference_range}). "
            f"Please contact your doctor immediately. - VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="urgent")

    async def send_payment_confirmation(
        self,
        to: str,
        patient_name: str,
        amount: float,
        invoice_id: str,
        payment_mode: str
    ) -> SMSResponse:
        """Send payment confirmation SMS"""
        body = (
            f"Dear {patient_name}, we have received a payment of ₹{amount:.2f} "
            f"via {payment_mode}. Invoice ID: {invoice_id}. "
            f"Thank you for choosing VaidyaVihar Diagnostic."
        )
        return await self.send_sms(to, body, priority="low")

    async def send_otp(
        self,
        to: str,
        otp: str,
        purpose: str = "verification"
    ) -> SMSResponse:
        """Send OTP SMS"""
        body = (
            f"Your OTP for {purpose} is: {otp}. "
            f"This OTP is valid for 10 minutes. Do not share with anyone. "
            f"- VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="high")

    async def send_appointment_confirmation(
        self,
        to: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        branch_name: str,
        appointment_id: str
    ) -> SMSResponse:
        """Send appointment confirmation SMS"""
        body = (
            f"Dear {patient_name}, your appointment has been confirmed with "
            f"Dr. {doctor_name} on {appointment_date} at {appointment_time} "
            f"at {branch_name}. Appointment ID: {appointment_id}. "
            f"Please arrive 15 minutes early. - VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="normal")

    async def send_appointment_cancellation(
        self,
        to: str,
        patient_name: str,
        appointment_id: str,
        reason: str = "Not specified"
    ) -> SMSResponse:
        """Send appointment cancellation SMS"""
        body = (
            f"Dear {patient_name}, your appointment (ID: {appointment_id}) "
            f"has been cancelled. Reason: {reason}. "
            f"Please contact us to reschedule. - VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="normal")

    async def send_sample_collection_reminder(
        self,
        to: str,
        patient_name: str,
        test_names: List[str],
        collection_date: str,
        instructions: Optional[str] = None
    ) -> SMSResponse:
        """Send sample collection reminder SMS"""
        menu_items = ", ".join(test_names)
        instructions_text = f"Instructions: {instructions}. " if instructions else ""
        body = (
            f"Dear {patient_name}, reminder for sample collection on {collection_date}. "
            f"MenuItems: {menu_items}. "
            f"{instructions_text}"
            f"Please fast 8-10 hours before collection if required. "
            f"- VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="normal")

    async def send_doctor_report_notification(
        self,
        to: str,
        doctor_name: str,
        patient_name: str,
        report_type: str,
        is_urgent: bool = False
    ) -> SMSResponse:
        """Send notification to doctor about new report"""
        urgency = "URGENT: " if is_urgent else ""
        body = (
            f"{urgency}Dr. {doctor_name}, a new {report_type} report is ready "
            f"for patient {patient_name}. Please check your portal or email "
            f"for the detailed report. - VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="urgent" if is_urgent else "normal")

    async def send_low_stock_alert(
        self,
        to: str,
        item_name: str,
        current_stock: int,
        minimum_stock: int,
        branch_name: str
    ) -> SMSResponse:
        """Send low stock alert SMS"""
        status = "OUT OF STOCK" if current_stock == 0 else "LOW STOCK"
        body = (
            f"ALERT: {status} - {item_name} at {branch_name}. "
            f"Current: {current_stock}, Minimum Required: {minimum_stock}. "
            f"Please arrange for immediate replenishment. - VaidyaVihar Diagnostic"
        )
        return await self.send_sms(to, body, priority="high")


# Global SMS service instance
sms_service = SMSService()


def get_sms_service() -> SMSService:
    """Get the global SMS service instance"""
    return sms_service


# Factory function for creating service with environment variables
def create_sms_service_from_env() -> SMSService:
    """Create SMS service from environment variables"""
    config = SMSConfig(
        provider=SMSProvider(os.getenv("SMS_PROVIDER", "twilio")),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER", ""),
        fast2sms_api_key=os.getenv("FAST2SMS_API_KEY", ""),
        default_sender=os.getenv("SMS_SENDER", "VAIDYA")
    )

    service = SMSService(config)
    return service

