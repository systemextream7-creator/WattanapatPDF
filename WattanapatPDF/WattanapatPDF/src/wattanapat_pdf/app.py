"""Application bootstrap."""
from __future__ import annotations

import multiprocessing
import sys


def main() -> int:
    multiprocessing.freeze_support()  # required for the engine process in the frozen (.exe) build
    from . import applog
    applog.setup()
    from PySide6.QtWidgets import QApplication, QMessageBox
    from .sandbox import Sandbox
    from .settings import Settings
    from .engine.service import EngineClient
    from .ui import theme
    from .ui.context import AppContext
    from .ui.main_window import MainWindow
    from . import APP_NAME, APP_ORG

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    theme.apply(app)
    sandbox = Sandbox()
    sandbox.start()
    engine = EngineClient(str(sandbox.session))
    ctx = AppContext(Settings(), sandbox, engine)
    try:
        engine.start()
        win = MainWindow(ctx)
    except Exception as e:  # noqa: BLE001
        applog.log_exception("startup", e)
        QMessageBox.critical(None, APP_NAME, "เริ่มโปรแกรมไม่สำเร็จ (บันทึกไว้ในบันทึกข้อผิดพลาดแล้ว)")
        sandbox.close()
        return 1
    win.show()
    app.aboutToQuit.connect(ctx.shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
