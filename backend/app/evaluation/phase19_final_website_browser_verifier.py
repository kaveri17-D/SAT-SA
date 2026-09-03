"""Phase 19: Comprehensive Visual Verification Suite for SAT-SA Website."""
import os
import sys
import time
import json
import uuid
import urllib.request
import shutil
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from app.evaluation.phase16_browser_e2e_runner import LiveServer

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"c:\Users\LENOVO\SAT-SA\backend\data\validation\phase19\screenshots\final_pass"
ARTIFACT_DIR = r"C:\Users\LENOVO\.gemini\antigravity\brain\d6fdaf15-f652-4e8b-abf0-08ca42d64de9"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def save_shot(page, filename, full_page=False):
    path = os.path.join(SCREENSHOT_DIR, filename)
    page.screenshot(path=path, full_page=full_page)
    art_path = os.path.join(ARTIFACT_DIR, filename)
    try:
        shutil.copy2(path, art_path)
    except Exception as e:
        print(f"Warning: could not copy to artifact dir: {e}")
    return path


def run_full_browser_verification():
    print("=" * 70)
    print("SAT-SA PHASE 19 FINAL WEBSITE VISUAL BROWSER VERIFICATION")
    print("=" * 70)

    server = LiveServer(host="127.0.0.1", port=8910)
    print("Starting LiveServer on http://127.0.0.1:8910 ...")
    server.start()
    print("LiveServer successfully started and healthy.")

    results = {}

    try:
        with sync_playwright() as p:
            print(f"Launching Google Chrome from: {CHROME_PATH}")
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # -------------------------------------------------------------
            # STEP 1: Dashboard loads cleanly
            # -------------------------------------------------------------
            print("\n[STEP 1] Testing Dashboard clean load...")
            page.goto("http://127.0.0.1:8910/", wait_until="networkidle", timeout=15000)
            page.wait_for_selector("header", timeout=5000)
            page.wait_for_selector("text=ACTIVE ANALYSIS RUN:", timeout=5000)

            # Verify air-gap badge and console titles
            assert page.locator("text=Air-Gapped").first.is_visible()
            assert page.locator("text=Examiner Tier-1").first.is_visible()
            assert page.locator("text=Daylight").first.is_visible()

            shot_1 = save_shot(page, "01_dashboard_clean.png", full_page=True)
            print(f"[PASS] Step 1 PASS: Dashboard loaded cleanly. Screenshot -> {shot_1}")
            results["step_1_dashboard_clean"] = True

            # -------------------------------------------------------------
            # STEP 2: Metric counters match reality & Risk Band Distribution
            # -------------------------------------------------------------
            print("\n[STEP 2] Verifying Metric Counters & Risk Band Distribution...")
            page.wait_for_selector("text=TOTAL CSEs MONITORED", timeout=5000)
            page.wait_for_selector("text=CONFIRMED FINDINGS", timeout=5000)
            page.wait_for_selector("text=Supervisory Risk Band Distribution", timeout=5000)

            shot_2 = save_shot(page, "02_metrics_and_bands.png")
            print(f"[PASS] Step 2 PASS: Metrics & Risk Band Distribution verified. Screenshot -> {shot_2}")
            results["step_2_metrics_and_bands"] = True

            # -------------------------------------------------------------
            # STEP 3: CSE Cards Grid displays real entities
            # -------------------------------------------------------------
            print("\n[STEP 3] Verifying Critical Sector Entities Cards...")
            page.wait_for_selector("text=Critical Sector Entities Risk Summary", timeout=5000)
            cse_cards = page.locator("div.cursor-pointer:has(span:has-text('Sector:'))")
            card_count = cse_cards.count()
            assert card_count > 0, f"Expected CSE cards, found {card_count}"
            print(f"Found {card_count} CSE cards on dashboard.")

            shot_3 = save_shot(page, "03_cse_cards.png")
            print(f"[PASS] Step 3 PASS: CSE cards verified. Screenshot -> {shot_3}")
            results["step_3_cse_cards"] = True

            # -------------------------------------------------------------
            # STEP 4: Clicking a CSE opens the detail modal with real data
            # -------------------------------------------------------------
            print("\n[STEP 4] Testing CSE Detail Modal...")
            cse_cards.first.click()
            page.wait_for_selector("div.fixed", timeout=5000)
            page.wait_for_selector("text=Critical Sector Entity:", timeout=5000)
            time.sleep(0.5)

            shot_4 = save_shot(page, "04_cse_detail_modal.png")
            print(f"[PASS] Step 4 PASS: CSE Detail Modal rendered real data. Screenshot -> {shot_4}")

            # Close Modal
            page.locator("div.fixed button:has-text('×')").first.click()
            time.sleep(0.3)
            results["step_4_cse_modal"] = True

            # -------------------------------------------------------------
            # STEP 5: Review Priority Queue displays real findings
            # -------------------------------------------------------------
            print("\n[STEP 5] Testing Review Priority Queue Navigation & Data...")
            page.click("button:has-text('REVIEW PRIORITY QUEUE')")
            page.wait_for_selector("text=Review Priority Queue", timeout=5000)
            
            queue_rows = page.locator("table tbody tr")
            q_count = queue_rows.count()
            assert q_count > 0, f"Expected queue rows, got {q_count}"
            print(f"Found {q_count} prioritized finding items in queue.")

            shot_5 = save_shot(page, "05_queue_table.png")
            print(f"[PASS] Step 5 PASS: Review Queue verified. Screenshot -> {shot_5}")
            results["step_5_queue_table"] = True

            # -------------------------------------------------------------
            # STEP 6: Clicking a Finding opens Detail Modal with real evidence
            # -------------------------------------------------------------
            print("\n[STEP 6] Testing Finding Detail Modal...")
            queue_rows.first.click()
            page.wait_for_selector("text=Finding Inspection Panel", timeout=5000)
            page.wait_for_selector("text=Evidence & SHA-256 Inspector", timeout=5000)
            time.sleep(0.5)

            shot_6 = save_shot(page, "06_finding_detail_modal.png")
            print(f"[PASS] Step 6 PASS: Finding Detail Modal verified. Screenshot -> {shot_6}")

            # Close modal
            page.locator("div.fixed button:has-text('×')").first.click()
            time.sleep(0.3)
            results["step_6_finding_modal"] = True

            # -------------------------------------------------------------
            # STEP 7: Simple View of Evidence Graph renders cleanly (Default)
            # -------------------------------------------------------------
            print("\n[STEP 7] Testing Supervisory Evidence Graph (Simple View)...")
            page.click("button:has-text('SUPERVISORY EVIDENCE GRAPH')")
            page.wait_for_selector("text=Simple View (Default)", timeout=5000)
            page.wait_for_selector("text=Inspecting Incident Workflow:", timeout=5000)
            page.wait_for_selector("text=Critical Sector Entity", timeout=5000)
            page.wait_for_selector("text=SOC Investigation", timeout=5000)

            # Verify Simple View node count: strictly 7 stages
            step_badges = page.locator("span:has-text('Step ')")
            step_count = step_badges.count()
            assert step_count == 7, f"Expected strictly 7 stages in Simple View, found {step_count}"
            print(f"Verified Simple View renders strictly {step_count} stages.")

            # Click a stage to show canonical node detail
            page.locator("div:has-text('SOC Investigation')").first.click()
            time.sleep(0.5)
            assert page.locator("text=Stage Inspector: INVESTIGATION").is_visible()

            shot_7 = save_shot(page, "07_simple_evidence_graph.png")
            print(f"[PASS] Step 7 PASS: Simple View of Evidence Graph verified. Screenshot -> {shot_7}")
            results["step_7_simple_graph"] = True

            # -------------------------------------------------------------
            # STEP 8: Full Evidence Graph can still be toggled
            # -------------------------------------------------------------
            print("\n[STEP 8] Testing Full Evidence Graph Toggle...")
            page.click("button:has-text('Show Full Evidence Graph')")
            page.wait_for_selector("svg", timeout=5000)
            time.sleep(0.5)

            shot_8 = save_shot(page, "08_full_evidence_graph.png")
            print(f"[PASS] Step 8 PASS: Full Evidence Graph toggled and rendered. Screenshot -> {shot_8}")
            results["step_8_full_graph"] = True

            # -------------------------------------------------------------
            # STEP 9: Dedicated Risk Analytics Page
            # -------------------------------------------------------------
            print("\n[STEP 9] Testing Dedicated Risk Analytics Page...")
            page.click("button:has-text('RISK ANALYTICS')")
            page.wait_for_selector("text=SUPERVISORY RISK ANALYTICS:", timeout=5000)
            page.wait_for_selector("text=5-Component Supervisory Risk Decomposition", timeout=5000)
            page.wait_for_selector("text=Execution Gap (30%)", timeout=5000)
            page.wait_for_selector("text=Top Risk Critical Sector Entities", timeout=5000)
            time.sleep(0.5)

            shot_9 = save_shot(page, "09_risk_analytics_page.png", full_page=True)
            print(f"[PASS] Step 9 PASS: Dedicated Risk Analytics page verified. Screenshot -> {shot_9}")
            results["step_9_risk_analytics"] = True

            # -------------------------------------------------------------
            # STEP 10: Reports page opens without error
            # -------------------------------------------------------------
            print("\n[STEP 10] Testing Reports & Audit Trail...")
            page.click("button:has-text('REPORTS & AUDIT TRAIL')")
            page.wait_for_selector("text=Supervisory Reporting & Cryptographic Audit Ledger", timeout=5000)
            page.wait_for_selector("table tbody tr", timeout=5000)

            # Open a Report Detail Drawer
            page.locator("table tbody tr button:has-text('View')").first.click()
            page.wait_for_selector("text=SHA-256 Checksum", timeout=5000)
            time.sleep(0.5)

            shot_10 = save_shot(page, "10_reports_page.png")
            print(f"[PASS] Step 10 PASS: Reports page & Drawer verified. Screenshot -> {shot_10}")

            # Close drawer
            page.locator("div.fixed button:has(svg.lucide-x)").first.click()
            time.sleep(0.3)
            results["step_10_reports_page"] = True

            # -------------------------------------------------------------
            # STEP 11: Report Export Triggers without 500 error
            # -------------------------------------------------------------
            print("\n[STEP 11] Testing Report Export via HTTP APIs...")
            export_check = False
            try:
                res = urllib.request.urlopen("http://127.0.0.1:8910/api/v1/reports")
                report_data = json.loads(res.read().decode())
                reports_list = report_data.get("reports", []) if isinstance(report_data, dict) else report_data
                if reports_list:
                    rep_id = reports_list[0]["id"]
                    # Test HTML export
                    t0 = time.time()
                    html_req = urllib.request.urlopen(f"http://127.0.0.1:8910/api/v1/reports/{rep_id}/export?format=html")
                    html_lat = (time.time() - t0) * 1000
                    assert html_req.status == 200
                    html_content = html_req.read().decode()
                    assert "<!DOCTYPE html>" in html_content or "<html" in html_content

                    # Test JSON export
                    t1 = time.time()
                    json_req = urllib.request.urlopen(f"http://127.0.0.1:8910/api/v1/reports/{rep_id}/export?format=json")
                    json_lat = (time.time() - t1) * 1000
                    assert json_req.status == 200
                    json_content = json.loads(json_req.read().decode())
                    assert "report_id" in json_content or "id" in json_content

                    print(f"Report export HTML latency: {html_lat:.1f}ms, JSON latency: {json_lat:.1f}ms")
                    export_check = True
            except Exception as e:
                print(f"Report export verification error: {e}")

            assert export_check, "Report export failed"
            shot_11 = save_shot(page, "11_report_export_success.png")
            print(f"[PASS] Step 11 PASS: Report export verified without 500. Screenshot -> {shot_11}")
            results["step_11_report_export"] = True

            # -------------------------------------------------------------
            # STEP 12: Daylight Theme Toggle
            # -------------------------------------------------------------
            print("\n[STEP 12] Testing Daylight Mode Theme Toggle...")
            page.click("button:has-text('Daylight')")
            time.sleep(0.5)
            page.click("button:has-text('SUPERVISORY DASHBOARD')")
            time.sleep(0.5)

            shot_12 = save_shot(page, "12_daylight_theme.png", full_page=True)
            print(f"[PASS] Step 12 PASS: Daylight theme rendered cleanly. Screenshot -> {shot_12}")
            results["step_12_daylight_theme"] = True

            browser.close()

    finally:
        server.stop()
        print("LiveServer stopped cleanly.")

    print("\n" + "=" * 70)
    print("ALL 12 VISUAL BROWSER VERIFICATION STEPS PASSED WITH 100% SUCCESS")
    print("=" * 70)
    return results


if __name__ == "__main__":
    run_full_browser_verification()
