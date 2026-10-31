from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from dotenv import load_dotenv
import os

from alembic import context
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
from app.database import DATABASE_URL
config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.database import Base
# Import all models to ensure they're registered
from app.models import (
    Branch, User, Customer, DailyEntry, Staff, AttendanceRecord,
    SalaryRecord, InventoryItem, StockMovement, Appointment, Invoice,
    InvoiceItem, LabResult, ActivityLog, SystemSettings
)
from app.models.authority import ProfileType, ProfileMembership, RoleAssignment
from app.models.lis import (
    MenuItemOrder, MenuItemOrderItem, Sample, MenuItemResult,
    LabMenuItemMaster, LISOrderTemplate, GeneratedOrder,
    QualityControl, InstrumentCalibration
)
from app.models.branch_lis import (
    MenuItemCatalog, MenuItemPanel, OrderQueue, Sample as BranchLISSample,
    Worklist, InstrumentCalibration as BranchLISInstrumentCalibration, QCResult,
    ProficiencyMenuItemRun, LISOrderArchive, WestgardRule
)
from app.models.payment import InsuranceClaim, Payment, PaymentReminder, ReconciliationLog, Refund
from app.models.accounting import ExpenseEntry, ExpenseCategory, Transaction, Account
from app.models.hr import (
    LeaveRequest,
    EmployeeProfile,
    Attendance,
    DirectorProfile,
    StaffProfile,
    StaffSalaryDetail,
    StaffAttendanceLog,
    StaffLeaveRequest,
    StaffPerformanceNote,
    StaffTask,
    StaffNotification,
    StaffDocument,
    DirectorNotification,
)
from app.models.patient_portal import CustomerAppointment, CustomerPrescription, CustomerPortalUser
from app.models.customer import CustomerProfile, FamilyMember
from app.models.staff import Staff, StaffBranch, OrderDistribution, StaffNotification, StaffSchedule
from app.models.daily_entry_module import DailyEntryModule
from app.models.finance import BranchAccount, FinanceExpense, FinanceInvoice, FinanceTransaction
from app.models.analytics import DailyAnalyticsSnapshot
from app.models.payroll import (
    AdvanceRequest,
    EarningHead,
    PayrollDispute,
    PayrollLock,
    PayrollRun,
    PayrollTransaction,
    ReimbursementClaim,
    SalaryGrade,
    StaffSalaryConfig,
    StaffTaxDeclaration,
)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
