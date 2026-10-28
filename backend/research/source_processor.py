"""Source normalization, cleaning, and safe optional page fetching."""

from __future__ import annotations

import asyncio
import html
import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from config import get_settings
from models import Source

_TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "ref",
    "ref_src",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}


@dataclass(slots=True)
class ProcessedContent:
    text: str
    fetched: bool = False

def clean_text(text: str, limit: int = 6000) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[:limit].rsplit(" ", 1)[0].strip()
    return text


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if parsed.port in {80, 443}:
        netloc = parsed.hostname or netloc
    query_params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in _TRACKING_PARAMS]
    query = urlencode(query_params, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def safe_domain(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname
    if not host:
        return False
    host = host.lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
        return True
    except ValueError:
        pass

    try:
        for _, _, addresses in socket.gethostbyname_ex(host):
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
    except socket.gaierror:
        return False
    return True


async def fetch_page_content(url: str) -> Optional[str]:
    if not safe_domain(url):
        return None

    settings = get_settings()
    timeout = httpx.Timeout(settings.tavily_timeout_seconds)
    headers = {"User-Agent": "ScholarSynth/2.0"}

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
    except httpx.TimeoutException:
        return None
    except httpx.HTTPError:
        return None

    if response.status_code >= 400:
        return None

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type and "application/xhtml+xml" not in content_type:
        return None

    text = clean_text(response.text, limit=8000)
    return text or None


async def enrich_source_content(source: Source) -> Source:
    content = clean_text(source.content or source.snippet or "")
    if content:
        source.content = content
        source.snippet = source.snippet or content[:400]
        return source

    fetched = await fetch_page_content(source.url)
    if fetched:
        source.content = fetched
        source.snippet = source.snippet or fetched[:400]
    else:
        source.content = source.snippet or ""
    return source


def assign_source_ids(sources: list[Source], start_index: int = 1) -> list[Source]:
    for offset, source in enumerate(sources, start=start_index):
        source.id = f"S{offset}"
    return sources


def source_text_bundle(source: Source, max_content_length: int = 3000) -> str:
    parts = [f"[{source.id}] {source.title}", f"URL: {source.url}"]
    if source.published_date:
        parts.append(f"Published: {source.published_date}")
    if source.snippet:
        parts.append(f"Snippet: {source.snippet}")
    if source.content:
        content = source.content[:max_content_length].strip()
        parts.append(f"Content: {content}")
    return "\n".join(parts)
