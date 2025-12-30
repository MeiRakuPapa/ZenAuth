import html
from typing import Iterable

from starlette.requests import Request
from zen_auth.dto import UserDTO
from zen_html import H

from .._tmp_lib import (
    BTN_CLS,
    DEL_ICON,
    EDIT_ICON,
    NEXT_PAGE_ICON,
    PREV_PAGE_ICON,
    AdminNav,
    Dialog,
    DlgHeader,
    InputPassword,
    InputText,
    PageNationButton,
    Selector,
    display_alert,
    reload,
)
from ..ui_ids import (
    ADM_CHANGE_PW_ID,
    ADM_CREATE_USER_ID,
    ADM_EDIT_USER_ID,
    ADM_USER_LIST_ID,
)
from ..url_names import (
    ADM_APP_LIST_CONTENT,
    ADM_CHANGE_PW_API,
    ADM_CREATE_USER_API,
    ADM_CREATE_USER_CONTENT,
    ADM_DELETE_USER_API,
    ADM_EDIT_USER_CONTENT,
    ADM_ROLE_LIST_CONTENT,
    ADM_SCOPE_LIST_CONTENT,
    ADM_UPDATE_USER_API,
    ADM_USER_LIST_CONTENT,
    AUTH_LOGOUT_API,
)


def _roles(roles: Iterable[str], role_map: dict[str, str]) -> H:
    return H.div(
        children=(H.span(role_map.get(role, role), class_="badge bg-primary me-1") for role in roles),
        class_="d-flex",
    )


def UserRow(user: UserDTO, *, page: int, req: Request, role_map: dict[str, str]) -> H:
    edit_path = str(
        req.url_for(ADM_EDIT_USER_CONTENT, user_name=user.user_name).include_query_params(page=page)
    )
    del_path = str(req.url_for(ADM_DELETE_USER_API, user_name=user.user_name).include_query_params(page=page))
    user_list_path = str(req.url_for(ADM_USER_LIST_CONTENT).include_query_params(page=page))

    btn_cls = BTN_CLS + ["btn-outline-primary"]

    return H.tr(
        dataset={"id": user.user_name},
        class_=["user-row"],
        children=[
            H.td(user.user_name),
            H.td(user.real_name),
            H.td(user.description),
            H.td(user.division),
            H.td(_roles(user.roles, role_map)),
            H.td(
                H.button(
                    EDIT_ICON, class_=btn_cls, hxGet=edit_path, hxTarget="#APP_ROOT", hxSwap="innerHTML"
                ),
                H.button(
                    DEL_ICON,
                    type="button",
                    class_=btn_cls,
                    hxDelete=del_path,
                    hxConfirm=f"Delete user: {html.escape(user.user_name)}[{html.escape(user.real_name)}]?",
                    hxOn__afterOnLoad=H.RAW_STR(reload(ADM_USER_LIST_ID, user_list_path)),
                ),
            ),
        ],
    )


