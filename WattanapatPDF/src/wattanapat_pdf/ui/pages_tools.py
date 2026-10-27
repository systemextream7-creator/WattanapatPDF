"""The eight tool pages."""
from __future__ import annotations

import os
import re

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QColor, QKeySequence, QPixmap, QShortcut, QTransform, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidgetItem, QMessageBox, QPushButton, QRadioButton, QScrollArea,
                               QSlider, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from ..engine import fonts, ops
from ..engine.ops import EngineError
from .base import ListWorkspace, ToolPage, pdf_row_text
from .context import Plan, Step, UserError
from .theme import icon
from .widgets import (FileListWidget, PageGrid, PreviewLabel, banner, human_size, image_icon,
                      placeholder_pixmap)

IMG_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp")


def safe_name(s: str, default: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', "_", (s or "").strip()).strip(". ")
    for ext in (".pdf", ".docx"):
        if s.lower().endswith(ext):
            s = s[: -len(ext)]
    return s or default


def form(*rows) -> QWidget:
    w = QWidget()
    f = QFormLayout(w)
    f.setContentsMargins(2, 4, 2, 4)
    f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
    f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    for label, widget in rows:
        if label is None:
            f.addRow(widget)
        else:
            f.addRow(label, widget)
    return w


def pixmap_from(data: bytes) -> QPixmap:
    pm = QPixmap()
    pm.loadFromData(data)
    return pm


def vbox(*widgets, margins=(0, 0, 0, 0), spacing=8) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(*margins)
    v.setSpacing(spacing)
    for x in widgets:
        v.addWidget(x)
    return w


class PdfListPage(ToolPage):
    """Common behaviour for pages that work on a list of PDF files."""
    multi = True
    hint = "ลากไฟล์ PDF จาก Windows Explorer มาวางที่นี่ หรือกดปุ่ม “เพิ่มไฟล์…”"

    def make_list(self, single=False, reorder=True) -> ListWorkspace:
        self.lw = ListWorkspace((".pdf",), "ไฟล์ PDF (*.pdf)", pdf_row_text, self.hint, reorder=reorder, single=single)
        self.lw.addRequested.connect(self.accept_paths)
        return self.lw

    def accept_paths(self, paths):
        self.ctx.add_pdfs([p for p in paths if p.lower().endswith(".pdf")], self._entry_ready, self)

    def _entry_ready(self, e: dict) -> None:
        self.lw.add_entry(e, QIcon(placeholder_pixmap(56, 72, "PDF")))
        self._load_thumb(e)
        self.entry_added(e)

    def entry_added(self, e: dict) -> None: ...

    def _load_thumb(self, e: dict) -> None:
        def ok(r):
            if r:
                self.lw.set_icon_for(e, QIcon(pixmap_from(r[0]["data"])))
        self.ctx.call_async("render_pages", {"path": e["path"], "indices": [0], "width": 120,
                                             "password": e["password"]}, ok)

    def clear_all(self):
        self.lw.list.clear()

    def paths(self) -> list[str]:
        return [e["path"] for e in self.lw.entries()]

    def need_files(self) -> list[dict]:
        es = self.lw.entries()
        if not es:
            raise UserError("ยังไม่ได้เพิ่มไฟล์ PDF")
        return es


# =================================================================== merge ==
class MergePage(PdfListPage):
    key, title, icon_name, run_text = "merge", "รวมไฟล์ PDF", "merge", "รวมไฟล์เป็น PDF เดียว"
    subtitle = "จัดลำดับไฟล์ใหม่ เลือกเฉพาะบางช่วงหน้า แล้วส่งออกเป็นไฟล์เดียว"

    def build_workspace(self):
        lw = self.make_list()
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("เว้นว่าง = ใช้ทุกหน้า  ตัวอย่าง: 1-3, 7, 10-")
        self.range_edit.setEnabled(False)
        self.range_edit.textEdited.connect(self._range_edited)
        lw.list.itemSelectionChanged.connect(self._sel_changed)
        row = QHBoxLayout()
        row.addWidget(QLabel("ช่วงหน้าของไฟล์ที่เลือก:"))
        row.addWidget(self.range_edit, 1)
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(lw, 1)
        v.addLayout(row)
        return w

    def build_options(self):
        self.name_edit = QLineEdit("merged")
        self.summary = QLabel("")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        return vbox(form(("ชื่อไฟล์ผลลัพธ์", self.name_edit)), self.summary,
                    banner("ลำดับในรายการทางซ้าย = ลำดับหน้าในไฟล์ที่รวม ลากเพื่อสลับตำแหน่งได้", "info"), margins=(2, 2, 2, 2))

    def entry_added(self, e):
        self._summarize()

    def _sel_changed(self):
        sel = self.lw.selected_entries()
        self.range_edit.setEnabled(len(sel) == 1)
        self.range_edit.setText(sel[0].get("range", "") if len(sel) == 1 else "")
        self.range_edit.setStyleSheet("")

    def _range_edited(self, text):
        sel = self.lw.selected_entries()
        if len(sel) != 1:
            return
        e = sel[0]
        try:
            if text.strip():
                ops.parse_ranges(text, e["page_count"])
            self.range_edit.setStyleSheet("")
            e["range"] = text.strip()
        except EngineError:
            self.range_edit.setStyleSheet("border:1px solid #C0392B;")
            e["range"] = ""
        self.lw.refresh_text()
        self._summarize()

    def _summarize(self):
        es = self.lw.entries()
        total = sum(len(ops.parse_ranges(e["range"], e["page_count"])) if e.get("range") else e["page_count"] for e in es)
        self.summary.setText(f"{len(es)} ไฟล์ · รวม {total} หน้า" if es else "")

    def plan(self):
        es = self.need_files()
        for e in es:
            if e.get("range"):
                try:
                    ops.parse_ranges(e["range"], e["page_count"])
                except EngineError as ex:
                    raise UserError(f"{os.path.basename(e['path'])}: {ex}")
        dest = self.ctx.resolve_dest([e["path"] for e in es])
        name = safe_name(self.name_edit.text(), "merged") + ".pdf"
        items = [{"path": e["path"], "password": e["password"], "pages": e.get("range", "")} for e in es]
        total = self.summary.text()
        return Plan([Step("merge", {"items": items, "out_path": os.path.join(dest, name)}, "รวมไฟล์")],
                    [f"รวม {total}", f"ชื่อไฟล์: {name}"], [e["path"] for e in es], dest)

    def clear_all(self):
        super().clear_all()
        self.summary.setText("")


# =================================================================== split ==
class SplitPage(PdfListPage):
    key, title, icon_name, run_text = "split", "แยกหน้า PDF", "split", "แยกเป็นไฟล์ย่อย"
    subtitle = "แยกเอกสารตามช่วงหน้า เช่น 1-5, 8, 12-15 หรือแยกทุกหน้าเป็นไฟล์ละหน้า"

    def build_workspace(self):
        lw = self.make_list(single=True)
        lw.setMaximumHeight(190)
        self.preview = PreviewLabel("ตัวอย่างหน้าแรกจะแสดงที่นี่")
        return vbox(lw, self.preview, spacing=10)

    def build_options(self):
        self.r_ranges = QRadioButton("ตามช่วงหน้าที่กำหนด")
        self.r_each = QRadioButton("แยกทุกหน้า (ไฟล์ละหน้า)")
        self.r_ranges.setChecked(True)
        self.ranges = QLineEdit()
        self.ranges.setPlaceholderText("เช่น 1-5, 8, 12-15")
        self.r_each.toggled.connect(lambda on: self.ranges.setEnabled(not on))
        self.ranges.textChanged.connect(self._name_preview)
        self.r_each.toggled.connect(self._name_preview)
        self.names = QLabel("")
        self.names.setObjectName("muted")
        self.names.setWordWrap(True)
        return vbox(self.r_ranges, self.ranges, self.r_each, self.names,
                    banner("1 ช่วง = 1 ไฟล์ ชื่อไฟล์ใหม่ตั้งอัตโนมัติตามเลขหน้า รองรับไฟล์ใหญ่โดยไม่กินหน่วยความจำมาก", "info"),
                    margins=(2, 2, 2, 2))

    def entry_added(self, e):
        self.preview.clear_preview("กำลังโหลดตัวอย่าง…")
        self.ctx.call_async("render_pages", {"path": e["path"], "indices": [0], "width": 520, "password": e["password"]},
                            lambda r: self.preview.set_pixmap(pixmap_from(r[0]["data"])) if r else None)
        self._name_preview()

    def _name_preview(self, *_):
        es = self.lw.entries()
        if not es:
            self.names.setText("")
            return
        stem = os.path.splitext(os.path.basename(es[0]["path"]))[0]
        if self.r_each.isChecked():
            self.names.setText(f"จะได้ {es[0]['page_count']} ไฟล์ เช่น {stem}_p1.pdf …")
            return
        try:
            g = ops.parse_range_groups(self.ranges.text(), es[0]["page_count"])
            self.names.setText("จะได้ไฟล์: " + ", ".join(f"{stem}_p{lbl}.pdf" for lbl, _ in g[:4]) + (" …" if len(g) > 4 else ""))
        except EngineError:
            self.names.setText("")

    def plan(self):
        e = self.need_files()[0]
        mode = "each" if self.r_each.isChecked() else "ranges"
        if mode == "ranges":
            try:
                ops.parse_range_groups(self.ranges.text(), e["page_count"])
            except EngineError as ex:
                raise UserError(str(ex))
        dest = self.ctx.resolve_dest([e["path"]])
        desc = "แยกทุกหน้า" if mode == "each" else f"ช่วงหน้า: {self.ranges.text().strip()}"
        return Plan([Step("split", {"src": e["path"], "out_dir": dest, "mode": mode,
                                    "ranges_text": self.ranges.text(), "password": e["password"]}, "แยกหน้า")],
                    [desc, f"จำนวนหน้าต้นฉบับ: {e['page_count']}"], [e["path"]], dest)

    def clear_all(self):
        super().clear_all()
        self.preview.clear_preview()
        self.names.setText("")


# ================================================================ organize ==
class OrganizePage(ToolPage):
    key, title, icon_name, run_text = "organize", "จัดการหน้า", "organize", "บันทึกเป็นไฟล์ใหม่"
    subtitle = "ลากสลับหน้า หมุน ลบ ดูตัวอย่าง และย้อนกลับได้หลายขั้น — ไม่แก้ไฟล์ต้นฉบับจนกว่าคุณจะสั่งบันทึกเป็นไฟล์ใหม่"

    def build_workspace(self):
        self.entry = None
        self.order: list[int] = []
        self.rot: dict[int, int] = {}
        self.hist: list[tuple] = []
        self.hpos = -1
        self.thumbs: dict[int, QPixmap] = {}
        self._token = 0
        self._ptoken = 0

        bar = QHBoxLayout()
        open_btn = QPushButton("เปิดไฟล์ PDF…")
        open_btn.clicked.connect(self._browse)
        bar.addWidget(open_btn)

        def tb(text, tip, slot):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            bar.addWidget(b)
            return b
        self.b_undo = tb("↶ ย้อนกลับ", "Ctrl+Z", self.undo)
        self.b_redo = tb("↷ ทำซ้ำ", "Ctrl+Y", self.redo)
        self.b_rl = tb("⟲ หมุนซ้าย", "หมุนหน้าที่เลือก 90° ทวนเข็ม", lambda: self.rotate(-90))
        self.b_rr = tb("⟳ หมุนขวา", "หมุนหน้าที่เลือก 90° ตามเข็ม", lambda: self.rotate(90))
        self.b_del = tb("ลบหน้า", "ลบหน้าที่เลือก (Delete)", self.delete)
        self.b_left = tb("◀", "ย้ายไปทางซ้าย", lambda: self.move(-1))
        self.b_right = tb("▶", "ย้ายไปทางขวา", lambda: self.move(1))
        tb("เลือกทั้งหมด", "Ctrl+A", lambda: self.grid.selectAll())
        bar.addStretch(1)
        bar.addWidget(QLabel("ขนาด"))
        z = QSlider(Qt.Orientation.Horizontal)
        z.setRange(90, 260)
        z.setValue(150)
        z.setFixedWidth(110)
        z.valueChanged.connect(self._zoom)
        bar.addWidget(z)

        self.grid = PageGrid()
        self.grid.itemSelectionChanged.connect(self._sel_changed)
        self.grid.orderChanged.connect(self._order_changed)
        self.grid.itemDoubleClicked.connect(self._full_preview)
        self.info = QLabel("เปิดไฟล์ PDF หรือลากไฟล์มาวางที่หน้านี้")
        self.info.setObjectName("muted")

        for seq, slot in (("Ctrl+Z", self.undo), ("Ctrl+Y", self.redo), ("Delete", self.delete)):
            QShortcut(QKeySequence(seq), self.grid, activated=slot)
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.addLayout(bar)
        v.addWidget(self.grid, 1)
        v.addWidget(self.info)
        self._update_buttons()
        return w

    def build_options(self):
        self.preview = PreviewLabel("เลือกหน้าเดียวเพื่อดูตัวอย่างขนาดใหญ่")
        self.preview.setMinimumHeight(260)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("ชื่อไฟล์ใหม่")
        return vbox(self.preview, form(("ชื่อไฟล์ใหม่", self.name_edit)),
                    banner("ดับเบิลคลิกที่หน้าเพื่อดูภาพเต็ม · ย้อนกลับ/ทำซ้ำได้หลายระดับ (Ctrl+Z / Ctrl+Y)", "info"),
                    margins=(2, 2, 2, 2))

    # ---- loading
    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "เลือกไฟล์ PDF", "", "ไฟล์ PDF (*.pdf)")
        if f:
            self.accept_paths([f])

    def accept_paths(self, paths):
        self.ctx.add_pdfs(paths[:1], self.load, self)

    def load(self, entry: dict):
        self.entry = entry
        self.order = list(range(entry["page_count"]))
        self.rot = {}
        self.thumbs = {}
        self.hist, self.hpos = [], -1
        self._push()
        self._token += 1
        self.name_edit.setText(os.path.splitext(os.path.basename(entry["path"]))[0] + "_edited")
        self.refresh()
        self._load_batch(0, self._token)

    def _load_batch(self, start: int, token: int):
        if not self.entry or start >= self.entry["page_count"]:
            return
        idx = list(range(start, min(start + 8, self.entry["page_count"])))

        def ok(r):
            if token != self._token:
                return
            for x in r:
                self.thumbs[x["index"]] = pixmap_from(x["data"])
            self._refresh_icons()
            self._load_batch(start + 8, token)
        self.ctx.call_async("render_pages", {"path": self.entry["path"], "indices": idx, "width": 240,
                                             "password": self.entry["password"]}, ok)

    # ---- model / history
    def _snap(self):
        return (tuple(self.order), dict(self.rot))

    def _push(self):
        del self.hist[self.hpos + 1:]
        self.hist.append(self._snap())
        self.hist = self.hist[-100:]
        self.hpos = len(self.hist) - 1

    def _restore(self):
        o, r = self.hist[self.hpos]
        self.order, self.rot = list(o), dict(r)
        self.refresh()

    def undo(self):
        if self.hpos > 0:
            self.hpos -= 1
            self._restore()

    def redo(self):
        if self.hpos < len(self.hist) - 1:
            self.hpos += 1
            self._restore()

    def _selected(self) -> list[int]:
        return [i.data(Qt.ItemDataRole.UserRole) for i in self.grid.selectedItems()]

    def rotate(self, deg: int):
        sel = self._selected()
        if not sel:
            return
        for s in sel:
            self.rot[s] = (self.rot.get(s, 0) + deg) % 360
        self._push()
        self.refresh(sel)

    def delete(self):
        sel = set(self._selected())
        if not sel:
            return
        self.order = [s for s in self.order if s not in sel]
        self._push()
        self.refresh()

    def move(self, delta: int):
        sel = set(self._selected())
        pos = sorted(i for i, s in enumerate(self.order) if s in sel)
        if not pos or (delta < 0 and pos[0] == 0) or (delta > 0 and pos[-1] == len(self.order) - 1):
            return
        for i in (pos if delta < 0 else reversed(pos)):
            self.order[i], self.order[i + delta] = self.order[i + delta], self.order[i]
        self._push()
        self.refresh(list(sel))

    def _order_changed(self):
        new = [self.grid.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.grid.count())]
        if new != self.order:
            sel = self._selected()
            self.order = new
            self._push()
            self.refresh(sel)

    # ---- view
    def _icon(self, src: int) -> QIcon:
        pm = self.thumbs.get(src) or placeholder_pixmap(150, 212, "…")
        r = self.rot.get(src, 0) % 360
        if r:
            pm = pm.transformed(QTransform().rotate(r), Qt.TransformationMode.SmoothTransformation)
        return QIcon(pm)

    def refresh(self, keep: list[int] | None = None):
        keep_s = set(keep or [])
        self.grid.blockSignals(True)
        self.grid.clear()
        for pos, src in enumerate(self.order):
            it = QListWidgetItem(self._icon(src), str(pos + 1))
            it.setData(Qt.ItemDataRole.UserRole, src)
            it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.grid.addItem(it)
            if src in keep_s:
                it.setSelected(True)
        self.grid.blockSignals(False)
        total = self.entry["page_count"] if self.entry else 0
        if self.entry:
            self.info.setText(f"{os.path.basename(self.entry['path'])} · เหลือ {len(self.order)} จาก {total} หน้า")
        self._sel_changed()

    def _refresh_icons(self):
        for i in range(self.grid.count()):
            it = self.grid.item(i)
            it.setIcon(self._icon(it.data(Qt.ItemDataRole.UserRole)))

    def _zoom(self, v: int):
        self.grid.set_zoom(v)

    def _update_buttons(self):
        has_sel = bool(self.grid.selectedItems()) if hasattr(self, "grid") else False
        for b in (self.b_rl, self.b_rr, self.b_del, self.b_left, self.b_right):
            b.setEnabled(has_sel)
        self.b_undo.setEnabled(self.hpos > 0)
        self.b_redo.setEnabled(self.hpos < len(self.hist) - 1)

    def _sel_changed(self):
        self._update_buttons()
        sel = self._selected()
        if len(sel) != 1 or not self.entry:
            self.preview.clear_preview(f"เลือกแล้ว {len(sel)} หน้า" if sel else "เลือกหน้าเดียวเพื่อดูตัวอย่างขนาดใหญ่")
            return
        self._ptoken += 1
        tok, src = self._ptoken, sel[0]

        def ok(r):
            if tok == self._ptoken and r:
                pm = pixmap_from(r[0]["data"])
                if self.rot.get(src, 0) % 360:
                    pm = pm.transformed(QTransform().rotate(self.rot[src] % 360), Qt.TransformationMode.SmoothTransformation)
                self.preview.set_pixmap(pm)
        self.ctx.call_async("render_pages", {"path": self.entry["path"], "indices": [src], "width": 640,
                                             "password": self.entry["password"]}, ok)

    def _full_preview(self, item):
        if not self.entry:
            return
        src = item.data(Qt.ItemDataRole.UserRole)
        rot = self.rot.get(src, 0) % 360
        dlg = QDialog(self)
        dlg.setWindowTitle(f"หน้า {self.order.index(src) + 1}")
        dlg.resize(820, 900)
        v = QVBoxLayout(dlg)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        lb = QLabel("กำลังโหลด…")
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc.setWidget(lb)
        v.addWidget(sc)

        def ok(r):
            if r:
                pm = pixmap_from(r[0]["data"])
                if rot:
                    pm = pm.transformed(QTransform().rotate(rot), Qt.TransformationMode.SmoothTransformation)
                lb.setPixmap(pm)
        self.ctx.call_async("render_pages", {"path": self.entry["path"], "indices": [src], "width": 1100,
                                             "password": self.entry["password"]}, ok)
        dlg.exec()

    # ---- run
    def plan(self):
        if not self.entry:
            raise UserError("ยังไม่ได้เปิดไฟล์ PDF")
        if not self.order:
            raise UserError("ไม่มีหน้าเหลือให้บันทึก (ลบครบทุกหน้าแล้ว)")
        dest = self.ctx.resolve_dest([self.entry["path"]])
        name = safe_name(self.name_edit.text(), "edited") + ".pdf"
        pages = [[s, self.rot.get(s, 0)] for s in self.order]
        rotated = sum(1 for s in self.order if self.rot.get(s, 0) % 360)
        return Plan([Step("organize", {"src": self.entry["path"], "pages": pages, "out_path": os.path.join(dest, name),
                                       "password": self.entry["password"]}, "จัดเรียงหน้า")],
                    [f"บันทึก {len(self.order)} จาก {self.entry['page_count']} หน้า", f"หน้าที่หมุน: {rotated}",
                     f"ชื่อไฟล์: {name}"], [self.entry["path"]], dest)

    def clear_all(self):
        self.entry = None
        self.order, self.rot, self.thumbs = [], {}, {}
        self.hist, self.hpos = [], -1
        self._token += 1
        self.grid.clear()
        self.preview.clear_preview()
        self.name_edit.clear()
        self.info.setText("เปิดไฟล์ PDF หรือลากไฟล์มาวางที่หน้านี้")
        self._update_buttons()


