import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from crawler import RegulatoryCrawler
from document_store import DocumentStore


def test_crawler_initial_cycle():
    fresh_store = DocumentStore()
    crawler = RegulatoryCrawler(doc_store=fresh_store)

    summary = crawler.crawl_portals(force_live=False)
    assert summary["new_documents_count"] > 0
    assert summary["duplicates_count"] == 0
    assert len(summary["sources_checked"]) == 4
    assert fresh_store.count() == summary["new_documents_count"]


def test_crawler_subsequent_cycle_skips_duplicates():
    fresh_store = DocumentStore()
    crawler = RegulatoryCrawler(doc_store=fresh_store)

    # First crawl registers circulars
    crawler.crawl_portals(force_live=False)
    initial_count = fresh_store.count()

    # Second crawl should detect all as duplicates
    second_summary = crawler.crawl_portals(force_live=False)
    assert second_summary["new_documents_count"] == 0
    assert second_summary["duplicates_count"] == initial_count
    assert fresh_store.count() == initial_count
