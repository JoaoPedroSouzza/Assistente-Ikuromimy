from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor
from ui.theme.colors import ACCENTS, mix

class ReactiveTheme(QObject):
    changed = Signal(object)
    def __init__(self, engine, bus, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.accent = QColor(ACCENTS["inicio"])
        self.previous = QColor(self.accent)
        self.target = QColor(self.accent)
        self.progress = 1.
        self.page = "inicio"
        self.overrides = {}
        engine.frame.connect(self.advance)
        bus.page_changed.connect(self.select_page)
        bus.theme_changed.connect(self.customize)

    def customize(self, color):
        self.overrides[self.page] = QColor(color)
        self.select_page(self.page)

    def select_page(self, page):
        self.page = page
        self.previous = QColor(self.accent)
        self.target = QColor(self.overrides.get(page, ACCENTS.get(page, ACCENTS["inicio"])))
        self.progress = 0.
        if self.engine.quality == "Desativado":
            self.advance(2.)

    def advance(self, dt):
        if self.progress >= 1:
            return
        self.progress = min(1., self.progress + dt / .85)
        t = self.progress * self.progress * (3 - 2*self.progress)
        self.accent = mix(self.previous, self.target, t)
        self.changed.emit(self.accent)

    def line_color(self, position):
        return mix(self.previous, self.target, (self.progress * 1.5 - position * .5) * 2)

    def stylesheet(self):
        accent = self.accent.name()
        return f"""
QWidget {{ color: #dce5ee; font-family: 'Segoe UI'; font-size: 13px; }}
QMainWindow, QDialog {{ background: #080b12; }}
QWidget#reactiveShell, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: 0; }}
QLabel {{ background: transparent; }}
QLabel#titulo {{ font-size: 22px; font-weight: 600; }}
QLabel#eyebrow {{ color: {accent}; font-size: 10px; font-weight: 600; letter-spacing: 3px; }}
QLabel#muted {{ color: #8794a7; }}
QLabel#heroTitle {{ font-size: 34px; font-weight: 300; }}
QLabel#brand {{ font-size: 16px; font-weight: 600; letter-spacing: 5px; }}
QFrame#glass, QWidget#glass {{ background: rgba(9, 15, 24, 190); border: 1px solid #24313d; border-radius: 16px; }}
QWidget#sidebar {{ background: rgba(7, 11, 18, 220); border-right: 1px solid #1f2b35; }}
QPushButton {{ background: rgba(19, 28, 39, 205); border: 1px solid #2b3949; border-radius: 9px; padding: 9px 12px; }}
QPushButton:hover {{ border-color: {accent}; background: #182938; }}
QPushButton:pressed, QPushButton:checked {{ border-color: {accent}; color: {accent}; background: #14232e; }}
QPushButton:disabled {{ color: #647080; border-color: #1b2531; }}
QPushButton#botao_sidebar {{ text-align: left; background: transparent; border: 1px solid transparent; padding: 12px 8px; }}
QPushButton#botao_sidebar:checked {{ background: #14232e; border-color: {accent}; color: {accent}; }}
QLineEdit, QTextEdit, QListWidget, QComboBox {{ background: rgba(8, 15, 24, 210); border: 1px solid #2b3949; border-radius: 9px; padding: 10px; selection-background-color: #354d63; }}
QLineEdit:focus {{ border-color: {accent}; }}
QComboBox QAbstractItemView, QMenu {{ background: #111b27; color: #dce5ee; selection-background-color: #354d63; }}
QProgressBar {{ background: #162331; border: 0; border-radius: 3px; min-height: 5px; max-height: 5px; }}
QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}
QSlider::groove:horizontal {{ background: #243442; height: 4px; }}
QSlider::handle:horizontal {{ background: {accent}; width: 12px; margin: -5px 0; border-radius: 6px; }}
QScrollBar:vertical {{ background: transparent; width: 7px; }}
QScrollBar::handle:vertical {{ background: #344552; border-radius: 3px; min-height: 22px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QWidget#barra_titulo {{ background: rgba(8,12,19,230); border-bottom: 1px solid #1d2935; }}
QPushButton#botao_titulo, QPushButton#botao_fechar {{ background: transparent; border: 0; padding: 0; }}
QPushButton#botao_fechar:hover {{ background: #a63249; }}
"""
