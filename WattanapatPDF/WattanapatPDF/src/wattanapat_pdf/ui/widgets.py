"""Reusable widgets."""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, Signal, QUrl
from PySide6.QtGui import QColor, QImageReader, QPixmap, QPainter, QIcon, QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QLabel, QListView, QListWidget,
                               QListWidgetItem, QVBoxLayout, QWidget)


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def open_path(path: str) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def banner(text: str, kind: str = "warn") -> QFrame:
    f = QFrame()
    f.setObjectName(kind)
    lay = QHBoxLayout(f)
    lay.setContentsMargins(12, 8, 12, 8)
    lb = QLabel(text)
    lb.setWordWrap(True)
    lay.addWidget(lb)
    return f


def placeholder_pixmap(w: int, h: int, text: str = "") -> QPixmap:
    pm = QPixmap(w, h)
    pm.fill(QColor("#E8EEF5"))
    p = QPainter(pm)
    p.setPen(QColor("#9AA8B8"))
    p.drawRect(0, 0, w - 1, h - 1)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return pm


def image_icon(path: str, box: int = 72) -> QIcon:
    r = QImageReader(path)
    r.setAutoTransform(True)
    sz = r.size()
    if sz.isValid():
        r.setScaledSize(sz.scaled(box * 2, box * 2, Qt.AspectRatioMode.KeepAspectRatio))
    img = r.read()
    return QIcon(QPixmap.fromImage(img)) if not img.isNull() else QIcon(placeholder_pixmap(box, box, "?"))


class FileListWidget(QListWidget):
    """Accepts files dragged from Explorer (filesDropped) and lets the user reorder rows."""
    filesDropped = Signal(list)

    def __init__(self, exts: tuple[str, ...], reorder: bool = True):
        super().__init__()
        self.exts = tuple(e.lower() for e in exts)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if reorder:
            self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            self.setDefaultDropAction(Qt.DropAction.MoveAction)
        else:
            self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setIconSize(QSize(56, 72))
        self.setSpacing(2)

    def set_exts(self, exts: tuple[str, ...]) -> None:
        self.exts = tuple(e.lower() for e in exts)

    def _paths(self, md) -> list[str]:
        out = []
        for u in md.urls():
            if not u.isLocalFile():
                continue
            p = u.toLocalFile()
            if os.path.isdir(p):
                out += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith(self.exts)]
            elif p.lower().endswith(self.exts):
                out.append(p)
        return out

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls() and e.source() is not self:
            e.acceptProposedAction()
            paths = self._paths(e.mimeData())
            if paths:
                self.filesDropped.emit(paths)
        else:
            super().dropEvent(e)

    def entries(self) -> list[dict]:
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]

    def remove_selected(self) -> None:
        for it in self.selectedItems():
            self.takeItem(self.row(it))

    def move_selected(self, delta: int) -> None:
        rows = sorted(self.row(i) for i in self.selectedItems())
        if not rows:
            return
        if delta < 0 and rows[0] == 0 or delta > 0 and rows[-1] == self.count() - 1:
            return
        for r in (rows if delta < 0 else reversed(rows)):
            it = self.takeItem(r)
            self.insertItem(r + delta, it)
            it.setSelected(True)


class PageGrid(QListWidget):
    """Thumbnail grid of PDF pages with drag-to-reorder."""
    orderChanged = Signal()

    def __init__(self):
        super().__init__()
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setMovement(QListView.Movement.Snap)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setWrapping(True)
        self.setSpacing(8)
        self.setUniformItemSizes(True)
        self.set_zoom(150)

    def set_zoom(self, width: int) -> None:
        h = int(width * 1.42)
        self.setIconSize(QSize(width, h))
        self.setGridSize(QSize(width + 24, h + 44))

    def dropEvent(self, e):
        super().dropEvent(e)
        self.orderChanged.emit()


class PreviewLabel(QLabel):
    """Image area that keeps aspect ratio when the pixmap or the widget size changes."""

    def __init__(self, empty_text: str = "ยังไม่มีตัวอย่าง"):
        super().__init__(empty_text)
        self._pm: QPixmap | None = None
        self._empty = empty_text
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self.setObjectName("muted")
        self.setStyleSheet("background:#E8EEF5;border:1px solid #D6E2EF;border-radius:10px;")

    def set_pixmap(self, pm: QPixmap | None) -> None:
        self._pm = pm
        self._refresh()

    def clear_preview(self, text: str | None = None) -> None:
        self._pm = None
        self.setPixmap(QPixmap())
        self.setText(text or self._empty)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refresh()

    def _refresh(self) -> None:
        if self._pm is None or self._pm.isNull():
            return
        self.setPixmap(self._pm.scaled(self.size() - QSize(12, 12), Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation))
