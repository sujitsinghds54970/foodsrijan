from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ProfileType(Base):
    __tablename__ = "profile_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    memberships = relationship("ProfileMembership", back_populates="profile_type")


class ProfileMembership(Base):
    __tablename__ = "profile_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    profile_type_id = Column(Integer, ForeignKey("profile_types.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="profile_memberships")
    profile_type = relationship("ProfileType", back_populates="memberships")
    company = relationship("Company")
    brand = relationship("Brand")
    branch = relationship("Branch")


class RoleAssignment(Base):
    __tablename__ = "role_assignments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="canonical_role_assignments")
    role = relationship("Role")
    company = relationship("Company")
    brand = relationship("Brand")
    branch = relationship("Branch")
