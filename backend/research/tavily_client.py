"""Tavily search client with normalized source output."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from config import get_settings
from models import Source
from research.source_processor import clean_text


class TavilyError(RuntimeError):
    pass


class TavilyClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.tavily_api_key
        self.base_url = "https://api.tavily.com"

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise TavilyError("TAVILY_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def search(
        self,
        query: str,
        *,
        max_results: int | None = None,
        include_raw_content: bool = True,
        include_published_date: bool = True,
        search_depth: str = "basic",
        topic: str = "general",
    ) -> list[Source]:
        payload = {
            "query": query,
            "max_results": max_results or self.settings.max_results_per_query,
            "include_raw_content": include_raw_content,
            "include_published_date": include_published_date,
            "search_depth": search_depth,
            "topic": topic,
            "include_answer": False,
        }
        timeout = httpx.Timeout(self.settings.tavily_timeout_seconds)
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
                response = await client.post("/search", json=payload, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise TavilyError("Tavily search timed out") from exc
        except httpx.HTTPError as exc:
            raise TavilyError(f"Tavily search request failed: {exc}") from exc

        if response.status_code >= 400:
            raise TavilyError(f"Tavily error {response.status_code}: {response.text[:500]}")

        data = response.json()
        results = data.get("results", []) or []
        sources: list[Source] = []
        for result in results:
            url = result.get("url")
            title = result.get("title") or url or query
            if not url:
                continue
            domain = urlparse(url).hostname
            content = result.get("raw_content") or result.get("content") or ""
            content = clean_text(content, limit=6000)
            snippet = clean_text(result.get("content") or content[:500], limit=500)
            sources.append(
                Source(
                    id="",
                    title=title,
                    url=url,
                    content=content,
                    snippet=snippet or None,
                    published_date=result.get("published_date"),
                    domain=domain,
                    score=float(result.get("score") or 0.0),
                    query=query,
                    source_type="tavily",
                    metadata={k: v for k, v in result.items() if k not in {"title", "url", "content", "raw_content", "published_date", "score"}},
                )
            )
        return sources

    async def search_with_retry(self, query: str, *, max_attempts: int = 2) -> list[Source]:
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return await self.search(query)
            except TavilyError as exc:
                last_error = exc
                if attempt >= max_attempts - 1:
                    break
                await asyncio.sleep(min(2**attempt, 3))
        if last_error:
            raise last_error
        return []
