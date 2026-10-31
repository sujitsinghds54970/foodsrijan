from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, Brand, Company, Role, User, UserCompany, UserRole
from app.utils.auth_system import auth_guard, require_super_admin

router = APIRouter(tags=["Super CEO"])


class CompanyCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class CompanyUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2)
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyAdminAssignRequest(BaseModel):
    user_id: int
    role_name: str = "company_admin"


class BrandCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class BrandUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2)
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3)
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=7)
    role: str = "staff"
    company_id: Optional[int] = None
    is_super_admin: bool = False
    is_active: bool = True


def _slugify(value: str) -> str:
    slug = (value or "").strip().lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in slug)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _ensure_company_role(db: Session, company_id: int, slug: str = "company_admin") -> Role:
    role = db.query(Role).filter(Role.company_id == company_id, Role.slug == slug).first()
    if role:
        return role

    business_title = "Company Admin" if slug == "company_admin" else slug.replace("_", " ").title()
    role = Role(
        company_id=company_id,
        name=business_title,
        slug=slug,
        description=f"{business_title} role for the company.",
        is_active=True,
        is_system_role=False,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def _company_ceo_payload(db: Session, company_id: int) -> Optional[dict]:
    ceo_role = db.query(Role).filter(Role.company_id == company_id, Role.slug == "ceo").first()
    if not ceo_role:
        return None
    assignment = (
        db.query(UserRole)
        .filter(UserRole.company_id == company_id, UserRole.role_id == ceo_role.id, UserRole.is_active.is_(True))
        .first()
    )
    if not assignment:
        return None
    user = db.query(User).filter(User.id == assignment.user_id).first()
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
    }


def _serialize_brand(db: Session, brand: Brand) -> dict:
    return {
        "id": brand.id,
        "company_id": brand.company_id,
        "name": brand.name,
        "slug": brand.slug,
        "description": brand.description,
        "is_active": bool(brand.is_active),
        "created_at": brand.created_at.isoformat() if brand.created_at else None,
        "updated_at": brand.updated_at.isoformat() if brand.updated_at else None,
    }


def _serialize_company(db: Session, company: Company) -> dict:
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "description": company.description,
        "is_active": company.is_active,
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
        "users_count": db.query(UserCompany).filter(UserCompany.company_id == company.id, UserCompany.is_active.is_(True)).count(),
        "brands_count": db.query(Brand).filter(Brand.company_id == company.id, Brand.is_active.is_(True)).count(),
        "branches_count": db.query(Branch).filter(Branch.company_id == company.id).count(),
        "brands": [
            _serialize_brand(db, brand) for brand in db.query(Brand).filter(Brand.company_id == company.id).order_by(Brand.name.asc()).all()
        ],
        "ceo": _company_ceo_payload(db, company.id),
    }


@router.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    companies = db.query(Company).order_by(Company.created_at.desc()).all()
    return {"companies": [_serialize_company(db, company) for company in companies]}


@router.get("/companies/{company_id}")
def get_company_by_id(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"company": _serialize_company(db, company)}