# ================================================================== images ==
class ImagesPage(ToolPage):
    key, title, icon_name, run_text = "images", "รูปภาพ → PDF", "image", "สร้างไฟล์ PDF"
    subtitle = "รวมรูปภาพ (JPEG, PNG, TIFF…) เป็น PDF ฉบับเดียว เหมาะกับใบเสร็จและเอกสารสแกน"
    accept_exts = IMG_EXTS

    def build_workspace(self):
        self.lw = ListWorkspace(IMG_EXTS, "รูปภาพ (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp)",
                                lambda e: f"{os.path.basename(e['path'])}\n{human_size(e.get('size', 0))}",
                                "ลากรูปภาพมาวางที่นี่ ลำดับในรายการ = ลำดับหน้า")
        self.lw.addRequested.connect(self.accept_paths)
        return self.lw

    def build_options(self):
        self.size_combo = QComboBox()
        self.size_combo.addItem("A4 (หมุนอัตโนมัติตามรูป)", "A4")
        self.size_combo.addItem("พอดีกับขนาดรูปภาพ", "fit")
        self.margin = QSpinBox()
        self.margin.setRange(0, 50)
        self.margin.setValue(10)
        self.margin.setSuffix(" มม.")
        self.size_combo.currentIndexChanged.connect(lambda: self.margin.setEnabled(self.size_combo.currentData() == "A4"))
        self.name_edit = QLineEdit("images")
        return vbox(form(("ขนาดหน้ากระดาษ", self.size_combo), ("ขอบกระดาษ", self.margin), ("ชื่อไฟล์ผลลัพธ์", self.name_edit)),
                    margins=(2, 2, 2, 2))

    def accept_paths(self, paths):
        for p in paths:
            if p.lower().endswith(IMG_EXTS) and os.path.isfile(p):
                self.ctx.settings.add_recent(p)
                self.lw.add_entry({"path": p, "size": os.path.getsize(p)}, image_icon(p))

    def clear_all(self):
        self.lw.list.clear()

    def plan(self):
        es = self.lw.entries()
        if not es:
            raise UserError("ยังไม่ได้เพิ่มรูปภาพ")
        dest = self.ctx.resolve_dest([es[0]["path"]])
        name = safe_name(self.name_edit.text(), "images") + ".pdf"
        a4 = self.size_combo.currentData() == "A4"
        return Plan([Step("images_to_pdf", {"images": [e["path"] for e in es], "out_path": os.path.join(dest, name),
                                            "page_size": self.size_combo.currentData(),
                                            "margin_mm": self.margin.value() if a4 else 0}, "สร้าง PDF")],
                    [f"{len(es)} รูป → {len(es)} หน้า", "หน้ากระดาษ: " + self.size_combo.currentText(), f"ชื่อไฟล์: {name}"],
                    [e["path"] for e in es], dest)


