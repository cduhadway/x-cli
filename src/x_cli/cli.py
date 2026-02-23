"""Click CLI: x bookmarks, x search, x auth."""

from urllib.parse import quote as url_quote

import click
from playwright.sync_api import sync_playwright

from .browser import check_auth, create_context, save_auth
from .config import DEFAULT_COUNT, DEFAULT_MAX_SCROLLS
from .output import format_json, format_pretty
from .scraper import scrape_bookmarks, scrape_search


@click.group()
def cli():
    """Read-only Twitter/X CLI."""
    pass


@cli.command()
@click.option("--count", default=DEFAULT_COUNT, help="Max bookmarks to fetch.")
@click.option("--max-scrolls", default=DEFAULT_MAX_SCROLLS, help="Max scroll iterations.")
@click.option("--follow-quotes/--no-follow-quotes", default=True, help="Follow quoted tweets for links.")
@click.option("--follow-threads/--no-follow-threads", default=True, help="Follow author threads for links.")
@click.option("--pretty", is_flag=True, help="Rich table output instead of JSON.")
def bookmarks(count, max_scrolls, follow_quotes, follow_threads, pretty):
    """Scrape your Twitter/X bookmarks."""
    with sync_playwright() as pw:
        context = create_context(pw)
        page = context.new_page()
        try:
            result = scrape_bookmarks(
                page,
                count=count,
                max_scrolls=max_scrolls,
                follow_quotes=follow_quotes,
                follow_threads=follow_threads,
            )
        finally:
            context.browser.close()

    if pretty:
        format_pretty(result)
    else:
        click.echo(format_json(result))


@cli.command()
@click.argument("query")
@click.option("--count", default=DEFAULT_COUNT, help="Max tweets to fetch.")
@click.option("--max-scrolls", default=DEFAULT_MAX_SCROLLS, help="Max scroll iterations.")
@click.option("--filter", "filter_mode", type=click.Choice(["top", "latest"]), default="top", help="Search filter.")
@click.option("--follow-quotes/--no-follow-quotes", default=True, help="Follow quoted tweets for links.")
@click.option("--follow-threads/--no-follow-threads", default=True, help="Follow author threads for links.")
@click.option("--pretty", is_flag=True, help="Rich table output instead of JSON.")
def search(query, count, max_scrolls, filter_mode, follow_quotes, follow_threads, pretty):
    """Search Twitter/X for tweets."""
    encoded_query = url_quote(query)
    with sync_playwright() as pw:
        context = create_context(pw)
        page = context.new_page()
        try:
            result = scrape_search(
                page,
                encoded_query,
                count=count,
                max_scrolls=max_scrolls,
                filter_mode=filter_mode,
                follow_quotes=follow_quotes,
                follow_threads=follow_threads,
            )
        finally:
            context.browser.close()

    if pretty:
        format_pretty(result)
    else:
        click.echo(format_json(result))


@cli.group()
def auth():
    """Manage X authentication."""
    pass


@auth.command("save")
def auth_save():
    """Interactive headed browser login. Save storage_state."""
    with sync_playwright() as pw:
        save_auth(pw)


@auth.command("check")
def auth_check():
    """Verify auth is still valid."""
    valid = check_auth()
    if valid:
        click.echo("Auth is valid.")
    else:
        click.echo("Auth is expired or missing. Run: x auth save")
        raise SystemExit(1)
