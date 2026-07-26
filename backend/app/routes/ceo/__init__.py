from fastapi import APIRouter

from app.routes.ceo.doctors import router as doctors_router
from app.routes.ceo.finance import router as finance_router
from app.routes.ceo.inventory import router as inventory_router
from app.routes.ceo.compliance import router as compliance_router
from app.routes.ceo.settings import router as settings_router
from app.routes.ceo.patients import router as patients_router
from app.routes.ceo.people import router as people_router
from app.routes.ceo.security import router as security_router

router = APIRouter()
router.include_router(security_router)
router.include_router(people_router)
router.include_router(finance_router)
router.include_router(doctors_router)
router.include_router(patients_router)
router.include_router(inventory_router)
router.include_router(compliance_router)
router.include_router(settings_router)

__all__ = ["router"]