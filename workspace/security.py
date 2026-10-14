"""A tiny sample for exploring permission decisions."""

ROLE_PERMISSIONS = {
    "reader": {"read"},
    "editor": {"read", "write"},
    "admin": {"read", "write", "delete"},
}


def can_execute(role: str, action: str) -> bool:
    """Deny unknown roles and unknown actions by default."""
    allowed = ROLE_PERMISSIONS.get(role, set())
    return action in allowed


def delete_document(role: str, doc_id: str) -> str:
    if not can_execute(role, "delete"):
        raise PermissionError(f"{role!r} cannot delete document {doc_id}")
    # Demo only; no data is actually deleted.
    return f"Would delete {doc_id}"
