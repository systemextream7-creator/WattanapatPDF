"""Error-only system log.  Never records file names, document text or passwords.

Only the exception *class*, the operation name and the innermost code location
(file:line of our own source) are written - exception messages are dropped on
purpose because they frequently embed user file paths.
"""
from __future__ import annotations
import logging, traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from . import paths

_log = logging.getLogger("wattanapat")
_ready = False


def log_file() -> Path:
    d = paths.data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d / "errors.log"


def setup() -> None:
    global _ready
    if _ready:
        return
    h = RotatingFileHandler(log_file(), maxBytes=256_000, backupCount=2, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _log.setLevel(logging.ERROR)
    _log.addHandler(h)
    _log.propagate = False
    _ready = True


def log_exception(op: str, exc: BaseException) -> None:
    setup()
    where = "?"
    tb = exc.__traceback__
    if tb is not None:
        fr = traceback.extract_tb(tb)[-1]
        where = f"{Path(fr.filename).name}:{fr.lineno}"
    _log.error("op=%s exc=%s at=%s", op, type(exc).__name__, where)


def clear() -> None:
    setup()
    for h in list(_log.handlers):
        h.flush()
    for f in log_file().parent.glob("errors.log*"):
        try:
            f.unlink()
        except OSError:
            try:
                f.write_text("", encoding="utf-8")
            except OSError:
                pass
