from urllib.parse import quote, unquote

from fastapi import status
from fastapi.datastructures import URL
from fastapi.requests import Request
from fastapi.responses import RedirectResponse, Response


def error_redirect(to: URL | str, error_msg: str | None) -> Response:
    resp = RedirectResponse(url=to, status_code=status.HTTP_303_SEE_OTHER)
    if error_msg:
        resp.set_cookie("flash_error", quote(error_msg), httponly=True, samesite="lax")
    return resp


def get_redirect_error_msg(req: Request) -> str | None:
    msg = req.cookies.get("flash_error")
    if msg:
        msg = unquote(msg)
    return msg


def clear_redirect_error_msg(resp: Response) -> Response:
    resp.delete_cookie("flash_error")
    return resp
