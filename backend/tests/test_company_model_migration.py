from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260926_extend_company_model.py"


def test_company_extension_migration_preserves_data_and_adds_required_schema():
    spec = spec_from_file_location("company_model_migration_test", MIGRATION_PATH)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, company_id INTEGER, is_active BOOLEAN)"))
        connection.execute(
            text(
                """
                CREATE TABLE companies (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    slug VARCHAR(120) NOT NULL,
                    description TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO companies (id, name, slug, description) "
                "VALUES (1, 'Legacy Co', 'legacy-co', 'preserve me')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO companies (id, name, slug, is_active) "
                "VALUES (4, 'Inactive Legacy Co', 'inactive-legacy-co', 0)"
            )
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        company_columns = {column["name"] for column in inspect(connection).get_columns("companies")}
        user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        company_indexes = {index["name"] for index in inspect(connection).get_indexes("companies")}
        row = connection.execute(
            text(
                "SELECT name, slug, description, status, onboarding_status, is_deleted "
                "FROM companies WHERE id = 1"
            )
        ).one()

        assert row == ("Legacy Co", "legacy-co", "preserve me", "active", "pending", 0)
        inactive_status = connection.execute(
            text("SELECT status FROM companies WHERE id = 4")
        ).scalar_one()
        assert inactive_status == "inactive"
        assert {"tagline", "gstin", "operating_regions", "metadata", "created_by"} <= company_columns
        assert {
            "is_company_ceo",
            "ceo_assigned_at",
            "ceo_assigned_by",
            "password_changed_at",
            "force_password_change",
        } <= user_columns
        assert {
            "uq_companies_legal_name",
            "uq_companies_registration_number",
            "uq_companies_gstin",
            "uq_companies_pan_number",
        } <= company_indexes

        connection.execute(
            text(
                "INSERT INTO companies (id, name, slug, gstin) "
                "VALUES (2, 'Second Co', 'second-co', '22AAAAA0000A1Z5')"
            )
        )
        with pytest.raises(IntegrityError, match="companies.gstin"):
            connection.execute(
                text(
                    "INSERT INTO companies (id, name, slug, gstin) "
                    "VALUES (3, 'Third Co', 'third-co', '22AAAAA0000A1Z5')"
                )
            )