# ================================================================== protect ==
class ProtectPage(PdfListPage):
    key, title, icon_name, run_text = "protect", "ใส่รหัสผ่าน PDF", "lock", "เข้ารหัสไฟล์"
    subtitle = "ตั้งรหัสเปิดอ่าน (User) และรหัสควบคุมสิทธิ์ (Owner) ด้วยการเข้ารหัส AES-256"

    def build_workspace(self):
        return self.make_list()

    def build_options(self):
        self.user_pw, self.user_pw2, self.owner_pw = QLineEdit(), QLineEdit(), QLineEdit()
        for e in (self.user_pw, self.user_pw2, self.owner_pw):
            e.setEchoMode(QLineEdit.EchoMode.Password)
        self.user_pw.setPlaceholderText("เว้นว่าง = เปิดอ่านได้โดยไม่ต้องใช้รหัส")
        self.owner_pw.setPlaceholderText("ใช้ปลดล็อกสิทธิ์ (แนะนำให้ตั้ง)")
        show = QCheckBox("แสดงรหัสผ่าน")
        show.toggled.connect(lambda on: [e.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)
                                         for e in (self.user_pw, self.user_pw2, self.owner_pw)])
        self.a_print = QCheckBox("อนุญาตให้พิมพ์")
        self.a_modify = QCheckBox("อนุญาตให้แก้ไขเนื้อหา")
        self.a_copy = QCheckBox("อนุญาตให้คัดลอกข้อความ")
        for c in (self.a_print, self.a_modify, self.a_copy):
            c.setChecked(True)
        return vbox(form(("รหัสเปิดอ่าน", self.user_pw), ("ยืนยันรหัสเปิดอ่าน", self.user_pw2), ("รหัสเจ้าของ", self.owner_pw)),
                    show, self.a_print, self.a_modify, self.a_copy,
                    banner("โปรแกรมไม่บันทึกรหัสผ่านไว้ที่ใด (ไม่อยู่ในบันทึกข้อผิดพลาด ชุดตั้งค่า หรือไฟล์ชั่วคราว) "
                           "หากลืมรหัสเปิดอ่านจะกู้คืนไม่ได้", "info"), margins=(2, 2, 2, 2))

    def _perms(self):
        return {"allow_print": self.a_print.isChecked(), "allow_modify": self.a_modify.isChecked(),
                "allow_copy": self.a_copy.isChecked()}

    def preset_part(self):
        return {"permissions": self._perms()}

    def apply_preset(self, p):
        q = p.get("permissions", {})
        self.a_print.setChecked(q.get("allow_print", True))
        self.a_modify.setChecked(q.get("allow_modify", True))
        self.a_copy.setChecked(q.get("allow_copy", True))

    def plan(self):
        es = self.need_files()
        if self.user_pw.text() != self.user_pw2.text():
            raise UserError("รหัสเปิดอ่านกับช่องยืนยันไม่ตรงกัน")
        perms = self._perms()
        if not self.user_pw.text() and not self.owner_pw.text() and all(perms.values()):
            raise UserError("กรุณาตั้งรหัสผ่านอย่างน้อยหนึ่งรหัส หรือเอาเครื่องหมายอนุญาตบางรายการออกเพื่อจำกัดสิทธิ์")
        dest = self.ctx.resolve_dest([es[0]["path"]])
        steps = []
        for e in es:
            stem = os.path.splitext(os.path.basename(e["path"]))[0]
            steps.append(Step("protect", {"src": e["path"], "out_path": os.path.join(dest, stem + "_protected.pdf"),
                                          "user_password": self.user_pw.text(), "owner_password": self.owner_pw.text(),
                                          "password": e["password"], **perms}, "เข้ารหัส"))
        yn = lambda b: "อนุญาต" if b else "ไม่อนุญาต"
        summ = [f"{len(es)} ไฟล์ · AES-256", "รหัสเปิดอ่าน: " + ("ตั้งไว้" if self.user_pw.text() else "ไม่ตั้ง"),
                "รหัสเจ้าของ: " + ("ตั้งไว้" if self.owner_pw.text() else "ไม่ตั้ง"),
                f"พิมพ์: {yn(perms['allow_print'])} · แก้ไข: {yn(perms['allow_modify'])} · คัดลอก: {yn(perms['allow_copy'])}"]
        if not self.owner_pw.text() and not all(perms.values()):
            summ.append("คำเตือน: ไม่ได้ตั้งรหัสเจ้าของ จะไม่สามารถปลดล็อกสิทธิ์ที่จำกัดไว้ได้อีก")
        return Plan(steps, summ, [e["path"] for e in es], dest)

    def clear_all(self):
        super().clear_all()
        for e in (self.user_pw, self.user_pw2, self.owner_pw):
            e.clear()


