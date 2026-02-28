"""Core scraping logic: scroll loop, tweet extraction, quote/thread following."""

import time

from playwright.sync_api import Page

from .config import (
    BOOKMARKS_URL,
    DEFAULT_COUNT,
    DEFAULT_MAX_SCROLLS,
    EMPTY_SCROLL_THRESHOLD,
    INITIAL_LOAD_PAUSE,
    NAV_TIMEOUT,
    SCROLL_PAUSE,
    SEARCH_URL,
    SELECTOR_TIMEOUT,
)
from .js import EXTRACT_SINGLE_TWEET_LINKS_JS, EXTRACT_THREAD_JS, EXTRACT_TWEETS_JS
from .links import extract_arxiv_ids, resolve_link
from .models import BookmarksResult, Link, SearchResult, Tweet


def _raw_to_tweet(raw: dict) -> Tweet:
    """Convert raw JS tweet dict to Tweet model with resolved links."""
    links = []
    for lnk in raw.get("links", []):
        resolved_url, domain, category = resolve_link(lnk["href"], lnk.get("text", ""))
        links.append(Link(
            href=lnk["href"],
            text=lnk.get("text", ""),
            resolved_url=resolved_url,
            domain=domain,
            category=category,
        ))

    return Tweet(
        text=raw.get("text", ""),
        user_name=raw.get("user_name", ""),
        user_handle=raw.get("user_handle", ""),
        tweet_url=raw.get("tweet_url", ""),
        timestamp=raw.get("timestamp"),
        links=links,
        quoted_text=raw.get("quoted_text", ""),
        quoted_user=raw.get("quoted_user", ""),
        quoted_url=raw.get("quoted_url", ""),
        truncated=raw.get("truncated", False),
    )


