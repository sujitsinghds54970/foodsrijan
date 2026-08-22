"""
WhatsApp Service for VaidyaVihar Diagnostic ERP

Provides WhatsApp messaging via WhatsApp Cloud API for:
- Order delivery
- Appointment reminders
- Payment receipts
- Critical alerts
- Staff notifications
"""

import os
import json
import base64
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class WhatsAppProvider(str, Enum):
    """Supported WhatsApp providers"""
    WHATSAPP_CLOUD = "whatsapp_cloud"
    TWILIO_WHATSAPP = "twilio_whatsapp"
    DIALOG360 = "dialog360"


@dataclass
class WhatsAppConfig:
    """WhatsApp configuration settings"""
    provider: WhatsAppProvider = WhatsAppProvider.WHATSAPP_CLOUD
    
    # WhatsApp Cloud API credentials
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_access_token: str = ""
    
    # Twilio WhatsApp credentials
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""
    
    # Dialog360 credentials
    dialog360_business_id: str = ""
    dialog360_token: str = ""
    
    # Common settings
    default_country_code: str = "91"
    webhook_verify_token: str = ""
    app_secret: str = ""
    
    # Template approval
    approved_templates: Dict[str, str] = field(default_factory=dict)


@dataclass
class WhatsAppMessage:
    """WhatsApp message structure"""
    to: str  # Phone number with country code
    message_type: str = "text"  # text, template, image, document, audio, video
    content: Dict = field(default_factory=dict)
    priority: str = "normal"
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None


@dataclass
class WhatsAppResponse:
    """Response from WhatsApp send operation"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    sent_at: Optional[datetime] = None


class WhatsAppServiceError(Exception):
    """Custom exception for WhatsApp service errors"""
    pass


class BaseWhatsAppProvider:
    """Base class for WhatsApp providers"""

    def __init__(self, config: WhatsAppConfig):
        self.config = config

    async def send(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send a single WhatsApp message"""
        raise NotImplementedError

    async def send_bulk(self, messages: List[WhatsAppMessage]) -> List[WhatsAppResponse]:
        """Send multiple WhatsApp messages"""
        responses = []
        for message in messages:
            response = await self.send(message)
            responses.append(response)
        return responses


