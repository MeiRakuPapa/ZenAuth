from ...util.router_factory import APIRouterFactory
from . import meta

router = APIRouterFactory()
router.include_router(meta.router)
__all__ = ["router"]
