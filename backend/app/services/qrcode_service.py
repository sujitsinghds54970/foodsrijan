"""
QR Code Service for VaidyaVihar Diagnostic ERP

Generates QR codes for:
- Patient ID cards
- Sample tracking
- Report access
- Appointment verification
"""

import io
import base64
from typing import Optional
import qrcode
from PIL import Image
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import SquareModuleDrawer, GappedSquareModuleDrawer, CircleModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from datetime import datetime


class QRCodeService:
    """QR Code generation service"""

    # Brand colors
    PRIMARY_COLOR = (37, 99, 235)  # Blue
    SECONDARY_COLOR = (16, 185, 129)  # Green

    @staticmethod
    def generate_qr_code(
        data: str,
        box_size: int = 10,
        border: int = 4,
        include_branding: bool = True
    ) -> io.BytesIO:
        """
        Generate a standard QR code
        
        Args:
            data: Data to encode in QR
            box_size: Size of each QR module
            border: Border width around QR
            include_branding: Include brand logo overlay
            
        Returns:
            BytesIO object containing QR code image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return buffer

    @staticmethod
    def generate_qr_with_logo(
        data: str,
        logo_path: Optional[str] = None,
        box_size: int = 10,
        logo_size: int = 60
    ) -> io.BytesIO:
        """Generate QR code with logo in center"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=box_size,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        # If logo provided, paste it in center
        if logo_path:
            try:
                logo = Image.open(logo_path)
                logo = logo.convert("RGBA")
                
                # Resize logo
                logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Calculate position
                pos = ((img.size[0] - logo.size[0]) // 2,
                       (img.size[1] - logo.size[1]) // 2)
                
                # Create white background for logo
                background = Image.new("RGBA", logo.size, (255, 255, 255, 255))
                background = Image.composite(logo, background, logo)
                
                img.paste(background, pos, background)
            except Exception as e:
                print(f"Error adding logo: {e}")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return buffer

    @staticmethod
    def generate_colored_qr(
        data: str,
        fill_color: tuple = (37, 99, 235),
        back_color: tuple = (255, 255, 255)
    ) -> io.BytesIO:
        """Generate QR code with custom colors"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color=fill_color,
            back_color=back_color
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return buffer

    @staticmethod
    def generate_patient_qr(
        patient_id: str,
        patient_name: str,
        dob: str,
        blood_group: Optional[str] = None
    ) -> io.BytesIO:
        """Generate patient ID QR code with medical info"""
        import json
        
        data = {
            "type": "patient",
            "id": patient_id,
            "name": patient_name,
            "dob": dob,
            "blood_group": blood_group,
            "generated_at": datetime.now().isoformat()
        }
        
        return QRCodeService.generate_qr_code(
            data=json.dumps(data),
            box_size=12,
            include_branding=True
        )

    @staticmethod
    def generate_sample_qr(
        sample_id: str,
        patient_id: str,
        test_types: list,
        collection_date: str,
        branch_code: str
    ) -> io.BytesIO:
        """Generate sample tracking QR code"""
        import json
        
        data = {
            "type": "sample",
            "sample_id": sample_id,
            "patient_id": patient_id,
            "tests": test_types,
            "collection_date": collection_date,
            "branch": branch_code,
            "generated_at": datetime.now().isoformat()
        }
        
        return QRCodeService.generate_qr_code(
            data=json.dumps(data),
            box_size=10,
            include_branding=True
        )

    @staticmethod
    def generate_report_access_qr(
        report_id: str,
        patient_id: str,
        access_token: str,
        expiry_days: int = 30
    ) -> io.BytesIO:
        """Generate secure report access QR code"""
        import json
        
        data = {
            "type": "report_access",
            "report_id": report_id,
            "patient_id": patient_id,
            "access_token": access_token,
            "expires_at": datetime.now().isoformat(),
            "expiry_days": expiry_days
        }
        
        return QRCodeService.generate_qr_code(
            data=json.dumps(data),
            box_size=12,
            include_branding=True
        )

    @staticmethod
    def generate_appointment_qr(
        appointment_id: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str
    ) -> io.BytesIO:
        """Generate appointment QR code for quick check-in"""
        import json
        
        data = {
            "type": "appointment",
            "appointment_id": appointment_id,
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "date": appointment_date,
            "time": appointment_time,
            "generated_at": datetime.now().isoformat()
        }
        
        return QRCodeService.generate_qr_code(
            data=json.dumps(data),
            box_size=10,
            include_branding=True
        )

    @staticmethod
    def qr_to_base64(buffer: io.BytesIO) -> str:
        """Convert QR code BytesIO to base64 string"""
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    def qr_to_data_uri(buffer: io.BytesIO) -> str:
        """Convert QR code to data URI"""
        b64 = QRCodeService.qr_to_base64(buffer)
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def generate_qr_svg(
        data: str,
        box_size: int = 10,
        border: int = 4
    ) -> str:
        """Generate QR code as SVG string"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Generate SVG
        from qrcode.image.svg import SvgImage
        img = qr.make_image(image_factory=SvgImage)
        
        svg_buffer = io.StringIO()
        img.save(svg_buffer)
        return svg_buffer.getvalue()


# Convenience functions
def generate_qr_code(data: str, box_size: int = 10, border: int = 4) -> io.BytesIO:
    """Generate a standard QR code - convenience wrapper"""
    return QRCodeService.generate_qr_code(data, box_size, border)


def generate_patient_qr_code(patient_id: str, patient_name: str, dob: str, blood_group: str = None) -> str:
    """Generate patient QR and return as base64"""
    buffer = QRCodeService.generate_patient_qr(patient_id, patient_name, dob, blood_group)
    return QRCodeService.qr_to_data_uri(buffer)


def generate_sample_qr_code(sample_id: str, patient_id: str, test_types: list, collection_date: str, branch_code: str) -> str:
    """Generate sample tracking QR and return as base64"""
    buffer = QRCodeService.generate_sample_qr(sample_id, patient_id, test_types, collection_date, branch_code)
    return QRCodeService.qr_to_data_uri(buffer)


def generate_report_access_qr(report_id: str, patient_id: str, access_token: str) -> str:
    """Generate report access QR and return as base64"""
    buffer = QRCodeService.generate_report_access_qr(report_id, patient_id, access_token)
    return QRCodeService.qr_to_data_uri(buffer)

