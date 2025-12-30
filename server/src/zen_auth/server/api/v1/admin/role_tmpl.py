import html
from typing import Iterable, overload

from starlette.requests import Request
from zen_auth.dto import RoleDTO
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
from ..ui_ids import ADM_CREATE_ROLE_ID, ADM_EDIT_ROLE_ID, ADM_ROLE_LIST_ID
from ..url_names import (
    ADM_APP_LIST_CONTENT,
    ADM_CREATE_ROLE_API,
    ADM_CREATE_ROLE_CONTENT,
    ADM_DELETE_ROLE_API,
    ADM_EDIT_ROLE_CONTENT,
    ADM_ROLE_LIST_CONTENT,
    ADM_SCOPE_LIST_CONTENT,
    ADM_UPDATE_ROLE_API,
    ADM_USER_LIST_CONTENT,
    AUTH_LOGOUT_API,
)


def _badges(items: Iterable[str]) -> H:
    return H.div(
        children=(H.span(i, class_="badge bg-primary me-1") for i in items),
        class_="d-flex flex-wrap gap-1",
    )


def RoleRow(
    role: RoleDTO,
    *,
    req: Request,
    user_count: int,
    scope_count: int,
) -> H:
    edit_path = str(req.url_for(ADM_EDIT_ROLE_CONTENT, role_name=role.role_name))
    del_path = str(req.url_for(ADM_DELETE_ROLE_API, role_name=role.role_name))
    list_path = str(req.url_for(ADM_ROLE_LIST_CONTENT))
    btn_cls = BTN_CLS + ["btn-outline-primary"]

    return H.tr(
        dataset={"id": role.role_name},
        children=[
            H.td(role.role_name),
            H.td(role.display_name),
            H.td(role.description or ""),
            H.td(str(user_count), class_="text-end"),
            H.td(str(scope_count), class_="text-end"),
            H.td(
                H.button(
                    EDIT_ICON, class_=btn_cls, hxGet=edit_path, hxTarget="#APP_ROOT", hxSwap="innerHTML"
                ),
                H.button(
                    DEL_ICON,
                    type="button",
                    class_=btn_cls,
                    hxDelete=del_path,
                    hxConfirm=f"Delete role: {html.escape(role.role_name)}?",
                    hxOn__afterOnLoad=H.RAW_STR(reload(ADM_ROLE_LIST_ID, list_path)),
                ),
            ),
        ],
    )


@overload
def RoleList(roles: Iterable[RoleDTO], *, req: Request) -> H: ...


@overload
def RoleList(
    roles: Iterable[RoleDTO], *, req: Request, user_counts: dict[str, int], scope_counts: dict[str, int]
) -> H: ...


def RoleList(
    roles: Iterable[RoleDTO],
    *,
    req: Request,
    user_counts: dict[str, int] | None = None,
    scope_counts: dict[str, int] | None = None,
) -> H:
    user_counts = user_counts or {}
    scope_counts = scope_counts or {}
    tbl_header = ["Role", "Display", "Description", "Users", "Scopes", "-"]
    create_page_path = req.url_for(ADM_CREATE_ROLE_CONTENT).path
    user_path = req.url_for(ADM_USER_LIST_CONTENT).path
    app_path = req.url_for(ADM_APP_LIST_CONTENT).path
    role_path = req.url_for(ADM_ROLE_LIST_CONTENT).path
    scope_path = req.url_for(ADM_SCOPE_LIST_CONTENT).path
    logout_path = req.url_for(AUTH_LOGOUT_API).path

    return H.div(
        id=ADM_ROLE_LIST_ID,
        class_="p-4",
        children=[
            AdminNav(
                user_path=user_path,
                app_path=app_path,
                role_path=role_path,
                scope_path=scope_path,
                active="roles",
                logout_path=logout_path,
            ),
            H.div(
                class_="d-flex mb-2 align-items-center justify-content-between",
                children=[
                    H.h3("Role List"),
                    H.button(
                        "NewRole",
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
                    H.tbody(
                        (
                            RoleRow(
                                r,
                                req=req,
                                user_count=user_counts.get(r.role_name, 0),
                                scope_count=scope_counts.get(r.role_name, 0),
                            )
                            for r in roles
                        )
                    ),
                ],
            ),
        ],
    )


def CreateRoleDialog(
    *,
    req: Request,
    dialog_id: str = ADM_CREATE_ROLE_ID,
    dialog_title: str = "Create Role",
) -> H:
    list_path = str(req.url_for(ADM_ROLE_LIST_CONTENT))
    create_api = str(req.url_for(ADM_CREATE_ROLE_API))
    alert_id = dialog_id + "-alert"

    form_fields = [
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputText(dialog_id, "role_name", "Role", ""),
        InputText(dialog_id, "display_name", "Display", ""),
        InputText(dialog_id, "description", "Description", ""),
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


@overload
def EditRoleDialog(*, req: Request, role: RoleDTO, dialog_id: str = ..., dialog_title: str = ...) -> H: ...


@overload
def EditRoleDialog(
    *,
    req: Request,
    role: RoleDTO,
    user_count: int,
    scope_count: int,
    users: list[str],
    scopes: list[str],
    dialog_id: str = ...,
    dialog_title: str = ...,
) -> H: ...


def EditRoleDialog(
    *,
    req: Request,
    role: RoleDTO,
    user_count: int = 0,
    scope_count: int = 0,
    users: list[str] | None = None,
    scopes: list[str] | None = None,
    dialog_id: str = ADM_EDIT_ROLE_ID,
    dialog_title: str = "Edit Role",
) -> H:
    list_path = str(req.url_for(ADM_ROLE_LIST_CONTENT))
    update_api = str(req.url_for(ADM_UPDATE_ROLE_API))
    alert_id = dialog_id + "-alert"

    users = users or []
    scopes = scopes or []

    form_fields = [
        H.div(
            H.label("Role", class_=["form-label"]),
            H.div(role.role_name, class_=["fw-semibold"]),
            H.input(type="hidden", name="role_name", value=role.role_name),
            class_="mb-3",
        ),
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputText(dialog_id, "display_name", "Display", role.display_name),
        InputText(dialog_id, "description", "Description", role.description or ""),
        H.div(
            H.div(f"Users({user_count})", class_="fw-bold"),
            _badges(users if users else ["(none)"]),
            class_="mb-2",
        ),
        H.div(
            H.div(f"Scopes({scope_count})", class_="fw-bold"),
            _badges(scopes if scopes else ["(none)"]),
            class_="mb-2",
        ),
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
