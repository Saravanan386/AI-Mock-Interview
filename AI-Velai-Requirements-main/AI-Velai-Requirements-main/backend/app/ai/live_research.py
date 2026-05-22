from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote_plus

import httpx

from app.config import settings


class _DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[str] = []
        self._capture: str | None = None
        self._current_title: list[str] = []
        self._current_snippet: list[str] = []

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        attributes = dict(attrs)
        class_name = attributes.get("class", "") or ""
        if tag == "a" and "result__a" in class_name:
            self._capture = "title"
            self._current_title = []
            self._current_snippet = []
        elif tag in {"a", "div", "span"} and "result__snippet" in class_name:
            self._capture = "snippet"

    def handle_endtag(self, tag: str):  # type: ignore[override]
        if tag == "a" and self._capture == "title":
            self._capture = None
        elif tag in {"a", "div", "span"} and self._capture == "snippet":
            self._capture = None
            title = unescape(" ".join(self._current_title).strip())
            snippet = unescape(" ".join(self._current_snippet).strip())
            if title:
                entry = f"{title}: {snippet}" if snippet else title
                self.results.append(entry)
                self._current_title = []
                self._current_snippet = []

    def handle_data(self, data: str):  # type: ignore[override]
        if self._capture == "title":
            self._current_title.append(data)
        elif self._capture == "snippet":
            self._current_snippet.append(data)


async def fetch_live_research_snippets(query: str, limit: int = 4) -> list[str]:
    if not settings.live_search_enabled or not query.strip():
        return []

    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        async with httpx.AsyncClient(timeout=settings.live_search_timeout_seconds, headers={"User-Agent": "Mozilla/5.0"}) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception:
        return []

    parser = _DuckDuckGoResultParser()
    try:
        parser.feed(response.text)
    except Exception:
        return []
    return [item for item in parser.results if item][:limit]
