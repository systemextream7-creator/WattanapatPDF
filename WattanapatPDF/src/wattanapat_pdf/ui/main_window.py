"""Main window: left tool bar | central workspace (stacked pages) | per-page right settings panel."""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import __version__, APP_NAME, APP_NAME_TH
from ..paths import resource_path
from .pages_misc import HomePage, PresetsPage, SecurityPage, SettingsPage
from .pages_tools import (CompressPage, ConvertPage, ImagesPage, MergePage, OrganizePage, ProtectPage, SplitPage,
                          WatermarkPage)
from .theme import icon

TOOL_CLASSES = [MergePage, SplitPage, OrganizePage, ImagesPage, ProtectPage, WatermarkPage, CompressPage, ConvertPage]


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        ctx.main_window = self
        self.setWindowTitle(f"{APP_NAME} — {APP_NAME_TH}")
        self.setWindowIcon(QIcon(str(resource_path("assets/app.ico"))))
        self.resize(1360, 820)
        self.setMinimumSize(1120, 680)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(236)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 14, 0, 10)
        logo = QLabel()
        pm = QPixmap(str(resource_path("assets/logo-lockup-white.png")))
        logo.setPixmap(pm.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(logo)
        sv.addSpacing(8)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(22, 22))
        sv.addWidget(self.nav, 1)
        foot = QLabel(f"เวอร์ชัน {__version__}\nประมวลผลบนเครื่อง 100%")
        foot.setObjectName("navFoot")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(foot)
        h.addWidget(side)

        self.stack = QStackedWidget()
        h.addWidget(self.stack, 1)
        self.index: dict[str, int] = {}
        self._add("home", "หน้าแรก", "home", HomePage(ctx, self.go))
        for cls in TOOL_CLASSES:
            page = cls(ctx)
            ctx.pages[cls.key] = page
            self._add(cls.key, cls.title, cls.icon_name, page)
        self._separator()
        self._add("presets", "ชุดการตั้งค่า", "preset", PresetsPage(ctx))
        self._add("security", "ความปลอดภัย", "shield", SecurityPage(ctx))
        self._add("settings", "ตั้งค่า", "gear", SettingsPage(ctx))
        self.nav.currentRowChanged.connect(self._row_changed)
        self.nav.setCurrentRow(0)
        ctx.message.connect(lambda m: self.statusBar().showMessage(m, 6000))
        self.statusBar().showMessage("พร้อมใช้งาน — ทำงานออฟไลน์")

    def _add(self, key, title, icon_name, page):
        it = QListWidgetItem(icon(icon_name, "white"), title)
        it.setData(Qt.ItemDataRole.UserRole, key)
        self.nav.addItem(it)
        self.index[key] = self.stack.addWidget(page)
        it.setData(Qt.ItemDataRole.UserRole + 1, self.stack.count() - 1)

    def _separator(self):
        it = QListWidgetItem("")
        it.setFlags(Qt.ItemFlag.NoItemFlags)
        it.setSizeHint(QSize(10, 14))
        self.nav.addItem(it)

    def _row_changed(self, row):
        it = self.nav.item(row)
        if it is None:
            return
        idx = it.data(Qt.ItemDataRole.UserRole + 1)
        if idx is not None:
            self.stack.setCurrentIndex(idx)

    def go(self, key: str, paths: list[str] | None = None):
        for r in range(self.nav.count()):
            if self.nav.item(r).data(Qt.ItemDataRole.UserRole) == key:
                self.nav.setCurrentRow(r)
                break
        page = self.ctx.pages.get(key)
        if paths and page is not None:
            page.accept_paths(paths)

    def closeEvent(self, e):
        self.ctx.shutdown()
        super().closeEvent(e)
