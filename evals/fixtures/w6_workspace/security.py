# Permission demo
ROLE_PERMISSIONS = {
    "reader": {"read"},
    "admin": {"read", "delete"},
}

def can_execute(role, action):
    return action in ROLE_PERMISSIONS.get(role, set())

def delete_document(role):
    if not can_execute(role, "delete"):
        raise PermissionError("forbidden")
    return "deleted"
