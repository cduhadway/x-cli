"""Playwright browser context creation and auth management."""

import json
import sys

from playwright.sync_api import BrowserContext, Playwright, sync_playwright

from .config import AUTH_DIR, AUTH_FILE, USER_AGENT, VIEWPORT


def load_auth() -> dict:
    """Load storage_state from auth file."""
    if not AUTH_FILE.exists():
        print(f"Auth file not found: {AUTH_FILE}", file=sys.stderr)
        print("Run: x auth save", file=sys.stderr)
        sys.exit(1)
    return json.loads(AUTH_FILE.read_text())


def create_context(pw: Playwright, *, headless: bool = True) -> BrowserContext:
    """Create an authenticated browser context."""
    state = load_auth()
    browser = pw.chromium.launch(headless=headless)
    context = browser.new_context(
        storage_state=state,
        viewport=VIEWPORT,
        user_agent=USER_AGENT,
    )
    return context


def save_auth(pw: Playwright) -> None:
    """Interactive headed login — save storage_state afterward."""
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        viewport=VIEWPORT,
        user_agent=USER_AGENT,
    )
    page = context.new_page()
    page.goto("https://x.com/i/bookmarks", wait_until="domcontentloaded")

    print("Log in to X in the browser window.")
    print("Press Enter here when done...")
    input()

    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    state = context.storage_state()
    AUTH_FILE.write_text(json.dumps(state, indent=2))
    AUTH_FILE.chmod(0o600)
    print(f"Auth saved to {AUTH_FILE}")

    browser.close()


def check_auth() -> bool:
    """Verify auth is still valid by navigating to bookmarks."""
    if not AUTH_FILE.exists():
        return False

    with sync_playwright() as pw:
        context = create_context(pw, headless=True)
        page = context.new_page()
        try:
            page.goto("https://x.com/i/bookmarks", wait_until="domcontentloaded")
            if "login" in page.url.lower():
                return False
            page.wait_for_selector(
                'article[data-testid="tweet"]', timeout=15000
            )
            return True
        except Exception:
            return False
        finally:
            context.browser.close()
