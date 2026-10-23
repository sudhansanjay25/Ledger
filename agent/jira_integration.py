from datetime import datetime
from typing import Dict, Any, List, Optional


class MockJiraClient:
    """
    Mock Jira API Client for enterprise compliance task synchronization.
    Simulates Atlassian Jira issue creation, status transitions, and queries.
    """

    def __init__(self, project_key: str = "COMP"):
        self.project_key = project_key
        self._counter = 1000
        self._issues: Dict[str, Dict[str, Any]] = {}

    def create_issue(
        self,
        action_id: str,
        summary: str,
        description: str,
        department: str,
        priority: str = "Medium",
        due_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new Jira issue linked to an action ID."""
        self._counter += 1
        issue_key = f"{self.project_key}-{self._counter}"

        # Map Ledger priority to Jira priority
        jira_priority_map = {
            "Critical": "Highest",
            "High": "High",
            "Medium": "Medium",
            "Low": "Low"
        }
        jira_priority = jira_priority_map.get(priority, "Medium")

        issue = {
            "key": issue_key,
            "action_id": action_id,
            "summary": summary[:255],
            "description": description,
            "department": department,
            "status": "To Do",
            "priority": jira_priority,
            "due_date": due_date if due_date and due_date != "None" else None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        self._issues[issue_key] = issue
        return issue

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves an issue by key."""
        return self._issues.get(issue_key)

    def get_issue_by_action_id(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Finds issue linked to an action ID."""
        for issue in self._issues.values():
            if issue.get("action_id") == action_id:
                return issue
        return None

    def list_issues(
        self,
        department: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists issues with optional filtering."""
        results = list(self._issues.values())
        if department:
            results = [i for i in results if i.get("department") == department]
        if status:
            results = [i for i in results if i.get("status") == status]
        return results

    def transition_issue(self, issue_key: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Transitions issue to a new status (e.g. 'In Progress', 'Done')."""
        issue = self._issues.get(issue_key)
        if not issue:
            return None

        issue["status"] = new_status
        issue["updated_at"] = datetime.utcnow().isoformat()
        return issue


# Global Jira integration instance
JIRA = MockJiraClient()
