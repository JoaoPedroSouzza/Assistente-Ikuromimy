from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QVBoxLayout, QLabel
from ui.components.motion import ReactiveButton


class CommandBar(QFrame):
    submitted = Signal(str)
    suggestion_selected = Signal(str)
    voice_requested = Signal()
    file_selected = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glass")
        area = QVBoxLayout(self); area.setContentsMargins(16,10,16,10)
        row = QHBoxLayout()
        mark = QLabel("✦"); mark.setObjectName("eyebrow"); row.addWidget(mark)
        self.input = QLineEdit(); self.input.setPlaceholderText("Pergunte ou dê um comando...")
        self.input.setAccessibleName("Mensagem ou comando")
        row.addWidget(self.input,1)
        self.attach = ReactiveButton("+"); self.attach.setToolTip("Anexar arquivo de texto à conversa")
        self.voice = ReactiveButton("◉"); self.voice.setToolTip("Gravar voz — transcrição online")
        self.send = ReactiveButton("Enviar  ↗")
        for button in (self.attach,self.voice,self.send): row.addWidget(button)
        area.addLayout(row)
        hint = QLabel("ENTER  enviar     /     CTRL + ESPAÇO  central de comandos")
        hint.setObjectName("muted"); area.addWidget(hint)
        suggestions = QHBoxLayout()
        self.suggestions = []
        for _ in range(3):
            button = ReactiveButton()
            button.clicked.connect(lambda checked=False,b=button:self.suggestion_selected.emit(b.property("destination")))
            suggestions.addWidget(button); self.suggestions.append(button)
        area.addLayout(suggestions)
        self.set_context("inicio")
        self.input.returnPressed.connect(self.submit)
        self.send.clicked.connect(self.submit)
        self.voice.clicked.connect(self.voice_requested)
        self.attach.clicked.connect(self.choose_file)
    def submit(self):
        text = self.input.text().strip()
        if text: self.submitted.emit(text)
    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self,"Anexar texto", "", "Texto (*.txt *.md *.csv *.json *.py);;Todos os arquivos (*)")
        if path: self.file_selected.emit(path)

    def set_context(self, page):
        contexts = {
            "musica": [("Play / pause","play"),("Próxima faixa","próxima"),("Abrir Spotify","abrir spotify")],
            "ia": [("Resumir uma ideia","draft:Ajude-me a resumir esta ideia: "),("Explicar um assunto","draft:Explique de forma simples: "),("Anexar texto","attach")],
            "modos": [("Ver meus modos","page:modos"),("Editar atalhos","page:atalhos"),("Ver sistema","page:sistema")],
        }
        options = contexts.get(page,[("Abrir Spotify","abrir spotify"),("Como está meu PC?","page:sistema"),("Meus modos","page:modos")])
        for button,(label,target) in zip(self.suggestions,options):
            button.setText(label); button.setProperty("destination",target)
