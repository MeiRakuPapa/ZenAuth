from logging import StreamHandler, getLogger

from .formatter import AuditFormatter

LOGGER = getLogger("zen_auth")
AUDIT_LOGGER = getLogger("zen_auth.audit")

handler = StreamHandler()
handler.setFormatter(AuditFormatter())
AUDIT_LOGGER.addHandler(handler)
AUDIT_LOGGER.setLevel("INFO")
AUDIT_LOGGER.propagate = False
