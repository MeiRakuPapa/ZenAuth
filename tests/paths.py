from __future__ import annotations

API_PREFIX = "/zen_auth/v1"

AUTH_EXAMPLE_HTTP = "http://auth.example"
AUTH_EXAMPLE_HTTPS = "https://auth.example.com"


def api_path(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return f"{API_PREFIX}{path}"


def auth_example_url(path: str, *, https: bool = False) -> str:
    base = AUTH_EXAMPLE_HTTPS if https else AUTH_EXAMPLE_HTTP
    return base + api_path(path)
