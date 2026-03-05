from .public import router as public_router
from .admin_auth import router as admin_auth_router
from .admin_panel import router as admin_panel_router

routers = (public_router, admin_auth_router, admin_panel_router)