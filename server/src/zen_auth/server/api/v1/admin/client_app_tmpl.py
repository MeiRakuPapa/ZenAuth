import html
from typing import Iterable

from starlette.requests import Request
from zen_html import H

from .._tmp_lib import (
    BTN_CLS,
    DEL_ICON,
    EDIT_ICON,
    AdminNav,
    Dialog,
    DlgHeader,
    InputText,
    display_alert,
    reload,
)
from ..ui_ids import ADM_APP_LIST_ID, ADM_CREATE_APP_ID, ADM_EDIT_APP_ID
from ..url_names import (
    ADM_APP_LIST_CONTENT,
    ADM_CREATE_APP_API,
    ADM_CREATE_APP_CONTENT,
    ADM_DELETE_APP_API,
    ADM_EDIT_APP_CONTENT,
    ADM_ROLE_LIST_CONTENT,
    ADM_SCOPE_LIST_CONTENT,
    ADM_UPDATE_APP_API,
    ADM_USER_LIST_CONTENT,
    AUTH_LOGOUT_API,
)


def ClientAppRow(app: dict[str, str | None], *, req: Request) -> H:
    app_id = app.get("app_id") or ""
    edit_path = str(req.url_for(ADM_EDIT_APP_CONTENT, app_id=app_id))
    del_path = str(req.url_for(ADM_DELETE_APP_API, app_id=app_id))
    list_path = str(req.url_for(ADM_APP_LIST_CONTENT))
    btn_cls = BTN_CLS + ["btn-outline-primary"]

    return H.tr(
        dataset={"id": app["app_id"]},
        children=[
            H.td(app_id),
            H.td(app.get("display_name") or ""),
            H.td(app.get("description") or ""),
            H.td(app.get("return_to") or ""),
            H.td(
                H.button(
                    EDIT_ICON, class_=btn_cls, hxGet=edit_path, hxTarget="#APP_ROOT", hxSwap="innerHTML"
                ),
                H.button(
                    DEL_ICON,
                    type="button",
                    class_=btn_cls,
                    hxDelete=del_path,
                    hxConfirm=f"Delete app: {html.escape(app_id)}?",
                    hxOn__afterOnLoad=H.RAW_STR(reload(ADM_APP_LIST_ID, list_path)),
                ),
            ),
        ],
    )


def ClientAppList(apps: Iterable[dict[str, str | None]], *, req: Request) -> H:
    tbl_header = ["App ID", "Display", "Description", "Return To", "-"]
    create_page_path = req.url_for(ADM_CREATE_APP_CONTENT).path

    user_path = req.url_for(ADM_USER_LIST_CONTENT).path
    app_path = req.url_for(ADM_APP_LIST_CONTENT).path
    role_path = req.url_for(ADM_ROLE_LIST_CONTENT).path
    scope_path = req.url_for(ADM_SCOPE_LIST_CONTENT).path
    logout_path = req.url_for(AUTH_LOGOUT_API).path

    return H.div(
        id=ADM_APP_LIST_ID,
        class_="p-4",
        children=[
            AdminNav(
                user_path=user_path,
                app_path=app_path,
                role_path=role_path,
                scope_path=scope_path,
                active="apps",
                logout_path=logout_path,
            ),
            H.div(
                class_="d-flex mb-2 align-items-center justify-content-between",
                children=[
                    H.h3("Client App List"),
                    H.button(
                        "NewApp",
                        class_=BTN_CLS + ["btn-primary"],
                        hxGet=create_page_path,
                        hxTarget="#APP_ROOT",
                        hxSwap="innerHTML",
                    ),
                ],
            ),
            H.table(
                class_="table table-sm table-striped table-hover user-list-table",
                children=[
                    H.thead(
                        H.colgroup(*(H.col() for _ in tbl_header)),
                        H.tr((H.th(n) for n in tbl_header)),
                    ),
                    H.tbody((ClientAppRow(a, req=req) for a in apps)),
                ],
            ),
        ],
    )


def CreateClientAppDialog(
    *, req: Request, dialog_id: str = ADM_CREATE_APP_ID, dialog_title: str = "Create App"
) -> H:
    list_path = str(req.url_for(ADM_APP_LIST_CONTENT))
    create_api = str(req.url_for(ADM_CREATE_APP_API))
    alert_id = dialog_id + "-alert"

    form_fields = [
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputText(dialog_id, "app_id", "App ID", ""),
        InputText(dialog_id, "display_name", "Display", ""),
        InputText(dialog_id, "description", "Description", ""),
        InputText(dialog_id, "return_to", "Return To", ""),
    ]

    close_btn = H.button(
        "Close",
        type="button",
        class_=BTN_CLS + ["btn-secondary", "me-2"],
        hxGet=list_path,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
    )
    apply_btn = H.button(
        "Apply",
        type="button",
        class_=BTN_CLS + ["btn-primary"],
        hxPost=create_api,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
        hxOn____responseError=display_alert(alert_id),
    )

    header = DlgHeader(dialog_title)
    body = (
        H.form(form_fields + [H.div(close_btn, apply_btn, class_=["d-flex", "me-3"])], autocomplete="off"),
    )
    return Dialog(dialog_id, header, body)


def EditClientAppDialog(
    *,
    req: Request,
    app: dict[str, str | None],
    dialog_id: str = ADM_EDIT_APP_ID,
    dialog_title: str = "Edit App",
) -> H:
    list_path = str(req.url_for(ADM_APP_LIST_CONTENT))
    update_api = str(req.url_for(ADM_UPDATE_APP_API))
    alert_id = dialog_id + "-alert"

    form_fields = [
        H.div(
            H.label("App ID", class_=["form-label"]),
            H.div(app["app_id"], class_=["fw-semibold"]),
            H.input(type="hidden", name="app_id", value=app["app_id"]),
            class_="mb-3",
        ),
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputText(dialog_id, "display_name", "Display", app.get("display_name") or ""),
        InputText(dialog_id, "description", "Description", app.get("description") or ""),
        InputText(dialog_id, "return_to", "Return To", app.get("return_to") or ""),
    ]

    close_btn = H.button(
        "Close",
        type="button",
        class_=BTN_CLS + ["btn-secondary", "me-2"],
        hxGet=list_path,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
    )
    apply_btn = H.button(
        "Apply",
        type="button",
        class_=BTN_CLS + ["btn-primary"],
        hxPost=update_api,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
        hxOn____responseError=display_alert(alert_id),
    )

    header = DlgHeader(dialog_title)
    body = (
        H.form(form_fields + [H.div(close_btn, apply_btn, class_=["d-flex", "me-3"])], autocomplete="off"),
    )
    return Dialog(dialog_id, header, body)
