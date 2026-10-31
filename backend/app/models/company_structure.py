from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, DECIMAL, ForeignKey, Index, Integer, JSON, String, Table, Text, inspect, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


user_companies = Table(
    "user_companies",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("company_id", Integer, ForeignKey("companies.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), nullable=True, index=True),
    Column("is_active", Boolean, default=True, nullable=False),
    Column("created_at", DateTime, default=func.now(), nullable=False),
)


class UserCompany(Base):
    __table__ = user_companies


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        Index("uq_companies_legal_name", "legal_name", unique=True),
        Index("uq_companies_registration_number", "registration_number", unique=True),
        Index("uq_companies_gstin", "gstin", unique=True),
        Index("uq_companies_pan_number", "pan_number", unique=True),
        Index("ix_companies_status", "status"),
        Index("ix_companies_is_deleted", "is_deleted"),
        Index("ix_companies_is_parent", "is_parent"),
        Index("ix_companies_business_domain", "business_domain"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    slug = Column(String(120), nullable=False, unique=True)
    tagline = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(2048), nullable=True)
    banner_url = Column(String(2048), nullable=True)
    favicon_url = Column(String(2048), nullable=True)
    primary_color = Column(String(7), nullable=True)
    secondary_color = Column(String(7), nullable=True)
    accent_color = Column(String(7), nullable=True)
    display_font = Column(String(100), nullable=True)
    body_font = Column(String(100), nullable=True)
    founded_date = Column(Date, nullable=True)
    legal_name = Column(String(255), nullable=True)
    registration_number = Column(String(100), nullable=True)
    gstin = Column(String(15), nullable=True)
    pan_number = Column(String(10), nullable=True)
    fssai_license = Column(String(14), nullable=True)
    cin_number = Column(String(21), nullable=True)
    registered_address = Column(Text, nullable=True)
    corporate_address = Column(Text, nullable=True)
    bank_account_name = Column(String(255), nullable=True)
    bank_account_number = Column(String(100), nullable=True)
    ifsc_code = Column(String(11), nullable=True)
    bank_name = Column(String(255), nullable=True)
    annual_revenue_range = Column(String(20), nullable=True)
    funding_stage = Column(String(40), nullable=True)
    headquarters_city = Column(String(120), nullable=True)
    headquarters_state = Column(String(120), nullable=True)
    headquarters_country = Column(String(120), nullable=True)
    headquarters_pincode = Column(String(20), nullable=True)
    operating_regions = Column(JSON, nullable=True)
    number_of_branches = Column(Integer, nullable=True)
    website_url = Column(String(2048), nullable=True)
    linkedin_url = Column(String(2048), nullable=True)
    instagram_url = Column(String(2048), nullable=True)
    facebook_url = Column(String(2048), nullable=True)
    twitter_url = Column(String(2048), nullable=True)
    youtube_url = Column(String(2048), nullable=True)
    mobile_app_url = Column(String(2048), nullable=True)
    ios_app_url = Column(String(2048), nullable=True)
    android_app_url = Column(String(2048), nullable=True)
    support_email = Column(String(254), nullable=True)
    support_phone = Column(String(32), nullable=True)
    whatsapp_business_number = Column(String(32), nullable=True)
    business_domain = Column(String(64), nullable=True)
    sub_domains = Column(JSON, nullable=True)
    target_market = Column(String(16), nullable=True)
    employee_count_estimate = Column(String(32), nullable=True)
    business_description = Column(Text, nullable=True)
    last_funding_round_date = Column(Date, nullable=True)
    total_funding_raised = Column(DECIMAL(18, 2), nullable=True)
    is_parent = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    profile_draft = Column(JSON, nullable=True)
    published_at = Column(DateTime, nullable=True)
    published_by = Column(Integer, ForeignKey("users.id", name="fk_companies_published_by_users"), nullable=True)
    status = Column(String(20), nullable=False, default="active", server_default="active")
    onboarding_status = Column(String(20), nullable=False, default="pending", server_default="pending")
    created_by = Column(Integer, ForeignKey("users.id", name="fk_companies_created_by_users"), nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    company_metadata = Column("metadata", JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    brands = relationship("Brand", back_populates="company", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="company", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="company", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="company", cascade="all, delete-orphan")
    suppliers = relationship("BusinessSupplier", back_populates="company", cascade="all, delete-orphan")
    current_users = relationship("User", foreign_keys="User.current_company_id", back_populates="current_company")
    users = relationship("User", secondary=user_companies, back_populates="companies")


class RateLimitEntry(Base):
    __tablename__ = "rate_limit_entries"
    __table_args__ = (
        Index("ix_rate_limit_actor_action_time", "actor_id", "action", "occurred_at"),
    )

    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    occurred_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    was_allowed = Column(Boolean, nullable=False)


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    company = relationship("Company", back_populates="brands")
    branches = relationship("Branch", back_populates="brand", cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    company = relationship("Company", back_populates="departments")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    code = Column(String(150), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_role = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    company = relationship("Company", back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    user_assignments = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", back_populates="user_assignments")
    company = relationship("Company")
    brand = relationship("Brand")
    branch = relationship("Branch")


class BusinessSupplier(Base):
    __tablename__ = "business_suppliers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(150), nullable=True)
    address = Column(Text, nullable=True)
    gstin = Column(String(80), nullable=True)
    payment_terms = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    company = relationship("Company", back_populates="suppliers")


def ensure_sqlite_schema_compatibility(db):
    """Add newer columns to existing SQLite tables without forcing a destructive reset."""
    try:
        inspector = inspect(db.bind)
        tables = set(inspector.get_table_names())

        if "users" in tables:
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            for column_name in ("current_company_id", "company_id", "brand_id", "is_super_admin", "is_super_ceo"):
                if column_name not in user_columns:
                    column_type = "BOOLEAN NOT NULL DEFAULT 0" if column_name in {"is_super_admin", "is_super_ceo"} else "INTEGER"
                    db.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
            for column_name, column_type in {
                "is_company_ceo": "BOOLEAN NOT NULL DEFAULT 0",
                "password_changed_at": "DATETIME",
                "force_password_change": "BOOLEAN NOT NULL DEFAULT 0",
                "is_outlet_manager": "BOOLEAN NOT NULL DEFAULT 0",
                "outlet_id": "INTEGER",
                "manager_assigned_at": "DATETIME",
                "manager_assigned_by": "INTEGER",
                "manager_photo_url": "VARCHAR(2048)",
                "manager_address": "TEXT",
                "manager_bank_account_name": "VARCHAR(255)",
                "manager_bank_account_number": "VARCHAR(34)",
                "manager_ifsc_code": "VARCHAR(11)",
                "manager_bank_name": "VARCHAR(255)",
                "is_staff": "BOOLEAN NOT NULL DEFAULT 0",
                "staff_role": "VARCHAR(40)",
                "employee_code": "VARCHAR(40)",
                "manager_id": "INTEGER",
                "staff_assigned_at": "DATETIME",
                "staff_assigned_by": "INTEGER",
                "alternate_phone": "VARCHAR(32)",
                "blood_group": "VARCHAR(10)",
                "marital_status": "VARCHAR(32)",
                "current_address": "TEXT",
                "permanent_address": "TEXT",
                "emergency_contact_relation": "VARCHAR(100)",
                "aadhaar_number": "VARCHAR(32)",
                "pan_number": "VARCHAR(16)",
                "voter_id": "VARCHAR(32)",
                "driving_license": "VARCHAR(32)",
                "passport_number": "VARCHAR(32)",
                "bank_account_name": "VARCHAR(255)",
                "bank_account_number": "VARCHAR(34)",
                "ifsc_code": "VARCHAR(11)",
                "bank_name": "VARCHAR(255)",
                "branch_name": "VARCHAR(255)",
                "upi_id": "VARCHAR(100)",
                "experience_years": "FLOAT",
                "previous_employer": "VARCHAR(255)",
                "skills": "JSON",
                "joining_date": "DATE",
                "employment_type": "VARCHAR(20)",
                "probation_end_date": "DATE",
                "salary_type": "VARCHAR(20)",
                "monthly_salary": "DECIMAL(12, 2)",
                "daily_wage": "DECIMAL(12, 2)",
                "hourly_rate": "DECIMAL(12, 2)",
                "shift_preference": "VARCHAR(100)",
                "weekly_off_day": "VARCHAR(20)",
                "pf_applicable": "BOOLEAN NOT NULL DEFAULT 0",
                "esi_applicable": "BOOLEAN NOT NULL DEFAULT 0",
                "tds_applicable": "BOOLEAN NOT NULL DEFAULT 0",
                "deactivated_at": "DATETIME",
                "deactivated_reason": "TEXT",
                "created_by": "INTEGER",
                "updated_at": "DATETIME",
                "deleted_at": "DATETIME",
                "is_deleted": "BOOLEAN NOT NULL DEFAULT 0",
            }.items():
                if column_name not in user_columns:
                    db.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))

        if "roles" in tables:
            role_columns = {column["name"] for column in inspector.get_columns("roles")}
            role_column_meta = {column["name"]: column for column in inspector.get_columns("roles")}
            if "is_system_role" not in role_columns:
                db.execute(text("ALTER TABLE roles ADD COLUMN is_system_role BOOLEAN DEFAULT 0"))
            if "company_id" in role_column_meta and role_column_meta["company_id"]["nullable"] is False:
                db.execute(text("ALTER TABLE roles RENAME TO roles_legacy"))
                db.execute(
                    text(
                        """
                        CREATE TABLE roles (
                            id INTEGER NOT NULL,
                            company_id INTEGER,
                            name VARCHAR(100) NOT NULL,
                            slug VARCHAR(100) NOT NULL,
                            description TEXT,
                            is_active BOOLEAN NOT NULL DEFAULT 1,
                            is_system_role BOOLEAN NOT NULL DEFAULT 0,
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (id)
                        )
                        """
                    )
                )
                db.execute(
                    text(
                        """
                        INSERT INTO roles (id, company_id, name, slug, description, is_active, is_system_role, created_at)
                        SELECT id, company_id, name, slug, description, is_active,
                               COALESCE(is_system_role, 0), created_at
                        FROM roles_legacy
                        """
                    )
                )
                db.execute(text("DROP TABLE roles_legacy"))

        if "user_companies" in tables:
            user_company_columns = {column["name"] for column in inspector.get_columns("user_companies")}
            for column_name, column_type in {
                "role_id": "INTEGER",
                "is_active": "BOOLEAN",
            }.items():
                if column_name not in user_company_columns:
                    db.execute(text(f"ALTER TABLE user_companies ADD COLUMN {column_name} {column_type}"))

        if "branches" in tables:
            branch_columns = {column["name"] for column in inspector.get_columns("branches")}
            for column_name in ("company_id", "brand_id"):
                if column_name not in branch_columns:
                    db.execute(text(f"ALTER TABLE branches ADD COLUMN {column_name} INTEGER"))

        for table_name, columns in {
            "customers": ("company_id", "brand_id"),
            "staff_employees": ("company_id", "brand_id"),
            "inventory_items": ("company_id", "brand_id"),
        }.items():
            if table_name in tables:
                existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
                for column_name in columns:
                    if column_name not in existing_columns:
                        db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER"))

        if "users" in tables:
            db.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_users_active_super_ceo
                    ON users (is_super_ceo)
                    WHERE is_super_ceo = 1 AND is_active = 1
                    """
                )
            )
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_users_outlet_id ON users (outlet_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_users_company_outlet_manager ON users (company_id, is_outlet_manager)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_users_company_outlet_staff ON users (company_id, outlet_id, is_staff)"))
            db.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_users_staff_phone_active
                    ON users (phone)
                    WHERE is_staff = 1 AND is_deleted = 0
                    """
                )
            )
            db.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_users_staff_outlet_employee_code
                    ON users (outlet_id, employee_code)
                    WHERE is_staff = 1 AND is_deleted = 0 AND employee_code IS NOT NULL
                    """
                )
            )
            db.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_users_staff_aadhaar_active
                    ON users (aadhaar_number)
                    WHERE is_staff = 1 AND is_deleted = 0 AND aadhaar_number IS NOT NULL
                    """
                )
            )

        if "staff_requests" not in tables:
            db.execute(
                text(
                    """
                    CREATE TABLE staff_requests (
                        id INTEGER PRIMARY KEY,
                        staff_id INTEGER NOT NULL,
                        company_id INTEGER NOT NULL,
                        outlet_id INTEGER NOT NULL,
                        type VARCHAR(40) NOT NULL,
                        reason TEXT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_staff_requests_staff_id ON staff_requests (staff_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_staff_requests_company_outlet_status ON staff_requests (company_id, outlet_id, status)"))

        db.commit()
    except Exception:
        db.rollback()
        raise


def ensure_food_erp_seed_data(db):
    """Create the default FoodSrijan structure if the database is empty."""
    ensure_sqlite_schema_compatibility(db)
    from app.models import Company, Brand, Role, Permission, User, UserRole

    company = db.query(Company).filter(Company.slug == "foodsrijan-group").first()
    if company is None:
        company = Company(
            name="FoodSrijan Group",
            slug="foodsrijan-group",
            description="Parent food business operating company",
            is_active=True,
        )
        db.add(company)
        db.commit()
        db.refresh(company)

    brand_names = ["Rasoi Republic", "FoodSrijan Express"]
    for brand_name in brand_names:
        slug = brand_name.lower().replace(" & ", "-").replace(" ", "-")
        brand = db.query(Brand).filter(Brand.company_id == company.id, Brand.slug == slug).first()
        if brand is None:
            db.add(Brand(company_id=company.id, name=brand_name, slug=slug, is_active=True))
    db.commit()

    system_permissions = {
        "create_company": "Create a new company",
        "edit_company": "Edit company details",
        "delete_company": "Delete or archive a company",
        "view_all_companies": "View all companies in the system",
        "assign_company_admin": "Assign company admins",
        "view_system_dashboard": "View the system dashboard",
        "manage_system_settings": "Manage system-level settings",
        "view_audit_logs": "View audit logs",
    }
    company_permissions = {
        "manage_brands": "Manage brands",
        "manage_branches": "Manage branches",
        "manage_company_users": "Manage company users",
        "view_company_settings": "View company settings",
        "manage_company_settings": "Manage company settings",
        "view_customers": "View customers",
        "manage_inventory": "Manage inventory",
        "manage_orders": "Manage orders",
        "manage_staff": "Manage staff",
    }
    default_permissions = {**system_permissions, **company_permissions}

    for code, description in default_permissions.items():
        permission = db.query(Permission).filter(Permission.code == code).first()
        if permission is None:
            db.add(Permission(name=description, code=code, description=description, category="core"))
    db.commit()

    default_roles = {
        "super_ceo": {"label": "Super CEO", "company_id": None, "is_system_role": True},
        "super_admin": {"label": "Super CEO", "company_id": None, "is_system_role": True},
        "company_admin": {"label": "Company Admin", "company_id": company.id, "is_system_role": False},
        "ceo": {"label": "CEO", "company_id": company.id, "is_system_role": False},
        "branch_manager": {"label": "Branch Manager", "company_id": company.id, "is_system_role": False},
        "kitchen_manager": {"label": "Kitchen Manager", "company_id": company.id, "is_system_role": False},
        "inventory_manager": {"label": "Inventory Manager", "company_id": company.id, "is_system_role": False},
        "sales_cashier": {"label": "Sales / Cashier", "company_id": company.id, "is_system_role": False},
        "customer_service": {"label": "Customer Service", "company_id": company.id, "is_system_role": False},
    }

    for slug, config in default_roles.items():
        if config["company_id"] is None:
            role = db.query(Role).filter(Role.slug == slug, Role.company_id.is_(None)).first()
        else:
            role = db.query(Role).filter(Role.slug == slug, Role.company_id == config["company_id"]).first()
        if role is None:
            db.add(
                Role(
                    company_id=config["company_id"],
                    name=config["label"],
                    slug=slug,
                    description=config["label"],
                    is_active=True,
                    is_system_role=config["is_system_role"],
                )
            )
    db.commit()

    super_ceo_role = db.query(Role).filter(Role.slug == "super_ceo", Role.company_id.is_(None)).first()
    if super_ceo_role is None:
        super_ceo_role = db.query(Role).filter(Role.slug == "super_admin", Role.company_id.is_(None)).first()
        if super_ceo_role:
            super_ceo_role.slug = "super_ceo"
            super_ceo_role.name = "Super CEO"
            super_ceo_role.description = "Super CEO"
    super_admin_role = db.query(Role).filter(Role.slug == "super_admin", Role.company_id.is_(None)).first()
    if super_admin_role is None and super_ceo_role is not None:
        db.add(
            Role(
                company_id=None,
                name="Super CEO",
                slug="super_admin",
                description="Legacy alias for Super CEO",
                is_active=True,
                is_system_role=True,
            )
        )
        db.commit()

    super_admin_role = db.query(Role).filter(Role.slug == "super_admin", Role.company_id.is_(None)).first()
    canonical_role = super_ceo_role or super_admin_role
    if canonical_role:
        all_permissions = db.query(Permission).all()
        for permission in all_permissions:
            if permission not in canonical_role.permissions:
                canonical_role.permissions.append(permission)
        db.commit()

    if super_admin_role and super_ceo_role and super_admin_role.id != super_ceo_role.id:
        for permission in list(super_ceo_role.permissions):
            if permission not in super_admin_role.permissions:
                super_admin_role.permissions.append(permission)
        db.commit()

    company_admin_role = db.query(Role).filter(Role.slug == "company_admin", Role.company_id == company.id).first()
    if company_admin_role:
        company_permissions_objs = db.query(Permission).filter(Permission.code.in_(list(company_permissions.keys()))).all()
        for permission in company_permissions_objs:
            if permission not in company_admin_role.permissions:
                company_admin_role.permissions.append(permission)
        db.commit()

    admin_user = db.query(User).filter(User.username == "sujitep").first()
    if admin_user:
        existing_assignment = db.query(UserRole).filter(UserRole.user_id == admin_user.id, UserRole.company_id == company.id).first()
        if existing_assignment is None:
            db.add(UserRole(user_id=admin_user.id, role_id=super_admin_role.id, company_id=company.id, is_active=True))
        db.commit()

    return company
