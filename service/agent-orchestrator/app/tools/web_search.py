from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import httpx

from app.core.config import settings
from app.tools.base import ToolResult


class WebSearchTool:
    name = "web.search"
    description = "Search the public web for external context when enabled."

    def run(self, **kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query", "")).strip()
        limit = min(
            int(kwargs.get("limit", settings.WEB_SEARCH_MAX_RESULTS)),
            settings.WEB_SEARCH_MAX_RESULTS,
        )

        if not settings.WEB_SEARCH_ENABLED:
            return ToolResult(
                name=self.name,
                output=[],
                metadata={"result_count": 0, "status": "disabled"},
            )

        if not query:
            return ToolResult(
                name=self.name,
                output=[],
                metadata={"result_count": 0, "status": "empty_query"},
            )

        try:
            results = self._search_duckduckgo(query=query, limit=limit)
        except Exception as exc:
            return ToolResult(
                name=self.name,
                output=[],
                metadata={"result_count": 0, "status": "failed", "error": str(exc)},
            )

        return ToolResult(
            name=self.name,
            output=results,
            metadata={"result_count": len(results), "status": "completed"},
        )

    def _search_duckduckgo(self, query: str, limit: int) -> list[dict[str, str]]:
        url = f"https://duckduckgo.com/html/?{urlencode({'q': query})}"
        response = httpx.get(
            url,
            headers={"User-Agent": "agent-governance-platform-demo/1.0"},
            timeout=settings.WEB_SEARCH_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        response.raise_for_status()

        parser = _DuckDuckGoHTMLParser()
        parser.feed(response.text)
        return parser.results[:limit]


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result_link = False
        self._current_href: str | None = None
        self._current_title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        css_class = attrs_dict.get("class", "")
        if tag == "a" and "result__a" in css_class:
            self._in_result_link = True
            self._current_href = attrs_dict.get("href")
            self._current_title_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_result_link:
            self._current_title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._in_result_link:
            return

        title = " ".join(part.strip() for part in self._current_title_parts if part.strip())
        url = _normalize_duckduckgo_url(self._current_href or "")
        if title and url:
            self.results.append({"title": title, "url": url})

        self._in_result_link = False
        self._current_href = None
        self._current_title_parts = []


def _normalize_duckduckgo_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    return url

