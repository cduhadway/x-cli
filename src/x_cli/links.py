"""t.co URL recovery and link classification."""

import re
from urllib.parse import urlparse

ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b")

PAPER_DOMAINS: dict[str, str] = {
    "arxiv.org": "arxiv",
    "openreview.net": "openreview",
    "papers.nips.cc": "neurips",
    "proceedings.mlr.press": "mlr",
    "ieeexplore.ieee.org": "ieee",
    "dl.acm.org": "acm",
    "paperswithcode.com": "paperswithcode",
    "scholar.google.com": "scholar",
    "semanticscholar.org": "semanticscholar",
    "huggingface.co": "huggingface",
    "github.com": "github",
}


def recover_url_from_anchor_text(text: str) -> str | None:
    """Reconstruct a URL from Twitter's split anchor text."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return None

    has_scheme = lines[0].lower().startswith("http")
    if has_scheme:
        url_parts = []
        for line in lines:
            clean = line.rstrip("\u2026").strip()
            if not clean:
                continue
            if " " in clean:
                break
            url_parts.append(clean)
        recovered = "".join(url_parts)
    else:
        first = lines[0].rstrip("\u2026").strip()
        if " " in first or len(first) > 80:
            return None
        recovered = "https://" + first

    if not recovered.startswith("http"):
        recovered = "https://" + recovered
    return recovered


def classify_domain(url: str) -> tuple[str, str | None]:
    """Return (domain, category) for a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.hostname or ""
    except Exception:
        return ("", None)

    # Check known domains
    for known, category in PAPER_DOMAINS.items():
        if domain == known or domain.endswith("." + known):
            return (domain, category)

    # *.github.io → project page
    if domain.endswith(".github.io"):
        return (domain, "project_page")

    return (domain, None)


def resolve_link(href: str, anchor_text: str) -> tuple[str, str, str | None]:
    """Resolve a link, returning (resolved_url, domain, category)."""
    # If it's a t.co link, try to recover from anchor text
    if "t.co/" in href:
        recovered = recover_url_from_anchor_text(anchor_text)
        if recovered:
            domain, category = classify_domain(recovered)
            return (recovered, domain, category)

    domain, category = classify_domain(href)
    return (href, domain, category)


def extract_arxiv_ids(text: str) -> list[str]:
    """Extract arXiv paper IDs from text."""
    return ARXIV_ID_RE.findall(text)
