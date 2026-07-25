"""add director and staff management tables

Revision ID: add_director_staff_management
Revises: add_branch_bank_details
Create Date: 2026-07-08 10:15:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_director_staff_management"
down_revision = "add_branch_bank_details"
branch_labels = None
depends_on = None


def upgrade():
    status_enum = sa.Enum("active", "inactive", name="directorstaffstatus")
    attendance_enum = sa.Enum("present", "absent", "leave", "holiday", name="directorattendancetype")
    leave_status_enum = sa.Enum("pending", "approved", "rejected", "cancelled", name="leavestatus")

    status_enum.create(op.get_bind(), checkfirst=True)
    attendance_enum.create(op.get_bind(), checkfirst=True)
    leave_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "director_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("photo_path", sa.String(), nullable=True),
        sa.Column("designation", sa.String(), nullable=True),
        sa.Column("mobile", sa.String(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("date_of_joining", sa.DateTime(), nullable=True),
        sa.Column("specialization", sa.String(), nullable=True),
        sa.Column("emergency_contact", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_director_profiles_id", "director_profiles", ["id"])

    op.create_table(
        "staff_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.String(length=30), nullable=False),
        sa.Column("photo_path", sa.String(), nullable=True),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("specialization", sa.String(), nullable=True),
        sa.Column("shift_timings", sa.String(), nullable=True),
        sa.Column("reporting_manager_id", sa.Integer(), nullable=True),
        sa.Column("date_of_joining", sa.DateTime(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("emergency_contact", sa.String(), nullable=True),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["reporting_manager_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_staff_profiles_id", "staff_profiles", ["id"])

    op.create_table(
        "staff_salary_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), nullable=False),
        sa.Column("basic", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("allowances", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("deductions", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("net_pay", sa.DECIMAL(12, 2), nullable=True),
        sa.Column("bank_name", sa.String(), nullable=True),
        sa.Column("account_number", sa.String(), nullable=True),
        sa.Column("ifsc_code", sa.String(), nullable=True),
        sa.Column("upi_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["staff_profile_id"], ["staff_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_profile_id"),
    )
    op.create_index("ix_staff_salary_details_id", "staff_salary_details", ["id"])

    op.create_table(
        "staff_attendance_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("attendance_date", sa.DateTime(), nullable=False),
        sa.Column("attendance_type", attendance_enum, nullable=False),
        sa.Column("clock_in_time", sa.DateTime(), nullable=True),
        sa.Column("clock_out_time", sa.DateTime(), nullable=True),
        sa.Column("clock_in_latitude", sa.String(), nullable=True),
        sa.Column("clock_in_longitude", sa.String(), nullable=True),
        sa.Column("clock_out_latitude", sa.String(), nullable=True),
        sa.Column("clock_out_longitude", sa.String(), nullable=True),
        sa.Column("clock_in_photo_path", sa.String(), nullable=True),
        sa.Column("clock_out_photo_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["staff_profile_id"], ["staff_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_attendance_logs_id", "staff_attendance_logs", ["id"])

    op.create_table(
        "staff_leave_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("leave_type", sa.String(), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("total_days", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", leave_status_enum, nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["staff_profile_id"], ["staff_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_leave_requests_id", "staff_leave_requests", ["id"])

    op.create_table(
        "staff_performance_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), nullable=False),
        sa.Column("director_user_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["director_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["staff_profile_id"], ["staff_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_performance_notes_id", "staff_performance_notes", ["id"])

    op.create_table(
        "staff_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("staff_profile_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["staff_profile_id"], ["staff_profiles.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_documents_id", "staff_documents", ["id"])

    op.create_table(
        "director_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("director_user_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["director_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_director_notifications_id", "director_notifications", ["id"])


def downgrade():
    op.drop_index("ix_director_notifications_id", table_name="director_notifications")
    op.drop_table("director_notifications")

    op.drop_index("ix_staff_documents_id", table_name="staff_documents")
    op.drop_table("staff_documents")

    op.drop_index("ix_staff_performance_notes_id", table_name="staff_performance_notes")
    op.drop_table("staff_performance_notes")

    op.drop_index("ix_staff_leave_requests_id", table_name="staff_leave_requests")
    op.drop_table("staff_leave_requests")

    op.drop_index("ix_staff_attendance_logs_id", table_name="staff_attendance_logs")
    op.drop_table("staff_attendance_logs")

    op.drop_index("ix_staff_salary_details_id", table_name="staff_salary_details")
    op.drop_table("staff_salary_details")

    op.drop_index("ix_staff_profiles_id", table_name="staff_profiles")
    op.drop_table("staff_profiles")

    op.drop_index("ix_director_profiles_id", table_name="director_profiles")
    op.drop_table("director_profiles")

    leave_status_enum = sa.Enum("pending", "approved", "rejected", "cancelled", name="leavestatus")
    attendance_enum = sa.Enum("present", "absent", "leave", "holiday", name="directorattendancetype")
    status_enum = sa.Enum("active", "inactive", name="directorstaffstatus")

    leave_status_enum.drop(op.get_bind(), checkfirst=True)
    attendance_enum.drop(op.get_bind(), checkfirst=True)
    status_enum.drop(op.get_bind(), checkfirst=True)
