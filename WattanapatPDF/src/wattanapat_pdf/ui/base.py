"""Base class for every tool page: [workspace | right-hand settings panel] + run/progress/result."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QProgressBar, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget, QAbstractItemView)

from .context import AppContext, Plan, UserError
from .widgets import FileListWidget, human_size, open_path


class ConfirmDialog(QDialog):
    """Shows source folder(s), destination folder and the settings that will be used - before anything runs."""

    def __init__(self, parent, title: str, plan: Plan):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        v.setSpacing(10)
        h = QLabel("ตรวจสอบก่อนเริ่มประมวลผล")
        h.setObjectName("h2")
        v.addWidget(h)
        folders = sorted({os.path.dirname(os.path.abspath(p)) for p in plan.inputs})
        lines = []
        if folders:
            lines.append("<b>โฟลเดอร์ต้นทาง</b><br>" + "<br>".join(self._esc(f) for f in folders[:4])
                         + ("<br>…" if len(folders) > 4 else ""))
        lines.append("<b>โฟลเดอร์ปลายทาง</b><br>" + self._esc(plan.dest))
        if plan.summary:
            lines.append("<b>ค่าที่จะใช้</b><br>" + "<br>".join("• " + self._esc(s) for s in plan.summary))
        lines.append("<span style='color:#1E8E5A'>ไฟล์ต้นฉบับจะไม่ถูกเขียนทับ ผลลัพธ์จะถูกบันทึกเป็นไฟล์ใหม่เสมอ</span>")
        for t in lines:
            lb = QLabel(t)
            lb.setTextFormat(Qt.TextFormat.RichText)
            lb.setWordWrap(True)
            v.addWidget(lb)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("ยกเลิก")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("เริ่มประมวลผล")
        ok.setProperty("primary", True)
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        v.addLayout(row)

    @staticmethod
    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ListWorkspace(QWidget):
    """File list with add/remove/reorder buttons; `text_fn(entry)` renders each row."""
    addRequested = Signal(list)

    def __init__(self, exts: tuple[str, ...], dialog_filter: str, text_fn, hint: str,
                 reorder: bool = True, single: bool = False):
        super().__init__()
        self.dialog_filter, self.text_fn, self.single = dialog_filter, text_fn, single
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.list = FileListWidget(exts, reorder=reorder and not single)
        self.list.filesDropped.connect(self.addRequested.emit)
        if single:
            self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        v.addWidget(self.list, 1)
        self.hint = QLabel(hint)
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        v.addWidget(self.hint)
        row = QHBoxLayout()
        self.add_btn = QPushButton("เลือกไฟล์…" if single else "เพิ่มไฟล์…")
        self.add_btn.clicked.connect(self._browse)
        row.addWidget(self.add_btn)
        if not single:
            for text, slot in (("▲ ขึ้น", lambda: self.list.move_selected(-1)),
                               ("▼ ลง", lambda: self.list.move_selected(1))):
                b = QPushButton(text)
                b.clicked.connect(slot)
                row.addWidget(b)
        rm = QPushButton("ลบที่เลือก")
        rm.clicked.connect(self.list.remove_selected)
        clr = QPushButton("ล้างทั้งหมด")
        clr.clicked.connect(self.list.clear)
        row.addWidget(rm)
        row.addWidget(clr)
        row.addStretch(1)
        v.addLayout(row)

    def _browse(self):
        files, _ = QFileDialog.getOpenFileNames(self, "เลือกไฟล์", "", self.dialog_filter + ";;ทุกไฟล์ (*.*)")
        if files:
            self.addRequested.emit(files[:1] if self.single else files)

    def add_entry(self, entry: dict, icon=None) -> None:
        if self.single:
            self.list.clear()
        from PySide6.QtWidgets import QListWidgetItem
        it = QListWidgetItem(self.text_fn(entry))
        it.setData(Qt.ItemDataRole.UserRole, entry)
        if icon is not None:
            it.setIcon(icon)
        self.list.addItem(it)
        if self.single:
            it.setSelected(True)

    def entries(self) -> list[dict]:
        return self.list.entries()

    def selected_entries(self) -> list[dict]:
        return [i.data(Qt.ItemDataRole.UserRole) for i in self.list.selectedItems()]

    def refresh_text(self) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setText(self.text_fn(it.data(Qt.ItemDataRole.UserRole)))

    def set_icon_for(self, entry: dict, icon) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) is entry:
                it.setIcon(icon)
                return


def pdf_row_text(e: dict) -> str:
    extra = f" · ช่วงหน้า {e['range']}" if e.get("range") else ""
    pages = f"{e['page_count']} หน้า · " if e.get("page_count") else ""
    return f"{os.path.basename(e['path'])}\n{pages}{human_size(e.get('size', 0))}{extra}"


class ToolPage(QWidget):
    key = ""
    title = ""
    subtitle = ""
    icon_name = "home"
    run_text = "ประมวลผล"
    accept_exts: tuple[str, ...] = (".pdf",)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("page")
        self.setAcceptDrops(True)
        self.ctx = ctx
        self.last_outputs: list[str] = []
        self._thread = None

        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(16)
        left = QVBoxLayout()
        h = QLabel(self.title)
        h.setObjectName("h1")
        sub = QLabel(self.subtitle)
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        left.addWidget(h)
        left.addWidget(sub)
        left.addSpacing(6)
        self.workspace = self.build_workspace()
        left.addWidget(self.workspace, 1)
        outer.addLayout(left, 1)
        outer.addWidget(self._build_panel())
        ctx.presetsChanged.connect(self._reload_presets)
        ctx.outputChanged.connect(self._show_output)
        self._reload_presets()
        self._show_output(ctx.output_folder())

    # ------------------------------------------------------------- hooks ---
    def build_workspace(self) -> QWidget:
        raise NotImplementedError

    def build_options(self) -> QWidget:
        return QWidget()

    def plan(self) -> Plan:
        raise NotImplementedError

    def accept_paths(self, paths: list[str]) -> None: ...
    def clear_all(self) -> None: ...
    def apply_preset(self, p: dict) -> None: ...
    def preset_part(self) -> dict | None:
        return None

    def result_note(self, results: list) -> str:
        return ""

    # ------------------------------------------------------------- panel ---
    def _build_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(360)
        v = QVBoxLayout(panel)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(10)

        lab = QLabel("ชุดการตั้งค่า")
        lab.setObjectName("h2")
        v.addWidget(lab)
        row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.activated.connect(lambda i: self.ctx.apply_preset(i))
        save = QPushButton("บันทึกลงชุด")
        save.setToolTip("บันทึกค่าที่ตั้งไว้ตอนนี้ทับลงในชุดที่เลือก")
        save.clicked.connect(self._save_preset)
        row.addWidget(self.preset_combo, 1)
        row.addWidget(save)
        v.addLayout(row)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        opts = self.build_options()
        opts.setObjectName("page")
        opts.setStyleSheet("QWidget#page{background:transparent;}")
        sc.setWidget(opts)
        v.addWidget(sc, 1)

        v.addWidget(self._sep())
        v.addWidget(QLabel("โฟลเดอร์ปลายทาง"))
        orow = QHBoxLayout()
        self.out_edit = QLineEdit()
        self.out_edit.setReadOnly(True)
        self.out_edit.setPlaceholderText("ข้างไฟล์ต้นฉบับ (ค่าเริ่มต้น)")
        pick = QPushButton("เลือก…")
        pick.clicked.connect(self._pick_output)
        clr = QPushButton("✕")
        clr.setToolTip("กลับไปบันทึกข้างไฟล์ต้นฉบับ")
        clr.setFixedWidth(36)
        clr.clicked.connect(lambda: self.ctx.set_output_folder(""))
        orow.addWidget(self.out_edit, 1)
        orow.addWidget(pick)
        orow.addWidget(clr)
        v.addLayout(orow)

        self.run_btn = QPushButton(self.run_text)
        self.run_btn.setProperty("primary", True)
        self.run_btn.clicked.connect(self.run)
        v.addWidget(self.run_btn)
        self.cancel_btn = QPushButton("ยกเลิกการทำงาน")
        self.cancel_btn.clicked.connect(self.ctx.engine.cancel)
        self.cancel_btn.hide()
        v.addWidget(self.cancel_btn)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        v.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        v.addWidget(self.status)

        self.result_box = QFrame()
        self.result_box.setObjectName("info")
        rb = QVBoxLayout(self.result_box)
        rb.setContentsMargins(10, 8, 10, 8)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("background:transparent;")
        rb.addWidget(self.result_label)
        rrow = QHBoxLayout()
        for text, slot in (("เปิดไฟล์", self._open_file), ("เปิดโฟลเดอร์", self._open_folder),
                           ("ล้างหน้าจอ", self._clear_clicked)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            rrow.addWidget(b)
        rb.addLayout(rrow)
        self.result_box.hide()
        v.addWidget(self.result_box)
        return panel

    @staticmethod
    def _sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("color:#D6E2EF;")
        return f

    # ----------------------------------------------------------- presets ---
    def _reload_presets(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for p in self.ctx.settings.presets:
            self.preset_combo.addItem(p["name"])
        self.preset_combo.setCurrentIndex(self.ctx.settings.get("active_preset", 0))
        self.preset_combo.blockSignals(False)

    def _save_preset(self) -> None:
        i = self.preset_combo.currentIndex()
        name = self.ctx.settings.presets[i]["name"]
        if QMessageBox.question(self, "บันทึกชุดการตั้งค่า",
                                f"บันทึกค่าที่ตั้งไว้ตอนนี้ทับลงในชุด “{name}” ใช่หรือไม่?") == QMessageBox.StandardButton.Yes:
            self.ctx.capture_into(i)

    # ------------------------------------------------------------ output ---
    def _show_output(self, folder: str) -> None:
        self.out_edit.setText(folder or "")

    def _pick_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "เลือกโฟลเดอร์ปลายทาง", self.ctx.output_folder() or os.path.expanduser("~"))
        if d:
            self.ctx.set_output_folder(d)

    # --------------------------------------------------------------- run ---
    def run(self) -> None:
        self.result_box.hide()
        try:
            plan = self.plan()
        except UserError as e:
            QMessageBox.warning(self, "ตรวจสอบข้อมูล", str(e))
            return
        if ConfirmDialog(self, self.title, plan).exec() != QDialog.DialogCode.Accepted:
            return
        self._busy(True)
        self._thread = self.ctx.run_steps(plan.steps, ok=self._ok, err=self._err, progress=self._progress)

    def _busy(self, on: bool) -> None:
        self.run_btn.setEnabled(not on)
        self.cancel_btn.setVisible(on)
        self.progress.setVisible(on)
        if on:
            self.progress.setValue(0)
            self.status.setText("กำลังประมวลผล…")

    def _progress(self, f: float, text: str) -> None:
        self.progress.setValue(int(f * 100))
        if text:
            self.status.setText(text)

    @staticmethod
    def _paths_of(r) -> list[str]:
        if isinstance(r, str):
            return [r]
        if isinstance(r, list):
            return [x for y in r for x in ToolPage._paths_of(y)]
        if isinstance(r, dict) and r.get("path"):
            return [r["path"]]
        return []

    def _ok(self, results: list) -> None:
        self._busy(False)
        self.status.setText("")
        self.last_outputs = self._paths_of(results)
        note = self.result_note(results)
        self.result_label.setText(f"<b>เสร็จสิ้น</b> — สร้างไฟล์ใหม่ {len(self.last_outputs)} รายการ"
                                  + (f"<br>{note}" if note else ""))
        self.result_label.setTextFormat(Qt.TextFormat.RichText)
        self.result_box.show()
        self.ctx.message.emit("ประมวลผลเสร็จสิ้น")
        if self.ctx.settings.get("notify_on_finish", True):
            QApplication.alert(self.window(), 0)

    def _err(self, code: str, msg: str, i: int) -> None:
        self._busy(False)
        self.status.setText("")
        if code == "cancelled":
            self.status.setText("ยกเลิกการทำงานแล้ว")
            return
        QMessageBox.warning(self, "ประมวลผลไม่สำเร็จ", msg)

    def _open_file(self) -> None:
        if self.last_outputs:
            open_path(self.last_outputs[0])

    def _open_folder(self) -> None:
        if self.last_outputs:
            open_path(os.path.dirname(self.last_outputs[0]))

    def _clear_clicked(self) -> None:
        self.result_box.hide()
        self.status.setText("")
        self.clear_all()

    # -------------------------------------------------- drag & drop (page) ---
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p and p.lower().endswith(self.accept_exts):
                paths.append(p)
        if paths:
            e.acceptProposedAction()
            self.accept_paths(paths)
