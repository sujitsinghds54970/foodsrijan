from app.database import engine, Base
from app.models.branch import Branch
from app.models.calendar_day import CalendarDay  # Add more models as you build them

def create_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    create_tables()
    print("✅ Tables created successfully in vaidya_vihar database.")
from app.models.patient_entry import CustomerEntry
from app.models.expense_entry import ExpenseEntry
from app.models.note_entry import NoteEntry
from app.models.test_entry import MenuItemEntry
from app.models.billing_entry import BillingEntry
from app.models.user import User
from app.models.inventory_item import InventoryItem
from app.models.activity_log import ActivityLog
from app.models.appointment import Appointment
from app.models.invoice import Invoice
from app.models.lab_test import LabMenuItem
from app.models.audit_log import AuditLog