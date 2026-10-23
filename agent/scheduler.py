from datetime import datetime
from typing import Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from crawler import MONITORING_CRAWLER, RegulatoryCrawler


class MonitoringScheduler:
    """
    Manages periodic background crawling tasks for regulatory portals
    using APScheduler.
    """

    def __init__(self, crawler: Optional[RegulatoryCrawler] = None):
        self.crawler = crawler or MONITORING_CRAWLER
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running: bool = False
        self.interval_hours: int = 6
        self.last_run_summary: Optional[Dict[str, Any]] = None

    def _scheduled_crawl_job(self):
        """Internal execution job triggered on schedule."""
        self.last_run_summary = self.crawler.crawl_portals()

    def start(self, interval_hours: int = 6, run_immediately: bool = True):
        """Starts the background scheduler."""
        if self.is_running and self.scheduler and self.scheduler.running:
            return

        self.interval_hours = interval_hours
        self.scheduler = BackgroundScheduler(daemon=True)
        self.scheduler.add_job(
            func=self._scheduled_crawl_job,
            trigger=IntervalTrigger(hours=interval_hours),
            id="regulatory_portal_crawler_job",
            name="Regulatory Portal Monitoring Job",
            replace_existing=True
        )
        self.scheduler.start()
        self.is_running = True

        if run_immediately:
            self._scheduled_crawl_job()

    def stop(self):
        """Stops the background scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self.is_running = False

    def trigger_now(self) -> Dict[str, Any]:
        """Triggers an on-demand crawl cycle immediately."""
        summary = self.crawler.crawl_portals()
        self.last_run_summary = summary
        return summary

    def get_status(self) -> Dict[str, Any]:
        """Returns scheduler state, intervals, and execution logs."""
        next_run = None
        if self.scheduler and self.scheduler.running:
            job = self.scheduler.get_job("regulatory_portal_crawler_job")
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()

        return {
            "is_running": self.is_running,
            "interval_hours": self.interval_hours,
            "last_crawl_time": self.crawler.last_crawl_time,
            "next_scheduled_run": next_run,
            "last_summary": self.last_run_summary,
            "crawl_history_count": len(self.crawler.crawl_history),
            "catalog_document_count": self.crawler.doc_store.count()
        }


# Global scheduler instance
CRAWLER_SCHEDULER = MonitoringScheduler()
