from __future__ import annotations

import ipaddress
import json
import re
import socket
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

CHALLENGE_MARKERS = (
    "captcha",
    "verify you are human",
    "checking your browser",
    "access denied",
    "cloudflare ray id",
    "unusual traffic",
)

CTA_WORDS = (
    "buy", "start", "try", "get started", "sign up", "subscribe", "book",
    "demo", "contact", "order", "купить", "начать", "попробовать", "регистрация",
    "демо", "связаться", "заказать",
)


def validate_public_url(url: str, allowed_domains: set[str] | None = None) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("Credential-bearing URLs are not allowed")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("URL hostname is required")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise PermissionError("Local/private hosts are not allowed")
    if allowed_domains and host not in allowed_domains and not any(host.endswith("." + d) for d in allowed_domains):
        raise PermissionError(f"Host is outside allowed_domains: {host}")

    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        addresses = []
        try:
            for info in socket.getaddrinfo(host, None):
                addresses.append(ipaddress.ip_address(info[4][0]))
        except OSError:
            pass

    for ip in addresses:
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise PermissionError(f"Private/reserved address is not allowed: {ip}")
    return url


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta_description = ""
        self.headings: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.buttons: list[str] = []
        self.forms = 0
        self.inputs: list[dict[str, str]] = []
        self.json_ld: list[Any] = []
        self._tag: str | None = None
        self._attrs: dict[str, str] = {}
        self._text: list[str] = []
        self._script_jsonld = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag = tag.lower()
        self._attrs = {k.lower(): (v or "") for k, v in attrs}
        self._text = []
        if tag.lower() == "meta":
            if self._attrs.get("name", "").lower() == "description":
                self.meta_description = self._attrs.get("content", "")
        elif tag.lower() == "form":
            self.forms += 1
        elif tag.lower() == "input":
            self.inputs.append({
                "type": self._attrs.get("type", "text"),
                "name": self._attrs.get("name", ""),
                "placeholder": self._attrs.get("placeholder", ""),
            })
        elif tag.lower() == "script" and self._attrs.get("type", "").lower() == "application/ld+json":
            self._script_jsonld = True

    def handle_data(self, data: str) -> None:
        if self._tag:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        text = " ".join(" ".join(self._text).split()).strip()
        lower = tag.lower()
        if lower == "title" and text:
            self.title = text
        elif lower in {"h1", "h2", "h3"} and text:
            self.headings.append({"level": lower, "text": text})
        elif lower == "a":
            href = self._attrs.get("href", "")
            if href or text:
                self.links.append({"href": href, "text": text})
        elif lower == "button" and text:
            self.buttons.append(text)
        elif lower == "script" and self._script_jsonld:
            raw = "".join(self._text).strip()
            if raw:
                try:
                    self.json_ld.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
            self._script_jsonld = False
        self._tag = None
        self._attrs = {}
        self._text = []


def extract_html_snapshot(html: str, *, url: str | None = None) -> dict[str, Any]:
    parser = _Extractor()
    parser.feed(html)
    all_text = re.sub(r"<[^>]+>", " ", html)
    all_text = " ".join(all_text.split())
    ctas = []
    for candidate in parser.buttons + [x["text"] for x in parser.links]:
        low = candidate.lower()
        if candidate and any(word in low for word in CTA_WORDS):
            ctas.append(candidate)
    prices = re.findall(r"(?:[$€£₽₾]\s?\d[\d,.]*|\d[\d,.]*\s?(?:USD|EUR|RUB|GEL|₽|₾))", all_text, flags=re.I)
    challenge = any(marker in all_text.lower() for marker in CHALLENGE_MARKERS)
    return {
        "url": url,
        "title": parser.title,
        "meta_description": parser.meta_description,
        "headings": parser.headings[:50],
        "links": parser.links[:500],
        "buttons": parser.buttons[:100],
        "ctas": list(dict.fromkeys(ctas))[:50],
        "prices": list(dict.fromkeys(prices))[:50],
        "forms": parser.forms,
        "inputs": parser.inputs[:100],
        "json_ld": parser.json_ld[:20],
        "text_excerpt": all_text[:12000],
        "challenge_detected": challenge,
    }


def fetch_public_page(
    url: str,
    *,
    timeout_ms: int = 30000,
    allowed_domains: set[str] | None = None,
    headless: bool = True,
) -> dict[str, Any]:
    """Fetch one public page with Camoufox.

    No login automation, CAPTCHA solving, challenge bypass, proxy rotation or
    authenticated-session import is implemented here.
    """
    validate_public_url(url, allowed_domains)
    try:
        from camoufox.sync_api import Camoufox
    except ImportError as exc:
        raise RuntimeError("Camoufox extra is not installed: pip install -e '.[camoufox]'") from exc

    with Camoufox(headless=headless) as browser:
        page = browser.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        html = page.content()
        snapshot = extract_html_snapshot(html, url=page.url)
        snapshot["http_status"] = response.status if response else None
        snapshot["requested_url"] = url
        snapshot["blocked_by_challenge"] = bool(snapshot["challenge_detected"])
        return snapshot


def crawl_public(
    start_url: str,
    *,
    max_pages: int = 5,
    max_depth: int = 1,
    delay_seconds: float = 1.0,
    allowed_domains: set[str] | None = None,
) -> list[dict[str, Any]]:
    if max_pages < 1 or max_pages > 25:
        raise ValueError("max_pages must be between 1 and 25")
    if max_depth < 0 or max_depth > 3:
        raise ValueError("max_depth must be between 0 and 3")
    start = validate_public_url(start_url, allowed_domains)
    origin = urlparse(start).hostname or ""
    queue: list[tuple[str, int]] = [(start, 0)]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    while queue and len(out) < max_pages:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        snap = fetch_public_page(url, allowed_domains=allowed_domains or {origin})
        out.append(snap)
        if snap.get("blocked_by_challenge") or depth >= max_depth:
            continue
        for link in snap.get("links", []):
            href = link.get("href") or ""
            candidate = urljoin(url, href)
            parsed = urlparse(candidate)
            if parsed.hostname == origin and parsed.scheme in {"http", "https"} and candidate not in seen:
                queue.append((candidate, depth + 1))
        if delay_seconds:
            time.sleep(max(0.0, delay_seconds))
    return out
