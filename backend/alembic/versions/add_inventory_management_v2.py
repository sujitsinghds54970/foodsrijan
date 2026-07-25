"""add inventory management v2 tables and daily entry consumption field

Revision ID: add_inventory_management_v2
Revises: add_referring_doctor_crm
Create Date: 2026-07-08 04:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "add_inventory_management_v2"
down_revision = "add_referring_doctor_crm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("contact_person", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("gstin", sa.String(length=30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_suppliers_id", "inventory_suppliers", ["id"], unique=False)
    op.create_index("ix_inventory_suppliers_branch_id", "inventory_suppliers", ["branch_id"], unique=False)
    op.create_index("ix_inventory_suppliers_name", "inventory_suppliers", ["name"], unique=False)

    op.create_table(
        "inventory_items_v2",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=30), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("current_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("min_threshold", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("unit_cost", sa.DECIMAL(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=50), nullable=False, server_default="units"),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("barcode_number", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["inventory_suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_items_v2_id", "inventory_items_v2", ["id"], unique=False)
    op.create_index("ix_inventory_items_v2_branch_id", "inventory_items_v2", ["branch_id"], unique=False)
    op.create_index("ix_inventory_items_v2_department", "inventory_items_v2", ["department"], unique=False)
    op.create_index("ix_inventory_items_v2_item_name", "inventory_items_v2", ["item_name"], unique=False)
    op.create_index("ix_inventory_items_v2_category", "inventory_items_v2", ["category"], unique=False)
    op.create_index("ix_inventory_items_v2_supplier_id", "inventory_items_v2", ["supplier_id"], unique=False)
    op.create_index("ix_inventory_items_v2_barcode_number", "inventory_items_v2", ["barcode_number"], unique=False)

    op.create_table(
        "inventory_equipment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=30), nullable=False),
        sa.Column("machine_name", sa.String(length=200), nullable=False),
        sa.Column("brand_model", sa.String(length=200), nullable=True),
        sa.Column("serial_number", sa.String(length=150), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("warranty_end_date", sa.Date(), nullable=True),
        sa.Column("amc_company", sa.String(length=200), nullable=True),
        sa.Column("dealer_contact", sa.String(length=100), nullable=True),
        sa.Column("last_service_date", sa.Date(), nullable=True),
        sa.Column("next_service_due_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_equipment_id", "inventory_equipment", ["id"], unique=False)
    op.create_index("ix_inventory_equipment_branch_id", "inventory_equipment", ["branch_id"], unique=False)
    op.create_index("ix_inventory_equipment_department", "inventory_equipment", ["department"], unique=False)
    op.create_index("ix_inventory_equipment_serial_number", "inventory_equipment", ["serial_number"], unique=False)
    op.create_index("ix_inventory_equipment_next_service_due_date", "inventory_equipment", ["next_service_due_date"], unique=False)

    op.create_table(
        "equipment_service_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["equipment_id"], ["inventory_equipment.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equipment_service_logs_id", "equipment_service_logs", ["id"], unique=False)
    op.create_index("ix_equipment_service_logs_equipment_id", "equipment_service_logs", ["equipment_id"], unique=False)
    op.create_index("ix_equipment_service_logs_branch_id", "equipment_service_logs", ["branch_id"], unique=False)

    op.create_table(
        "inventory_stock_movements_v2",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("previous_qty", sa.Float(), nullable=False),
        sa.Column("new_qty", sa.Float(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items_v2.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_stock_movements_v2_id", "inventory_stock_movements_v2", ["id"], unique=False)
    op.create_index("ix_inventory_stock_movements_v2_branch_id", "inventory_stock_movements_v2", ["branch_id"], unique=False)
    op.create_index("ix_inventory_stock_movements_v2_inventory_item_id", "inventory_stock_movements_v2", ["inventory_item_id"], unique=False)

    op.create_table(
        "inventory_consumption_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), nullable=False),
        sa.Column("daily_entry_id", sa.Integer(), nullable=True),
        sa.Column("patient_identifier", sa.String(length=60), nullable=True),
        sa.Column("test_name", sa.String(length=500), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("consumed_on", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items_v2.id"]),
        sa.ForeignKeyConstraint(["daily_entry_id"], ["daily_entries_module.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_consumption_history_id", "inventory_consumption_history", ["id"], unique=False)
    op.create_index("ix_inventory_consumption_history_branch_id", "inventory_consumption_history", ["branch_id"], unique=False)
    op.create_index("ix_inventory_consumption_history_inventory_item_id", "inventory_consumption_history", ["inventory_item_id"], unique=False)
    op.create_index("ix_inventory_consumption_history_daily_entry_id", "inventory_consumption_history", ["daily_entry_id"], unique=False)
    op.create_index("ix_inventory_consumption_history_patient_identifier", "inventory_consumption_history", ["patient_identifier"], unique=False)
    op.create_index("ix_inventory_consumption_history_consumed_on", "inventory_consumption_history", ["consumed_on"], unique=False)

    op.create_table(
        "inventory_stock_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), nullable=False),
        sa.Column("expected_qty", sa.Float(), nullable=False),
        sa.Column("physical_qty", sa.Float(), nullable=False),
        sa.Column("discrepancy", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("audited_on", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items_v2.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_stock_audits_id", "inventory_stock_audits", ["id"], unique=False)
    op.create_index("ix_inventory_stock_audits_branch_id", "inventory_stock_audits", ["branch_id"], unique=False)
    op.create_index("ix_inventory_stock_audits_inventory_item_id", "inventory_stock_audits", ["inventory_item_id"], unique=False)

    op.add_column(
        "daily_entries_module",
        sa.Column("consumed_inventory_items", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("daily_entries_module", "consumed_inventory_items")

    op.drop_index("ix_inventory_stock_audits_inventory_item_id", table_name="inventory_stock_audits")
    op.drop_index("ix_inventory_stock_audits_branch_id", table_name="inventory_stock_audits")
    op.drop_index("ix_inventory_stock_audits_id", table_name="inventory_stock_audits")
    op.drop_table("inventory_stock_audits")

    op.drop_index("ix_inventory_consumption_history_consumed_on", table_name="inventory_consumption_history")
    op.drop_index("ix_inventory_consumption_history_patient_identifier", table_name="inventory_consumption_history")
    op.drop_index("ix_inventory_consumption_history_daily_entry_id", table_name="inventory_consumption_history")
    op.drop_index("ix_inventory_consumption_history_inventory_item_id", table_name="inventory_consumption_history")
    op.drop_index("ix_inventory_consumption_history_branch_id", table_name="inventory_consumption_history")
    op.drop_index("ix_inventory_consumption_history_id", table_name="inventory_consumption_history")
    op.drop_table("inventory_consumption_history")

    op.drop_index("ix_inventory_stock_movements_v2_inventory_item_id", table_name="inventory_stock_movements_v2")
    op.drop_index("ix_inventory_stock_movements_v2_branch_id", table_name="inventory_stock_movements_v2")
    op.drop_index("ix_inventory_stock_movements_v2_id", table_name="inventory_stock_movements_v2")
    op.drop_table("inventory_stock_movements_v2")

    op.drop_index("ix_equipment_service_logs_branch_id", table_name="equipment_service_logs")
    op.drop_index("ix_equipment_service_logs_equipment_id", table_name="equipment_service_logs")
    op.drop_index("ix_equipment_service_logs_id", table_name="equipment_service_logs")
    op.drop_table("equipment_service_logs")

    op.drop_index("ix_inventory_equipment_next_service_due_date", table_name="inventory_equipment")
    op.drop_index("ix_inventory_equipment_serial_number", table_name="inventory_equipment")
    op.drop_index("ix_inventory_equipment_department", table_name="inventory_equipment")
    op.drop_index("ix_inventory_equipment_branch_id", table_name="inventory_equipment")
    op.drop_index("ix_inventory_equipment_id", table_name="inventory_equipment")
    op.drop_table("inventory_equipment")

    op.drop_index("ix_inventory_items_v2_barcode_number", table_name="inventory_items_v2")
    op.drop_index("ix_inventory_items_v2_supplier_id", table_name="inventory_items_v2")
    op.drop_index("ix_inventory_items_v2_category", table_name="inventory_items_v2")
    op.drop_index("ix_inventory_items_v2_item_name", table_name="inventory_items_v2")
    op.drop_index("ix_inventory_items_v2_department", table_name="inventory_items_v2")
    op.drop_index("ix_inventory_items_v2_branch_id", table_name="inventory_items_v2")
    op.drop_index("ix_inventory_items_v2_id", table_name="inventory_items_v2")
    op.drop_table("inventory_items_v2")

    op.drop_index("ix_inventory_suppliers_name", table_name="inventory_suppliers")
    op.drop_index("ix_inventory_suppliers_branch_id", table_name="inventory_suppliers")
    op.drop_index("ix_inventory_suppliers_id", table_name="inventory_suppliers")
    op.drop_table("inventory_suppliers")
