import html
from typing import Iterable

from starlette.requests import Request
from zen_auth.dto import ScopeDTO
from zen_html import H

from .._tmp_lib import (
    BTN_CLS,
    DEL_ICON,
    EDIT_ICON,
    AdminNav,
    Dialog,
    DlgHeader,
    InputText,
    Selector,
    display_alert,
    reload,
)
from ..ui_ids import ADM_CREATE_SCOPE_ID, ADM_EDIT_SCOPE_ID, ADM_SCOPE_LIST_ID
from ..url_names import (
    ADM_APP_LIST_CONTENT,
    ADM_CREATE_SCOPE_API,
    ADM_CREATE_SCOPE_CONTENT,
    ADM_DELETE_SCOPE_API,
    ADM_EDIT_SCOPE_CONTENT,
    ADM_ROLE_LIST_CONTENT,
    ADM_SCOPE_LIST_CONTENT,
    ADM_UPDATE_SCOPE_API,
    ADM_USER_LIST_CONTENT,
    AUTH_LOGOUT_API,
)


def ScopeRow(scope: ScopeDTO, *, req: Request, role_map: dict[str, str]) -> H:
    edit_path = str(req.url_for(ADM_EDIT_SCOPE_CONTENT, scope_name=scope.scope_name))
    del_path = str(req.url_for(ADM_DELETE_SCOPE_API, scope_name=scope.scope_name))
    list_path = str(req.url_for(ADM_SCOPE_LIST_CONTENT))
    btn_cls = BTN_CLS + ["btn-outline-primary"]

    roles_badges = H.div(
        children=(H.span(role_map.get(rn, rn), class_="badge bg-primary me-1") for rn in scope.roles),
        class_="d-flex",
    )

    return H.tr(
        dataset={"id": scope.scope_name},
        children=[
            H.td(scope.scope_name),
            H.td(scope.display_name),
            H.td(scope.description or ""),
            H.td(roles_badges),
            H.td(
                H.button(
                    EDIT_ICON, class_=btn_cls, hxGet=edit_path, hxTarget="#APP_ROOT", hxSwap="innerHTML"
                ),
                H.button(
                    DEL_ICON,
                    type="button",
                    class_=btn_cls,
                    hxDelete=del_path,
                    hxConfirm=f"Delete scope: {html.escape(scope.scope_name)}?",
                    hxOn__afterOnLoad=H.RAW_STR(reload(ADM_SCOPE_LIST_ID, list_path)),
                ),
            ),
        ],
    )


def ScopeList(scopes: Iterable[ScopeDTO], *, req: Request, role_map: dict[str, str]) -> H:
    tbl_header = ["Scope", "Display", "Description", "Roles", "-"]
    create_page_path = req.url_for(ADM_CREATE_SCOPE_CONTENT).path
    user_path = req.url_for(ADM_USER_LIST_CONTENT).path
    app_path = req.url_for(ADM_APP_LIST_CONTENT).path
    role_path = req.url_for(ADM_ROLE_LIST_CONTENT).path
    scope_path = req.url_for(ADM_SCOPE_LIST_CONTENT).path
    logout_path = req.url_for(AUTH_LOGOUT_API).path

    return H.div(
        id=ADM_SCOPE_LIST_ID,
        class_="p-4",
        children=[
            AdminNav(
                user_path=user_path,
                app_path=app_path,
                role_path=role_path,
                scope_path=scope_path,
                active="scopes",
                logout_path=logout_path,
            ),
            H.div(
                class_="d-flex mb-2 align-items-center justify-content-between",
                children=[
                    H.h3("Scope List"),
                    H.button(
                        "NewScope",
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
                    H.tbody((ScopeRow(s, req=req, role_map=role_map) for s in scopes)),
                ],
            ),
        ],
    )


def CreateScopeDialog(
    *,
    req: Request,
    role_map: dict[str, str],
    dialog_id: str = ADM_CREATE_SCOPE_ID,
    dialog_title: str = "Create Scope",
) -> H:
    list_path = str(req.url_for(ADM_SCOPE_LIST_CONTENT))
    create_api = str(req.url_for(ADM_CREATE_SCOPE_API))
    alert_id = dialog_id + "-alert"

    form_fields = [
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputText(dialog_id, "scope_name", "Scope", ""),
        InputText(dialog_id, "display_name", "Display", ""),
        InputText(dialog_id, "description", "Description", ""),
        Selector(dialog_id, "roles", "Roles", role_map, []),
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


def EditScopeDialog(
    *,
    req: Request,
    scope: ScopeDTO,
    role_map: dict[str, str],
    dialog_id: str = ADM_EDIT_SCOPE_ID,
    dialog_title: str = "Edit Scope",
) -> H:
    list_path = str(req.url_for(ADM_SCOPE_LIST_CONTENT))
    update_api = str(req.url_for(ADM_UPDATE_SCOPE_API))
    alert_id = dialog_id + "-alert"

    form_fields = [
        H.div(
            H.label("Scope", class_=["form-label"]),
            H.div(scope.scope_name, class_=["fw-semibold"]),
            H.input(type="hidden", name="scope_name", value=scope.scope_name),
            class_="mb-3",
        ),
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputText(dialog_id, "display_name", "Display", scope.display_name),
        InputText(dialog_id, "description", "Description", scope.description or ""),
        Selector(dialog_id, "roles", "Roles", role_map, scope.roles),
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
