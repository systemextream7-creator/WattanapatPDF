# PyInstaller spec - ONEDIR build on purpose: a one-file exe unpacks itself into %TEMP% on every start,
# which would leave program files outside the sandbox and slow start-up.
from pathlib import Path
root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "installer" / "entry.py")],
    pathex=[str(root / "src")],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=["wattanapat_pdf.engine.service", "wattanapat_pdf.engine.ops", "wattanapat_pdf.engine.fonts"],
    excludes=["tkinter", "unittest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml",
              "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtSql", "PySide6.QtNetwork"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="WattanapatPDF", console=False,
          icon=str(root / "assets" / "app.ico"), upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="WattanapatPDF", upx=False)
