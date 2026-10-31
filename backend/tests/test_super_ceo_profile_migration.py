from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260927_super_ceo_profile.py"
)


def _load_migration():
    spec = spec_from_file_location("super_ceo_profile_migration_test", MIGRATION_PATH)
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
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                slug VARCHAR(120) NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            "INSERT INTO users (id, username, first_name, last_name) "
            "VALUES (1, 'sujitep', 'Sujit', 'Singh')"
        )
    )
    connection.execute(
        text(
            "INSERT INTO companies (id, name, slug) "
            "VALUES (1, 'FoodSrijan Group', 'foodsrijan-group')"
        )
    )


def test_profile_foundation_upgrade_preserves_data_and_adds_schema():
    migration = _load_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        _create_legacy_schema(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        company_columns = {column["name"] for column in inspect(connection).get_columns("companies")}
        company_indexes = {index["name"] for index in inspect(connection).get_indexes("companies")}

        assert {
            "display_name",
            "bio",
            "profile_photo_url",
            "cover_photo_url",
            "qualifications",
            "certifications",
            "achievements",
            "preferences",
            "recovery_email",
            "recovery_phone",
        } <= user_columns
        assert {
            "banner_url",
            "accent_color",
            "display_font",
            "body_font",
            "is_parent",
            "profile_draft",
            "published_at",
            "published_by",
        } <= company_columns
        assert "ix_companies_is_parent" in company_indexes
        assert connection.execute(text("SELECT username FROM users WHERE id = 1")).scalar_one() == "sujitep"
        company = connection.execute(
            text("SELECT name, is_parent FROM companies WHERE id = 1")
        ).one()
        assert company == ("FoodSrijan Group", 0)


def test_profile_foundation_downgrade_removes_only_new_schema():
    migration = _load_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        _create_legacy_schema(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.downgrade()

        user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        company_columns = {column["name"] for column in inspect(connection).get_columns("companies")}

        assert user_columns == {"id", "username", "first_name", "last_name"}
        assert company_columns == {"id", "name", "slug"}
        assert connection.execute(text("SELECT username FROM users WHERE id = 1")).scalar_one() == "sujitep"
        assert connection.execute(text("SELECT name FROM companies WHERE id = 1")).scalar_one() == "FoodSrijan Group"