# ================================================================ watermark ==
class WatermarkPage(PdfListPage):
    key, title, icon_name, run_text = "watermark", "ประทับลายน้ำ", "watermark", "ประทับลายน้ำ"
    subtitle = "ลายน้ำข้อความหรือรูปตรายาง เลือกตำแหน่ง 9 จุด ปรับความโปร่งใส/สี/องศา พร้อมดูผลแบบเรียลไทม์"

    def build_workspace(self):
        lw = self.make_list(reorder=False)
        lw.setMaximumHeight(170)
        lw.list.itemSelectionChanged.connect(self._schedule)
        self.preview = PreviewLabel("ตัวอย่างหน้าแรกพร้อมลายน้ำจะแสดงที่นี่")
        self.preview.setMinimumSize(320, 360)
        return vbox(lw, self.preview, spacing=10)

    def build_options(self):
        self.color = "#808080"
        self.r_text, self.r_img = QRadioButton("ข้อความ"), QRadioButton("รูปภาพ/ตรายาง")
        self.r_text.setChecked(True)
        kind = QWidget()
        kl = QHBoxLayout(kind)
        kl.setContentsMargins(0, 0, 0, 0)
        kl.addWidget(self.r_text)
        kl.addWidget(self.r_img)
        self.text = QLineEdit("เอกสารภายใน")
        self.img_path = QLineEdit()
        self.img_path.setReadOnly(True)
        self.img_path.setPlaceholderText("เลือกรูป PNG/JPEG")
        img_btn = QPushButton("เลือกรูป…")
        img_btn.clicked.connect(self._pick_image)
        imgrow = QWidget()
        il = QHBoxLayout(imgrow)
        il.setContentsMargins(0, 0, 0, 0)
        il.addWidget(self.img_path, 1)
        il.addWidget(img_btn)
        self.img_scale = QSpinBox()
        self.img_scale.setRange(5, 100)
        self.img_scale.setValue(40)
        self.img_scale.setSuffix(" % ของความกว้างหน้า")
        self.font = QComboBox()
        self.font.addItem("อัตโนมัติ (รองรับภาษาไทย)", "auto")
        for name, path, _ in fonts.installed():
            self.font.addItem(name, name)
        self.size = QSpinBox()
        self.size.setRange(6, 300)
        self.size.setValue(56)
        self.color_btn = QPushButton("  เลือกสี")
        self.color_btn.clicked.connect(self._pick_color)
        self._paint_color()
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(5, 100)
        self.opacity.setValue(25)
        self.opacity_lbl = QLabel("25%")
        orow = QWidget()
        ol = QHBoxLayout(orow)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(self.opacity, 1)
        ol.addWidget(self.opacity_lbl)
        self.rotation = QSpinBox()
        self.rotation.setRange(-180, 180)
        self.rotation.setValue(45)
        self.rotation.setSuffix("°")
        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText("เว้นว่าง = ทุกหน้า เช่น 1-3, 5")

        grid = QWidget()
        gl = QGridLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(4)
        self.pos = 4
        self.pos_btns: list[QToolButton] = []
        for i in range(9):
            b = QToolButton()
            b.setCheckable(True)
            b.setFixedSize(40, 30)
            b.setText("●" if i == 4 else "○")
            b.clicked.connect(lambda _=False, i=i: self._set_pos(i))
            gl.addWidget(b, i // 3, i % 3)
            self.pos_btns.append(b)
        self.pos_btns[4].setChecked(True)

        for w in (self.text,):
            w.textChanged.connect(self._schedule)
        for w in (self.size, self.rotation, self.img_scale):
            w.valueChanged.connect(self._schedule)
        self.opacity.valueChanged.connect(lambda v: (self.opacity_lbl.setText(f"{v}%"), self._schedule()))
        self.font.currentIndexChanged.connect(self._schedule)
        self.r_text.toggled.connect(self._schedule)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._do_preview)
        self._tok = 0

        return vbox(form((None, kind), ("ข้อความ", self.text), ("รูปภาพ", imgrow), ("ขนาดรูป", self.img_scale),
                         ("ฟอนต์", self.font), ("ขนาดตัวอักษร", self.size), ("สี", self.color_btn),
                         ("ความทึบ", orow), ("องศาหมุน", self.rotation), ("ตำแหน่ง", grid), ("ช่วงหน้า", self.pages_edit)),
                    margins=(2, 2, 2, 2))

    # ---- helpers
    def _set_pos(self, i: int):
        self.pos = i
        for k, b in enumerate(self.pos_btns):
            b.setChecked(k == i)
            b.setText("●" if k == i else "○")
        self._schedule()

    def _paint_color(self):
        self.color_btn.setStyleSheet(f"QPushButton{{border-left:22px solid {self.color};}}")

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, "เลือกสีลายน้ำ")
        if c.isValid():
            self.color = c.name()
            self._paint_color()
            self._schedule()

    def _pick_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "เลือกรูปลายน้ำ/ตรายาง", "", "รูปภาพ (*.png *.jpg *.jpeg)")
        if f:
            self.img_path.setText(f)
            self.r_img.setChecked(True)
            self._schedule()

    def spec(self) -> dict:
        return {"kind": "image" if self.r_img.isChecked() else "text", "text": self.text.text(),
                "image_path": self.img_path.text(), "position": self.pos, "opacity": self.opacity.value() / 100.0,
                "font_size": self.size.value(), "color": self.color, "rotation": self.rotation.value(),
                "font": self.font.currentData() or "auto", "image_scale": self.img_scale.value() / 100.0,
                "pages": self.pages_edit.text().strip()}

    def preset_part(self):
        s = self.spec()
        s.pop("pages")
        return {"watermark": s}

    def apply_preset(self, p):
        w = p.get("watermark", {})
        widgets = (self.text, self.img_path, self.size, self.opacity, self.rotation, self.img_scale, self.font, self.r_img, self.r_text)
        for x in widgets:
            x.blockSignals(True)
        self.r_img.setChecked(w.get("kind") == "image")
        self.r_text.setChecked(w.get("kind") != "image")
        self.text.setText(w.get("text", ""))
        self.img_path.setText(w.get("image_path", ""))
        self.size.setValue(int(w.get("font_size", 56)))
        self.opacity.setValue(int(round(w.get("opacity", 0.25) * 100)))
        self.opacity_lbl.setText(f"{self.opacity.value()}%")
        self.rotation.setValue(int(w.get("rotation", 45)))
        self.img_scale.setValue(int(round(w.get("image_scale", 0.4) * 100)))
        i = self.font.findData(w.get("font", "auto"))
        self.font.setCurrentIndex(max(0, i))
        for x in widgets:
            x.blockSignals(False)
        self.color = w.get("color", "#808080")
        self._paint_color()
        self._set_pos(int(w.get("position", 4)))

    # ---- live preview
    def entry_added(self, e):
        self._schedule()

    def _schedule(self, *_):
        self._timer.start()

    def _do_preview(self):
        es = self.lw.selected_entries() or self.lw.entries()
        if not es:
            self.preview.clear_preview()
            return
        s = self.spec()
        if s["kind"] == "text" and not s["text"].strip():
            self.preview.clear_preview("พิมพ์ข้อความลายน้ำเพื่อดูตัวอย่าง")
            return
        if s["kind"] == "image" and not s["image_path"]:
            self.preview.clear_preview("เลือกรูปภาพลายน้ำเพื่อดูตัวอย่าง")
            return
        self._tok += 1
        tok = self._tok
        e = es[0]
        self.ctx.call_async("watermark_preview", {"src": e["path"], "spec": s, "width": 640, "password": e["password"]},
                            lambda r: self.preview.set_pixmap(pixmap_from(r["data"])) if tok == self._tok else None,
                            lambda c, m: self.preview.clear_preview(m) if tok == self._tok else None)

    def plan(self):
        es = self.need_files()
        s = self.spec()
        if s["kind"] == "text" and not s["text"].strip():
            raise UserError("กรุณาพิมพ์ข้อความลายน้ำ")
        if s["kind"] == "image" and not os.path.isfile(s["image_path"]):
            raise UserError("กรุณาเลือกรูปภาพลายน้ำ")
        dest = self.ctx.resolve_dest([es[0]["path"]])
        steps = []
        for e in es:
            if s["pages"]:
                try:
                    ops.parse_ranges(s["pages"], e["page_count"])
                except EngineError as ex:
                    raise UserError(f"{os.path.basename(e['path'])}: {ex}")
            stem = os.path.splitext(os.path.basename(e["path"]))[0]
            steps.append(Step("watermark", {"src": e["path"], "out_path": os.path.join(dest, stem + "_watermarked.pdf"),
                                            "spec": s, "password": e["password"]}, "ประทับลายน้ำ"))
        what = f"ข้อความ “{s['text']}”" if s["kind"] == "text" else "รูปภาพ " + os.path.basename(s["image_path"])
        names = ["ซ้ายบน", "กลางบน", "ขวาบน", "ซ้ายกลาง", "กึ่งกลาง", "ขวากลาง", "ซ้ายล่าง", "กลางล่าง", "ขวาล่าง"]
        return Plan(steps, [f"{len(es)} ไฟล์", what, f"ตำแหน่ง: {names[s['position']]} · หมุน {s['rotation']}° · ความทึบ {int(s['opacity'] * 100)}%",
                            "หน้า: " + (s["pages"] or "ทั้งหมด")], [e["path"] for e in es], dest)

    def clear_all(self):
        super().clear_all()
        self.preview.clear_preview()


