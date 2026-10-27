"""Optional update check.  Off by default.  Sends ONLY the program version number."""
from __future__ import annotations
import json, urllib.request, urllib.parse
from . import __version__


def _ver(s: str):
    return tuple(int(x) for x in s.strip().lstrip("v").split(".") if x.isdigit())


def check(url: str, current: str = __version__, timeout: float = 5.0) -> dict:
    if not url.lower().startswith("https://"):
        raise ValueError("ต้องเป็นที่อยู่ HTTPS เท่านั้น")
    q = urllib.parse.urlencode({"v": current})
    full = url + ("&" if "?" in url else "?") + q
    req = urllib.request.Request(full, headers={"User-Agent": f"WattanapatPDF/{current}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (https enforced above)
        data = json.loads(r.read(65536).decode("utf-8"))
    latest = str(data.get("latest", ""))
    return {"latest": latest, "url": str(data.get("url", "")),
            "update_available": bool(latest) and _ver(latest) > _ver(current)}
