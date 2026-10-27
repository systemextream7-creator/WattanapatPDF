"""Shared application state + the bridge between the UI thread and the engine process."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from ..engine.ops import EngineError, PasswordRequired, WrongPassword
from ..engine.service import Cancelled, EngineClient
from ..settings import Settings
from ..sandbox import Sandbox
from .. import applog


class UserError(Exception):
    """Validation problem to show to the user before anything runs."""


@dataclass
class Step:
    op: str
    params: dict
    label: str = ""


@dataclass
class Plan:
    steps: list[Step]
    summary: list[str]                 # human readable settings preview
    inputs: list[str] = field(default_factory=list)
    dest: str = ""


def _code(exc: Exception) -> str:
    if isinstance(exc, PasswordRequired):
        return "password_required"
    if isinstance(exc, WrongPassword):
        return "wrong_password"
    if isinstance(exc, Cancelled):
        return "cancelled"
    return "engine"


class CallThread(QThread):
    """Runs one or more engine calls off the UI thread."""
    progress = Signal(float, str)
    stepDone = Signal(int, object)
    ok = Signal(object)
    err = Signal(str, str, int)        # code, message, step index

    def __init__(self, client: EngineClient, steps: list[Step]):
        super().__init__()
        self.client, self.steps = client, steps

    def run(self):
        results = []
        n = len(self.steps)
        for i, s in enumerate(self.steps):
            try:
                r = self.client.call(s.op, progress=lambda f, t, i=i: self.progress.emit((i + f) / n, t), **s.params)
            except (EngineError, Cancelled) as e:
                self.err.emit(_code(e), str(e), i)
                return
            except Exception as e:  # noqa: BLE001
                applog.log_exception(s.op, e)
                self.err.emit("internal", "เกิดข้อผิดพลาดที่ไม่คาดคิด", i)
                return
            results.append(r)
            self.stepDone.emit(i, r)
        self.ok.emit(results)


class AppContext(QObject):
    presetsChanged = Signal()
    outputChanged = Signal(str)
    message = Signal(str)

    def __init__(self, settings: Settings, sandbox: Sandbox, engine: EngineClient):
        super().__init__()
        self.settings, self.sandbox, self.engine = settings, sandbox, engine
        self.pages: dict[str, object] = {}
        self._threads: set[CallThread] = set()
        self.main_window = None

    # ---------------------------------------------------------------- async
    def run_steps(self, steps: list[Step], ok=None, err=None, progress=None, stepdone=None) -> CallThread:
        t = CallThread(self.engine, steps)
        if ok:
            t.ok.connect(ok)
        if err:
            t.err.connect(err)
        if progress:
            t.progress.connect(progress)
        if stepdone:
            t.stepDone.connect(stepdone)
        self._threads.add(t)
        t.finished.connect(lambda t=t: self._threads.discard(t))
        t.start()
        return t

    def call_async(self, op: str, params: dict, ok: Callable | None = None, err: Callable | None = None) -> CallThread:
        return self.run_steps([Step(op, params)], ok=(lambda r: ok(r[0])) if ok else None,
                              err=(lambda code, msg, i: err(code, msg)) if err else None)

    # ------------------------------------------------------------ PDF intake
    def add_pdfs(self, paths: list[str], each: Callable[[dict], None], parent=None) -> None:
        """Inspect PDFs (asking for a password when needed) and hand each usable one to `each`."""
        queue = [p for p in paths if p]

        def next_one():
            if not queue:
                return
            self._inspect(queue.pop(0), None, each, next_one, parent)
        next_one()

    def _inspect(self, path, password, each, nxt, parent, attempt=0):
        def ok(r):
            if r["needs_password"]:
                return ask(None)
            self.settings.add_recent(path)
            each({"path": path, "password": password, "page_count": r["pages"], "size": r["size"]})
            nxt()

        def ask(_):
            if attempt >= 3:
                self.message.emit(f"ข้ามไฟล์ {os.path.basename(path)} (รหัสผ่านไม่ถูกต้อง)")
                return nxt()
            pw, accepted = QInputDialog.getText(parent, "ไฟล์มีรหัสผ่าน",
                                                f"พิมพ์รหัสผ่านเพื่อเปิด\n{os.path.basename(path)}",
                                                QLineEdit.EchoMode.Password)
            if not accepted:
                return nxt()
            self._inspect(path, pw, each, nxt, parent, attempt + 1)

        def fail(code, msg):
            if code in ("password_required", "wrong_password"):
                return ask(None)
            QMessageBox.warning(parent, "เปิดไฟล์ไม่ได้", f"{os.path.basename(path)}\n\n{msg}")
            nxt()
        self.call_async("inspect", {"path": path, "password": password}, ok, fail)

    # ---------------------------------------------------------------- output
    def output_folder(self) -> str:
        return self.settings.get("output_folder", "") or ""

    def set_output_folder(self, folder: str) -> None:
        self.settings.set("output_folder", folder)
        self.outputChanged.emit(folder)

    def resolve_dest(self, inputs: list[str]) -> str:
        f = self.output_folder()
        if f:
            return f
        return os.path.dirname(os.path.abspath(inputs[0])) if inputs else os.path.expanduser("~")

    # ---------------------------------------------------------------- presets
    def apply_preset(self, i: int) -> None:
        if not (0 <= i < len(self.settings.presets)):
            return
        self.settings.set("active_preset", i)
        p = self.settings.presets[i]
        for page in self.pages.values():
            if hasattr(page, "apply_preset"):
                page.apply_preset(p)
        if p.get("output_folder") is not None:
            self.set_output_folder(p.get("output_folder", ""))
        self.presetsChanged.emit()
        self.message.emit(f"ใช้ชุดการตั้งค่า “{p['name']}” แล้ว")

    def capture_into(self, i: int) -> None:
        part: dict = {}
        for page in self.pages.values():
            if hasattr(page, "preset_part"):
                part.update(page.preset_part() or {})
        part["output_folder"] = self.output_folder()
        self.settings.update_preset(i, part)
        self.presetsChanged.emit()
        self.message.emit(f"บันทึกค่าปัจจุบันลงชุด “{self.settings.presets[i]['name']}” แล้ว")

    def shutdown(self) -> None:
        for t in list(self._threads):
            t.wait(1500)
        self.engine.stop()
        self.sandbox.close()
