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

_TRACKED_TEXT_TAGS = {"title", "h1", "h2", "h3", "a", "button", "script"}


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

    if allowed_domains:
        allowed = {str(d).lower().rstrip(".") for d in allowed_domains}
        if host not in allowed and not any(host.endswith("." + d) for d in allowed):
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
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
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
        self._frames: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        attr_map = {k.lower(): (v or "") for k, v in attrs}

        if lower == "meta" and attr_map.get("name", "").lower() == "description":
            self.meta_description = attr_map.get("content", "")
        elif lower == "form":
            self.forms += 1
        elif lower == "input":
            self.inputs.append({
                "type": attr_map.get("type", "text"),
                "name": attr_map.get("name", ""),
                "placeholder": attr_map.get("placeholder", ""),
            })

        if lower in _TRACKED_TEXT_TAGS:
            self._frames.append({
                "tag": lower,
                "attrs": attr_map,
                "text": [],
                "jsonld": lower == "script" and attr_map.get("type", "").lower() == "application/ld+json",
            })

    def handle_data(self, data: str) -> None:
        # Append to every tracked open ancestor so <a><span>Start</span></a>
        # preserves "Start" for the anchor.
        for frame in self._frames:
            frame["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        idx = next((i for i in range(len(self._frames) - 1, -1, -1) if self._frames[i]["tag"] == lower), None)
        if idx is None:
            return
        frame = self._frames.pop(idx)
        text = " ".join("".join(frame["text"]).split()).strip()
        attrs = frame["attrs"]

        if lower == "title" and text:
            self.title = text
        elif lower in {"h1", "h2", "h3"} and text:
            self.headings.append({"level": lower, "text": text})
        elif lower == "a":
            href = attrs.get("href", "")
            if href or text:
                self.links.append({"href": href, "text": text})
        elif lower == "button" and text:
            self.buttons.append(text)
        elif lower == "script" and frame.get("jsonld"):
            raw = "".join(frame["text"]).strip()
            if raw:
                try:
                    self.json_ld.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass


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
    prices = re.findall(
        r"(?:[$€£₽₾]\s?\d[\d,.]*|\d[\d,.]*\s?(?:USD|EUR|RUB|GEL|₽|₾))",
        all_text,
        flags=re.I,
    )
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

    Requests are restricted to an explicit domain allowlist (the initial hostname
    by default) and public IP space. No login automation, CAPTCHA solving,
    challenge bypass, proxy rotation or authenticated-session import is implemented.
    """
    validate_public_url(url, allowed_domains)
    origin = (urlparse(url).hostname or "").lower().rstrip(".")
    effective_allowed = {str(x).lower().rstrip(".") for x in (allowed_domains or {origin})}
    effective_allowed.add(origin)

    try:
        from camoufox.sync_api import Camoufox
    except ImportError as exc:
        raise RuntimeError("Camoufox extra is not installed: pip install -e '.[camoufox]'") from exc

    with Camoufox(headless=headless) as browser:
        page = browser.new_page()

        def guard_request(route: Any) -> None:
            request_url = route.request.url
            try:
                validate_public_url(request_url, effective_allowed)
            except (ValueError, PermissionError):
                route.abort()
                return
            route.continue_()

        page.route("**/*", guard_request)
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        validate_public_url(page.url, effective_allowed)
        html = page.content()
        snapshot = extract_html_snapshot(html, url=page.url)
        snapshot["http_status"] = response.status if response else None
        snapshot["requested_url"] = url
        snapshot["blocked_by_challenge"] = bool(snapshot["challenge_detected"])
        snapshot["allowed_domains"] = sorted(effective_allowed)
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
    origin = (urlparse(start).hostname or "").lower().rstrip(".")
    effective_allowed = {str(x).lower().rstrip(".") for x in (allowed_domains or {origin})}
    effective_allowed.add(origin)
    queue: list[tuple[str, int]] = [(start, 0)]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    while queue and len(out) < max_pages:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        snap = fetch_public_page(url, allowed_domains=effective_allowed)
        out.append(snap)
        if snap.get("blocked_by_challenge") or depth >= max_depth:
            continue
        for link in snap.get("links", []):
            href = link.get("href") or ""
            candidate = urljoin(url, href)
            parsed = urlparse(candidate)
            host = (parsed.hostname or "").lower().rstrip(".")
            if (
                parsed.scheme in {"http", "https"}
                and host in effective_allowed
                and candidate not in seen
            ):
                queue.append((candidate, depth + 1))
        if delay_seconds:
            time.sleep(max(0.0, delay_seconds))
    return out
