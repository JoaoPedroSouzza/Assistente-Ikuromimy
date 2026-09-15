from PySide6.QtGui import QColor
ACCENTS = {"inicio": "#61d9ed", "ia": "#ae8bfa", "musica": "#f07cab",
           "atalhos": "#79dfa5", "modos": "#f3ae74", "amigos": "#c69beb",
           "sistema": "#6eddd9", "remoto": "#82b1f4", "config": "#bacbdf"}
BACKGROUND = "#05070a"
ERROR = "#f47986"
def mix(a, b, amount):
    amount = max(0., min(1., amount))
    return QColor.fromRgbF(*(a.getRgbF()[i] * (1-amount) + b.getRgbF()[i] * amount for i in range(4)))