class WhatsAppCloudProvider(BaseWhatsAppProvider):
    """WhatsApp Cloud API provider implementation"""

    def __init__(self, config: WhatsAppConfig):
        super().__init__(config)
        self.base_url = "https://graph.facebook.com/v17.0"
        self.api_version = "v17.0"

    async def send(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send WhatsApp message via Cloud API"""
        try:
            # Format phone number
            to = self._format_phone(message.to)
            
            headers = {
                "Authorization": f"Bearer {self.config.whatsapp_access_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": message.message_type,
                **message.content
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{self.config.whatsapp_phone_number_id}/messages",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return WhatsAppResponse(
                        success=True,
                        message_id=data.get("messages", [{}])[0].get("id"),
                        provider="whatsapp_cloud",
                        sent_at=datetime.now()
                    )
                else:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    return WhatsAppResponse(
                        success=False,
                        error=error_message,
                        provider="whatsapp_cloud"
                    )

        except Exception as e:
            logger.error(f"WhatsApp Cloud API error: {e}")
            return WhatsAppResponse(
                success=False,
                error=str(e),
                provider="whatsapp_cloud"
            )

    def _format_phone(self, phone: str) -> str:
        """Format phone number for WhatsApp"""
        # Remove any spaces or special characters
        phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")

        # Add country code if not present
        if len(phone) == 10:
            phone = self.config.default_country_code + phone

        return phone


class TwilioWhatsAppProvider(BaseWhatsAppProvider):
    """Twilio WhatsApp provider implementation"""

    def __init__(self, config: WhatsAppConfig):
        super().__init__(config)
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{config.twilio_account_sid}"

    async def send(self, message: WhatsAppMessage) -> WhatsAppResponse:
        """Send WhatsApp message via Twilio"""
        try:
            # Format phone number for Twilio WhatsApp
            to = f"whatsapp:{self._format_phone(message.to)}"
            from_num = f"whatsapp:{self.config.twilio_whatsapp_number}"

            async with httpx.AsyncClient() as client:
                if message.message_type == "text":
                    response = await client.post(
                        f"{self.base_url}/Messages.json",
                        auth=(self.config.twilio_account_sid, self.config.twilio_auth_token),
                        data={
                            "To": to,
                            "From": from_num,
                            "Body": message.content.get("body", "")
                        },
                        timeout=30
                    )
                else:
                    # Handle media messages
                    response = await client.post(
                        f"{self.base_url}/Messages.json",
                        auth=(self.config.twilio_account_sid, self.config.twilio_auth_token),
                        data={
                            "To": to,
                            "From": from_num,
                            **message.content
                        },
                        timeout=30
                    )

                if response.status_code == 201:
                    data = response.json()
                    return WhatsAppResponse(
                        success=True,
                        message_id=data.get("sid"),
                        provider="twilio_whatsapp",
                        sent_at=datetime.now()
                    )
                else:
                    error_data = response.json()
                    return WhatsAppResponse(
                        success=False,
                        error=error_data.get("message", "Unknown error"),
                        provider="twilio_whatsapp"
                    )

        except Exception as e:
            logger.error(f"Twilio WhatsApp error: {e}")
            return WhatsAppResponse(
                success=False,
                error=str(e),
                provider="twilio_whatsapp"
            )

    def _format_phone(self, phone: str) -> str:
        """Format phone number for Twilio"""
        phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
        
        if len(phone) == 10:
            phone = self.config.default_country_code + phone
        
        return phone


class WhatsAppService:
    """
    Main WhatsApp service class
    """

    def __init__(self, config: Optional[WhatsAppConfig] = None):
        self.config = config or WhatsAppConfig()
        self._provider: Optional[BaseWhatsAppProvider] = None

    def configure(self, config: WhatsAppConfig):
        """Configure WhatsApp service"""
        self.config = config
        self._provider = self._create_provider()
        logger.info(f"WhatsApp service configured with provider: {config.provider}")

    def _create_provider(self) -> BaseWhatsAppProvider:
        """Create WhatsApp provider based on configuration"""
        if self.config.provider == WhatsAppProvider.WHATSAPP_CLOUD:
            return WhatsAppCloudProvider(self.config)
        elif self.config.provider == WhatsAppProvider.TWILIO_WHATSAPP:
            return TwilioWhatsAppProvider(self.config)
        else:
            return WhatsAppCloudProvider(self.config)

    async def send_message(
        self,
        to: str,
        body: str,
        priority: str = "normal",
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None
    ) -> WhatsAppResponse:
        """Send a simple text message"""
        if not self._provider:
            self._provider = self._create_provider()

        message = WhatsAppMessage(
            to=to,
            message_type="text",
            content={"text": {"body": body}},
            priority=priority,
            reference_id=reference_id,
            reference_type=reference_type
        )

        return await self._provider.send(message)

    async def send_document(
        self,
        to: str,
        document_url: str,
        caption: str,
        filename: str,
        mime_type: str = "application/pdf",
        reference_id: Optional[str] = None
    ) -> WhatsAppResponse:
        """Send a document (PDF, etc.)"""
        if not self._provider:
            self._provider = self._create_provider()

        message = WhatsAppMessage(
            to=to,
            message_type="document",
            content={
                "document": {
                    "link": document_url,
                    "caption": caption,
                    "filename": filename,
                    "mime_type": mime_type
                }
            },
            reference_id=reference_id
        )

        return await self._provider.send(message)

    async def send_image(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None,
        reference_id: Optional[str] = None
    ) -> WhatsAppResponse:
        """Send an image"""
        if not self._provider:
            self._provider = self._create_provider()

        content = {"image": {"link": image_url}}
        if caption:
            content["image"]["caption"] = caption

        message = WhatsAppMessage(
            to=to,
            message_type="image",
            content=content,
            reference_id=reference_id
        )

        return await self._provider.send(message)

    async def send_template(
        self,
        to: str,
        template_name: str,
        template_params: Dict[str, str],
        reference_id: Optional[str] = None
    ) -> WhatsAppResponse:
        """Send a pre-approved template message"""
        if not self._provider:
            self._provider = self._create_provider()

        # Build components for template message
        components = []
        parameters = []

        for key, value in template_params.items():
            parameters.append({"type": "text", "text": value})

        components.append({
            "type": "body",
            "parameters": parameters
        })

        message = WhatsAppMessage(
            to=to,
            message_type="template",
            content={
                "template": {
                    "name": template_name,
                    "language": {"code": "en"},
                    "components": components
                }
            },
            reference_id=reference_id
        )

        return await self._provider.send(message)

    # === Pre-built Message Templates ===

    async def send_report_ready_message(
        self,
        to: str,
        patient_name: str,
        report_id: str,
        report_type: str,
        portal_url: str
    ) -> WhatsAppResponse:
        """Send report ready notification with download link"""
        body = (
            f"Dear {patient_name},\n\n"
            f"Your {report_type} report is ready!\n\n"
            f"📋 Order ID: {report_id}\n"
            f"You can download your report from:\n"
            f"{portal_url}\n\n"
            f"Thank you for choosing VaidyaVihar Diagnostic! 🏥"
        )
        return await self.send_message(to, body, reference_id=report_id)

    async def send_report_to_doctor(
        self,
        to: str,
        doctor_name: str,
        patient_name: str,
        patient_age: str,
        patient_gender: str,
        report_type: str,
        report_summary: str,
        report_url: str,
        is_urgent: bool = False
    ) -> WhatsAppResponse:
        """Send report to referring doctor"""
        urgency = "🔴 URGENT: " if is_urgent else ""
        body = (
            f"{urgency}Dear Dr. {doctor_name},\n\n"
            f"A new {report_type} report has been generated for your patient:\n\n"
            f"👤 Customer: {patient_name}\n"
            f"🎂 Age/Gender: {patient_age}/{patient_gender}\n"
            f"📋 Order Type: {report_type}\n\n"
            f"📝 Summary:\n{report_summary}\n\n"
            f"📥 View complete report:\n{report_url}\n\n"
            f"- VaidyaVihar Diagnostic"
        )
        priority = "urgent" if is_urgent else "normal"
        return await self.send_message(to, body, priority=priority)

    async def send_appointment_reminder(
        self,
        to: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        branch_name: str,
        branch_address: str
    ) -> WhatsAppResponse:
        """Send appointment reminder"""
        body = (
            f"Dear {patient_name},\n\n"
            f"⏰ Appointment Reminder\n\n"
            f"👨‍⚕️ Staff: Dr. {doctor_name}\n"
            f"📅 Date: {appointment_date}\n"
            f"🕐 Time: {appointment_time}\n"
            f"🏥 Location: {branch_name}\n"
            f"📍 Address: {branch_address}\n\n"
            f"Please arrive 15 minutes before your scheduled time.\n\n"
            f"- VaidyaVihar Diagnostic"
        )
        return await self.send_message(to, body)

    async def send_payment_receipt(
        self,
        to: str,
        patient_name: str,
        invoice_id: str,
        amount: float,
        payment_mode: str,
        balance: float,
        receipt_url: str
    ) -> WhatsAppResponse:
        """Send payment receipt"""
        body = (
            f"Dear {patient_name},\n\n"
            f"✅ Payment Received!\n\n"
            f"📄 Invoice ID: {invoice_id}\n"
            f"💰 Amount Paid: ₹{amount:.2f}\n"
            f"💳 Mode: {payment_mode}\n"
            f"📊 Balance Due: ₹{balance:.2f}\n\n"
            f"📥 Download Receipt:\n{receipt_url}\n\n"
            f"Thank you! - VaidyaVihar Diagnostic"
        )
        return await self.send_message(to, body)

    async def send_sample_collection_reminder(
        self,
        to: str,
        patient_name: str,
        test_names: List[str],
        collection_date: str,
        collection_time: str,
        instructions: Optional[str] = None
    ) -> WhatsAppResponse:
        """Send sample collection reminder"""
        menu_items = "\n• ".join(test_names)
        body = (
            f"Dear {patient_name},\n\n"
            f"🧪 Sample Collection Reminder\n\n"
            f"MenuItems:\n• {menu_items}\n\n"
            f"📅 Date: {collection_date}\n"
            f"🕐 Time: {collection_time}\n\n"
        )

        if instructions:
            body += f"📋 Instructions:\n{instructions}\n\n"

        body += (
            f"Please fast for 8-10 hours before collection (if required).\n"
            f"Bring this message for easy check-in.\n\n"
            f"- VaidyaVihar Diagnostic"
        )
        return await self.send_message(to, body)

    async def send_otp(
        self,
        to: str,
        otp: str,
        purpose: str = "verification"
    ) -> WhatsAppResponse:
        """Send OTP via WhatsApp"""
        body = (
            f"🔐 OTP for {purpose}\n\n"
            f"Your verification code is:\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"   {otp}\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"This OTP is valid for 10 minutes.\n"
            f"Do not share this with anyone.\n\n"
            f"- VaidyaVihar Diagnostic"
        )
        return await self.send_message(to, body, priority="high")

    async def send_critical_alert(
        self,
        to: str,
        recipient_name: str,
        patient_name: str,
        test_name: str,
        critical_value: str,
        recommendation: str
    ) -> WhatsAppResponse:
        """Send critical value alert"""
        body = (
            f"🔴 CRITICAL ALERT\n\n"
            f"Dear {recipient_name},\n\n"
            f"⚠️ Critical value detected for:\n"
            f"Customer: {patient_name}\n"
            f"MenuItem: {test_name}\n"
            f"Value: {critical_value}\n\n"
            f"💡 Recommendation:\n{recommendation}\n\n"
            f"Please take immediate action.\n\n"
            f"- VaidyaVihar Diagnostic"
        )
        return await self.send_message(to, body, priority="urgent")

    async def send_appointment_confirmation(
        self,
        to: str,
        patient_name: str,
        appointment_id: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str,
        branch_name: str
    ) -> WhatsAppResponse:
        """Send appointment confirmation"""
        body = (
            f"Dear {patient_name},\n\n"
            f"✅ Appointment Confirmed!\n\n"
            f"🆔 Appointment ID: {appointment_id}\n"
            f"👨‍⚕️ Staff: Dr. {doctor_name}\n"
            f"📅 Date: {appointment_date}\n"
            f"🕐 Time: {appointment_time}\n"
            f"🏥 Center: {branch_name}\n\n"
            f"Please arrive 15 minutes before your scheduled time.\n\n"
            f"- VaidyaVihar Diagnostic"
        )
        return await self.send_message(to, body)

    async def send_bulk_message(
        self,
        recipients: List[str],
        body: str
    ) -> List[WhatsAppResponse]:
        """Send message to multiple recipients"""
        responses = []
        for to in recipients:
            response = await self.send_message(to, body)
            responses.append(response)
        return responses


# Global WhatsApp service instance
whatsapp_service = WhatsAppService()


def get_whatsapp_service() -> WhatsAppService:
    """Get the global WhatsApp service instance"""
    return whatsapp_service


# Factory function
def create_whatsapp_service_from_env() -> WhatsAppService:
    """Create WhatsApp service from environment variables"""
    config = WhatsAppConfig(
        provider=WhatsAppProvider(os.getenv("WHATSAPP_PROVID", "whatsapp_cloud")),
        whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        whatsapp_business_account_id=os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
        whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
        default_country_code=os.getenv("WHATSAPP_DEFAULT_COUNTRY_CODE", "91")
    )

    service = WhatsAppService(config)
    return service

