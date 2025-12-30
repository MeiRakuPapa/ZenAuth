from ...util.router_factory import APIRouterFactory
from . import verify

router = APIRouterFactory()
router.include_router(verify.router)

__all__ = ["router"]
