import uuid

from app.core.logging import request_id_ctx


def get_request_id() -> str:
    """Retrieves the request ID for the current context, generating a new one if missing."""
    rid = request_id_ctx.get()
    if not rid:
        rid = str(uuid.uuid4())
        request_id_ctx.set(rid)
    return rid


def set_request_id(rid: str) -> None:
    """Explicitly updates the request ID context variable."""
    request_id_ctx.set(rid)


def clear_request_id() -> None:
    """Resets the request ID context to empty."""
    request_id_ctx.set("")
