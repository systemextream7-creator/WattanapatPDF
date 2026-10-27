"""Filesystem locations. Everything the app writes lives under the user's own profile."""
from __future__ import annotations
import os, sys
from pathlib import Path

DIR_NAME = "WattanapatPDF"


def data_dir() -> Path:
    """Settings, presets, error log (roaming profile)."""
    env = os.environ.get("WATTANAPAT_DATA_DIR")
    if env:
        p = Path(env)
    elif os.name == "nt":
        p = Path(os.environ.get("APPDATA", Path.home())) / DIR_NAME
    else:
        p = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def local_dir() -> Path:
    """Machine-local scratch space (sandbox)."""
    env = os.environ.get("WATTANAPAT_LOCAL_DIR")
    if env:
        p = Path(env)
    elif os.name == "nt":
        p = Path(os.environ.get("LOCALAPPDATA", Path.home())) / DIR_NAME
    else:
        p = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / rel
