from fastapi import APIRouter

from app.routes.staff.profile import router as profile_router


router = APIRouter()
router.include_router(profile_router)


__all__ = ["router"]
