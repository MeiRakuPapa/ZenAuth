from ...api.util.router_factory import APIRouterFactory
from . import admin, auth, meta, verify

router = APIRouterFactory()

router.include_router(auth.router)
router.include_router(meta.router)
router.include_router(verify.router)
router.include_router(admin.router)
__all__ = ["router"]
