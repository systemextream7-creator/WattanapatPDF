"""User settings and reusable presets (JSON in the roaming profile).

Presets store *settings only* - never file names, passwords or document content.
"""
from __future__ import annotations
import copy, json, os
from pathlib import Path
from . import paths

DEFAULT_WATERMARK = {"kind": "text", "text": "เอกสารภายใน", "image_path": "", "position": 4,
                     "opacity": 0.25, "font_size": 56, "color": "#808080", "rotation": 45,
                     "font": "auto", "image_scale": 0.4}


def _preset(name, wm_text, level, fmt, allow_print, allow_modify, allow_copy):
    wm = dict(DEFAULT_WATERMARK, text=wm_text)
    return {"name": name, "watermark": wm, "compression": {"level": level},
            "convert": {"format": fmt, "dpi": 150},
            "permissions": {"allow_print": allow_print, "allow_modify": allow_modify, "allow_copy": allow_copy},
            "output_folder": ""}


def default_presets():
    return [
        _preset("ชุดที่ 1", "เอกสารภายใน", "email", "png", True, False, False),
        _preset("ชุดที่ 2", "สำเนา", "quality", "jpeg", True, False, True),
        _preset("ชุดที่ 3", "ห้ามเผยแพร่", "email", "png", False, False, False),
        _preset("ชุดที่ 4", "DRAFT", "smallest", "png", True, True, True),
    ]


DEFAULTS = {
    "language": "th", "output_folder": "", "notify_on_finish": True,
    "remember_recent": True, "recent": [], "update_check_on_start": False,
    "update_url": "", "active_preset": 0, "presets": None,
}


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else paths.data_dir() / "settings.json"
        self.data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, ValueError):
            pass
        if not self.data.get("presets"):
            self.data["presets"] = default_presets()

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def get(self, k, default=None):
        return self.data.get(k, default)

    def set(self, k, v) -> None:
        self.data[k] = v
        self.save()

    # presets ---------------------------------------------------------------
    @property
    def presets(self) -> list:
        return self.data["presets"]

    def add_preset(self, name: str, base: dict | None = None) -> int:
        p = copy.deepcopy(base) if base else default_presets()[0]
        p["name"] = name
        self.presets.append(p)
        self.save()
        return len(self.presets) - 1

    def delete_preset(self, i: int) -> None:
        if len(self.presets) > 1:
            del self.presets[i]
            self.data["active_preset"] = min(self.data.get("active_preset", 0), len(self.presets) - 1)
            self.save()

    def rename_preset(self, i: int, name: str) -> None:
        self.presets[i]["name"] = name
        self.save()

    def update_preset(self, i: int, part: dict) -> None:
        self.presets[i].update(copy.deepcopy(part))
        self.save()

    # recent files (only when the user allows it) ---------------------------
    def add_recent(self, path: str) -> None:
        if not self.data.get("remember_recent"):
            return
        r = [p for p in self.data["recent"] if p != path]
        self.data["recent"] = ([path] + r)[:10]
        self.save()

    def clear_history(self) -> None:
        self.data["recent"] = []
        self.save()
