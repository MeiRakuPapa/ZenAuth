from typing import Any, Iterable

from fastapi.responses import JSONResponse
from starlette import status
from starlette.datastructures import URL
from starlette.responses import StreamingResponse
from zen_html import H

from ..v1._assets import default_body_links, default_header_links

BASE_URL = "http://localhost"

FORM_INPUT_CLS = ["form-control", "form-control-sm"]
BTN_CLS = ["btn", "btn-sm"]


def BiIcon(icon_name: str) -> H:
    return H.i(class_=f"bi {icon_name}")


EDIT_ICON = BiIcon("bi-pencil")
DEL_ICON = BiIcon("bi-trash")
NEXT_PAGE_ICON = BiIcon("bi-caret-right")
PREV_PAGE_ICON = BiIcon("bi-caret-left")


def open_modal(target: str) -> str:
    return f"UIHelper.openModal('#{target}');"


def close_modal(target: str) -> str:
    return f"UIHelper.closeModal('#{target}');"


def reload(target: str, api_path: str) -> str:
    return f"UIHelper.reload('#{target}', '{api_path}');"


def setup_dual_list(target: str) -> str:
    return f"DualList.setup('#{target}');"


class HResponse(StreamingResponse):

    def __init__(
        self,
        content: H | Iterable[H] | Iterable[str],
        status_code: int = 200,
        include_doctype: bool = False,
        media_type: str = "text/html; charset=utf-8",
        **kwargs: Any,
    ) -> None:
        stream = self._render(content, include_doctype)
        super().__init__(stream, status_code=status_code, media_type=media_type, **kwargs)

    @staticmethod
    def _render(content: H | Iterable[H] | Iterable[str], include_doctype: bool) -> Iterable[str]:
        if include_doctype:
            yield "<!DOCTYPE html>"
        if isinstance(content, H):
            yield from content.to_token()
        elif isinstance(content, str):
            yield content
        else:
            for i in content:
                yield from HResponse._render(i, include_doctype=False)


def PageNationButton(*_children: H, condition: bool, path: str, target: str, class_: list[str]) -> H:
    if condition:
        return H.button(*_children, class_=class_, hxGet=path, hxTarget=target, hxSwap="outerHTML")
    else:
        return H.button(*_children, class_=(class_ + ["disabled"]), disabled=True)


def AdminNav(
    *,
    user_path: str | None,
    app_path: str | None,
    role_path: str,
    scope_path: str,
    active: str,
    logout_path: str | None = None,
) -> H:
    def _tab(label: str, path: str, is_active: bool) -> H:
        cls = BTN_CLS + (["btn-primary"] if is_active else ["btn-outline-primary"])
        return H.button(
            label,
            type="button",
            class_=cls,
            hxGet=path,
            hxTarget="#APP_ROOT",
            hxSwap="innerHTML",
        )

    children: list[H] = []
    if user_path is not None:
        children.append(_tab("Users", user_path, active == "users"))
    if app_path is not None:
        children.append(_tab("Apps", app_path, active == "apps"))
    children.append(_tab("Roles", role_path, active == "roles"))
    children.append(_tab("Scopes", scope_path, active == "scopes"))

    tabs = H.div(*children, class_="d-flex gap-2")
    if logout_path:
        logout_btn = H.button(
            "Logout",
            type="button",
            class_=BTN_CLS + ["btn-outline-secondary"],
            hxPost=logout_path,
            hxSwap="none",
        )
        return H.div(tabs, logout_btn, class_="d-flex justify-content-between align-items-center mb-3")

    return H.div(tabs, class_="mb-3")


def StyleSheet(href: URL | str) -> H:
    return H.link(href=H.RAW_STR(f"{href}"), rel="stylesheet")


def Script(src: URL | str) -> H:
    return H.script(src=H.RAW_STR(f"{src}"))


