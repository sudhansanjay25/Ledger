import os
import sys
import pytest
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from database import SessionLocal, MAPRecordModel
from notifier import NotificationService


@pytest.fixture
def notifier_with_test_maps():
    db = SessionLocal()
    # Clean previous records
    db.query(MAPRecordModel).filter(MAPRecordModel.action_id.in_(["MAP-NOTIF-01", "MAP-NOTIF-02"])).delete()

    # Overdue map
    m1 = MAPRecordModel(
        action_id="MAP-NOTIF-01",
        circular_id="circ_notif",
        action="Complete customer KYC re-verification.",
        department=["Compliance"],
        deadline="2026-06-01",
        deadline_type="explicit",
        priority="High",
        obligation_type="REQUIRED",
        source_sentence="KYC re-verification mandatory.",
        status="approved",
        assigned_department="Compliance"
    )
    # Approaching in 5 days
    m2 = MAPRecordModel(
        action_id="MAP-NOTIF-02",
        circular_id="circ_notif",
        action="Submit liquidity coverage ratio report.",
        department=["Finance"],
        deadline="2026-07-20",
        deadline_type="explicit",
        priority="Critical",
        obligation_type="REQUIRED",
        source_sentence="LCR reports must be filed.",
        status="auto_assigned",
        assigned_department="Finance"
    )
    db.add_all([m1, m2])
    db.commit()
    db.close()

    notifier = NotificationService()
    return notifier


def test_notifier_dispatch_alerts(notifier_with_test_maps):
    # Reference date is 2026-07-15:
    # MAP-NOTIF-01 is due 2026-06-01 -> Overdue
    # MAP-NOTIF-02 is due 2026-07-20 -> Due in 5 days (APPROACHING_7D)
    alerts = notifier_with_test_maps.check_and_dispatch_alerts(reference_date_str="2026-07-15")
    
    assert len(alerts) >= 2
    types = {a["alert_type"] for a in alerts if a["action_id"] in ["MAP-NOTIF-01", "MAP-NOTIF-02"]}
    assert "OVERDUE" in types
    assert "APPROACHING_7D" in types


def test_notifier_history_and_filtering(notifier_with_test_maps):
    notifier_with_test_maps.check_and_dispatch_alerts(reference_date_str="2026-07-15")
    
    comp_alerts = notifier_with_test_maps.get_notifications(department="Compliance")
    assert len(comp_alerts) >= 1
    assert comp_alerts[0]["department"] == "Compliance"

    crit_alerts = notifier_with_test_maps.get_notifications(urgency="Critical")
    assert len(crit_alerts) >= 1
    assert any(a["urgency"] == "Critical" for a in crit_alerts)
