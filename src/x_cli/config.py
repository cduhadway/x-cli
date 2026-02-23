"""Configuration and paths."""

from pathlib import Path

# Auth
AUTH_DIR = Path.home() / ".config" / "x-cli" / "auth"
AUTH_FILE = AUTH_DIR / "twitter.json"

# Browser
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1280, "height": 720}

# URLs
BOOKMARKS_URL = "https://x.com/i/bookmarks"
SEARCH_URL = "https://x.com/search"

# Timeouts (seconds)
NAV_TIMEOUT = 30_000
SELECTOR_TIMEOUT = 15_000
SCROLL_PAUSE = 2.0
INITIAL_LOAD_PAUSE = 1.0

# Scroll loop defaults
DEFAULT_COUNT = 50
DEFAULT_MAX_SCROLLS = 20
EMPTY_SCROLL_THRESHOLD = 3  # consecutive empty scrolls before stopping
