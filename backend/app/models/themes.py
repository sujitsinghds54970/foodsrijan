from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Theme(Base):
    __tablename__ = "themes"
    __table_args__ = (
        Index("uq_themes_published_scope", "profile_type_id", "company_id", "brand_id", "status", unique=True,
              sqlite_where=text("status = 'published'"), postgresql_where=text("status = 'published'")),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_type_id = Column(Integer, ForeignKey("profile_types.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(180), nullable=False, index=True)
    parent_theme_id = Column(Integer, ForeignKey("themes.id"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    is_default = Column(Boolean, nullable=False, default=False)
    current_version_id = Column(Integer, ForeignKey("theme_versions.id", use_alter=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    profile_type = relationship("ProfileType")
    parent_theme = relationship("Theme", remote_side=[id])
    versions = relationship("ThemeVersion", back_populates="theme", foreign_keys="ThemeVersion.theme_id", cascade="all, delete-orphan")


class ThemeVersion(Base):
    __tablename__ = "theme_versions"
    __table_args__ = (
        Index("uq_theme_versions_published", "theme_id", "status", unique=True,
              sqlite_where=text("status = 'published'"), postgresql_where=text("status = 'published'")),
    )

    id = Column(Integer, primary_key=True, index=True)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="draft", index=True)
    tokens = Column(JSON, nullable=False, default=dict)
    schema_version = Column(String(20), nullable=False, default="1.0")
    contrast_report = Column(JSON, nullable=False, default=dict)
    change_summary = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    published_at = Column(DateTime, nullable=True)
    rolled_back_from_version_id = Column(Integer, ForeignKey("theme_versions.id"), nullable=True)

    theme = relationship("Theme", back_populates="versions", foreign_keys=[theme_id])
    rolled_back_from = relationship("ThemeVersion", remote_side=[id])


class ThemeAssignment(Base):
    __tablename__ = "theme_assignments"
    __table_args__ = (
        CheckConstraint(
            "user_id IS NOT NULL OR role_id IS NOT NULL OR company_id IS NOT NULL OR "
            "brand_id IS NOT NULL OR branch_id IS NOT NULL OR department_id IS NOT NULL",
            name="ck_theme_assignment_target",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False, index=True)
    profile_type_id = Column(Integer, ForeignKey("profile_types.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    theme = relationship("Theme")
    profile_type = relationship("ProfileType")
