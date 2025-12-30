from ...util.router_factory import APIRouterFactory
from . import auth

router = APIRouterFactory()
router.include_router(auth.router)

__all__ = ["router"]
