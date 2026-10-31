from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260928_outlet_management.py"
)


def _load_migration():
    spec = spec_from_file_location("outlet_management_migration_test", MIGRATION_PATH)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _create_legacy_schema(connection):
    connection.execute(
        text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_company_ceo BOOLEAN NOT NULL DEFAULT 0,
                company_id INTEGER
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE branches (
                id INTEGER PRIMARY KEY,
                company_id INTEGER,
                name VARCHAR(100) NOT NULL,
                location VARCHAR(200) NOT NULL,
                branch_code VARCHAR(20) NOT NULL UNIQUE
            )
            """
        )
    )
    connection.execute(
        text("INSERT INTO users (id, username, company_id) VALUES (1, 'ceo_one', 1)")
    )
    connection.execute(
        text(
            "INSERT INTO branches (id, company_id, name, location, branch_code) "
            "VALUES (1, 1, 'Main Outlet', 'Downtown', 'O1-MAIN')"
        )
    )


def test_outlet_management_upgrade_preserves_data_and_adds_schema():
    migration = _load_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        _create_legacy_schema(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        branch_columns = {column["name"] for column in inspect(connection).get_columns("branches")}
        user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        branch_indexes = {index["name"] for index in inspect(connection).get_indexes("branches")}
        user_indexes = {index["name"] for index in inspect(connection).get_indexes("users")}
        table_names = set(inspect(connection).get_table_names())

        assert {
            "slug", "code", "outlet_type", "status", "gstin", "fssai_license",
            "bank_account_number", "ifsc_code", "upi_id", "is_deleted", "deleted_at",
            "metadata",
        } <= branch_columns
        assert {
            "is_outlet_manager", "outlet_id", "manager_assigned_at", "manager_assigned_by",
            "manager_bank_account_number", "manager_ifsc_code",
        } <= user_columns
        assert {
            "uq_branches_company_code", "uq_branches_company_slug", "uq_branches_gstin",
            "ix_branches_company_status", "ix_branches_is_deleted",
        } <= branch_indexes
        assert {
            "ix_users_outlet_id", "ix_users_company_outlet_manager", "uq_users_active_outlet_manager",
        } <= user_indexes
        assert "login_attempts" in table_names

        assert connection.execute(text("SELECT username FROM users WHERE id = 1")).scalar_one() == "ceo_one"
        branch = connection.execute(text("SELECT name, branch_code FROM branches WHERE id = 1")).one()
        assert branch == ("Main Outlet", "O1-MAIN")


def test_outlet_management_upgrade_is_idempotent():
    migration = _load_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        _create_legacy_schema(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            # Running upgrade a second time must not raise (idempotent guard).
            migration.upgrade()


def test_outlet_management_downgrade_removes_only_new_schema():
    migration = _load_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        _create_legacy_schema(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.downgrade()

        branch_columns = {column["name"] for column in inspect(connection).get_columns("branches")}
        user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        table_names = set(inspect(connection).get_table_names())

        assert branch_columns == {"id", "company_id", "name", "location", "branch_code"}
        assert user_columns == {"id", "username", "is_active", "is_company_ceo", "company_id"}
        assert "login_attempts" not in table_names
        assert connection.execute(text("SELECT username FROM users WHERE id = 1")).scalar_one() == "ceo_one"
