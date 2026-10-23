import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from scheduler import MonitoringScheduler
from crawler import RegulatoryCrawler
from document_store import DocumentStore


def test_scheduler_lifecycle():
    store = DocumentStore()
    crawler = RegulatoryCrawler(doc_store=store)
    sched = MonitoringScheduler(crawler=crawler)

    # Start scheduler
    sched.start(interval_hours=12, run_immediately=False)
    status = sched.get_status()
    assert status["is_running"] is True
    assert status["interval_hours"] == 12

    # Trigger on demand
    summary = sched.trigger_now()
    assert summary["new_documents_count"] > 0
    assert sched.get_status()["last_crawl_time"] is not None

    # Stop scheduler
    sched.stop()
    assert sched.get_status()["is_running"] is False
