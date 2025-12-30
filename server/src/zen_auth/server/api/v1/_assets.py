from zen_html import H

from ...ENV import BOOTSTRAP_CSS, BOOTSTRAP_ICONS_CSS, BOOTSTRAP_JS, HTMX_JS


def default_header_links() -> list[H]:
    return [
        H.link(rel="stylesheet", href=BOOTSTRAP_CSS, crossorigin="anonymous"),
        H.link(rel="stylesheet", href=BOOTSTRAP_ICONS_CSS, crossorigin="anonymous"),
        H.script(src=HTMX_JS),
    ]


def default_body_links() -> list[H]:
    return [
        H.script(src=BOOTSTRAP_JS, crossorigin="anonymous"),
    ]
