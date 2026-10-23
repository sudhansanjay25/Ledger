import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from jira_integration import MockJiraClient


def test_jira_create_issue():
    jira = MockJiraClient(project_key="TEST")
    issue = jira.create_issue(
        action_id="MAP-JIRA-01",
        summary="Implement MFA for digital banking",
        description="Full text description of requirements",
        department="IT",
        priority="Critical",
        due_date="2026-12-31"
    )
    assert issue["key"].startswith("TEST-")
    assert issue["status"] == "To Do"
    assert issue["priority"] == "Highest"
    assert issue["department"] == "IT"
    assert issue["due_date"] == "2026-12-31"


def test_jira_get_and_transition_issue():
    jira = MockJiraClient(project_key="TEST")
    issue = jira.create_issue(
        action_id="MAP-JIRA-02",
        summary="Establish fraud monitoring system",
        description="Real-time monitoring requirement",
        department="Operations",
        priority="High"
    )
    key = issue["key"]

    retrieved = jira.get_issue(key)
    assert retrieved is not None
    assert retrieved["action_id"] == "MAP-JIRA-02"

    by_action = jira.get_issue_by_action_id("MAP-JIRA-02")
    assert by_action is not None
    assert by_action["key"] == key

    updated = jira.transition_issue(key, "In Progress")
    assert updated["status"] == "In Progress"


def test_jira_list_filtering():
    jira = MockJiraClient(project_key="TEST")
    jira.create_issue("MAP-01", "Task 1", "Desc", "IT")
    jira.create_issue("MAP-02", "Task 2", "Desc", "Operations")

    it_issues = jira.list_issues(department="IT")
    assert len(it_issues) == 1
    assert it_issues[0]["action_id"] == "MAP-01"

    ops_issues = jira.list_issues(department="Operations")
    assert len(ops_issues) == 1
    assert ops_issues[0]["action_id"] == "MAP-02"
