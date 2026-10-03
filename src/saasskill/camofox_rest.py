from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import uuid
from typing import Any

from .camoufox_parser import validate_public_url

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
