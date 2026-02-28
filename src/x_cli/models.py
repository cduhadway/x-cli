"""Data models."""

from pydantic import BaseModel


class Link(BaseModel):
    href: str
    text: str = ""
    resolved_url: str | None = None
    domain: str | None = None
    category: str | None = None


class Tweet(BaseModel):
    text: str = ""
    user_name: str = ""
    user_handle: str = ""
    tweet_url: str = ""
    timestamp: str | None = None
    links: list[Link] = []
    quoted_text: str = ""
    quoted_user: str = ""
    quoted_url: str = ""
    quoted_links: list[Link] = []
    thread_links: list[Link] = []
    thread_text: str = ""
    truncated: bool = False


class BookmarksResult(BaseModel):
    tweets: list[Tweet]
    total_scraped: int
    scrolls_performed: int


class SearchResult(BaseModel):
    query: str
    filter: str = "top"
    tweets: list[Tweet]
    total_scraped: int
