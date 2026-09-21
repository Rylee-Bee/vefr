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


def screenshot_export(page, color_scheme="dark"):
    """Screenshot the exported HTML title card + play surface."""
    export_path = Path(__file__).resolve().parents[1] / "dist"
    html_files = sorted(export_path.glob("sample-world-*.html"))
    if not html_files:
        print("  skip export — no woven HTML found in dist/")
        return

    suffix = f"-{color_scheme}" if color_scheme != "dark" else ""
    page.goto(f"file://{html_files[-1]}", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(
        path=str(SCREENSHOTS_DIR / f"export-title-card{suffix}.png"), full_page=True
    )
    print(f"  export-title-card{suffix}.png")

    enter_btn = page.locator("button:has-text('enter')").first
    if enter_btn.is_visible():
        enter_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(
            path=str(SCREENSHOTS_DIR / f"export-play-surface{suffix}.png"),
            full_page=True,
        )
        print(f"  export-play-surface{suffix}.png")


def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    print("capturing screenshots...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Dark mode (default)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        screenshot_workshop(page)
        screenshot_export(page, "dark")
        page.close()

        # Light mode (title card only — shows how export looks in light theme)
        page_light = browser.new_page(
            viewport={"width": 1280, "height": 900}, color_scheme="light"
        )
        screenshot_export(page_light, "light")
        page_light.close()

        browser.close()
    print(f"done — {len(list(SCREENSHOTS_DIR.glob('*.png')))} files in {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    main()
