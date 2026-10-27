# Wattanapat PDF — โปรแกรมจัดการ PDF ออฟไลน์สำหรับ Windows

ประมวลผลบนเครื่อง 100% ไม่ส่งไฟล์ออกนอกเครื่อง ตามเอกสาร *Product Specification* ที่ให้มา

## วิธีได้ไฟล์ติดตั้ง (.exe) — เลือกวิธีใดวิธีหนึ่ง
ชุดนี้เป็นซอร์สโค้ดที่พร้อมสร้างตัวติดตั้ง แต่ **ยังไม่ได้คอมไพล์เป็น .exe** (สภาพแวดล้อมที่สร้างชุดนี้ไม่ใช่ Windows และไม่มีอินเทอร์เน็ต)

**A. บนเครื่อง Windows (ง่ายสุด)**
1. ติดตั้ง Python 3.12 x64 (ติ๊ก “py launcher”) และ [Inno Setup 6](https://jrsoftware.org/isdl.php)
2. ดับเบิลคลิก `installer\build_windows.bat` (ต้องมีอินเทอร์เน็ตเฉพาะตอนสร้าง)
3. ได้ `dist\installer\WattanapatPDF-Setup-1.0.0.exe` — ดับเบิลคลิกเพื่อติดตั้งลงระบบ (Start Menu / Desktop)
   (ถ้าไม่มี Inno Setup จะได้ไฟล์ zip แบบพกพาแทน)

**B. ให้ GitHub สร้างให้** — อัปโหลดโฟลเดอร์นี้ขึ้น GitHub แล้วรัน workflow *Build Windows installer* (Actions → Run workflow) ดาวน์โหลด `WattanapatPDF-Setup` จาก Artifacts

**รันจากซอร์สเพื่อทดลอง:** `pip install -r requirements.txt` แล้ว `python -m wattanapat_pdf` (ตั้ง `PYTHONPATH=src`)

> ตัวติดตั้งยังไม่ได้เซ็นดิจิทัล (code signing) Windows SmartScreen อาจเตือน “unknown publisher” ต้องซื้อใบรับรองหากแจกจ่ายในวงกว้าง

## สถานะการทดสอบ (ตรงไปตรงมา)
| ส่วน | สถานะ |
|---|---|
| Engine (รวม/แยก/จัดหน้า/รูป↔PDF/รหัสผ่าน AES-256/ลายน้ำ/บีบอัด/แปลง Word, IPC, sandbox, ชุดตั้งค่า, log) | ทดสอบอัตโนมัติ 30 รายการ ผ่านบน Linux (`python -m unittest tests.test_engine`) |
| หน้าต่างโปรแกรม (PySide6) | **ยังไม่เคยรันจริง** — ตรวจได้แค่ว่าโค้ดสร้างหน้าได้ครบด้วย PySide6 จำลอง คาดว่าอาจมีบั๊กเล็กน้อยด้านการแสดงผล/การลากวางที่ต้องแก้หลังรันบน Windows ครั้งแรก |
| ตัวติดตั้ง / PyInstaller / ฟอนต์ไทยบน Windows | ยังไม่ได้ทดสอบ (เขียนตามแนวทางมาตรฐาน) ลายน้ำภาษาไทยใช้ฟอนต์ Tahoma/Leelawadee ของ Windows |

## ข้อจำกัดของรุ่นแรก
PDF→Word เก็บข้อความและลำดับบรรทัดเท่านั้น (ไม่มี OCR; หน้าสแกนใส่เป็นรูป) · Word→PDF รองรับ .docx พื้นฐาน · UI เป็นภาษาไทยเท่านั้น · ไม่มีการรับรอง PDPA (ดู `docs/`)

ดูตารางเทียบข้อกำหนดที่ `docs/SPEC_COVERAGE.md` · สร้างโลโก้ใหม่ด้วย `python tools/make_branding.py <โลโก้ต้นฉบับ>`
