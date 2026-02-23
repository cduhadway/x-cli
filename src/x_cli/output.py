"""Output formatting: JSON and rich tables."""

import json

from rich.console import Console
from rich.table import Table

from .models import BookmarksResult, SearchResult, Tweet


def _tweet_summary(tweet: Tweet) -> dict:
    """Compact tweet dict for JSON output."""
    d = {
        "user": tweet.user_handle,
        "text": tweet.text[:200],
        "url": tweet.tweet_url,
        "timestamp": tweet.timestamp,
        "links": [
            {"url": lnk.resolved_url or lnk.href, "domain": lnk.domain, "category": lnk.category}
            for lnk in tweet.links
        ],
    }
    if tweet.quoted_url:
        d["quoted_url"] = tweet.quoted_url
        d["quoted_text"] = tweet.quoted_text[:200]
    if tweet.quoted_links:
        d["quoted_links"] = [
            {"url": lnk.resolved_url or lnk.href, "domain": lnk.domain, "category": lnk.category}
            for lnk in tweet.quoted_links
        ]
    if tweet.thread_links:
        d["thread_links"] = [
            {"url": lnk.resolved_url or lnk.href, "domain": lnk.domain, "category": lnk.category}
            for lnk in tweet.thread_links
        ]
    return d


def format_json(result: BookmarksResult | SearchResult) -> str:
    """Format result as JSON string."""
    tweets = [_tweet_summary(t) for t in result.tweets]
    data: dict = {"total": result.total_scraped, "tweets": tweets}
    if isinstance(result, SearchResult):
        data["query"] = result.query
        data["filter"] = result.filter
    return json.dumps(data, indent=2)


def format_pretty(result: BookmarksResult | SearchResult) -> None:
    """Print result as a rich table."""
    console = Console()

    if isinstance(result, SearchResult):
        console.print(f"\n[bold]Search: {result.query}[/bold] ({result.filter})")

    table = Table(show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("User", style="cyan", width=16)
    table.add_column("Tweet", width=50)
    table.add_column("Links", width=40)

    for i, tweet in enumerate(result.tweets, 1):
        all_links = tweet.links + tweet.quoted_links + tweet.thread_links
        link_strs = []
        for lnk in all_links:
            url = lnk.resolved_url or lnk.href
            tag = f"[{lnk.category}]" if lnk.category else ""
            link_strs.append(f"{tag} {url}")

        table.add_row(
            str(i),
            tweet.user_handle,
            tweet.text[:120] + ("..." if len(tweet.text) > 120 else ""),
            "\n".join(link_strs) if link_strs else "[dim]none[/dim]",
        )

    console.print(table)
    console.print(f"\n[bold]{result.total_scraped}[/bold] tweets scraped")
