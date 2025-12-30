import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, cast


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class AuditFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, timezone(timedelta(hours=9))).isoformat(
            timespec="milliseconds"
        )

        log_data: dict[str, object] = {
            "ts": ts,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        request = getattr(record, "request", None)
        if request:
            log_data.update(
                {
                    "req_id": getattr(request.state, "req_id", "--"),
                    "path": request.url.path,
                    "method": request.method,
                    "ip": request.client.host if request.client else "--",
                    "ua": request.headers.get("user-agent", "--"),
                    "url": str(request.url),
                }
            )

        # Token timestamps can be useful for ops, but may be noisy and can
        # reveal session timing. Make this opt-in.
        token = cast(dict[str, Any] | None, getattr(record, "token", None))
        include_token_ts = _env_bool("ZENAUTH_AUDIT_INCLUDE_TOKEN_TIMESTAMPS", default=False)
        if include_token_ts and token:
            log_data.update({"token_iat": token.get("iat"), "token_exp": token.get("exp")})

        log_data["user_name"] = getattr(record, "user_name", "--")
        log_data["result"] = getattr(record, "result", "--")
        # required_context: authorization context such as role/scope
        required_context = getattr(record, "required_context", None)
        if required_context is not None:
            log_data["required_context"] = required_context

        return json.dumps({k: v for k, v in log_data.items() if v is not None}, ensure_ascii=False)
