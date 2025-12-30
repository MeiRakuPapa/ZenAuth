from starlette.requests import Request
from zen_html import H

from .._assets import default_header_links
from .._tmp_lib import (
    BTN_CLS,
    Dialog,
    DlgHeader,
    HtmlDocument,
    InputPassword,
    InputText,
    display_alert,
)
from ..ui_ids import AUTH_CHANGE_PW_ID, AUTH_LOGIN_ID
from ..url_names import (
    ADM_HELPER_JS_PATH,
    AUTH_CANCEL_API,
    AUTH_CHANGE_PW_API,
    AUTH_LOGIN_API,
)


def NotFoundPage(*, req: Request, title: str = "Not Found", message: str) -> H:
    _ = req
    return HtmlDocument(
        H.div(
            H.div(
                H.h2(title),
                H.p(message, class_="mb-0"),
                class_="p-4 border rounded",
            ),
            class_=["d-flex", "justify-content-center", "align-items-center", "vh-100"],
        ),
        title=title,
    )


def LoginPage(
    *,
    req: Request,
    dialog_id: str = AUTH_LOGIN_ID,
    dialog_title: str = "Login",
    user_id_label: str = "User ID",
    password_label: str = "Password",
    login_btn_label: str = "Login",
    close_btn_label: str = "Close",
) -> H:
    alert_id = dialog_id + "-alert"
    login_api = str(req.url_for(AUTH_LOGIN_API))
    cancel_api = str(req.url_for(AUTH_CANCEL_API))
    login_content = Dialog(
        dialog_id,
        DlgHeader(dialog_title),
        H.form(
            H.div(class_="alert alert-danger d-none", id=alert_id),
            InputText(dialog_id, "user_name", user_id_label, "", autocomplete="off"),
            InputPassword(dialog_id, "password", password_label, "", autocomplete="off"),
            H.div(
                CancelBtn(close_btn_label, cancel_api),
                ApplyBtn(login_btn_label, alert_id, login_api),
                class_=["d-flex", "me-3", "justify-content-center"],
            ),
            autocomplete="off",
        ),
    )
    return HtmlDocument(
        H.div(
            login_content,
            class_=["d-flex", "justify-content-center", "align-items-center", "vh-100"],
        ),
        title=dialog_title,
        header_links=default_header_links() + [H.script(src=req.url_for(ADM_HELPER_JS_PATH))],
    )


def ChangePasswordPage(
    *,
    req: Request,
    dialog_id: str = AUTH_CHANGE_PW_ID,
    dialog_title: str = "Change Password",
    user_name: str,
    current_password_label: str = "Current Password",
    password_label: str = "New Password",
    confirm_password_label: str = "Confirm Password",
    close_btn_label: str = "Close",
    apply_btn_label: str = "Apply",
) -> H:
    change_password_api = str(req.url_for(AUTH_CHANGE_PW_API))
    return_to = str(req.url_for(AUTH_CANCEL_API))
    alert_id = dialog_id + "-alert"

    change_password_content = Dialog(
        dialog_id,
        DlgHeader(dialog_title),
        H.form(
            H.input(type="hidden", name="user_name", value=user_name),
            H.div(class_="alert alert-danger d-none", id=alert_id),
            InputPassword(dialog_id, "current_password", current_password_label, ""),
            InputPassword(dialog_id, "password", password_label, ""),
            InputPassword(dialog_id, "confirm_password", confirm_password_label, ""),
            H.div(
                CancelBtn(close_btn_label, return_to),
                ApplyBtn(apply_btn_label, alert_id, change_password_api),
                class_=["d-flex", "me-3"],
            ),
            autocomplete="off",
        ),
    )
    return HtmlDocument(
        H.div(
            change_password_content,
            class_=["d-flex", "justify-content-center", "align-items-center", "vh-100"],
        ),
        title="Login",
    )


def ApplyBtn(apply_label: str, alert_id: str, url: str) -> H:
    return H.button(
        apply_label,
        type="button",
        class_=BTN_CLS + ["btn-primary"],
        hxPost=url,
        hxSwap="none",
        hxOn____responseError=display_alert(alert_id),
    )


def CancelBtn(cancel_label: str, url: str) -> H:
    return H.button(
        cancel_label,
        type="button",
        class_=BTN_CLS + ["btn-secondary", "me-2"],
        hxGet=url,
        hxSwap="none",
        tabindex="0",
    )
