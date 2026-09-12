"""
Gerenciador de tema: transforma UMA cor escolhida na roda em um esquema
monocromático completo pro app inteiro (fundo, cards, bordas, destaque),
monta o QSS correspondente e cuida de salvar/carregar a preferência
entre sessões (via QSettings, não precisa de arquivo separado).
"""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

_ORG = "Ikuromimy"
_APP = "AssistenteVirtual"
_CHAVE_COR = "tema/cor_base"

COR_PADRAO = "#7c8cff"


def _com_hsl(cor: QColor, h: float | None = None, s: float | None = None,
             l: float | None = None) -> QColor:
    """Devolve uma nova cor a partir de 'cor', trocando só os componentes
    HSL que forem passados (os outros mantêm o valor original)."""
    hh, ss, ll, aa = cor.getHslF()
    nova = QColor()
    nova.setHslF(
        h if h is not None else hh,
        max(0.0, min(1.0, s if s is not None else ss)),
        max(0.0, min(1.0, l if l is not None else ll)),
        aa,
    )
    return nova


def gerar_paleta_monocromatica(cor_base: QColor, n: int = 5) -> list[QColor]:
    """Gera N variações de luminosidade da MESMA cor (mesmo matiz e
    saturação) — do mais escuro pro mais claro. É o esquema monocromático
    clássico que aparece embaixo da roda como prévia."""
    h, s, _, _ = cor_base.getHslF()
    luminosidades = [0.20, 0.35, 0.50, 0.65, 0.80][:n]
    return [_com_hsl(cor_base, h=h, s=s, l=l) for l in luminosidades]


def _construir_cores_tema(cor_base: QColor) -> dict:
    _, s, l, _ = cor_base.getHslF()
    sat_fundo = min(s, 0.35)  # evita fundo "gritante" em cores muito saturadas

    return {
        "destaque": cor_base.name(),
        "destaque_hover": _com_hsl(cor_base, l=min(l + 0.12, 0.85)).name(),
        "fundo": _com_hsl(cor_base, s=sat_fundo, l=0.07).name(),
        "card": _com_hsl(cor_base, s=sat_fundo, l=0.13).name(),
        "card_hover": _com_hsl(cor_base, s=sat_fundo, l=0.18).name(),
        "borda": _com_hsl(cor_base, s=sat_fundo, l=0.24).name(),
        "texto": "#e8e8ea",
        "texto_fraco": _com_hsl(cor_base, s=0.10, l=0.62).name(),
    }


def gerar_qss(cor_base: QColor) -> str:
    c = _construir_cores_tema(cor_base)
    return f"""
QWidget {{
    background-color: {c['fundo']};
    color: {c['texto']};
    font-family: 'Segoe UI';
    font-size: 14px;
}}

QLabel#titulo {{
    font-size: 20px;
    font-weight: 700;
}}

QPushButton {{
    background-color: {c['card']};
    border: 1px solid {c['borda']};
    border-radius: 8px;
    padding: 8px 12px;
}}
QPushButton:hover {{
    background-color: {c['card_hover']};
    border: 1px solid {c['destaque']};
}}
QPushButton:pressed {{
    background-color: {c['destaque']};
    color: #ffffff;
}}

QPushButton#botao_sidebar {{
    text-align: left;
    border: none;
    border-radius: 8px;
}}
QPushButton#botao_sidebar:hover {{
    background-color: {c['card']};
    border: none;
}}

QLineEdit, QTextEdit {{
    background-color: {c['card']};
    border: 1px solid {c['borda']};
    border-radius: 8px;
    padding: 8px;
    color: {c['texto']};
}}
QLineEdit:focus {{
    border: 1px solid {c['destaque']};
}}

QSlider::groove:horizontal {{
    background: {c['borda']};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {c['destaque']};
    width: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}

QScrollBar:vertical {{
    background: {c['fundo']};
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {c['borda']};
    border-radius: 4px;
}}

QWidget#barra_titulo {{
    background-color: {c['card']};
    border-bottom: 1px solid {c['borda']};
}}
QLabel#titulo_barra {{
    font-size: 13px;
    font-weight: 600;
    color: {c['texto']};
}}
QPushButton#botao_titulo {{
    background-color: transparent;
    border: none;
    border-radius: 0px;
    padding: 0px;
    font-size: 13px;
}}
QPushButton#botao_titulo:hover {{
    background-color: {c['card_hover']};
    border: none;
}}
QPushButton#botao_fechar {{
    background-color: transparent;
    border: none;
    border-radius: 0px;
    padding: 0px;
    font-size: 13px;
}}
QPushButton#botao_fechar:hover {{
    background-color: #e81123;
    color: #ffffff;
    border: none;
}}
"""


def salvar_cor(cor: QColor) -> None:
    settings = QSettings(_ORG, _APP)
    settings.setValue(_CHAVE_COR, cor.name())


def carregar_cor() -> QColor:
    settings = QSettings(_ORG, _APP)
    valor = settings.value(_CHAVE_COR, COR_PADRAO)
    cor = QColor(valor)
    return cor if cor.isValid() else QColor(COR_PADRAO)


def aplicar_tema(cor: QColor) -> None:
    """Aplica o QSS gerado no app inteiro (QApplication) e salva a
    escolha pra próxima vez que o programa abrir."""
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(gerar_qss(cor))
    salvar_cor(cor)
