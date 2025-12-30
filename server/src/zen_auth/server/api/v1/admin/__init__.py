from ...util.router_factory import APIRouterFactory
from . import admin, client_app, role, scope, user

router = APIRouterFactory()
router.include_router(admin.router)
router.include_router(user.router)
router.include_router(client_app.router)
router.include_router(role.router)
router.include_router(scope.router)

__all__ = ["router"]