def UserList(
    users: Iterable[UserDTO], *, req: Request, page: int, num_pages: int, role_map: dict[str, str]
) -> H:
    tbl_header = ["ID", "Name", "Description", "Division", "Roles", "-"]
    create_page_path = req.url_for(ADM_CREATE_USER_CONTENT).path
    user_list_page = req.url_for(ADM_USER_LIST_CONTENT)
    user_path = user_list_page.path
    app_path = req.url_for(ADM_APP_LIST_CONTENT).path
    role_path = req.url_for(ADM_ROLE_LIST_CONTENT).path
    scope_path = req.url_for(ADM_SCOPE_LIST_CONTENT).path
    logout_path = req.url_for(AUTH_LOGOUT_API).path
    prev_page = str(user_list_page.include_query_params(page=(page - 1)))
    next_page = str(user_list_page.include_query_params(page=(page + 1)))
    move_btn_cls = BTN_CLS + ["btn-outline-primary"]
    return H.div(
        id=ADM_USER_LIST_ID,
        class_="p-4",
        children=[
            AdminNav(
                user_path=user_path,
                app_path=app_path,
                role_path=role_path,
                scope_path=scope_path,
                active="users",
                logout_path=logout_path,
            ),
            H.div(
                class_="d-flex mb-2 align-items-center justify-content-between",
                children=[
                    H.h3("User List"),
                    H.button(
                        "NewUser",
                        class_=BTN_CLS + ["btn-primary"],
                        hxGet=create_page_path,
                        hxTarget="#APP_ROOT",
                        hxSwap="innerHTML",
                    ),
                ],
            ),
            H.div(
                class_="mb-2",
                children=[
                    H.table(
                        class_="table table-sm table-striped table-hover user-list-table",
                        children=[
                            H.thead(
                                H.colgroup(*(H.col() for _ in tbl_header)),
                                H.tr(
                                    (H.th(n) for n in tbl_header),
                                ),
                            ),
                            H.tbody((UserRow(u, page=page, req=req, role_map=role_map) for u in users)),
                        ],
                    ),
                    H.div(
                        class_="d-flex justify-content-end align-items-center page pe-4",
                        children=[
                            PageNationButton(
                                PREV_PAGE_ICON,
                                condition=page > 1,
                                target=f"#{ADM_USER_LIST_ID}",
                                path=prev_page,
                                class_=move_btn_cls,
                            ),
                            H.div(f"page: {page}/ {num_pages}", class_=["ms-2", "me-2"]),
                            PageNationButton(
                                NEXT_PAGE_ICON,
                                condition=page < num_pages,
                                target=f"#{ADM_USER_LIST_ID}",
                                path=next_page,
                                class_=move_btn_cls,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def EditUserDialog(
    *,
    req: Request,
    dialog_id: str = ADM_EDIT_USER_ID,
    dialog_title: str = "Edit User",
    user: UserDTO,
    role_map: dict[str, str],
    page: int = 1,
    id_label: str = "ID",
    real_name_label: str = "Real Name",
    division_label: str = "Division",
    description_label: str = "Description",
    roles_label: str = "Roles",
    close_btn_label: str = "Close",
    apply_btn_label: str = "Apply",
    change_pw_btn_label: str = "Change Password",
) -> H:
    user_list_path = str(req.url_for(ADM_USER_LIST_CONTENT).include_query_params(page=page))
    update_user_api = str(req.url_for(ADM_UPDATE_USER_API))
    alert_id = dialog_id + "-alert"
    form_fields = [
        H.div(
            H.label(id_label, class_=["form-label"]),
            H.div(
                H.div(user.user_name, class_=["fw-semibold", "me-2"]),
                H.button(
                    change_pw_btn_label,
                    type="button",
                    class_=BTN_CLS + ["btn-primary"],
                    dataset={"bs-toggle": "modal", "bs-target": "#change-pw-dialog"},
                ),
                class_=["d-flex", "align-items-center"],
            ),
            H.input(type="hidden", name="user_name", value=user.user_name),
            class_="mb-3",
        ),
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputText(dialog_id, "real_name", real_name_label, user.real_name),
        InputText(dialog_id, "division", division_label, user.division),
        InputText(dialog_id, "description", description_label, user.description),
        Selector(dialog_id, "roles", roles_label, role_map, user.roles),
    ]
    close_btn = H.button(
        close_btn_label,
        type="button",
        class_=BTN_CLS + ["btn-secondary", "me-2"],
        hxGet=user_list_path,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
    )
    apply_btn = H.button(
        apply_btn_label,
        type="button",
        class_=BTN_CLS + ["btn-primary"],
        hxPost=update_user_api,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
        hxOn____responseError=display_alert(alert_id),
    )
    dialog_buttons = H.div(close_btn, apply_btn, class_=["d-flex", "me-3"])
    header = DlgHeader(dialog_title)
    body = (H.form(form_fields + [dialog_buttons], autocomplete="off"),)
    return Dialog(dialog_id, header, body)


def CreateUserDialog(
    *,
    req: Request,
    dialog_id: str = ADM_CREATE_USER_ID,
    dialog_title: str = "Create User",
    page: int = 1,
    role_map: dict[str, str],
    id_label: str = "ID",
    real_name_label: str = "Real Name",
    password_label: str = "Password",
    confirm_password_label: str = "Confirm Password",
    division_label: str = "Division",
    description_label: str = "Description",
    roles_label: str = "Roles",
    close_btn_label: str = "Close",
    apply_btn_label: str = "Apply",
) -> H:
    user_list_path = str(req.url_for(ADM_USER_LIST_CONTENT).include_query_params(page=page))
    user_create_api = str(req.url_for(ADM_CREATE_USER_API))
    alert_id = dialog_id + "-alert"
    form_fields = [
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputText(dialog_id, "user_name", id_label, ""),
        InputPassword(dialog_id, "password", password_label, ""),
        InputPassword(dialog_id, "confirm_password", confirm_password_label, ""),
        InputText(dialog_id, "real_name", real_name_label, ""),
        InputText(dialog_id, "division", division_label, ""),
        InputText(dialog_id, "description", description_label, ""),
        Selector(dialog_id, "roles", roles_label, role_map, []),
    ]
    close_btn = H.button(
        close_btn_label,
        type="button",
        class_=BTN_CLS + ["btn-secondary", "me-2"],
        hxGet=user_list_path,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
    )
    apply_btn = H.button(
        apply_btn_label,
        type="button",
        class_=BTN_CLS + ["btn-primary"],
        hxPost=user_create_api,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
        hxOn____responseError=display_alert(alert_id),
    )
    dialog_buttons = H.div(close_btn, apply_btn, class_=["d-flex", "me-3"])
    header = DlgHeader(dialog_title)
    body = (H.form(form_fields + [dialog_buttons], autocomplete="off"),)
    return Dialog(dialog_id, header, body)


def ChangePasswordAdminDialog(
    *,
    req: Request,
    dialog_id: str = ADM_CHANGE_PW_ID,
    dialog_title: str = "Change Password",
    user_name: str,
    page: int = 1,
    password_label: str = "New Password",
    confirm_password_label: str = "Confirm Password",
    close_btn_label: str = "Close",
    apply_btn_label: str = "Apply",
) -> H:
    change_password_api = str(req.url_for(ADM_CHANGE_PW_API))
    edit_user_path = str(
        req.url_for(ADM_EDIT_USER_CONTENT, user_name=user_name).include_query_params(page=page)
    )
    alert_id = dialog_id + "-alert"

    form_fields = [
        H.input(type="hidden", name="user_name", value=user_name),
        H.div(class_="alert alert-danger d-none", id=alert_id),
        InputPassword(dialog_id, "password", password_label, ""),
        InputPassword(dialog_id, "confirm_password", confirm_password_label, ""),
    ]
    close_btn = H.button(
        close_btn_label,
        type="button",
        class_=BTN_CLS + ["btn-secondary", "me-2"],
        hxGet=edit_user_path,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
    )
    apply_btn = H.button(
        apply_btn_label,
        type="button",
        class_=BTN_CLS + ["btn-primary"],
        hxPost=change_password_api,
        hxSwap="innerHTML",
        hxTarget="#APP_ROOT",
        hxOn____responseError=display_alert(alert_id),
    )
    dialog_buttons = H.div(close_btn, apply_btn, class_=["d-flex", "me-3"])
    header = DlgHeader(dialog_title)
    body = H.form(
        form_fields + [dialog_buttons],
        autocomplete="off",
    )

    return Dialog(dialog_id, header, body)
