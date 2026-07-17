"""Browser-level smoke check for the local Mission Control dashboard."""

import os
import re
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    base_url = os.environ.get("MISSION_CONTROL_URL", "http://127.0.0.1:4317")
    screenshot = Path(tempfile.gettempdir()) / "codex-mission-control.png"
    mobile_screenshot = Path(tempfile.gettempdir()) / "codex-mission-control-mobile.png"
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 900}, device_scale_factor=1)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(base_url)
        page.wait_for_load_state("networkidle")

        page.get_by_role("heading", name="Know what every Codex task is doing.").wait_for()
        page.get_by_text("Live · local only").wait_for()
        page.locator(".task-card").first.wait_for()
        metric_boxes = [page.locator(".metric").nth(index).bounding_box() for index in range(3)]
        assert all(box and box["y"] >= 0 and box["y"] + box["height"] <= 900 for box in metric_boxes)
        visible = page.locator("body").inner_text()
        assert "Task ID" not in visible
        assert "Needs a look" not in visible
        assert "Overlap radar" not in visible
        assert not re.search(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", visible, re.I)

        page.locator("#settings-button").click()
        page.get_by_label("Local refresh").select_option("300")
        page.get_by_role("button", name="Save settings").click()
        page.locator("#collector-cadence").get_by_text("Every 5 minutes", exact=True).wait_for()

        page.locator("#settings-button").click()
        page.get_by_label("Local refresh").select_option("60")
        page.get_by_role("button", name="Save settings").click()
        page.locator("#collector-cadence").get_by_text("Every 1 minute", exact=True).wait_for()

        page.locator('.metric[data-filter="live"]').click()
        assert page.locator('.metric[data-filter="live"]').get_attribute("aria-pressed") == "true"
        assert page.locator("#workboard-title").inner_text().endswith("in motion")
        page.locator('.metric[data-filter="action"]').click()
        assert "action" in page.locator("#workboard-title").inner_text()

        project_tabs = page.locator(".project-tab")
        assert project_tabs.count() >= 2
        overall_active = int(page.locator("#metric-active").inner_text())
        project_name = project_tabs.nth(1).inner_text()
        project_tabs.nth(1).click()
        page.get_by_role("button", name="All", exact=True).click()
        page.locator(".task-card").first.wait_for()
        assert int(page.locator("#metric-active").inner_text()) <= overall_active
        assert all(value == project_name for value in page.locator(".project-pill").all_inner_texts())
        assert "Local collector" in page.locator("#agent-model").inner_text()
        page.get_by_role("button", name="Overall", exact=True).click()

        page.get_by_role("button", name="All", exact=True).click()
        assert page.locator(".task-card").count() >= 1
        assert page.locator(".task-update").count() == 0
        summaries = page.locator(".task-summary").all_inner_texts()
        assert summaries and all(len(summary) <= 180 for summary in summaries)
        page.get_by_role("button", name="In motion", exact=True).click()
        page.wait_for_timeout(250)
        page.screenshot(path=str(screenshot), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("button", name="All", exact=True).click()
        page.wait_for_timeout(250)
        page.locator(".task-card").first.wait_for()
        page.screenshot(path=str(mobile_screenshot), full_page=False)
        browser.close()

    if console_errors:
        raise AssertionError("Browser console errors: " + " | ".join(console_errors))
    print(f"Mission Control browser check passed. Screenshots: {screenshot} and {mobile_screenshot}")


if __name__ == "__main__":
    main()
