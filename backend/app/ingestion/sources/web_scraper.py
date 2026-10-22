"""Web source loader implementation."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections import deque
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

from app.ingestion.exceptions import IngestionValidationError, SourceLoadError
from app.ingestion.schemas import RawDocument, SourceConfig
from app.ingestion.sources.base import BaseSourceLoader

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = os.getenv("WEB_SCRAPER_USER_AGENT", "RAGAiBot/1.0 (+https://example.local/bot)")
DEFAULT_MAX_DEPTH = int(os.getenv("WEB_SCRAPER_MAX_DEPTH", "1"))
DEFAULT_MAX_PAGES = int(os.getenv("WEB_SCRAPER_MAX_PAGES", "20"))
HARD_MAX_PAGES = int(os.getenv("WEB_SCRAPER_HARD_MAX_PAGES", "200"))


@dataclass(slots=True)
class _FetchedPage:
    """Fetched page payload container."""

    url: str
    final_url: str
    html: str
    status_code: int


class PlaywrightRendererAdapter:
    """Optional Playwright-based HTML renderer for JS-heavy pages."""

    async def render(self, url: str, timeout_seconds: int, user_agent: str) -> str:
        """Render URL and return final page HTML."""
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:  # pragma: no cover - dependency optional
            raise SourceLoadError("playwright is not installed") from exc

        timeout_ms = timeout_seconds * 1000
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=user_agent)
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                return await page.content()
            finally:
                await context.close()
                await browser.close()


class WebScraperSource(BaseSourceLoader):
    """Crawl and extract web pages into normalized `RawDocument` records."""

    def __init__(self, playwright_adapter: PlaywrightRendererAdapter | None = None) -> None:
        self.playwright_adapter = playwright_adapter or PlaywrightRendererAdapter()
        self._robots_cache: dict[str, RobotFileParser] = {}

    async def load(self, config: SourceConfig) -> list[RawDocument]:
        """Load and parse web pages using bounded crawl rules."""
        self.validate_source(config)
        if config.source_type != "web":
            raise IngestionValidationError("WebScraperSource requires source_type='web'")

        crawl_options = self._parse_crawl_options(config)
        base_url = self._normalize_url(config.source_uri)
        base_domain = self._get_domain(base_url)

        queue: deque[tuple[str, int]] = deque([(base_url, 0)])
        visited: set[str] = set()
        documents: list[RawDocument] = []

        while queue and len(documents) < crawl_options.max_pages:
            current_url, depth = queue.popleft()
            canonical_current = self._normalize_url(current_url)
            if canonical_current in visited:
                continue
            visited.add(canonical_current)

            if depth > crawl_options.max_depth:
                continue
            if not self._is_url_allowed(canonical_current, base_domain, crawl_options):
                continue
            if crawl_options.respect_robots and not await self._can_fetch(canonical_current, crawl_options.user_agent):
                logger.info("web_scraper_robots_disallow", extra={"url": canonical_current})
                continue

            page = await self._fetch_page(canonical_current, crawl_options)
            if page is None:
                continue

            extracted = self._extract_page_content(page.final_url, page.html)
            if not extracted["main_content"]:
                continue

            document = self.build_raw_document(
                config=config,
                raw_content=extracted["main_content"],
                title=extracted["title"],
                metadata={
                    "headings": extracted["headings"],
                    "raw_html": extracted["raw_html"],
                    "publication_date": extracted["publication_date"],
                    "author": extracted["author"],
                    "canonical_url": extracted["canonical_url"] or page.final_url,
                    "status_code": page.status_code,
                    "crawl_depth": depth,
                },
            )
            documents.append(document)

            if depth < crawl_options.max_depth:
                links = self._extract_links(page.final_url, page.html)
                for link in links:
                    normalized_link = self._normalize_url(link)
                    if normalized_link in visited:
                        continue
                    if self._is_url_allowed(normalized_link, base_domain, crawl_options):
                        queue.append((normalized_link, depth + 1))

        logger.info(
            "web_scraper_completed",
            extra={"start_url": config.source_uri, "pages_collected": len(documents), "visited_urls": len(visited)},
        )
        return documents

    async def _fetch_page(self, url: str, options: "_CrawlOptions") -> _FetchedPage | None:
        """Fetch one page with retry and optional JS-render fallback."""
        http_html: str | None = None
        final_url = url
        status_code = 0

        for attempt in range(options.retries + 1):
            try:
                fetched = await self._fetch_with_httpx(url, options)
                http_html = fetched.html
                final_url = fetched.final_url
                status_code = fetched.status_code
                break
            except Exception as exc:
                logger.warning(
                    "web_scraper_http_retry",
                    extra={"url": url, "attempt": attempt + 1, "max_attempts": options.retries + 1, "error": str(exc)},
                )
                if attempt >= options.retries:
                    http_html = None
                    break
                await asyncio.sleep(min(2**attempt, 5))

        html = http_html
        if (not html or len(html.strip()) < 50) and options.use_playwright:
            try:
                html = await self.playwright_adapter.render(url=url, timeout_seconds=options.timeout_seconds, user_agent=options.user_agent)
                status_code = status_code or 200
            except Exception as exc:
                logger.warning("web_scraper_playwright_failed", extra={"url": url, "error": str(exc)})

        if not html:
            return None
        return _FetchedPage(url=url, final_url=final_url, html=html, status_code=status_code)

    async def _fetch_with_httpx(self, url: str, options: "_CrawlOptions") -> _FetchedPage:
        """Fetch URL via httpx with timeout."""
        try:
            import httpx
        except Exception as exc:  # pragma: no cover - dependency optional
            raise SourceLoadError("httpx is required for web scraping") from exc

        timeout = httpx.Timeout(options.timeout_seconds)
        headers = {"User-Agent": options.user_agent}
        async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return _FetchedPage(
                url=url,
                final_url=str(response.url),
                html=response.text,
                status_code=response.status_code,
            )

    async def _can_fetch(self, url: str, user_agent: str) -> bool:
        """Check robots.txt rules for URL/domain."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        origin = f"{parsed.scheme}://{parsed.netloc}"

        parser = self._robots_cache.get(origin)
        if parser is None:
            parser = await self._load_robots_parser(origin, user_agent)
            self._robots_cache[origin] = parser
        return parser.can_fetch(user_agent, url)

    async def _load_robots_parser(self, origin: str, user_agent: str) -> RobotFileParser:
        """Load and parse robots.txt file for a domain."""
        parser = RobotFileParser()
        robots_url = urljoin(origin, "/robots.txt")
        parser.set_url(robots_url)
        try:
            options = _CrawlOptions(
                max_depth=0,
                max_pages=1,
                same_domain_only=True,
                respect_robots=False,
                include_patterns=[],
                exclude_patterns=[],
                user_agent=user_agent,
                timeout_seconds=8,
                retries=0,
                use_playwright=False,
            )
            page = await self._fetch_with_httpx(robots_url, options)
            parser.parse(page.html.splitlines())
        except Exception:
            logger.debug("web_scraper_robots_unavailable", extra={"origin": origin})
            parser.parse([])
        return parser

    def _extract_page_content(self, url: str, html: str) -> dict[str, Any]:
        """Extract title/headings/content/raw_html/date/author/canonical URL."""
        try:
            from bs4 import BeautifulSoup
        except Exception as exc:  # pragma: no cover - dependency optional
            raise SourceLoadError("beautifulsoup4 is required for web scraping") from exc

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()

        title = (soup.title.string or "").strip() if soup.title and soup.title.string else None
        headings = [node.get_text(" ", strip=True) for node in soup.find_all(re.compile("^h[1-6]$"))]

        article = soup.find("article")
        main = soup.find("main")
        body_candidate = article or main or soup.body or soup
        main_content = body_candidate.get_text("\n", strip=True) if body_candidate else ""

        canonical_url = None
        canonical_tag = soup.find("link", attrs={"rel": lambda v: v and "canonical" in v})
        if canonical_tag and canonical_tag.get("href"):
            canonical_url = urljoin(url, canonical_tag["href"].strip())

        publication_date = self._extract_first_meta_content(
            soup,
            keys=[
                ("property", "article:published_time"),
                ("name", "pubdate"),
                ("name", "publish_date"),
                ("itemprop", "datePublished"),
                ("property", "og:published_time"),
                ("name", "date"),
            ],
        )
        author = self._extract_first_meta_content(
            soup,
            keys=[("name", "author"), ("property", "article:author"), ("itemprop", "author")],
        )

        return {
            "title": title,
            "headings": headings,
            "main_content": main_content,
            "raw_html": html,
            "publication_date": publication_date,
            "author": author,
            "canonical_url": canonical_url,
        }

    def _extract_first_meta_content(self, soup: Any, keys: list[tuple[str, str]]) -> str | None:
        """Extract first matching meta content value."""
        for attr_name, attr_value in keys:
            tag = soup.find("meta", attrs={attr_name: attr_value})
            if tag and tag.get("content"):
                content = str(tag.get("content")).strip()
                if content:
                    return content
        return None

    def _extract_links(self, base_url: str, html: str) -> list[str]:
        """Extract anchor links from page HTML."""
        try:
            from bs4 import BeautifulSoup
        except Exception as exc:  # pragma: no cover - dependency optional
            raise SourceLoadError("beautifulsoup4 is required for web scraping") from exc

        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"]).strip()
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
                continue
            links.append(urljoin(base_url, href))
        return links

    def _parse_crawl_options(self, config: SourceConfig) -> "_CrawlOptions":
        """Build crawl options from config and environment defaults."""
        options = config.options or {}
        max_depth = int(options.get("max_depth", DEFAULT_MAX_DEPTH))
        max_pages_requested = int(options.get("max_pages", min(config.max_items, DEFAULT_MAX_PAGES)))
        max_pages = max(1, min(max_pages_requested, config.max_items, HARD_MAX_PAGES))
        retries = int(options.get("retries", 2))

        return _CrawlOptions(
            max_depth=max(0, max_depth),
            max_pages=max_pages,
            same_domain_only=bool(options.get("same_domain_only", True)),
            respect_robots=bool(options.get("respect_robots", True)),
            include_patterns=[str(item) for item in options.get("include_patterns", [])],
            exclude_patterns=[str(item) for item in options.get("exclude_patterns", [])],
            user_agent=str(options.get("user_agent", DEFAULT_USER_AGENT)),
            timeout_seconds=config.timeout_seconds,
            retries=max(0, retries),
            use_playwright=bool(options.get("use_playwright", False)),
        )

    def _is_url_allowed(self, url: str, base_domain: str, options: "_CrawlOptions") -> bool:
        """Apply domain and pattern filters to candidate URLs."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if options.same_domain_only and self._get_domain(url) != base_domain:
            return False
        if options.include_patterns and not any(re.search(pattern, url) for pattern in options.include_patterns):
            return False
        if any(re.search(pattern, url) for pattern in options.exclude_patterns):
            return False
        return True

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for stable deduplication."""
        parsed = urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            raise IngestionValidationError(f"invalid URL: {url}")
        normalized = parsed._replace(fragment="")
        path = normalized.path or "/"
        normalized = normalized._replace(path=path)
        return urlunparse(normalized)

    def _get_domain(self, url: str) -> str:
        """Extract lowercased domain name from URL."""
        return urlparse(url).netloc.lower()


@dataclass(slots=True)
class _CrawlOptions:
    """Internal crawl controls parsed from source config."""

    max_depth: int
    max_pages: int
    same_domain_only: bool
    respect_robots: bool
    include_patterns: list[str]
    exclude_patterns: list[str]
    user_agent: str
    timeout_seconds: int
    retries: int
    use_playwright: bool
