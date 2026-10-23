from functools import wraps
from typing import List, Optional, Dict, Any, Callable
from flask import request, jsonify


class UserRole:
    ADMIN = "admin"
    COMPLIANCE_HEAD = "compliance_head"
    DEPARTMENT_HEAD = "department_head"
    AUDITOR = "auditor"

    ALL_ROLES = [ADMIN, COMPLIANCE_HEAD, DEPARTMENT_HEAD, AUDITOR]


class Permission:
    VIEW_ALL_MAPS = "view_all_maps"
    VIEW_ASSIGNED_MAPS = "view_assigned_maps"
    APPROVE_MAP = "approve_map"
    REJECT_MAP = "reject_map"
    EDIT_MAP = "edit_map"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    TRIGGER_CRAWLER = "trigger_crawler"
    SYNC_JIRA = "sync_jira"
    MANAGE_USERS = "manage_users"


ROLE_PERMISSIONS: Dict[str, set] = {
    UserRole.ADMIN: {
        Permission.VIEW_ALL_MAPS,
        Permission.VIEW_ASSIGNED_MAPS,
        Permission.APPROVE_MAP,
        Permission.REJECT_MAP,
        Permission.EDIT_MAP,
        Permission.VIEW_AUDIT_LOGS,
        Permission.TRIGGER_CRAWLER,
        Permission.SYNC_JIRA,
        Permission.MANAGE_USERS,
    },
    UserRole.COMPLIANCE_HEAD: {
        Permission.VIEW_ALL_MAPS,
        Permission.VIEW_ASSIGNED_MAPS,
        Permission.APPROVE_MAP,
        Permission.REJECT_MAP,
        Permission.EDIT_MAP,
        Permission.VIEW_AUDIT_LOGS,
        Permission.TRIGGER_CRAWLER,
        Permission.SYNC_JIRA,
    },
    UserRole.DEPARTMENT_HEAD: {
        Permission.VIEW_ASSIGNED_MAPS,
    },
    UserRole.AUDITOR: {
        Permission.VIEW_ALL_MAPS,
        Permission.VIEW_ASSIGNED_MAPS,
        Permission.VIEW_AUDIT_LOGS,
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Checks whether a given role holds the requested permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms


def can_access_map(role: str, user_department: Optional[str], map_data: Dict[str, Any]) -> bool:
    """
    Evaluates multi-tenant / department tenancy boundaries:
    - Admin, Compliance Head, Auditor can view all MAPs.
    - Department Heads can only view MAPs assigned to their specific department.
    """
    if role in [UserRole.ADMIN, UserRole.COMPLIANCE_HEAD, UserRole.AUDITOR]:
        return True

    if role == UserRole.DEPARTMENT_HEAD:
        assigned = map_data.get("assigned_department") or ""
        target_depts = map_data.get("department") or []
        if isinstance(target_depts, str):
            target_depts = [target_depts]
        return (user_department and (user_department == assigned or user_department in target_depts))

    return False


def get_current_user_context() -> Dict[str, Any]:
    """
    Extracts user identity from HTTP headers:
    - X-User-Role: admin | compliance_head | department_head | auditor (default: compliance_head)
    - X-User-Id: e.g. 'compliance_lead'
    - X-User-Department: e.g. 'IT'
    """
    role = request.headers.get("X-User-Role", UserRole.COMPLIANCE_HEAD)
    if role not in UserRole.ALL_ROLES:
        role = UserRole.COMPLIANCE_HEAD

    user_id = request.headers.get("X-User-Id", f"user_{role}")
    dept = request.headers.get("X-User-Department", None)

    return {
        "role": role,
        "user_id": user_id,
        "department": dept
    }


def require_permission(permission: str):
    """Flask route decorator enforcing specific RBAC permission."""
    def decorator(f: Callable):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user_context()
            if not has_permission(user["role"], permission):
                return jsonify({
                    "error": "Forbidden",
                    "message": f"Role '{user['role']}' does not possess permission '{permission}'."
                }), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
