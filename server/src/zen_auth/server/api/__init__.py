from ..api.util.router_factory import APIRouterFactory
from . import v1

router = APIRouterFactory(prefix="/zen_auth")
router.include_router(v1.router)

__all__ = ["router"]
