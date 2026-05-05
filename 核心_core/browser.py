from typing import Any


def launch_browser(playwright: Any, mode: str, headless: bool):
    if mode == "edge_only":
        return playwright.chromium.launch(channel="msedge", headless=headless), "edge"

    if mode == "chromium_only":
        return playwright.chromium.launch(headless=headless), "chromium"

    try:
        browser = playwright.chromium.launch(channel="msedge", headless=headless)
        return browser, "edge"
    except Exception:
        browser = playwright.chromium.launch(headless=headless)
        return browser, "chromium"
