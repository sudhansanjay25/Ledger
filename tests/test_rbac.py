import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from rbac import (
    UserRole, Permission, has_permission, can_access_map
)


def test_rbac_admin_permissions():
    assert has_permission(UserRole.ADMIN, Permission.APPROVE_MAP) is True
    assert has_permission(UserRole.ADMIN, Permission.REJECT_MAP) is True
    assert has_permission(UserRole.ADMIN, Permission.EDIT_MAP) is True
    assert has_permission(UserRole.ADMIN, Permission.TRIGGER_CRAWLER) is True
    assert has_permission(UserRole.ADMIN, Permission.MANAGE_USERS) is True


def test_rbac_compliance_head_permissions():
    assert has_permission(UserRole.COMPLIANCE_HEAD, Permission.APPROVE_MAP) is True
    assert has_permission(UserRole.COMPLIANCE_HEAD, Permission.REJECT_MAP) is True
    assert has_permission(UserRole.COMPLIANCE_HEAD, Permission.EDIT_MAP) is True
    assert has_permission(UserRole.COMPLIANCE_HEAD, Permission.VIEW_AUDIT_LOGS) is True
    assert has_permission(UserRole.COMPLIANCE_HEAD, Permission.MANAGE_USERS) is False


def test_rbac_department_head_permissions():
    assert has_permission(UserRole.DEPARTMENT_HEAD, Permission.VIEW_ASSIGNED_MAPS) is True
    assert has_permission(UserRole.DEPARTMENT_HEAD, Permission.APPROVE_MAP) is False
    assert has_permission(UserRole.DEPARTMENT_HEAD, Permission.REJECT_MAP) is False
    assert has_permission(UserRole.DEPARTMENT_HEAD, Permission.TRIGGER_CRAWLER) is False


def test_rbac_auditor_permissions():
    assert has_permission(UserRole.AUDITOR, Permission.VIEW_ALL_MAPS) is True
    assert has_permission(UserRole.AUDITOR, Permission.VIEW_AUDIT_LOGS) is True
    assert has_permission(UserRole.AUDITOR, Permission.APPROVE_MAP) is False
    assert has_permission(UserRole.AUDITOR, Permission.EDIT_MAP) is False


def test_department_head_tenancy_isolation():
    it_map = {
        "action_id": "MAP-01",
        "assigned_department": "IT",
        "department": ["IT"]
    }
    ops_map = {
        "action_id": "MAP-02",
        "assigned_department": "Operations",
        "department": ["Operations"]
    }

    # IT Head can access IT MAP, but not Operations MAP
    assert can_access_map(UserRole.DEPARTMENT_HEAD, "IT", it_map) is True
    assert can_access_map(UserRole.DEPARTMENT_HEAD, "IT", ops_map) is False

    # Compliance Head and Auditor can access both
    assert can_access_map(UserRole.COMPLIANCE_HEAD, None, ops_map) is True
    assert can_access_map(UserRole.AUDITOR, None, it_map) is True
