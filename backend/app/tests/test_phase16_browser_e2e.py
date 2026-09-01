"""Phase 16: Real Google Chrome Browser E2E Test Suite for SAT-SA."""
import os
import time
import uuid
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.models import CSE, Asset, Finding, ReportSnapshot, ReportType, AssetCriticality, FindingSeverity, FindingStatus
from app.reporting.builder import ReportBuilder
from app.reporting.schemas import ReportGenerateRequest
from app.evaluation.phase16_browser_e2e_runner import LiveServer, seed_operational_e2e_data

client = TestClient(app)
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def test_phase16_browser_environment_detection():
    """Verify local Google Chrome binary availability."""
    assert os.path.exists(CHROME_PATH), f"Google Chrome binary not found at {CHROME_PATH}"


def test_phase16_spa_static_serving():
    """Verify FastAPI single-origin static mount serves compiled React frontend."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "<!doctype html>" in resp.text.lower()
    assert '<div id="root">' in resp.text.lower()


def test_phase16_browser_startup_and_airgap_badge():
    """Verify genuine Google Chrome launches, navigates to SAT-SA, and renders airgap badge."""
    server = LiveServer(host="127.0.0.1", port=8895)
    server.start()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True)
            page = browser.new_page()
            page.goto("http://127.0.0.1:8895/", wait_until="domcontentloaded")
            page.wait_for_selector("header", timeout=5000)

            header_text = page.locator("header").text_content()
            assert "SAT-SA" in header_text or "SUPERVISORY" in header_text.upper()

            airgap_el = page.locator("text=STRICT_LOCAL_ONLY").first
            assert airgap_el.is_visible()
            browser.close()
    finally:
        server.stop()


def test_phase16_browser_report_generation_and_audit():
    """Verify report generation, drawer viewing, and cryptographic audit verification in Chrome."""
    db = SessionLocal()
    try:
        seed_operational_e2e_data(db)
    finally:
        db.close()

    server = LiveServer(host="127.0.0.1", port=8896)
    server.start()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True)
            page = browser.new_page()
            page.goto("http://127.0.0.1:8896/", wait_until="domcontentloaded")

            # Navigate to Reports
            page.click("button:has-text('REPORTS & AUDIT TRAIL')")
            page.wait_for_selector("text=Supervisory Reporting & Cryptographic Audit Ledger", timeout=5000)

            # Generate Report
            page.click("button:has-text('Generate Report')")
            page.wait_for_selector("h3:has-text('Generate Assessment Report Snapshot')", timeout=4000)

            unique_title = f"Pytest Browser Executive Audit {uuid.uuid4().hex[:6]}"
            page.locator("div.fixed input[type='text']").first.fill(unique_title)
            with page.expect_response(lambda res: "/api/v1/reports/generate" in res.url, timeout=10000):
                page.locator("div.fixed button[type='submit']").click()

            page.wait_for_selector(f"text={unique_title}", timeout=8000)

            # Open Detail Drawer
            with page.expect_response(lambda res: "/api/v1/reports/" in res.url and "export" not in res.url and "generate" not in res.url, timeout=10000):
                page.locator(f"tr:has-text('{unique_title}') button:has-text('View')").first.click()

            page.wait_for_selector("text=Executive Overview", timeout=5000)
            page.wait_for_selector("text=Verified", timeout=5000)

            # Close Drawer
            page.locator("button:has(svg.lucide-x)").first.click()

            # Switch to Audit Tab & Verify Integrity
            page.locator("button:has-text('Audit Trail (')").click()
            page.wait_for_selector("text=REPORT_GENERATED", timeout=8000)

            with page.expect_response(lambda res: "/api/v1/audit/verify" in res.url, timeout=10000):
                page.locator("button:has-text('Verify Audit Integrity')").click()

            page.wait_for_selector("button:has-text('Dismiss')", timeout=8000)

            browser.close()
    finally:
        server.stop()


def test_phase16_browser_tamper_detection_ui():
    """Verify tamper detection visual badge in browser when report content is altered in DB."""
    db = SessionLocal()
    tamper_title = f"Pytest Tamper Target {uuid.uuid4().hex[:6]}"
    try:
        meta = seed_operational_e2e_data(db)
        req = ReportGenerateRequest(
            assessment_id=meta["run_id"],
            report_type=ReportType.TECHNICAL,
            title=tamper_title,
            generated_by="PYTEST_EXAMINER"
        )
        snap = ReportBuilder.generate_report(db, req)
        snap.content_json = {"tampered": True, "fake": "unauthorized"}
        db.commit()
    finally:
        db.close()

    server = LiveServer(host="127.0.0.1", port=8897)
    server.start()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True)
            page = browser.new_page()
            page.goto("http://127.0.0.1:8897/", wait_until="domcontentloaded")

            page.click("button:has-text('REPORTS & AUDIT TRAIL')")
            page.wait_for_selector(f"text={tamper_title}", timeout=8000)

            with page.expect_response(lambda res: "/api/v1/reports/" in res.url and "export" not in res.url and "generate" not in res.url, timeout=10000):
                page.locator(f"tr:has-text('{tamper_title}') button:has-text('View')").first.click()

            page.wait_for_selector("text=Tampered", timeout=8000)
            browser.close()
    finally:
        server.stop()
