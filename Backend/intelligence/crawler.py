"""Tenant-safe website crawler primitives for website intelligence.

This module intentionally avoids browser automation and third-party crawlers in
the first live phase. It gives the platform a small, bounded HTTP crawler that
can be replaced by Firecrawl, Crawl4AI, Playwright, or Browserbase later without
changing the job/draft contracts.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin
from urllib.request import Request, urlopen

from .url_guard import SafeURL, validate_public_http_url


logger = logging.getLogger("intelligence.crawler")


class CrawlError(RuntimeError):
    """Raised when a crawl cannot safely complete."""


@dataclass(frozen=True)
class CrawledPage:
    url: str
    content_type: str
    body: str
    content_hash: str
    status_code: int = 200


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)
                return


class WebsiteCrawler:
    """Bounded same-domain crawler with SSRF validation on every URL."""

    def __init__(self, *, user_agent: str = "VoiceAgentWebsiteIntelligence/1.0") -> None:
        self.user_agent = user_agent

    async def crawl(
        self,
        url: str,
        *,
        max_pages: int,
        max_bytes: int,
        timeout_s: int,
    ) -> list[CrawledPage]:
        root = validate_public_http_url(url, resolve_dns=True)
        max_pages = max(1, min(int(max_pages or 1), 50))
        max_bytes = max(20_000, min(int(max_bytes or 20_000), 10_000_000))
        timeout_s = max(3, min(int(timeout_s or 10), 60))

        visited: set[str] = set()
        queued: list[SafeURL] = [root]
        pages: list[CrawledPage] = []
        bytes_remaining = max_bytes

        while queued and len(pages) < max_pages and bytes_remaining > 0:
            safe = queued.pop(0)
            if safe.normalized_url in visited:
                continue
            visited.add(safe.normalized_url)

            page = await self._fetch_page(safe, max_bytes=bytes_remaining, timeout_s=timeout_s)
            pages.append(page)
            bytes_remaining -= len(page.body.encode("utf-8", errors="ignore"))

            if "html" not in page.content_type.lower():
                continue

            for link in _extract_same_domain_links(page.body, page.url, root.domain):
                if len(queued) + len(visited) >= max_pages * 3:
                    break
                try:
                    candidate = validate_public_http_url(
                        link,
                        resolve_dns=True,
                        allowed_domains={root.domain},
                    )
                except Exception:
                    continue
                if candidate.normalized_url not in visited:
                    queued.append(candidate)

        if not pages:
            raise CrawlError("no crawlable public pages were fetched")
        logger.info("[INTEL] crawled pages=%d domain=%s", len(pages), root.domain)
        return pages

    async def _fetch_page(self, safe: SafeURL, *, max_bytes: int, timeout_s: int) -> CrawledPage:
        return await asyncio.to_thread(
            self._fetch_page_sync,
            safe,
            max_bytes=max_bytes,
            timeout_s=timeout_s,
        )

    def _fetch_page_sync(self, safe: SafeURL, *, max_bytes: int, timeout_s: int) -> CrawledPage:
        request = Request(
            safe.normalized_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,text/plain,application/xhtml+xml;q=0.9,*/*;q=0.5",
            },
        )
        try:
            with urlopen(request, timeout=timeout_s) as response:
                raw = response.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    raise CrawlError("crawl byte limit exceeded")
                content_type = response.headers.get("content-type", "application/octet-stream")
                charset = response.headers.get_content_charset() or "utf-8"
                body = raw.decode(charset, errors="replace")
                return CrawledPage(
                    url=response.geturl() or safe.normalized_url,
                    content_type=content_type,
                    body=body,
                    content_hash=hashlib.sha256(raw).hexdigest(),
                    status_code=getattr(response, "status", 200),
                )
        except CrawlError:
            raise
        except Exception as exc:
            raise CrawlError(f"crawl fetch failed for {safe.domain}") from exc


def _extract_same_domain_links(html: str, base_url: str, root_domain: str) -> list[str]:
    parser = _LinkExtractor()
    try:
        parser.feed(html or "")
    except Exception:
        return []

    links: list[str] = []
    seen: set[str] = set()
    for href in parser.links:
        absolute, _fragment = urldefrag(urljoin(base_url, href))
        if not absolute or absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links