def HtmlDocument(
    *content: H,
    title: str = "",
    keywords: str = "",
    description: str = "",
    header_links: list[H] | None = None,
    body_links: list[H] | None = None,
) -> H:
    header_links = header_links or default_header_links()
    body_links = body_links or default_body_links()
    return H.html(
        lang="ja",
        children=[
            H.head(
                H.meta(name="description", content=description),
                H.meta(name="keywords", content=keywords),
                H.meta(httpEquiv="Pragma", content="no-cache"),
                H.meta(httpEquiv="Cache-Control", content="no-store"),
                H.title(title),
                *header_links,
            ),
            H.body(*content, *body_links),
        ],
    )


def escapeHtmlJs() -> H:
    return H.script(
        H.RAW_STR(
            """
function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}
            """
        )
    )


def TopPage(
    initial_url: str,
    *,
    title: str = "",
    keywords: str = "",
    description: str = "",
    header_links: list[H] | None = None,
    body_links: list[H] | None = None,
) -> H:
    header_links = header_links or default_header_links()
    body_links = body_links or default_body_links()
    return HtmlDocument(
        H.div(
            id="APP_ROOT",
            hxGet=initial_url,
            hxTrigger="load",
            hxTarget="this",
            hxSwap="innerHTML",
            children=H.div("Loading...", class_="loading"),
        ),
        title=title,
        keywords=keywords,
        description=description,
        header_links=header_links,
        body_links=body_links,
    )


class SuccessResponse(JSONResponse):
    """JSON 200 response with body {"success": true}."""

    def __init__(self) -> None:
        super().__init__({"success": True}, status_code=status.HTTP_200_OK)


class ErrorResponse(JSONResponse):
    """JSON error response; returns {"errors": [msg, ...]}."""

    def __init__(self, msg: str | list[str], status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__({"errors": [msg] if isinstance(msg, str) else msg}, status_code=status_code)


def InputText(
    parent_id: str,
    name: str,
    label: str,
    value: str,
    class_: list[str] | None = None,
    autocomplete: str = "off",
) -> H:
    class_ = class_ or list()
    id = f"{parent_id}-{name}"
    return H.div(
        H.label(label, for_=id, class_=["form-label", "m-0"]),
        H.input(
            id=id,
            name=name,
            type="text",
            class_=FORM_INPUT_CLS + class_,
            value=value,
            autocomplete=autocomplete,
        ),
        dataset={"name": name},
        class_="mb-1",
    )


def InputPassword(
    parent_id: str,
    name: str,
    label: str,
    value: str,
    class_: list[str] | None = None,
    autocomplete: str = "new-password",
) -> H:
    class_ = class_ or list()
    id = f"{parent_id}-{name}"
    return H.div(
        H.label(label, for_=id, class_=["form-label", "m-0"]),
        H.input(
            id=id,
            name=name,
            type="password",
            class_=FORM_INPUT_CLS + class_,
            value=value,
            autocomplete=autocomplete,
        ),
        dataset={"name": name},
        class_="mb-1",
    )


def Selector(
    parent_id: str,
    name: str,
    label: str,
    item_map: dict[str, str],
    values: list[str],
    class_: list[str] | None = None,
    size: int = 8,
) -> H:
    class_ = class_ or list()
    id = f"{parent_id}-{name}"
    options = [H.option(label, value=key, selected=(key in values)) for key, label in item_map.items()]
    return H.div(
        H.label(label, for_=id, class_=["form-label", "m-0"]),
        H.select(*options, id=id, name=name, class_="dl", multiple=True, size=size),
        dataset={"name": name},
        class_="mb-1",
    )


def DlgHeader(dialog_title: str) -> H:
    return H.div(H.h2(dialog_title), class_="modal-header")


def Dialog(dialog_id: str, header: H, body: H) -> H:
    return H.div(
        H.div(
            header,
            body,
            class_=["modal-content", "p-2"],
        ),
        hxOn____load=f"DualList.setup('#{dialog_id}-roles')",
        id=dialog_id,
        class_=["modal-dialog"],
    )


def display_alert(alert_id: str) -> str:
    return (
        f"htmx.find('#{alert_id}').classList.remove('d-none');"
        f"htmx.find('#{alert_id}').innerHTML = renderErrors(JSON.parse(event.detail.xhr.responseText).errors);"
    )
