import copy

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.authority import ProfileType
from app.models.themes import Theme, ThemeVersion
from app.services.contrast import check_contrast, ratio
from app.services.theme_tokens import default_tokens, merge_tokens, validate_tokens


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE profile_types (id INTEGER PRIMARY KEY, code VARCHAR(100) UNIQUE NOT NULL, name VARCHAR(150) NOT NULL, description TEXT, is_active BOOLEAN NOT NULL DEFAULT 1, created_at DATETIME)")
        connection.exec_driver_sql("CREATE TABLE themes (id INTEGER PRIMARY KEY, profile_type_id INTEGER NOT NULL, company_id INTEGER, brand_id INTEGER, name VARCHAR(150) NOT NULL, slug VARCHAR(180) NOT NULL, parent_theme_id INTEGER, status VARCHAR(20) NOT NULL, is_default BOOLEAN NOT NULL, current_version_id INTEGER, created_by INTEGER, updated_by INTEGER, created_at DATETIME, updated_at DATETIME)")
        connection.exec_driver_sql("CREATE TABLE theme_versions (id INTEGER PRIMARY KEY, theme_id INTEGER NOT NULL, version_number INTEGER NOT NULL, status VARCHAR(20) NOT NULL, tokens JSON NOT NULL, schema_version VARCHAR(20) NOT NULL, contrast_report JSON NOT NULL, change_summary TEXT, created_by INTEGER, published_by INTEGER, created_at DATETIME, published_at DATETIME, rolled_back_from_version_id INTEGER)")
    with Session(engine) as session:
        yield session


def test_default_tokens_have_all_categories():
    assert set(default_tokens()) == {"color", "typography", "spacing", "radius", "shadow", "gradient", "motion", "icon"}


def test_default_tokens_have_required_semantics():
    assert set(("primary", "secondary", "accent", "success", "warning", "danger")).issubset(default_tokens()["color"]["semantic"])


def test_valid_tokens_pass_schema_validation():
    assert validate_tokens(default_tokens())["valid"] is True


def test_missing_category_fails_schema_validation():
    tokens = default_tokens()
    del tokens["motion"]
    result = validate_tokens(tokens)
    assert result["valid"] is False
    assert "Missing category: motion" in result["errors"]


def test_missing_semantic_token_fails_schema_validation():
    tokens = default_tokens()
    del tokens["color"]["semantic"]["danger"]
    assert validate_tokens(tokens)["valid"] is False


def test_css_injection_is_rejected():
    tokens = default_tokens()
    tokens["color"]["semantic"]["primary"] = "red; background:url(x)"
    assert validate_tokens(tokens)["valid"] is False


def test_unapproved_font_is_rejected():
    tokens = default_tokens()
    tokens["typography"]["family"]["body"] = "Comic Sans"
    assert validate_tokens(tokens)["valid"] is False


def test_contrast_ratio_is_calculated():
    assert ratio("#FFFFFF", "#000000") == 21.0


def test_contrast_checker_accepts_default_tokens():
    assert check_contrast(default_tokens())["passed"] is True


def test_contrast_checker_reports_failed_pair():
    tokens = default_tokens()
    tokens["color"]["text"]["primary"] = "#111111"
    result = check_contrast(tokens)
    assert result["passed"] is False
    assert result["failures"]


def test_merge_tokens_preserves_parent_values():
    merged = merge_tokens({"color": {"surface": {"default": "#000"}}}, {"color": {"surface": {"panel": "#fff"}}})
    assert merged["color"]["surface"] == {"default": "#000", "panel": "#fff"}


def test_merge_tokens_child_overrides_leaf():
    assert merge_tokens({"color": {"semantic": {"primary": "#000"}}}, {"color": {"semantic": {"primary": "#fff"}}})["color"]["semantic"]["primary"] == "#fff"


def test_profile_type_can_be_created_in_real_sqlite(db):
    profile = ProfileType(code="chef", name="Chef", is_active=True)
    db.add(profile)
    db.commit()
    assert db.query(ProfileType).filter_by(code="chef").one().name == "Chef"


def test_theme_version_snapshot_is_immutable_in_application_flow(db):
    profile = ProfileType(code="customer", name="Customer", is_active=True)
    db.add(profile)
    db.flush()
    tokens = default_tokens()
    theme = Theme(profile_type_id=profile.id, name="Customer Default", slug="customer-default", status="draft", is_default=True)
    db.add(theme)
    db.flush()
    version = ThemeVersion(theme_id=theme.id, version_number=1, status="draft", tokens=copy.deepcopy(tokens), schema_version="1.0", contrast_report=check_contrast(tokens))
    db.add(version)
    db.commit()
    tokens["color"]["semantic"]["primary"] = "#000000"
    assert db.get(ThemeVersion, version.id).tokens["color"]["semantic"]["primary"] == "#8B5E17"


def test_published_version_can_be_pointed_to_by_theme(db):
    profile = ProfileType(code="supplier", name="Supplier", is_active=True)
    db.add(profile)
    db.flush()
    theme = Theme(profile_type_id=profile.id, name="Supplier Default", slug="supplier-default", status="published", is_default=True)
    db.add(theme)
    db.flush()
    version = ThemeVersion(theme_id=theme.id, version_number=1, status="published", tokens=default_tokens(), schema_version="1.0", contrast_report=check_contrast(default_tokens()))
    db.add(version)
    db.flush()
    theme.current_version_id = version.id
    db.commit()
    assert db.get(Theme, theme.id).current_version_id == version.id


def test_version_numbers_are_monotonic(db):
    profile = ProfileType(code="investor", name="Investor", is_active=True)
    db.add(profile)
    db.flush()
    theme = Theme(profile_type_id=profile.id, name="Investor", slug="investor", status="draft")
    db.add(theme)
    db.flush()
    for number in (1, 2, 3):
        db.add(ThemeVersion(theme_id=theme.id, version_number=number, status="draft", tokens=default_tokens(), schema_version="1.0", contrast_report={}))
    db.commit()
    assert [row.version_number for row in db.query(ThemeVersion).filter_by(theme_id=theme.id).order_by(ThemeVersion.version_number)] == [1, 2, 3]
