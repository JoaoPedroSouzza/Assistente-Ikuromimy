from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ui.modes_manager import LIMITE_COMANDOS_POR_MODO


class CriarModoDialog(QDialog):
    """Caixa de criação/edição de modo: nome + campos de comando, com
    um botão '+' pra adicionar mais (até o limite de 5). Passando
    'nome_inicial' e 'comandos_iniciais', a caixa abre já preenchida
    (usado tanto pra criar um modo novo quanto editar um existente)."""

    def __init__(self, parent=None, nome_inicial: str = "", comandos_iniciais: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Editar modo" if comandos_iniciais else "Criar modo")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Nome do modo (ex: 🧑‍💻 Modo Programador):"))
        self.campo_nome = QLineEdit(nome_inicial)
        layout.addWidget(self.campo_nome)

        layout.addWidget(QLabel("Comandos (executam em sequência, um por vez):"))

        self._layout_comandos = QVBoxLayout()
        layout.addLayout(self._layout_comandos)

        self.campos_comando: list[QLineEdit] = []
        self.btn_adicionar = QPushButton("+ Adicionar comando")
        for texto in (comandos_iniciais or [""]):
            self._adicionar_campo_comando(texto)

        self.btn_adicionar.clicked.connect(lambda: self._adicionar_campo_comando())
        layout.addWidget(self.btn_adicionar)

        botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _adicionar_campo_comando(self, texto_inicial: str = "") -> None:
        if len(self.campos_comando) >= LIMITE_COMANDOS_POR_MODO:
            return

        campo = QLineEdit(texto_inicial)
        campo.setPlaceholderText(f"Comando {len(self.campos_comando) + 1} (ex: abrir spotify)")
        self._layout_comandos.addWidget(campo)
        self.campos_comando.append(campo)

        if len(self.campos_comando) >= LIMITE_COMANDOS_POR_MODO:
            self.btn_adicionar.setEnabled(False)
            self.btn_adicionar.setText("Limite de 5 comandos atingido")

    def dados(self) -> tuple[str, list[str]]:
        """Devolve (nome, lista_de_comandos) com o que foi digitado."""
        nome = self.campo_nome.text().strip()
        comandos = [c.text().strip() for c in self.campos_comando if c.text().strip()]
        return nome, comandos