@router.post("/companies", status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    normalized_name = (payload.name or "").strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Company name is required")

    slug = (payload.slug or _slugify(normalized_name)).strip()
    if not slug:
        raise HTTPException(status_code=400, detail="A valid company slug is required")

    if db.query(Company).filter((Company.name == normalized_name) | (Company.slug == slug)).first():
        raise HTTPException(status_code=400, detail="Company with this name or slug already exists")

    company = Company(
        name=normalized_name,
        slug=slug,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    default_brand = Brand(
        company_id=company.id,
        name=normalized_name,
        slug=slug,
        description=f"Default brand for {normalized_name}",
        is_active=True,
    )
    db.add(default_brand)
    db.commit()

    _ensure_company_role(db, company.id, "company_admin")
    _ensure_company_role(db, company.id, "ceo")
    return {"message": "Company created successfully", "company": _serialize_company(db, company)}


@router.put("/companies/{company_id}")
def update_company(
    company_id: int,
    payload: CompanyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if payload.name is not None:
        company.name = payload.name.strip()
    if payload.slug is not None:
        company.slug = payload.slug.strip()
    if payload.description is not None:
        company.description = payload.description
    if payload.is_active is not None:
        company.is_active = payload.is_active

    if not company.name:
        raise HTTPException(status_code=400, detail="Company name cannot be empty")

    existing = db.query(Company).filter(
        Company.id != company_id,
        (Company.name == company.name) | (Company.slug == company.slug),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Another company already uses this name or slug")

    db.commit()
    db.refresh(company)
    return {"message": "Company updated successfully", "company": _serialize_company(db, company)}


@router.delete("/companies/{company_id}")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.is_active = False
    db.query(UserCompany).filter(UserCompany.company_id == company_id).update({"is_active": False})
    db.query(Brand).filter(Brand.company_id == company_id).update({"is_active": False})
    db.commit()
    return {"message": "Company archived successfully", "company_id": company.id}


@router.get("/companies/{company_id}/brands")
def list_company_brands(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    brands = db.query(Brand).filter(Brand.company_id == company_id).order_by(Brand.name.asc()).all()
    return {"brands": [_serialize_brand(db, brand) for brand in brands]}


@router.post("/companies/{company_id}/brands", status_code=status.HTTP_201_CREATED)
def create_company_brand(
    company_id: int,
    payload: BrandCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    normalized_name = (payload.name or "").strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Brand name is required")

    slug = (payload.slug or _slugify(normalized_name)).strip()
    if not slug:
        raise HTTPException(status_code=400, detail="A valid brand slug is required")

    if db.query(Brand).filter(Brand.company_id == company_id, (Brand.name == normalized_name) | (Brand.slug == slug)).first():
        raise HTTPException(status_code=400, detail="A brand with this name or slug already exists for this company")

    brand = Brand(
        company_id=company_id,
        name=normalized_name,
        slug=slug,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return {"message": "Brand created successfully", "brand": _serialize_brand(db, brand)}


@router.put("/brands/{brand_id}")
def update_brand(
    brand_id: int,
    payload: BrandUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if payload.name is not None:
        brand.name = payload.name.strip()
    if payload.slug is not None:
        brand.slug = payload.slug.strip()
    if payload.description is not None:
        brand.description = payload.description
    if payload.is_active is not None:
        brand.is_active = payload.is_active

    if not brand.name:
        raise HTTPException(status_code=400, detail="Brand name cannot be empty")

    existing = db.query(Brand).filter(
        Brand.id != brand_id,
        Brand.company_id == brand.company_id,
        (Brand.name == brand.name) | (Brand.slug == brand.slug),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Another brand already uses this name or slug in the company")

    db.commit()
    db.refresh(brand)
    return {"message": "Brand updated successfully", "brand": _serialize_brand(db, brand)}


@router.delete("/brands/{brand_id}")
def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    brand.is_active = False
    db.commit()
    return {"message": "Brand archived successfully", "brand_id": brand.id}


@router.post("/companies/{company_id}/admins")
def assign_company_admin(
    company_id: int,
    payload: CompanyAdminAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    admin_role = _ensure_company_role(db, company.id, payload.role_name or "company_admin")

    assignment = db.query(UserCompany).filter(UserCompany.user_id == user.id, UserCompany.company_id == company.id).first()
    if assignment:
        assignment.role_id = admin_role.id
        assignment.is_active = True
    else:
        db.add(UserCompany(user_id=user.id, company_id=company.id, role_id=admin_role.id, is_active=True))

    existing_role_assignment = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.company_id == company.id,
        UserRole.role_id == admin_role.id,
    ).first()
    if not existing_role_assignment:
        db.add(UserRole(user_id=user.id, role_id=admin_role.id, company_id=company.id, is_active=True))

    user.role = "company_admin"
    user.current_company_id = company.id
    user.company_id = company.id
    db.commit()

    return {
        "message": "Company admin assigned successfully",
        "company_id": company.id,
        "user_id": user.id,
        "role": admin_role.slug,
    }


@router.post("/companies/{company_id}/ceo")
def assign_company_ceo(
    company_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ceo_role = _ensure_company_role(db, company.id, "ceo")
    assignment = db.query(UserCompany).filter(UserCompany.user_id == user.id, UserCompany.company_id == company.id).first()
    if assignment:
        assignment.role_id = ceo_role.id
        assignment.is_active = True
    else:
        db.add(UserCompany(user_id=user.id, company_id=company.id, role_id=ceo_role.id, is_active=True))

    existing_role_assignment = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.company_id == company.id,
        UserRole.role_id == ceo_role.id,
    ).first()
    if not existing_role_assignment:
        db.add(UserRole(user_id=user.id, role_id=ceo_role.id, company_id=company.id, is_active=True))

    user.role = "ceo"
    user.current_company_id = company.id
    user.company_id = company.id
    db.commit()

    return {"message": "CEO assigned successfully", "company_id": company.id, "user_id": user.id}


@router.delete("/companies/{company_id}/ceo")
def remove_company_ceo(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    ceo_role = db.query(Role).filter(Role.company_id == company_id, Role.slug == "ceo").first()
    if ceo_role:
        db.query(UserRole).filter(UserRole.company_id == company_id, UserRole.role_id == ceo_role.id).update({"is_active": False})
        db.query(UserCompany).filter(UserCompany.company_id == company_id, UserCompany.role_id == ceo_role.id).update({"is_active": False})

    db.commit()
    return {"message": "CEO removed successfully", "company_id": company.id}


@router.get("/dashboard")
def get_super_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    total_companies = db.query(Company).count()
    active_companies = db.query(Company).filter(Company.is_active.is_(True)).count()
    total_users = db.query(User).count()
    total_branches = db.query(Branch).count()
    total_brands = db.query(Brand).count()

    companies = []
    for company in db.query(Company).order_by(Company.created_at.desc()).all():
        companies.append(
            {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "description": company.description,
                "is_active": company.is_active,
                "users_count": db.query(UserCompany).filter(UserCompany.company_id == company.id, UserCompany.is_active.is_(True)).count(),
                "brands_count": db.query(Brand).filter(Brand.company_id == company.id, Brand.is_active.is_(True)).count(),
                "branches_count": db.query(Branch).filter(Branch.company_id == company.id).count(),
                "brands": [
                    _serialize_brand(db, brand)
                    for brand in db.query(Brand).filter(Brand.company_id == company.id).order_by(Brand.name.asc()).all()
                ],
                "ceo": _company_ceo_payload(db, company.id),
            }
        )

    return {
        "summary": {
            "total_companies": total_companies,
            "active_companies": active_companies,
            "total_users": total_users,
            "total_branches": total_branches,
            "total_brands": total_brands,
        },
        "companies": companies,
    }


@router.get("/users")
def list_system_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    users = db.query(User).order_by(User.id.asc()).all()
    serialized = []
    for user in users:
        company_names = []
        for association in db.query(UserCompany).filter(UserCompany.user_id == user.id, UserCompany.is_active.is_(True)).all():
            company = db.query(Company).filter(Company.id == association.company_id).first()
            if company:
                company_names.append({"id": company.id, "name": company.name})
        serialized.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "role": user.role,
                "is_super_admin": bool(user.is_super_admin),
                "is_active": user.is_active,
                "company_id": user.company_id,
                "current_company_id": user.current_company_id,
                "companies": company_names,
            }
        )
    return {"users": serialized}


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_system_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    username = payload.username.strip()
    email = payload.email.strip()
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    phone = payload.phone.strip()

    if not all([username, email, first_name, last_name, phone, payload.password]):
        raise HTTPException(status_code=400, detail="All required fields must be provided")

    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = User(
        username=username,
        email=email,
        hashed_password=auth_guard.hash_password(payload.password),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role=payload.role if payload.role else "staff",
        company_id=payload.company_id,
        current_company_id=payload.company_id,
        is_super_admin=payload.is_super_admin,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if payload.company_id:
        company = db.query(Company).filter(Company.id == payload.company_id).first()
        if company:
            admin_role = _ensure_company_role(db, company.id, "company_admin" if payload.role == "company_admin" else "company_admin")
            assignment = db.query(UserCompany).filter(UserCompany.user_id == user.id, UserCompany.company_id == company.id).first()
            if assignment:
                assignment.role_id = admin_role.id
                assignment.is_active = True
            else:
                db.add(UserCompany(user_id=user.id, company_id=company.id, role_id=admin_role.id, is_active=True))
            user.current_company_id = company.id
            user.company_id = company.id
            db.commit()

    return {"message": "System user created successfully", "user": {"id": user.id, "username": user.username, "email": user.email}}
