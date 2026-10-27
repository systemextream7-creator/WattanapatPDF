"""Home, presets, security and settings pages."""
from __future__ import annotations

import os
import shutil

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from .. import __version__, applog, updater
from ..paths import resource_path
from .theme import icon
from .widgets import banner, human_size, open_path

CARDS = [("merge", "รวมไฟล์ PDF", "รวมหลายไฟล์เป็นไฟล์เดียว เลือกช่วงหน้าได้"),
         ("split", "แยกหน้า", "แยกตามช่วงหน้าหรือทุกหน้า"),
         ("organize", "จัดการหน้า", "หมุน ลบ ลากสลับ พร้อมย้อนกลับ"),
         ("images", "รูปภาพ → PDF", "รวมรูป/สแกนเป็น PDF"),
         ("protect", "ใส่รหัสผ่าน", "AES-256 พร้อมคุมสิทธิ์พิมพ์/แก้ไข/คัดลอก"),
         ("watermark", "ประทับลายน้ำ", "ข้อความหรือตรายาง 9 ตำแหน่ง"),
         ("compress", "บีบอัดไฟล์", "3 ระดับ พร้อมประมาณขนาดก่อนส่งออก"),
         ("convert", "แปลงไฟล์", "PDF ↔ รูปภาพ / Word")]
ICONS = {"merge": "merge", "split": "split", "organize": "organize", "images": "image", "protect": "lock",
         "watermark": "watermark", "compress": "compress", "convert": "convert"}


def _scroll(inner: QWidget) -> QScrollArea:
    s = QScrollArea()
    s.setWidgetResizable(True)
    s.setFrameShape(QFrame.Shape.NoFrame)
    s.setWidget(inner)
    return s


def _card() -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName("card")
    v = QVBoxLayout(f)
    v.setContentsMargins(16, 14, 16, 14)
    v.setSpacing(8)
    return f, v


