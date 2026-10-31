from fastapi import APIRouter

from app.routes.manager.dashboard import router as dashboard_router
from app.routes.manager.profile import router as profile_router
from app.routes.manager.staff import router as staff_router


router = APIRouter()
router.include_router(profile_router)
router.include_router(dashboard_router)
router.include_router(staff_router)


__all__ = ["router"]