# ================================================================ compress ==
LEVEL_INFO = {
    "quality": ("ความคมชัดสูง", "ลดขนาดเล็กน้อย ภาพยังคมชัด เหมาะกับงานพิมพ์"),
    "email": ("มาตรฐานสำหรับอีเมล", "สมดุลระหว่างขนาดกับความชัด แนะนำสำหรับส่งอีเมล"),
    "smallest": ("ขนาดเล็กสุด", "บีบอัดสูงสุด ภาพอาจไม่คม เหมาะกับเก็บถาวร/แชร์ด่วน"),
}


class CompressPage(PdfListPage):
    key, title, icon_name, run_text = "compress", "บีบอัดขนาดไฟล์", "compress", "บีบอัดไฟล์"
    subtitle = "เลือกระดับการบีบอัด 3 ระดับ พร้อมคำนวณขนาดไฟล์โดยประมาณก่อนส่งออกจริง"

    def build_workspace(self):
        self.est: dict[str, dict] = {}
        lw = self.make_list(reorder=False)
        lw.text_fn = self._row
        return lw

    def build_options(self):
        self.radios: dict[str, QRadioButton] = {}
        parts = []
        for k, (t, d) in LEVEL_INFO.items():
            r = QRadioButton(t)
            r.toggled.connect(self._level_changed)
            self.radios[k] = r
            lab = QLabel(d)
            lab.setObjectName("muted")
            lab.setWordWrap(True)
            lab.setContentsMargins(22, 0, 0, 6)
            parts += [r, lab]
        self.radios["email"].setChecked(True)
        self.est_btn = QPushButton("คำนวณขนาดโดยประมาณ")
        self.est_btn.clicked.connect(self._estimate)
        self.est_status = QLabel("")
        self.est_status.setObjectName("muted")
        self.est_status.setWordWrap(True)
        return vbox(*parts, self.est_btn, self.est_status,
                    banner("การคำนวณจะบีบอัดจริงในหน่วยความจำ (ไม่เขียนไฟล์) จึงแม่นยำ แต่ไฟล์ใหญ่อาจใช้เวลา "
                           "หากบีบแล้วไฟล์ไม่เล็กลง โปรแกรมจะคงขนาดเดิมไว้", "info"), margins=(2, 2, 2, 2))

    def level(self) -> str:
        return next((k for k, r in self.radios.items() if r.isChecked()), "email")

    def _row(self, e):
        base = pdf_row_text(e)
        est = self.est.get(f"{e['path']}|{self.level()}") if hasattr(self, "radios") else None
        if est:
            pct = 100 - int(est["estimated"] * 100 / max(1, est["original"]))
            base += f"\n→ ประมาณ {human_size(est['estimated'])} (ลดลงประมาณ {pct}%)"
        return base

    def _level_changed(self, on):
        if on:
            self.lw.refresh_text()
            self.est_status.setText("")

    def _estimate(self):
        es = self.lw.selected_entries() or self.lw.entries()
        if not es:
            QMessageBox.information(self, "บีบอัดไฟล์", "ยังไม่ได้เพิ่มไฟล์ PDF")
            return
        lvl = self.level()
        steps = [Step("estimate_compress", {"src": e["path"], "level": lvl, "password": e["password"]}) for e in es]
        self.est_btn.setEnabled(False)

        def done(i, r):
            self.est[f"{es[i]['path']}|{lvl}"] = r
            self.lw.refresh_text()

        def fin(_):
            self.est_btn.setEnabled(True)
            self.est_status.setText("คำนวณเสร็จแล้ว")

        def fail(code, msg, i):
            self.est_btn.setEnabled(True)
            self.est_status.setText(msg if code != "cancelled" else "ยกเลิก")
        self.est_status.setText("กำลังคำนวณ…")
        self.ctx.run_steps(steps, ok=fin, err=fail, stepdone=done)

    def preset_part(self):
        return {"compression": {"level": self.level()}}

    def apply_preset(self, p):
        lvl = p.get("compression", {}).get("level", "email")
        self.radios.get(lvl, self.radios["email"]).setChecked(True)

    def plan(self):
        es = self.need_files()
        dest = self.ctx.resolve_dest([es[0]["path"]])
        lvl = self.level()
        steps = []
        for e in es:
            stem = os.path.splitext(os.path.basename(e["path"]))[0]
            steps.append(Step("compress", {"src": e["path"], "out_path": os.path.join(dest, stem + "_compressed.pdf"),
                                           "level": lvl, "password": e["password"]}, "บีบอัด"))
        return Plan(steps, [f"{len(es)} ไฟล์", "ระดับ: " + LEVEL_INFO[lvl][0],
                            "ขนาดรวมก่อนบีบอัด: " + human_size(sum(e["size"] for e in es))], [e["path"] for e in es], dest)

    def result_note(self, results):
        rs = [r for r in results if isinstance(r, dict) and "new" in r]
        if not rs:
            return ""
        o, n = sum(r["original"] for r in rs), sum(r["new"] for r in rs)
        return f"{human_size(o)} → {human_size(n)} (ลดลง {100 - int(n * 100 / max(1, o))}%)"


