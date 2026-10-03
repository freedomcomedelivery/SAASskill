from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import uuid
from typing import Any

from .camoufox_parser import CTA_WORDS, CHALLENGE_MARKERS, validate_public_url

DEFAULT_BASE = "http://127.0.0.1:9377"


def _base() -> str:
    value = str(os.getenv("CAMOFOX_BASE_URL") or DEFAULT_BASE).rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("CAMOFOX_BASE_URL must be http/https")
    return value


def _call(path: str, *, method: str = "GET", body: dict[str, Any] | None = None, timeout: float = 30.0) -> Any:
    headers = {"Accept": "application/json"}
    token = os.getenv("CAMOFOX_API_KEY") or os.getenv("CAMOFOX_ACCESS_KEY")
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(_base() + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


def health(timeout: float = 5.0) -> dict[str, Any]:
    return _call("/health", timeout=timeout)


def accessibility_to_surface(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Convert camofox-browser accessibility text into SAASskill commercial surface data."""
    text = str(snapshot.get("snapshot") or snapshot.get("content") or "")
    title = snapshot.get("title")
    headings = []
    links = []
    buttons = []
    ctas = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"\[(heading|link|button)(?:\s+([^\]]+))?\]\s*(.*)", line, re.I)
        if not m:
            continue
        kind, ref, label = m.group(1).lower(), (m.group(2) or "").strip(), (m.group(3) or "").strip()
        if kind == "heading" and label:
            headings.append({"level": "heading", "text": label})
        elif kind == "link":
            links.append({"ref": ref, "text": label})
        elif kind == "button":
            buttons.append(label)
        low = label.lower()
        if label and any(word in low for word in CTA_WORDS):
            ctas.append(label)
    prices = re.findall(r"(?:[$€£₽₾]\s?\d[\d,.]*|\d[\d,.]*\s?(?:USD|EUR|RUB|GEL|₽|₾))", text, flags=re.I)
    challenge = any(marker in text.lower() for marker in CHALLENGE_MARKERS)
    return {
        "url": snapshot.get("url"),
        "requested_url": snapshot.get("requested_url"),
        "title": title,
        "meta_description": None,
        "headings": headings[:50],
        "links": links[:500],
        "buttons": buttons[:100],
        "ctas": list(dict.fromkeys(ctas))[:50],
        "prices": list(dict.fromkeys(prices))[:50],
        "forms": [],
        "inputs": [],
        "json_ld": [],
        "text_excerpt": text[:12000],
        "challenge_detected": challenge,
        "blocked_by_challenge": challenge,
        "source_backend": "camofox-browser-rest",
    }


def fetch_snapshot(
    url: str,
    *,
    user_id: str | None = None,
    session_key: str | None = None,
    allowed_domains: set[str] | None = None,
    include_screenshot: bool = False,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Use camofox-browser REST for a public, read-only snapshot.

    No click/type/cookie import/login/challenge solving is exposed here.
    """
    validate_public_url(url, allowed_domains)
    user_id = user_id or ("saasskill-" + uuid.uuid4().hex[:8])
    session_key = session_key or "public-research"
    created = _call(
        "/tabs",
        method="POST",
        body={"userId": user_id, "sessionKey": session_key, "url": url},
        timeout=timeout,
    )
    tab_id = created.get("tabId")
    if not tab_id:
        raise RuntimeError(f"camofox-browser did not return tabId: {created}")
    try:
        query = urllib.parse.urlencode({"userId": user_id, "includeScreenshot": str(bool(include_screenshot)).lower()})
        snap = _call(f"/tabs/{urllib.parse.quote(str(tab_id))}/snapshot?{query}", timeout=timeout)
        final_url = snap.get("url") or created.get("url") or url
        validate_public_url(final_url, allowed_domains)
        return {
            "requested_url": url,
            "url": final_url,
            "title": snap.get("title") or created.get("title"),
            "snapshot": snap.get("snapshot") or snap.get("content") or "",
            "screenshot": snap.get("screenshot") if include_screenshot else None,
            "provider": "camofox-browser-rest",
            "tab_id": tab_id,
        }
    finally:
        try:
            query = urllib.parse.urlencode({"userId": user_id})
            _call(f"/tabs/{urllib.parse.quote(str(tab_id))}?{query}", method="DELETE", timeout=timeout)
        except Exception:
            pass


def fetch_surface(url: str, **kwargs: Any) -> dict[str, Any]:
    return accessibility_to_surface(fetch_snapshot(url, **kwargs))
