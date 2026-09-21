"""Capture screenshots of the vefr workshop and exported HTML.

Used by CI (screenshots.yml) and locally for docs.
Requires: playwright (pip install playwright && playwright install chromium)
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
ENGINE_URL = "http://127.0.0.1:8820"


def screenshot_workshop(page):
    """Screenshot the live workshop UI."""
    page.goto(ENGINE_URL, wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(SCREENSHOTS_DIR / "workshop-landing.png"), full_page=True)
    print("  workshop-landing.png")

    # Click "enter the house" if visible
    enter = page.locator("text=enter the house").first
    if enter.is_visible():
        enter.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "workshop-desk.png"), full_page=True)
        print("  workshop-desk.png")


def screenshot_export(page):
    """Screenshot the exported HTML title card + play surface."""
    export_path = (
        Path(__file__).resolve().parents[1] / "dist"
    )
    html_files = sorted(export_path.glob("sample-world-*.html"))
    if not html_files:
        print("  skip export — no woven HTML found in dist/")
        return

    page.goto(f"file://{html_files[-1]}", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(SCREENSHOTS_DIR / "export-title-card.png"), full_page=True)
    print("  export-title-card.png")

    enter_btn = page.locator("button:has-text('enter')").first
    if enter_btn.is_visible():
        enter_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / "export-play-surface.png"), full_page=True
        )
        print("  export-play-surface.png")


def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    print("capturing screenshots...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        screenshot_workshop(page)
        screenshot_export(page)
        browser.close()
    print(f"done — {len(list(SCREENSHOTS_DIR.glob('*.png')))} files in {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    main()