def _scroll_and_collect(
    page: Page,
    *,
    max_count: int = DEFAULT_COUNT,
    max_scrolls: int = DEFAULT_MAX_SCROLLS,
) -> tuple[list[Tweet], int]:
    """Scroll loop that collects tweets, deduplicating by URL."""
    seen_urls: set[str] = set()
    all_tweets: list[Tweet] = []
    empty_streak = 0

    for scroll_num in range(max_scrolls):
        raw_tweets = page.evaluate(EXTRACT_TWEETS_JS)
        new_count = 0
        for raw in raw_tweets:
            url = raw.get("tweet_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_tweets.append(_raw_to_tweet(raw))
                new_count += 1

        if len(all_tweets) >= max_count:
            break

        if new_count == 0:
            empty_streak += 1
            if empty_streak >= EMPTY_SCROLL_THRESHOLD:
                break
        else:
            empty_streak = 0

        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        time.sleep(SCROLL_PAUSE)

    return all_tweets[:max_count], scroll_num + 1


def _follow_truncated(page: Page, tweets: list[Tweet]) -> None:
    """Navigate to individual tweet pages for truncated tweets to get full text and links."""
    for tweet in tweets:
        if not tweet.truncated or not tweet.tweet_url:
            continue
        try:
            page.goto(tweet.tweet_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            page.wait_for_selector('article[data-testid="tweet"]', timeout=SELECTOR_TIMEOUT)
            time.sleep(INITIAL_LOAD_PAUSE)
            data = page.evaluate(EXTRACT_SINGLE_TWEET_LINKS_JS)
            # Update text with full version from individual page
            if data.get("text"):
                tweet.text = data["text"]
            # Merge newly found links (dedup by href)
            existing_hrefs = {lnk.href for lnk in tweet.links}
            for lnk in data.get("links", []):
                if lnk["href"] in existing_hrefs:
                    continue
                resolved_url, domain, category = resolve_link(lnk["href"], lnk.get("text", ""))
                tweet.links.append(Link(
                    href=lnk["href"],
                    text=lnk.get("text", ""),
                    resolved_url=resolved_url,
                    domain=domain,
                    category=category,
                ))
            tweet.truncated = False
        except Exception:
            continue


def _follow_quotes(page: Page, tweets: list[Tweet]) -> None:
    """Navigate to quoted tweets and extract their links."""
    for tweet in tweets:
        if not tweet.quoted_url or "x.com" not in tweet.quoted_url:
            continue
        try:
            page.goto(tweet.quoted_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            page.wait_for_selector('article[data-testid="tweet"]', timeout=SELECTOR_TIMEOUT)
            time.sleep(INITIAL_LOAD_PAUSE)
            data = page.evaluate(EXTRACT_SINGLE_TWEET_LINKS_JS)
            for lnk in data.get("links", []):
                resolved_url, domain, category = resolve_link(lnk["href"], lnk.get("text", ""))
                tweet.quoted_links.append(Link(
                    href=lnk["href"],
                    text=lnk.get("text", ""),
                    resolved_url=resolved_url,
                    domain=domain,
                    category=category,
                ))
        except Exception:
            continue


def _follow_threads(page: Page, tweets: list[Tweet]) -> None:
    """For tweets with no links, navigate to tweet page and scan author replies."""
    for tweet in tweets:
        has_links = tweet.links or tweet.quoted_links or tweet.quoted_url
        if has_links:
            continue
        if not tweet.tweet_url or not tweet.user_handle:
            continue

        try:
            page.goto(tweet.tweet_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            page.wait_for_selector('article[data-testid="tweet"]', timeout=SELECTOR_TIMEOUT)
            time.sleep(INITIAL_LOAD_PAUSE)

            # Scroll to load thread replies
            for _ in range(4):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(1)

            data = page.evaluate(EXTRACT_THREAD_JS, tweet.user_handle)
            for lnk in data.get("links", []):
                resolved_url, domain, category = resolve_link(lnk["href"], lnk.get("text", ""))
                tweet.thread_links.append(Link(
                    href=lnk["href"],
                    text=lnk.get("text", ""),
                    resolved_url=resolved_url,
                    domain=domain,
                    category=category,
                ))
            tweet.thread_text = "\n".join(data.get("texts", [])[:10])
        except Exception:
            continue


def scrape_bookmarks(
    page: Page,
    *,
    count: int = DEFAULT_COUNT,
    max_scrolls: int = DEFAULT_MAX_SCROLLS,
    follow_quotes: bool = True,
    follow_threads: bool = True,
) -> BookmarksResult:
    """Scrape Twitter bookmarks."""
    page.goto(BOOKMARKS_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    if "login" in page.url.lower():
        raise RuntimeError("Auth expired. Run: x auth save")
    page.wait_for_selector('article[data-testid="tweet"]', timeout=SELECTOR_TIMEOUT)
    time.sleep(INITIAL_LOAD_PAUSE)

    tweets, scrolls = _scroll_and_collect(page, max_count=count, max_scrolls=max_scrolls)

    _follow_truncated(page, tweets)
    if follow_quotes:
        _follow_quotes(page, tweets)
    if follow_threads:
        _follow_threads(page, tweets)

    return BookmarksResult(tweets=tweets, total_scraped=len(tweets), scrolls_performed=scrolls)


def scrape_search(
    page: Page,
    query: str,
    *,
    count: int = DEFAULT_COUNT,
    max_scrolls: int = DEFAULT_MAX_SCROLLS,
    filter_mode: str = "top",
    follow_quotes: bool = True,
    follow_threads: bool = True,
) -> SearchResult:
    """Search Twitter and scrape results."""
    filter_param = "&f=live" if filter_mode == "latest" else ""
    url = f"{SEARCH_URL}?q={query}{filter_param}&src=typed_query"
    page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    if "login" in page.url.lower():
        raise RuntimeError("Auth expired. Run: x auth save")
    page.wait_for_selector('article[data-testid="tweet"]', timeout=SELECTOR_TIMEOUT)
    time.sleep(INITIAL_LOAD_PAUSE)

    tweets, _ = _scroll_and_collect(page, max_count=count, max_scrolls=max_scrolls)

    _follow_truncated(page, tweets)
    if follow_quotes:
        _follow_quotes(page, tweets)
    if follow_threads:
        _follow_threads(page, tweets)

    return SearchResult(query=query, filter=filter_mode, tweets=tweets, total_scraped=len(tweets))
