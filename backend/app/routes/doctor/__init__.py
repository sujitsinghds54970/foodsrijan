"""Doctor-scoped route namespace for secured portal APIs."""

from app.routes.doctor_portal_api import router as doctor_portal_router

__all__ = ["doctor_portal_router"]
