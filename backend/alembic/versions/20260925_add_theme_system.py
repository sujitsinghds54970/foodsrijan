"""Add governed Super CEO theme system.

The canonical profile_types table is created by the authority foundation
migration, so this migration extends it with the theme tables and seeds the
platform profile catalog without duplicating that table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260925_add_theme_system"
down_revision: Union[str, Sequence[str], None] = "20260925_add_canonical_authority_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PROFILE_TYPES = [
    ("super_ceo", "Super CEO"), ("company_ceo", "Company CEO"), ("branch_manager", "Branch Manager"),
    ("chef", "Chef"), ("kitchen_manager", "Kitchen Manager"), ("inventory_manager", "Inventory Manager"),
    ("cashier", "Cashier"), ("customer_service", "Customer Service"), ("delivery_partner", "Delivery Partner"),
    ("customer", "Customer"), ("supplier", "Supplier"), ("investor", "Investor"),
    ("department_head", "Department Head"), ("brand_director", "Brand Director"),
    ("regional_manager", "Regional Manager"), ("admin", "Admin"),
]


def _tokens(primary="#D6A84F"):
    return {
        "color": {
            "palette": {"gold": "#D6A84F", "violet": "#8C78F5", "teal": "#2DD4BF"},
            "semantic": {"primary": "#8B5E17", "secondary": "#8C78F5", "accent": "#57C7F2", "success": "#56C58A", "warning": "#E8A24A", "danger": "#E87986"},
            "surface": {"default": "#090B14", "panel": "#25293D", "elevated": "#2B2F45"},
            "text": {"primary": "#FFF9EC", "secondary": "#D2CFD8", "tertiary": "#B7B5C1"},
            "border": {"default": "#4B4D5A", "focus": "#F3D58A"},
        },
        "typography": {"family": {"display": "Fraunces", "body": "Manrope"}, "size": {"base": "16px"}, "weight": {"regular": 400, "semibold": 600}, "line_height": {"base": 1.5}, "letter_spacing": {"base": "0px"}},
        "spacing": {"scale": [0, 4, 8, 12, 16, 24, 32], "padding": {"sm": "8px", "md": "16px", "lg": "24px"}, "margin": {"sm": "8px", "md": "16px", "lg": "24px"}, "gap": {"sm": "8px", "md": "16px", "lg": "24px"}},
        "radius": {"none": "0px", "sm": "8px", "md": "12px", "lg": "20px", "xl": "28px", "pill": "999px"},
        "shadow": {"elevation_1": "0 2px 8px rgba(0,0,0,.18)", "elevation_2": "0 8px 20px rgba(0,0,0,.22)", "elevation_3": "0 18px 44px rgba(0,0,0,.28)", "elevation_4": "0 28px 80px rgba(0,0,0,.42)"},
        "gradient": {"families": {}}, "motion": {"duration": {"fast": "120ms", "normal": "220ms"}, "easing": {"standard": "ease"}}, "icon": {"size": 24, "stroke": 1.5},
    }


def _seed_existing_schema(connection) -> None:
    for key, name in PROFILE_TYPES:
        connection.execute(sa.text("INSERT INTO profile_types (code, name, description, is_active, created_at) SELECT :code, :name, :description, 1, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM profile_types WHERE code = :code)"), {"code": key, "name": name, "description": f"System profile type: {name}"})
    profile_rows = []
    for key, _ in PROFILE_TYPES:
        row = connection.execute(sa.text("SELECT id, code FROM profile_types WHERE code = :code"), {"code": key}).first()
        if row:
            profile_rows.append(row)
    for profile_id, key in profile_rows:
        connection.execute(sa.text("INSERT INTO themes (profile_type_id, name, slug, status, is_default, created_at, updated_at) SELECT :profile_id, :name, :slug, 'published', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM themes WHERE profile_type_id = :profile_id AND is_default = 1)"), {"profile_id": profile_id, "name": f"{key.replace('_', ' ').title()} Default", "slug": f"{key}-default"})
    for name, slug in [("Executive Gold", "executive-gold"), ("Modern Minimal", "modern-minimal"), ("Warm Hospitality", "warm-hospitality"), ("Dark Command", "dark-command")]:
        profile_id = profile_rows[0][0]
        connection.execute(sa.text("INSERT INTO themes (profile_type_id, name, slug, status, is_default, created_at, updated_at) SELECT :profile_id, :name, :slug, 'published', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM themes WHERE slug = :slug)"), {"profile_id": profile_id, "name": name, "slug": slug})
    token_json = '{"color": {"semantic": {"primary": "#8B5E17", "secondary": "#8C78F5", "accent": "#57C7F2", "success": "#56C58A", "warning": "#E8A24A", "danger": "#E87986"}, "surface": {"default": "#090B14"}, "text": {"primary": "#FFF9EC", "secondary": "#D2CFD8"}}}'
    for theme_id, in connection.execute(sa.text("SELECT id FROM themes WHERE current_version_id IS NULL")).fetchall():
        version_id = connection.execute(sa.text("INSERT INTO theme_versions (theme_id, version_number, status, tokens, schema_version, contrast_report, change_summary, created_at, published_at) VALUES (:theme_id, 1, 'published', :tokens, '1.0', :report, 'Initial seeded theme', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id"), {"theme_id": theme_id, "tokens": token_json, "report": '{"passed": true, "failures": []}'}).scalar_one()
        connection.execute(sa.text("UPDATE themes SET current_version_id = :version_id WHERE id = :theme_id"), {"version_id": version_id, "theme_id": theme_id})


def upgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("themes") and sa.inspect(connection).has_table("theme_versions") and sa.inspect(connection).has_table("theme_assignments"):
        _seed_existing_schema(connection)
        return
    op.create_table(
        "themes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_type_id", sa.Integer(), sa.ForeignKey("profile_types.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("parent_theme_id", sa.Integer(), sa.ForeignKey("themes.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("current_version_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_themes_profile_type_id", "themes", ["profile_type_id"])
    op.create_index("ix_themes_company_id", "themes", ["company_id"])
    op.create_index("ix_themes_brand_id", "themes", ["brand_id"])
    op.create_index("ix_themes_status", "themes", ["status"])
    op.create_index("uq_themes_published_scope", "themes", ["profile_type_id", "company_id", "brand_id", "status"], unique=True, sqlite_where=sa.text("status = 'published'"), postgresql_where=sa.text("status = 'published'"))

    op.create_table(
        "theme_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("theme_id", sa.Integer(), sa.ForeignKey("themes.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("tokens", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("contrast_report", sa.JSON(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("published_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("rolled_back_from_version_id", sa.Integer(), sa.ForeignKey("theme_versions.id"), nullable=True),
    )
    op.create_index("ix_theme_versions_theme_id", "theme_versions", ["theme_id"])
    op.create_index("uq_theme_versions_published", "theme_versions", ["theme_id", "status"], unique=True, sqlite_where=sa.text("status = 'published'"), postgresql_where=sa.text("status = 'published'"))
    with op.batch_alter_table("themes") as batch:
        batch.create_foreign_key("fk_themes_current_version", "theme_versions", ["current_version_id"], ["id"])

    op.create_table(
        "theme_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("theme_id", sa.Integer(), sa.ForeignKey("themes.id"), nullable=False),
        sa.Column("profile_type_id", sa.Integer(), sa.ForeignKey("profile_types.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("user_id IS NOT NULL OR role_id IS NOT NULL OR company_id IS NOT NULL OR brand_id IS NOT NULL OR branch_id IS NOT NULL OR department_id IS NOT NULL", name="ck_theme_assignment_target"),
    )
    op.create_index("ix_theme_assignments_profile_type_id", "theme_assignments", ["profile_type_id"])
    op.create_index("ix_theme_assignments_user_id", "theme_assignments", ["user_id"])
    op.create_index("ix_theme_assignments_company_id", "theme_assignments", ["company_id"])

    connection = op.get_bind()
    for key, name in PROFILE_TYPES:
        connection.execute(sa.text("INSERT INTO profile_types (code, name, description, is_active, created_at) SELECT :code, :name, :description, 1, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM profile_types WHERE code = :code)"), {"code": key, "name": name, "description": f"System profile type: {name}"})
    profile_rows = []
    for key, _ in PROFILE_TYPES:
        row = connection.execute(sa.text("SELECT id, code FROM profile_types WHERE code = :code"), {"code": key}).first()
        if row:
            profile_rows.append(row)
    for profile_id, key in profile_rows:
        connection.execute(sa.text("INSERT INTO themes (profile_type_id, name, slug, status, is_default, created_at, updated_at) SELECT :profile_id, :name, :slug, 'published', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM themes WHERE profile_type_id = :profile_id AND is_default = 1)"), {"profile_id": profile_id, "name": f"{key.replace('_', ' ').title()} Default", "slug": f"{key}-default"})
    for name, slug, primary in [("Executive Gold", "executive-gold", "#D6A84F"), ("Modern Minimal", "modern-minimal", "#4F46E5"), ("Warm Hospitality", "warm-hospitality", "#EA580C"), ("Dark Command", "dark-command", "#8C78F5")]:
        profile_id = profile_rows[0][0]
        connection.execute(sa.text("INSERT INTO themes (profile_type_id, name, slug, status, is_default, created_at, updated_at) VALUES (:profile_id, :name, :slug, 'published', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"profile_id": profile_id, "name": name, "slug": slug})
    themes = connection.execute(sa.text("SELECT id, profile_type_id FROM themes")).fetchall()
    for theme_id, _ in themes:
        version_id = connection.execute(sa.text("INSERT INTO theme_versions (theme_id, version_number, status, tokens, schema_version, contrast_report, change_summary, created_at, published_at) VALUES (:theme_id, 1, 'published', :tokens, '1.0', :report, 'Initial seeded theme', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id"), {"theme_id": theme_id, "tokens": '{"color": {"semantic": {"primary": "#8B5E17", "secondary": "#8C78F5", "accent": "#57C7F2", "success": "#56C58A", "warning": "#E8A24A", "danger": "#E87986"}, "surface": {"default": "#090B14"}, "text": {"primary": "#FFF9EC", "secondary": "#D2CFD8"}}}', "report": '{"passed": true, "failures": []}'}).scalar_one()
        connection.execute(sa.text("UPDATE themes SET current_version_id = :version_id WHERE id = :theme_id"), {"version_id": version_id, "theme_id": theme_id})


def downgrade() -> None:
    op.drop_table("theme_assignments")
    with op.batch_alter_table("themes") as batch:
        batch.drop_constraint("fk_themes_current_version", type_="foreignkey")
    op.drop_table("theme_versions")
    op.drop_table("themes")
