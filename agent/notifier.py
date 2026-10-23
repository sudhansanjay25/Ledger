from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from database import SessionLocal, MAPRecordModel


class NotificationService:
    """
    Compliance Alert and Notification Service.
    Monitors deadlines across active MAPs and dispatches alerts
    to department Slack channels and email lists.
    """

    def __init__(self):
        self._notification_log: List[Dict[str, Any]] = []

    def check_and_dispatch_alerts(self, reference_date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scans all non-completed MAPs and creates alerts for:
          - Overdue mandates
          - Approaching deadlines (within 7 days)
          - Imminent deadlines (within 24 hours)
        """
        if reference_date_str:
            try:
                ref_dt = datetime.strptime(reference_date_str, "%Y-%m-%d")
            except Exception:
                ref_dt = datetime.utcnow()
        else:
            ref_dt = datetime.utcnow()

        dispatched = []
        db = SessionLocal()
        try:
            active_maps = (
                db.query(MAPRecordModel)
                .filter(MAPRecordModel.status.in_(["auto_assigned", "approved", "pending_approval"]))
                .all()
            )

            for item in active_maps:
                deadline_str = item.deadline
                if not deadline_str or deadline_str == "None":
                    continue

                try:
                    due_dt = datetime.strptime(deadline_str, "%Y-%m-%d")
                except Exception:
                    continue

                diff = (due_dt - ref_dt).days

                alert_type = None
                urgency = "Medium"
                message = ""

                if diff < 0:
                    alert_type = "OVERDUE"
                    urgency = "Critical"
                    message = f"MANDATE OVERDUE: Action '{item.action_id}' was due on {deadline_str} ({abs(diff)} days ago). Immediate escalation required."
                elif diff <= 1:
                    alert_type = "IMMINENT_24H"
                    urgency = "Critical"
                    message = f"URGENT: Action '{item.action_id}' is due in 24 hours ({deadline_str})."
                elif diff <= 7:
                    alert_type = "APPROACHING_7D"
                    urgency = "High"
                    message = f"Action '{item.action_id}' is due within {diff} days ({deadline_str})."

                if alert_type:
                    notification = {
                        "id": f"NOTIF-{len(self._notification_log)+1:04d}",
                        "action_id": item.action_id,
                        "department": item.assigned_department or "Operations",
                        "priority": item.priority,
                        "alert_type": alert_type,
                        "urgency": urgency,
                        "days_remaining": diff,
                        "deadline": deadline_str,
                        "channel": f"#{item.assigned_department.lower() if item.assigned_department else 'compliance'}-alerts",
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    self._notification_log.append(notification)
                    dispatched.append(notification)

            return dispatched
        finally:
            db.close()

    def get_notifications(
        self,
        department: Optional[str] = None,
        urgency: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieves history of dispatched compliance notifications."""
        results = list(reversed(self._notification_log))
        if department:
            results = [n for n in results if n.get("department") == department]
        if urgency:
            results = [n for n in results if n.get("urgency") == urgency]
        return results[:limit]


# Global notification service instance
NOTIFIER = NotificationService()
