"""Visual theme derived from the Wattanapat logo blue."""
from PySide6.QtGui import QFont, QIcon
from ..paths import resource_path

BLUE = "#0181EC"
BLUE_DARK = "#0068D2"
NAVY = "#0A2A54"
BG = "#F3F7FB"
CARD = "#FFFFFF"
BORDER = "#D6E2EF"
TEXT = "#12263F"
MUTED = "#5B6B80"
OK = "#1E8E5A"
DANGER = "#C0392B"
WARN_BG = "#FFF4D6"
WARN_BORDER = "#F0C24B"
INFO_BG = "#E6F2FD"

QSS = f"""
* {{ font-size: 14px; color: {TEXT}; }}
QMainWindow, QWidget#page, QWidget#root {{ background: {BG}; }}
QWidget#sidebar {{ background: {NAVY}; }}
QListWidget#nav {{ background: transparent; border: none; outline: none; color: white; }}
QListWidget#nav::item {{ color: #DCE8F7; padding: 11px 14px; margin: 2px 10px; border-radius: 8px; }}
QListWidget#nav::item:hover {{ background: rgba(255,255,255,0.09); }}
QListWidget#nav::item:selected {{ background: {BLUE}; color: white; }}
QLabel#navFoot {{ color: #9DB6D6; font-size: 12px; }}
QLabel#h1 {{ font-size: 24px; font-weight: 700; }}
QLabel#h2 {{ font-size: 16px; font-weight: 700; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#badge {{ background: #DFF3E8; color: {OK}; border-radius: 10px; padding: 3px 10px; font-weight: 600; }}
QFrame#panel {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#warn {{ background: {WARN_BG}; border: 1px solid {WARN_BORDER}; border-radius: 8px; }}
QFrame#info {{ background: {INFO_BG}; border: 1px solid #B8D8F6; border-radius: 8px; }}
QFrame#warn QLabel, QFrame#info QLabel {{ background: transparent; }}
QPushButton {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 14px; }}
QPushButton:hover {{ border-color: {BLUE}; color: {BLUE_DARK}; }}
QPushButton:disabled {{ color: #9AA8B8; background: #EEF2F6; }}
QPushButton[primary="true"] {{ background: {BLUE}; border-color: {BLUE}; color: white; font-weight: 700; padding: 11px 16px; }}
QPushButton[primary="true"]:hover {{ background: {BLUE_DARK}; color: white; }}
QPushButton[primary="true"]:disabled {{ background: #9CC8F3; border-color: #9CC8F3; color: white; }}
QPushButton[danger="true"] {{ color: {DANGER}; }}
QToolButton {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 10px; }}
QToolButton:hover {{ border-color: {BLUE}; }}
QToolButton:checked {{ background: {BLUE}; color: white; border-color: {BLUE}; }}
QToolButton:disabled {{ color: #9AA8B8; background: #EEF2F6; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
    background: white; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 8px; selection-background-color: {BLUE}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {BLUE}; }}
QListWidget {{ background: white; border: 1px solid {BORDER}; border-radius: 10px; padding: 4px; outline: none; }}
QListWidget::item {{ border-radius: 8px; padding: 6px; }}
QListWidget::item:selected {{ background: {INFO_BG}; color: {TEXT}; border: 1px solid {BLUE}; }}
QProgressBar {{ border: 1px solid {BORDER}; border-radius: 7px; background: #EAF0F7; height: 14px; text-align: center; font-size: 11px; }}
QProgressBar::chunk {{ background: {BLUE}; border-radius: 6px; }}
QGroupBox {{ border: 1px solid {BORDER}; border-radius: 10px; margin-top: 14px; padding: 12px 10px 8px 10px; font-weight: 700; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
QSlider::groove:horizontal {{ height: 6px; background: #DCE6F2; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {BLUE}; width: 16px; margin: -5px 0; border-radius: 8px; }}
QSlider::sub-page:horizontal {{ background: {BLUE}; border-radius: 3px; }}
QScrollArea {{ border: none; background: transparent; }}
QStatusBar {{ background: white; border-top: 1px solid {BORDER}; }}
QToolTip {{ background: {NAVY}; color: white; border: none; padding: 5px; }}
"""


def apply(app) -> None:
    f = QFont()
    f.setFamilies(["Segoe UI", "Leelawadee UI", "Tahoma", "Noto Sans Thai", "DejaVu Sans"])
    f.setPointSize(10)
    app.setFont(f)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)


def icon(name: str, color: str = "blue") -> QIcon:
    return QIcon(str(resource_path(f"assets/icons/{name}-{color}.png")))
