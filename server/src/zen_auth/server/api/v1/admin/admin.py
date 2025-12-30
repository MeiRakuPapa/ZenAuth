import os

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from zen_auth.dto import UserDTO
from zen_html import H

from ....claims_self import ClaimsSelf
from .._assets import default_header_links
from .._tmp_lib import HResponse, TopPage
from ..url_names import (
    ADM_CSS_PATH,
    ADM_DUAL_LIST_JS_PATH,
    ADM_HELPER_JS_PATH,
    ADM_RBAC_TOP_PAGE,
    ADM_ROLE_LIST_CONTENT,
    ADM_TOP_PAGE,
    ADM_USER_LIST_CONTENT,
)

router = APIRouter(prefix="", tags=["admin"])


@router.get("/", name=ADM_TOP_PAGE)
def _top_page(
    req: Request,
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = user
    page = TopPage(
        req.url_for(ADM_USER_LIST_CONTENT).path,
        header_links=default_header_links()
        + [
            H.link(rel="stylesheet", href=req.url_for(ADM_CSS_PATH)),
            H.script(src=req.url_for(ADM_DUAL_LIST_JS_PATH)),
            H.script(src=req.url_for(ADM_HELPER_JS_PATH)),
        ],
    )
    return HResponse(page)


@router.get("/rbac", name=ADM_RBAC_TOP_PAGE)
def _rbac_top(
    req: Request,
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = user
    return RedirectResponse(str(req.url_for(ADM_ROLE_LIST_CONTENT)), status_code=status.HTTP_303_SEE_OTHER)


_assets_dir = os.path.dirname(os.path.abspath(__file__))


@router.get("/dual_list.js", name=ADM_DUAL_LIST_JS_PATH)
def _dual_list_js(req: Request) -> Response:
    dual_list_path = os.path.join(_assets_dir, "dual_list.js")
    return FileResponse(dual_list_path, media_type="application/javascript; charset=utf-8")


@router.get("/zenauth_admin.css", name=ADM_CSS_PATH)
def _zenauth_admin_css(req: Request) -> Response:
    css_path = os.path.join(_assets_dir, "zenauth_admin.css")
    return FileResponse(css_path, media_type="text/css; charset=utf-8")


@router.get("/helper.js", name=ADM_HELPER_JS_PATH)
def get_helper_js() -> FileResponse:
    js_path = os.path.join(os.path.dirname(__file__), "../helper.js")
    return FileResponse(js_path, media_type="application/javascript")
