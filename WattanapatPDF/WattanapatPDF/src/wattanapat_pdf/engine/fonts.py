"""Locate TrueType fonts that can draw Thai (and Latin) text for watermarks / DOCX->PDF."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# (display name, regular file, bold file)  - Windows file names
_WIN = [
    ("Tahoma", "tahoma.ttf", "tahomabd.ttf"),
    ("Leelawadee UI", "LeelawUI.ttf", "LeelaUIb.ttf"),
    ("Segoe UI", "segoeui.ttf", "segoeuib.ttf"),
    ("Arial", "arial.ttf", "arialbd.ttf"),
    ("Times New Roman", "times.ttf", "timesbd.ttf"),
    ("Angsana New", "angsa.ttf", "angsab.ttf"),
    ("Cordia New", "cordia.ttf", "cordiab.ttf"),
    ("TH Sarabun New", "THSarabunNew.ttf", "THSarabunNew Bold.ttf"),
]
# Linux/macOS fallbacks (used for development and tests)
_NIX = [
    ("Noto Sans Thai", "NotoSansThai-Regular.ttf", "NotoSansThai-Bold.ttf"),
    ("Loma", "Loma.ttf", "Loma-Bold.ttf"),
    ("Garuda", "Garuda.ttf", "Garuda-Bold.ttf"),
    ("DejaVu Sans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ("Liberation Sans", "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
]


def _search_dirs() -> list[Path]:
    if os.name == "nt":
        win = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        user = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
        return [win, user]
    return [Path(p) for p in ("/usr/share/fonts", "/usr/local/share/fonts", str(Path.home() / ".fonts"),
                              "/Library/Fonts", "/System/Library/Fonts/Supplemental")]


_index: dict[str, Path] | None = None


def _file_index() -> dict[str, Path]:
    global _index
    if _index is None:
        _index = {}
        for d in _search_dirs():
            if d.is_dir():
                for f in d.rglob("*"):
                    if f.suffix.lower() == ".ttf":
                        _index.setdefault(f.name.lower(), f)
    return _index


def _find(fname: str) -> Path | None:
    return _file_index().get(fname.lower())


def installed() -> list[tuple[str, Path, Path | None]]:
    """[(display name, regular path, bold path or None)] for fonts present on this machine."""
    out = []
    for name, reg, bold in (_WIN if os.name == "nt" else _NIX + _WIN):
        r = _find(reg)
        if r:
            b = _find(bold)
            out.append((name, r, b))
    return out


@dataclass
class FontChoice:
    name: str          # reportlab font name
    path: str
    covers: bool       # True when every glyph of the requested text exists


def _register(path: Path) -> str:
    rl_name = f"WP-{path.stem}"
    if rl_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(rl_name, str(path)))
    return rl_name


def _covers(rl_name: str, text: str) -> bool:
    cmap = pdfmetrics.getFont(rl_name).face.charToGlyph
    return all(ord(c) in cmap for c in text if not c.isspace())


def pick(text: str, preferred: str = "auto") -> FontChoice:
    """Choose a font. `preferred` may be 'auto', a display name or a .ttf path."""
    cands: list[Path] = []
    if preferred and preferred != "auto":
        pp = Path(preferred)
        if pp.is_file():
            cands.append(pp)
        else:
            cands += [r for n, r, _ in installed() if n.lower() == preferred.lower()]
    cands += [r for _, r, _ in installed()]
    first = None
    for p in cands:
        try:
            nm = _register(p)
        except Exception:
            continue
        first = first or FontChoice(nm, str(p), False)
        if _covers(nm, text):
            return FontChoice(nm, str(p), True)
    if all(ord(c) < 128 for c in text):
        return FontChoice("Helvetica", "", True)
    if first:
        return first
    raise RuntimeError("no usable font")


def family() -> tuple[str, str]:
    """(regular, bold) reportlab names for document rendering, with bold registered as a family."""
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    for _, reg, bold in installed():
        try:
            r = _register(reg)
            nm = _register(bold) if bold else r
            if _covers(r, "กขคabc"):
                registerFontFamily(r, normal=r, bold=nm, italic=r, boldItalic=nm)
                return r, nm
        except Exception:
            continue
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("Helvetica", normal="Helvetica", bold="Helvetica-Bold",
                       italic="Helvetica-Oblique", boldItalic="Helvetica-BoldOblique")
    return "Helvetica", "Helvetica-Bold"