class HomePage(QWidget):
    def __init__(self, ctx, navigate):
        super().__init__()
        self.setObjectName("page")
        self.ctx, self.navigate = ctx, navigate
        inner = QWidget()
        inner.setObjectName("page")
        v = QVBoxLayout(inner)
        v.setContentsMargins(28, 22, 28, 22)
        v.setSpacing(14)
        top = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(resource_path("assets/logo-96.png"))))
        top.addWidget(logo)
        t = QVBoxLayout()
        h = QLabel("เริ่มงานเอกสารของคุณ")
        h.setObjectName("h1")
        s = QLabel("เลือกเครื่องมือด้านล่าง หรือลากไฟล์ PDF มาวางที่เครื่องมือที่ต้องการ")
        s.setObjectName("muted")
        t.addWidget(h)
        t.addWidget(s)
        top.addLayout(t, 1)
        badge = QLabel("● ประมวลผลบนเครื่อง 100% — ไม่ส่งไฟล์ออกนอกเครื่อง")
        badge.setObjectName("badge")
        top.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(12)
        for n, (key, title, desc) in enumerate(CARDS):
            b = QPushButton()
            b.setMinimumHeight(96)
            b.setStyleSheet("QPushButton{text-align:left;padding:12px 16px;}")
            b.setIcon(icon(ICONS[key]))
            b.setIconSize(b.iconSize() * 2)
            b.setText(f"  {title}\n  {desc}")
            b.clicked.connect(lambda _=False, k=key: navigate(k))
            grid.addWidget(b, n // 4, n % 4)
        v.addLayout(grid)

        row = QHBoxLayout()
        c1, v1 = _card()
        lab = QLabel("ชุดการตั้งค่าที่ใช้บ่อย")
        lab.setObjectName("h2")
        v1.addWidget(lab)
        self.preset_box = QVBoxLayout()
        v1.addLayout(self.preset_box)
        v1.addStretch(1)
        c2, v2 = _card()
        lab2 = QLabel("ไฟล์ล่าสุดที่คุณเลือกเอง")
        lab2.setObjectName("h2")
        v2.addWidget(lab2)
        self.recent = QListWidget()
        self.recent.setMaximumHeight(190)
        self.recent.itemClicked.connect(self._recent_clicked)
        v2.addWidget(self.recent)
        clr = QPushButton("ล้างรายการ")
        clr.clicked.connect(self._clear_recent)
        v2.addWidget(clr, 0, Qt.AlignmentFlag.AlignLeft)
        row.addWidget(c1, 1)
        row.addWidget(c2, 1)
        v.addLayout(row)
        v.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(_scroll(inner))
        ctx.presetsChanged.connect(self.reload)
        self.reload()

    def reload(self):
        while self.preset_box.count():
            w = self.preset_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        active = self.ctx.settings.get("active_preset", 0)
        for i, p in enumerate(self.ctx.settings.presets):
            b = QPushButton(("✓ " if i == active else "") + p["name"])
            b.clicked.connect(lambda _=False, i=i: self.ctx.apply_preset(i))
            self.preset_box.addWidget(b)
        self.recent.clear()
        for path in self.ctx.settings.get("recent", []):
            it = QListWidgetItem(os.path.basename(path))
            it.setToolTip(path)
            it.setData(Qt.ItemDataRole.UserRole, path)
            self.recent.addItem(it)

    def showEvent(self, e):
        super().showEvent(e)
        self.reload()

    def _recent_clicked(self, it):
        path = it.data(Qt.ItemDataRole.UserRole)
        if not os.path.isfile(path):
            QMessageBox.information(self, "ไม่พบไฟล์", "ไฟล์นี้ถูกย้ายหรือลบแล้ว")
            return
        m = QMenu(self)
        ext = path.lower().rsplit(".", 1)[-1]
        opts = ([("images", "รูปภาพ → PDF")] if ext in ("jpg", "jpeg", "png", "tif", "tiff", "bmp", "webp")
                else [("convert", "แปลงไฟล์")] if ext == "docx"
                else [(k, t) for k, t, _ in CARDS if k not in ("images",)])
        for k, t in opts:
            m.addAction(t, lambda k=k: self.navigate(k, [path]))
        m.exec(self.cursor().pos())

    def _clear_recent(self):
        self.ctx.settings.clear_history()
        self.reload()


class PresetsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(16)
        left = QVBoxLayout()
        h = QLabel("ชุดการตั้งค่า")
        h.setObjectName("h1")
        sub = QLabel("บันทึกค่าที่ใช้บ่อย (ลายน้ำ การบีบอัด การแปลงและสิทธิ์ โฟลเดอร์ส่งออก) เพื่อทำงานซ้ำได้รวดเร็ว "
                     "ชุดการตั้งค่าไม่เก็บชื่อไฟล์ รหัสผ่าน หรือเนื้อหาเอกสาร")
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        left.addWidget(h)
        left.addWidget(sub)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._show)
        left.addWidget(self.list, 1)
        lay.addLayout(left, 1)
        card, v = _card()
        card.setFixedWidth(430)
        self.detail = QLabel("")
        self.detail.setTextFormat(Qt.TextFormat.RichText)
        self.detail.setWordWrap(True)
        self.detail.setAlignment(Qt.AlignmentFlag.AlignTop)
        v.addWidget(self.detail, 1)
        for text, slot, primary in (("ใช้ชุดนี้ทันที", self._use, True), ("บันทึกค่าปัจจุบันทับชุดนี้", self._capture, False),
                                    ("สร้างชุดใหม่จากค่าปัจจุบัน", self._new, False), ("ทำสำเนา", self._dup, False),
                                    ("เปลี่ยนชื่อ", self._rename, False), ("ลบชุดนี้", self._delete, False)):
            b = QPushButton(text)
            if primary:
                b.setProperty("primary", True)
            if text.startswith("ลบ"):
                b.setProperty("danger", True)
            b.clicked.connect(slot)
            v.addWidget(b)
        lay.addWidget(card)
        ctx.presetsChanged.connect(self.reload)
        self.reload()

    def _i(self) -> int:
        return max(0, self.list.currentRow())

    def reload(self):
        keep = self._i() if self.list.count() else self.ctx.settings.get("active_preset", 0)
        self.list.blockSignals(True)
        self.list.clear()
        active = self.ctx.settings.get("active_preset", 0)
        for i, p in enumerate(self.ctx.settings.presets):
            self.list.addItem(("✓ " if i == active else "") + p["name"])
        self.list.setCurrentRow(min(keep, self.list.count() - 1))
        self.list.blockSignals(False)
        self._show(self._i())

    def _show(self, i):
        if i < 0 or i >= len(self.ctx.settings.presets):
            return
        p = self.ctx.settings.presets[i]
        w, c, cv, pm = p["watermark"], p["compression"], p["convert"], p["permissions"]
        yn = lambda b: "อนุญาต" if b else "ไม่อนุญาต"
        kinds = {"quality": "ความคมชัดสูง", "email": "มาตรฐานอีเมล", "smallest": "ขนาดเล็กสุด"}
        wm = (f"“{w.get('text', '')}” · {w.get('font_size')} pt · หมุน {w.get('rotation')}° · ความทึบ {int(w.get('opacity', 0) * 100)}%"
              if w.get("kind") != "image" else "รูปภาพ " + os.path.basename(w.get("image_path", "")))
        self.detail.setText(
            f"<h3>{p['name']}</h3>"
            f"<p><b>ลายน้ำ</b><br>{wm}</p>"
            f"<p><b>การบีบอัด</b><br>{kinds.get(c.get('level'), c.get('level'))}</p>"
            f"<p><b>การแปลง</b><br>{cv.get('format')} · {cv.get('dpi')} DPI</p>"
            f"<p><b>สิทธิ์ของไฟล์ที่เข้ารหัส</b><br>พิมพ์: {yn(pm['allow_print'])} · แก้ไข: {yn(pm['allow_modify'])} · "
            f"คัดลอก: {yn(pm['allow_copy'])}</p>"
            f"<p><b>โฟลเดอร์ส่งออก</b><br>{p.get('output_folder') or 'ข้างไฟล์ต้นฉบับ'}</p>")

    def _use(self):
        self.ctx.apply_preset(self._i())

    def _capture(self):
        self.ctx.capture_into(self._i())

    def _name(self, title, default=""):
        n, ok = QInputDialog.getText(self, title, "ชื่อชุดการตั้งค่า:", text=default)
        return n.strip() if ok and n.strip() else None

    def _new(self):
        n = self._name("สร้างชุดใหม่")
        if n:
            i = self.ctx.settings.add_preset(n, self.ctx.settings.presets[self._i()])
            self.ctx.capture_into(i)
            self.list.setCurrentRow(i)

    def _dup(self):
        i = self._i()
        self.ctx.settings.add_preset(self.ctx.settings.presets[i]["name"] + " (สำเนา)", self.ctx.settings.presets[i])
        self.ctx.presetsChanged.emit()

    def _rename(self):
        i = self._i()
        n = self._name("เปลี่ยนชื่อ", self.ctx.settings.presets[i]["name"])
        if n:
            self.ctx.settings.rename_preset(i, n)
            self.ctx.presetsChanged.emit()

    def _delete(self):
        if len(self.ctx.settings.presets) <= 1:
            QMessageBox.information(self, "ลบชุด", "ต้องเหลือชุดการตั้งค่าอย่างน้อย 1 ชุด")
            return
        i = self._i()
        if QMessageBox.question(self, "ลบชุด", f"ลบ “{self.ctx.settings.presets[i]['name']}” ใช่หรือไม่?") == QMessageBox.StandardButton.Yes:
            self.ctx.settings.delete_preset(i)
            self.ctx.presetsChanged.emit()


class SecurityPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        inner = QWidget()
        inner.setObjectName("page")
        v = QVBoxLayout(inner)
        v.setContentsMargins(28, 22, 28, 22)
        v.setSpacing(12)
        h = QLabel("ความปลอดภัยและความเป็นส่วนตัว")
        h.setObjectName("h1")
        v.addWidget(h)
        badge = QLabel("● โหมดออฟไลน์: โปรแกรมไม่มีโค้ดส่งไฟล์หรือข้อมูลเอกสารออกนอกเครื่อง")
        badge.setObjectName("badge")
        v.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)

        c, cv = _card()
        t = QLabel("สิทธิ์การเข้าถึงไฟล์")
        t.setObjectName("h2")
        cv.addWidget(t)
        cv.addWidget(QLabel("โปรแกรมเปิดเฉพาะไฟล์ที่คุณเลือกหรือลากมาวาง และเขียนไฟล์ใหม่ลงโฟลเดอร์ปลายทางที่แสดงให้ยืนยันทุกครั้ง "
                            "ไม่เขียนทับไฟล์ต้นฉบับ"))
        cv.itemAt(1).widget().setWordWrap(True)
        v.addWidget(c)

        c, cv = _card()
        t = QLabel("ไฟล์ชั่วคราว (Sandbox)")
        t.setObjectName("h2")
        cv.addWidget(t)
        self.sb_info = QLabel("")
        self.sb_info.setWordWrap(True)
        self.sb_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cv.addWidget(self.sb_info)
        row = QHBoxLayout()
        b1 = QPushButton("ล้างไฟล์ชั่วคราวทันที")
        b1.clicked.connect(self._clear_tmp)
        b2 = QPushButton("เปิดโฟลเดอร์ชั่วคราว")
        b2.clicked.connect(lambda: open_path(str(ctx.sandbox.session)))
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch(1)
        cv.addLayout(row)
        cv.addWidget(QLabel("ไฟล์ชั่วคราวจะถูกลบอัตโนมัติเมื่อปิดโปรแกรม และเมื่อเปิดครั้งถัดไป หากโปรแกรมปิดผิดปกติ"))
        cv.itemAt(cv.count() - 1).widget().setWordWrap(True)
        v.addWidget(c)

        c, cv = _card()
        t = QLabel("ประวัติการใช้งาน")
        t.setObjectName("h2")
        cv.addWidget(t)
        lab = QLabel("ล้างรายการไฟล์ล่าสุดและบันทึกข้อผิดพลาดของโปรแกรมได้ด้วยตนเองตลอดเวลา "
                     "(บันทึกข้อผิดพลาดไม่เก็บชื่อไฟล์ เนื้อหา หรือรหัสผ่าน)")
        lab.setWordWrap(True)
        cv.addWidget(lab)
        b = QPushButton("ล้างประวัติและบันทึกข้อผิดพลาดทั้งหมด")
        b.clicked.connect(self._clear_history)
        cv.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        v.addWidget(c)

        c, cv = _card()
        t = QLabel("การเข้ารหัสไฟล์")
        t.setObjectName("h2")
        cv.addWidget(t)
        lab = QLabel("ใช้มาตรฐาน AES-256 ตามข้อกำหนด PDF 2.0 รหัสผ่านอยู่ในหน่วยความจำเท่าที่จำเป็นและไม่ถูกบันทึกลงดิสก์")
        lab.setWordWrap(True)
        cv.addWidget(lab)
        v.addWidget(c)

        v.addWidget(banner("หมายเหตุด้านกฎหมาย: การทำงานแบบออฟไลน์ช่วยลดจุดเสี่ยงตามหลัก Data Minimization แต่การปฏิบัติตาม พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล (PDPA) "
                           "ขึ้นอยู่กับนโยบายและการบังคับใช้ขององค์กร โปรแกรมนี้ไม่ได้รับการรับรอง PDPA โดยอัตโนมัติ "
                           "ก่อนใช้งานจริงในองค์กรควรให้ฝ่ายกฎหมายหรือผู้เชี่ยวชาญ PDPA ตรวจสอบ (ดูเอกสาร docs/DATA_FLOW.md และ docs/PRIVACY_NOTICE.md)", "warn"))
        v.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(_scroll(inner))
        self._t = QTimer(self)
        self._t.setInterval(2500)
        self._t.timeout.connect(self.refresh)
        self.refresh()

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()
        self._t.start()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._t.stop()

    def refresh(self):
        n, size = self.ctx.sandbox.stats()
        self.sb_info.setText(f"ตำแหน่ง: {self.ctx.sandbox.session}\nขณะนี้มี {n} ไฟล์ · {human_size(size)}")

    def _clear_tmp(self):
        n = self.ctx.sandbox.clear()
        self.refresh()
        self.ctx.message.emit(f"ล้างไฟล์ชั่วคราวแล้ว ({n} ไฟล์)")

    def _clear_history(self):
        self.ctx.settings.clear_history()
        applog.clear()
        self.ctx.presetsChanged.emit()
        self.ctx.message.emit("ล้างประวัติแล้ว")


class SettingsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        s = ctx.settings
        inner = QWidget()
        inner.setObjectName("page")
        v = QVBoxLayout(inner)
        v.setContentsMargins(28, 22, 28, 22)
        v.setSpacing(12)
        h = QLabel("ตั้งค่า")
        h.setObjectName("h1")
        v.addWidget(h)

        c, cv = _card()
        lang = QComboBox()
        lang.addItem("ไทย")
        lang.addItem("English (เร็วๆ นี้)")
        lang.model().item(1).setEnabled(False)
        cv.addWidget(QLabel("ภาษา"))
        cv.addWidget(lang)
        cv.addWidget(QLabel("โฟลเดอร์ส่งออกเริ่มต้น"))
        row = QHBoxLayout()
        self.out = QLineEdit(s.get("output_folder", ""))
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("ข้างไฟล์ต้นฉบับ")
        pick = QPushButton("เลือก…")
        pick.clicked.connect(self._pick)
        clr = QPushButton("ล้าง")
        clr.clicked.connect(lambda: ctx.set_output_folder(""))
        row.addWidget(self.out, 1)
        row.addWidget(pick)
        row.addWidget(clr)
        cv.addLayout(row)
        ctx.outputChanged.connect(self.out.setText)
        self.notify = QCheckBox("แจ้งเตือน (กะพริบที่แถบงาน) เมื่อประมวลผลเสร็จ")
        self.notify.setChecked(s.get("notify_on_finish", True))
        self.notify.toggled.connect(lambda b: s.set("notify_on_finish", b))
        self.remember = QCheckBox("จดจำไฟล์ล่าสุดที่ฉันเลือก")
        self.remember.setChecked(s.get("remember_recent", True))
        self.remember.toggled.connect(self._remember)
        cv.addWidget(self.notify)
        cv.addWidget(self.remember)
        v.addWidget(c)

        c, cv = _card()
        t = QLabel("การอัปเดต")
        t.setObjectName("h2")
        cv.addWidget(t)
        info = QLabel("ปิดไว้เป็นค่าเริ่มต้น เมื่อเปิดใช้ โปรแกรมจะติดต่อผ่าน HTTPS ตามที่อยู่ด้านล่างและส่งเฉพาะหมายเลขเวอร์ชันของโปรแกรม ไม่ส่งข้อมูลไฟล์")
        info.setWordWrap(True)
        cv.addWidget(info)
        self.upd_url = QLineEdit(s.get("update_url", ""))
        self.upd_url.setPlaceholderText("https://example.com/wattanapat-pdf/latest.json")
        self.upd_url.editingFinished.connect(lambda: s.set("update_url", self.upd_url.text().strip()))
        cv.addWidget(self.upd_url)
        self.upd_auto = QCheckBox("ตรวจสอบอัปเดตอัตโนมัติเมื่อเปิดโปรแกรม")
        self.upd_auto.setChecked(s.get("update_check_on_start", False))
        self.upd_auto.toggled.connect(lambda b: s.set("update_check_on_start", b))
        cv.addWidget(self.upd_auto)
        b = QPushButton("ตรวจสอบอัปเดตตอนนี้")
        b.clicked.connect(self.check_update)
        cv.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        self.upd_result = QLabel("")
        self.upd_result.setWordWrap(True)
        cv.addWidget(self.upd_result)
        v.addWidget(c)

        c, cv = _card()
        t = QLabel("การวินิจฉัยปัญหา (ไม่ส่งเนื้อหาไฟล์)")
        t.setObjectName("h2")
        cv.addWidget(t)
        lab = QLabel("บันทึกข้อผิดพลาดมีเพียงชนิดข้อผิดพลาด ชื่อการทำงาน และตำแหน่งในโค้ดของโปรแกรม ไม่มีชื่อไฟล์ เนื้อหา หรือรหัสผ่าน "
                     "โปรแกรมไม่ส่งไฟล์นี้ไปที่ใดเอง คุณเลือกส่งให้ผู้ดูแลด้วยตนเองได้")
        lab.setWordWrap(True)
        cv.addWidget(lab)
        b = QPushButton("บันทึกสำเนาไฟล์บันทึกข้อผิดพลาด…")
        b.clicked.connect(self._export_log)
        cv.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        v.addWidget(c)
        v.addWidget(QLabel(f"Wattanapat PDF เวอร์ชัน {__version__}"))
        v.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(_scroll(inner))
        if s.get("update_check_on_start") and s.get("update_url"):
            QTimer.singleShot(1500, self.check_update)

    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, "เลือกโฟลเดอร์ส่งออก", self.ctx.output_folder() or os.path.expanduser("~"))
        if d:
            self.ctx.set_output_folder(d)

    def _remember(self, on):
        self.ctx.settings.set("remember_recent", on)
        if not on:
            self.ctx.settings.clear_history()

    def check_update(self):
        url = self.upd_url.text().strip()
        if not url:
            self.upd_result.setText("ยังไม่ได้กำหนดที่อยู่สำหรับตรวจสอบอัปเดต")
            return
        self.upd_result.setText("กำลังตรวจสอบ…")
        import threading
        from PySide6.QtCore import QObject, Signal

        class Bridge(QObject):
            done = Signal(str)
        self._bridge = Bridge()
        self._bridge.done.connect(self.upd_result.setText)

        def work():
            try:
                r = updater.check(url)
                msg = (f"มีเวอร์ชันใหม่ {r['latest']} {r['url']}" if r["update_available"]
                       else f"คุณใช้เวอร์ชันล่าสุดแล้ว ({__version__})")
            except Exception:
                msg = "ตรวจสอบไม่สำเร็จ (ไม่มีอินเทอร์เน็ตหรือที่อยู่ไม่ถูกต้อง) — โปรแกรมยังใช้งานออฟไลน์ได้ตามปกติ"
            self._bridge.done.emit(msg)
        threading.Thread(target=work, daemon=True).start()

    def _export_log(self):
        src = applog.log_file()
        if not src.exists():
            QMessageBox.information(self, "บันทึกข้อผิดพลาด", "ยังไม่มีข้อผิดพลาดที่ถูกบันทึก")
            return
        dst, _ = QFileDialog.getSaveFileName(self, "บันทึกสำเนา", "wattanapat-errors.log", "Log (*.log)")
        if dst:
            shutil.copyfile(src, dst)