# ================================================================== convert ==
MODES = [("png", "PDF → รูปภาพ PNG"), ("jpeg", "PDF → รูปภาพ JPEG"), ("docx", "PDF → Word (.docx)"),
         ("topdf", "Word (.docx) → PDF")]


class ConvertPage(PdfListPage):
    key, title, icon_name, run_text = "convert", "แปลงไฟล์เอกสาร", "convert", "แปลงไฟล์"
    subtitle = "แปลงระหว่าง PDF กับรูปภาพ (PNG, JPEG) และไฟล์ Word พื้นฐาน — ประมวลผลบนเครื่องทั้งหมด"
    accept_exts = (".pdf", ".docx")

    def build_workspace(self):
        self.lw = ListWorkspace((".pdf",), "ไฟล์ PDF (*.pdf)", pdf_row_text, self.hint, reorder=False)
        self.lw.addRequested.connect(self.accept_paths)
        self.warn = banner("ข้อจำกัด: การแปลงเป็น Word เก็บเฉพาะข้อความและลำดับบรรทัด การจัดหน้า ตาราง คอลัมน์และฟอนต์อาจเปลี่ยนไป "
                           "หน้าที่เป็นภาพสแกนจะถูกใส่เป็นรูป (ไม่มี OCR) · Word → PDF รองรับเฉพาะ .docx แบบพื้นฐาน",
                           "warn")
        return vbox(self.lw, self.warn, spacing=10)

    def build_options(self):
        self.mode = QComboBox()
        for k, t in MODES:
            self.mode.addItem(t, k)
        self.dpi = QComboBox()
        for d in (100, 150, 200, 300):
            self.dpi.addItem(f"{d} DPI", d)
        self.dpi.setCurrentIndex(1)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.dpi_row = form(("ความละเอียดรูป", self.dpi))
        return vbox(form(("รูปแบบการแปลง", self.mode)), self.dpi_row, margins=(2, 2, 2, 2))

    def fmt(self) -> str:
        return self.mode.currentData()

    def _mode_changed(self):
        topdf = self.fmt() == "topdf"
        self.lw.list.set_exts((".docx",) if topdf else (".pdf",))
        self.lw.dialog_filter = "ไฟล์ Word (*.docx)" if topdf else "ไฟล์ PDF (*.pdf)"
        self.lw.hint.setText("ลากไฟล์ .docx มาวางที่นี่" if topdf else self.hint)
        self.dpi_row.setVisible(self.fmt() in ("png", "jpeg"))
        bad = [i for i, e in enumerate(self.lw.entries()) if not e["path"].lower().endswith(".docx" if topdf else ".pdf")]
        for i in reversed(bad):
            self.lw.list.takeItem(i)

    def accept_paths(self, paths):
        if self.fmt() == "topdf":
            for p in paths:
                if p.lower().endswith(".docx") and os.path.isfile(p):
                    self.ctx.settings.add_recent(p)
                    self.lw.add_entry({"path": p, "password": None, "size": os.path.getsize(p)})
        else:
            super().accept_paths(paths)

    def preset_part(self):
        return {"convert": {"format": self.fmt(), "dpi": self.dpi.currentData()}}

    def apply_preset(self, p):
        c = p.get("convert", {})
        i = self.mode.findData(c.get("format", "png"))
        if i >= 0:
            self.mode.setCurrentIndex(i)
        j = self.dpi.findData(c.get("dpi", 150))
        if j >= 0:
            self.dpi.setCurrentIndex(j)

    def plan(self):
        es = self.need_files()
        dest = self.ctx.resolve_dest([es[0]["path"]])
        f, steps = self.fmt(), []
        for e in es:
            stem = os.path.splitext(os.path.basename(e["path"]))[0]
            if f in ("png", "jpeg"):
                steps.append(Step("pdf_to_images", {"src": e["path"], "out_dir": os.path.join(dest, stem + "_images"),
                                                    "fmt": f, "dpi": self.dpi.currentData(), "password": e["password"]}, "แปลงเป็นรูป"))
            elif f == "docx":
                steps.append(Step("pdf_to_docx", {"src": e["path"], "out_path": os.path.join(dest, stem + ".docx"),
                                                  "password": e["password"]}, "แปลงเป็น Word"))
            else:
                steps.append(Step("docx_to_pdf", {"src": e["path"], "out_path": os.path.join(dest, stem + ".pdf")}, "แปลงเป็น PDF"))
        summ = [f"{len(es)} ไฟล์", self.mode.currentText()]
        if f in ("png", "jpeg"):
            summ += [f"ความละเอียด {self.dpi.currentData()} DPI", "ไฟล์รูปจะอยู่ในโฟลเดอร์ย่อย “ชื่อไฟล์_images”"]
        return Plan(steps, summ, [e["path"] for e in es], dest)

    def result_note(self, results):
        warns = []
        for r in results:
            if isinstance(r, dict):
                warns += [w for w in r.get("warnings", []) if w not in warns]
        return "<br>".join("⚠ " + w for w in warns)
