"""Sandbox temporary folder: one private folder per session, removed on exit."""
from __future__ import annotations
import os, shutil, uuid, time
from pathlib import Path
from . import paths


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class Sandbox:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else paths.local_dir() / "sandbox"
        self.session = self.root / f"session-{os.getpid()}-{uuid.uuid4().hex[:8]}"

    def start(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        self._purge_stale()
        self.session.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.session, 0o700)
        except OSError:
            pass
        return self.session

    def _purge_stale(self) -> None:
        for d in self.root.glob("session-*"):
            if d == self.session or not d.is_dir():
                continue
            try:
                pid = int(d.name.split("-")[1])
            except (IndexError, ValueError):
                pid = 0
            if not _pid_alive(pid) or time.time() - d.stat().st_mtime > 86400:
                shutil.rmtree(d, ignore_errors=True)

    def stats(self) -> tuple[int, int]:
        n = size = 0
        for f in self.session.rglob("*"):
            if f.is_file():
                n += 1
                try:
                    size += f.stat().st_size
                except OSError:
                    pass
        return n, size

    def clear(self) -> int:
        n, _ = self.stats()
        for c in list(self.session.iterdir()):
            if c.is_dir():
                shutil.rmtree(c, ignore_errors=True)
            else:
                try:
                    c.unlink()
                except OSError:
                    pass
        return n

    def close(self) -> None:
        shutil.rmtree(self.session, ignore_errors=True)
