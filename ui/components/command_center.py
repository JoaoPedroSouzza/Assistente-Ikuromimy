from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QLabel

class CommandCenter(QDialog):
    chosen = Signal(str, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Central de comandos")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True); self.resize(530,330)
        area = QVBoxLayout(self); area.setContentsMargins(24,24,24,24)
        title = QLabel("✦  O que você quer fazer?"); title.setObjectName("titulo"); area.addWidget(title)
        self.input = QLineEdit(); self.input.setPlaceholderText("Digite um comando ou uma pergunta..."); area.addWidget(self.input)
        self.list = QListWidget(); area.addWidget(self.list)
        self.actions = [("Executar comando", "comando"),("Perguntar para Ikuromimy", "ia"),("Pesquisar na web", "pesquisar"),("Abrir configurações", "config")]
        self.list.addItems([label for label,_ in self.actions]); self.list.setCurrentRow(0)
        self.input.returnPressed.connect(self.choose)
        self.list.itemActivated.connect(self.choose)
        hint = QLabel("↑ ↓ selecionar    ENTER confirmar    ESC fechar"); hint.setObjectName("muted"); area.addWidget(hint)
        self.input.installEventFilter(self)
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.input and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Up,Qt.Key_Down):
            delta = 1 if event.key() == Qt.Key_Down else -1
            self.list.setCurrentRow((self.list.currentRow()+delta)%len(self.actions)); return True
        return super().eventFilter(obj,event)
    def choose(self):
        action = self.actions[max(0,self.list.currentRow())][1]
        text = self.input.text().strip()
        if not text and action != "config": return
        self.accept(); self.chosen.emit(action,text)
    def open_center(self):
        self.input.clear(); self.list.setCurrentRow(0)
        self.show(); self.raise_(); self.activateWindow(); self.input.setFocus()
