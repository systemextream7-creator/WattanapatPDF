"""Local IPC between the UI shell and the background processing engine.

The engine runs in its own *process* and talks to the UI over an anonymous local
pipe (multiprocessing.Pipe) - no sockets, no ports, nothing reachable from the network.
"""
from __future__ import annotations

import multiprocessing as mp
import threading
import traceback
from typing import Callable, Optional

from . import ops
from .ops import EngineError, PasswordRequired, WrongPassword


class Cancelled(EngineError):
    pass


def _worker(conn, work_dir: str) -> None:  # runs in the child process
    from .. import applog
    ops.set_work_dir(work_dir)
    while True:
        try:
            msg = conn.recv()
        except (EOFError, OSError):
            break
        if msg is None:
            break
        job, op, params = msg["job"], msg["op"], msg["params"]

        def progress(f, text="", _job=job):
            try:
                conn.send({"job": _job, "type": "progress", "fraction": f, "text": text})
            except (OSError, ValueError):
                pass

        try:
            fn = ops.OPS[op]
            result = fn(**params, progress=progress)
            conn.send({"job": job, "type": "done", "result": result})
        except PasswordRequired as e:
            conn.send({"job": job, "type": "error", "code": "password_required", "message": str(e)})
        except WrongPassword as e:
            conn.send({"job": job, "type": "error", "code": "wrong_password", "message": str(e)})
        except EngineError as e:
            conn.send({"job": job, "type": "error", "code": "engine", "message": str(e)})
        except MemoryError as e:
            applog.log_exception(op, e)
            conn.send({"job": job, "type": "error", "code": "internal",
                       "message": "หน่วยความจำไม่พอสำหรับไฟล์นี้"})
        except Exception as e:  # noqa: BLE001 - last line of defence, logged without file names
            applog.log_exception(op, e)
            conn.send({"job": job, "type": "error", "code": "internal",
                       "message": "เกิดข้อผิดพลาดที่ไม่คาดคิดระหว่างประมวลผล (บันทึกไว้ในบันทึกข้อผิดพลาดแล้ว)"})


class EngineClient:
    """Thread-safe client: one job at a time, blocking `call()`; progress via callback."""

    def __init__(self, work_dir: str):
        self.work_dir = str(work_dir)
        self._lock = threading.Lock()
        self._proc: Optional[mp.Process] = None
        self._conn = None
        self._job = 0
        self._cancelled = False

    def start(self) -> None:
        ctx = mp.get_context("spawn")
        parent, child = ctx.Pipe()
        self._proc = ctx.Process(target=_worker, args=(child, self.work_dir), daemon=True)
        self._proc.start()
        child.close()
        self._conn = parent

    def stop(self) -> None:
        try:
            if self._conn:
                self._conn.send(None)
        except (OSError, ValueError):
            pass
        if self._proc:
            self._proc.join(1.5)
            if self._proc.is_alive():
                self._proc.terminate()
        self._proc = self._conn = None

    def cancel(self) -> None:
        self._cancelled = True
        if self._proc and self._proc.is_alive():
            self._proc.terminate()

    def call(self, op: str, progress: Callable[[float, str], None] | None = None, **params):
        with self._lock:
            if self._proc is None or not self._proc.is_alive():
                self.start()
            self._cancelled = False
            self._job += 1
            job = self._job
            try:
                self._conn.send({"job": job, "op": op, "params": params})
                while True:
                    msg = self._conn.recv()
                    if msg.get("job") != job:
                        continue
                    t = msg["type"]
                    if t == "progress":
                        if progress:
                            progress(msg["fraction"], msg.get("text", ""))
                    elif t == "done":
                        return msg["result"]
                    else:
                        code, text = msg["code"], msg["message"]
                        if code == "password_required":
                            raise PasswordRequired(text)
                        if code == "wrong_password":
                            raise WrongPassword(text)
                        raise EngineError(text)
            except (EOFError, OSError, BrokenPipeError):
                was = self._cancelled
                self._proc = self._conn = None  # next call restarts a fresh engine
                raise Cancelled("ยกเลิกการทำงานแล้ว") if was else EngineError("โปรแกรมประมวลผลหยุดทำงาน กรุณาลองอีกครั้ง")


class DirectClient:
    """Same interface, runs in-process (CLI and tests)."""

    def __init__(self, work_dir: str | None = None):
        if work_dir:
            ops.set_work_dir(work_dir)

    def start(self): ...
    def stop(self): ...
    def cancel(self): ...

    def call(self, op: str, progress=None, **params):
        return ops.OPS[op](**params, progress=progress)
