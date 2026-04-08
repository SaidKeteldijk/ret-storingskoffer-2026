"""
draw.py - Tekenfuncties voor alle elektrotechnische symbolen.
RET N.V. | Said Keteldijk (1045604)

Alle functies tekenen gecentreerd op (0,0). QPainter.translate/rotate
wordt door de canvas toegepast voor aanroep.
  HW   = 20px  halfbreedte symbool-body
  CONN = 40px  aansluitpunt op rasterpunt
"""

from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtCore import Qt

from constants import (
    C_GREEN,
    C_LAMP_ON,
    C_MAUVE,
    C_PEACH,
    C_RED,
    C_SKY,
    C_YELLOW,
    CONN,
    HW,
    TOOL_GND,
    TOOL_LAMP,
    TOOL_MOTOR,
    TOOL_NETLABEL,
    TOOL_POWER,
    TOOL_RCOIL,
    TOOL_RCONT,
    TOOL_RSPDT,
    TOOL_SPDT,
    TOOL_SWITCH,
    TOOL_SW2P_NC,
    TOOL_SW2P_NO,
)


def _ec_schakelaar(p, label, cs, gesloten=False):
    kleur = C_GREEN
    p.setPen(QPen(QColor(kleur), 2))
    p.drawLine(-CONN, 0, -9, 0)
    p.drawLine(9, 0, CONN, 0)
    if gesloten:
        p.drawLine(-9, 0, 9, 0)
    else:
        p.drawLine(-9, 0, 9, -7)
    p.setBrush(QBrush(QColor(kleur)))
    p.drawEllipse(-12, -3, 5, 5)
    p.drawEllipse(7, -3, 5, 5)
    p.setBrush(QBrush(Qt.transparent))
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    p.drawText(-len(label) * 3, -12, label)
    p.setFont(QFont("Courier New", 12))
    p.drawText(-CONN + 2, 10, str(cs))
    p.drawText(CONN - 10, 10, str(cs + 1))


def _ec_schakelaar2p(p, label, cs, gesloten=False, nc=False):
    """2-polige schakelaar. Pools op y = +/-CONN."""
    kleur = C_GREEN
    p.setRenderHint(QPainter.Antialiasing)
    for y, ci in [(-CONN, 0), (+CONN, 2)]:
        p.setPen(QPen(QColor(kleur), 2))
        p.drawLine(-CONN, y, -9, y)
        p.drawLine(9, y, CONN, y)
        if nc:
            if gesloten:
                p.drawLine(-9, y, 9, y + 7)
            else:
                p.drawLine(-9, y, 9, y)
        else:
            if gesloten:
                p.drawLine(-9, y, 9, y)
            else:
                p.drawLine(-9, y, 9, y - 7)
        p.setBrush(QBrush(QColor(kleur)))
        p.drawEllipse(-12, y - 3, 5, 5)
        p.drawEllipse(7, y - 3, 5, 5)
        p.setBrush(QBrush(Qt.transparent))
        p.setPen(QColor(kleur))
        p.setFont(QFont("Courier New", 12))
        p.drawText(-CONN + 2, y - 6, str(cs + ci))
        p.drawText(CONN - 10, y - 6, str(cs + ci + 1))
    p.setPen(QPen(QColor(kleur), 1, Qt.DashLine))
    p.drawLine(0, -CONN - 7, 0, CONN - 7)
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    p.drawText(-len(label) * 3, -CONN - 12, label)
    badge = "NC" if nc else "NO"
    p.setFont(QFont("Courier New", 14))
    p.drawText(CONN + 4, 4, badge)


def _towards_zero(value, offset):
    if value == 0:
        return value
    return value - (1 if value > 0 else -1) * offset


def _side_text_x(x, small_offset, large_offset):
    return x + small_offset if x > 0 else x - large_offset


def _ec_spdt(p, label, cs, positie_c=False, flipped=False):
    """
    2-weg wisselschakelaar (SPDT) gecentreerd op (0,0).

    In edit mode tekenen we het symbool 180 graden gedraaid zodat de visuele
    oriëntatie overeenkomt met de gewenste editorweergave, zonder de logica of
    contactvolgorde te veranderen.
    """
    kleur = "#6dd6a8"
    rc = 5

    if flipped:
        com_x, com_y = +HW, 0
        a_x, a_y = -HW, +HW
        b_x, b_y = -HW, -HW
    else:
        com_x, com_y = -HW, 0
        a_x, a_y = +HW, -HW
        b_x, b_y = +HW, +HW

    p.setPen(QPen(QColor(kleur), 2))
    p.drawLine(com_x * 2, 0, com_x, com_y)
    p.drawLine(a_x * 2, a_y * 2, a_x, a_y)
    p.drawLine(b_x * 2, b_y * 2, b_x, b_y)

    p.drawLine(_towards_zero(com_x, rc), com_y, 0, 0)

    if positie_c:
        p.setPen(QPen(QColor(kleur), 2))
        p.drawLine(0, 0, _towards_zero(b_x, 3), _towards_zero(b_y, 3))
        p.setPen(QPen(QColor(kleur + "55"), 1, Qt.DashLine))
        p.drawLine(0, 0, _towards_zero(a_x, 3), _towards_zero(a_y, 3))
    else:
        p.setPen(QPen(QColor(kleur), 2))
        p.drawLine(0, 0, _towards_zero(a_x, 3), _towards_zero(a_y, 3))
        p.setPen(QPen(QColor(kleur + "55"), 1, Qt.DashLine))
        p.drawLine(0, 0, _towards_zero(b_x, 3), _towards_zero(b_y, 3))

    p.setPen(QPen(QColor(kleur), 2))
    p.setBrush(QBrush(Qt.transparent))
    p.drawEllipse(com_x - rc, com_y - rc, rc * 2, rc * 2)
    p.drawEllipse(a_x - rc, a_y - rc, rc * 2, rc * 2)
    p.drawEllipse(b_x - rc, b_y - rc, rc * 2, rc * 2)

    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 14))
    p.drawText(_side_text_x(a_x, rc + 2, rc + 10), a_y + 4, "A")
    p.drawText(_side_text_x(b_x, rc + 2, rc + 10), b_y + 4, "B")
    p.drawText(_side_text_x(com_x, rc + 2, rc + 22), com_y + 4, "COM")

    p.setFont(QFont("Courier New", 9, QFont.Bold))
    p.drawText(-len(label) * 3, -CONN - 8, label)

    p.setFont(QFont("Courier New", 12))
    p.drawText(_side_text_x(com_x, rc + 2, rc + 12), com_y - rc - 2, str(cs))
    p.drawText(_side_text_x(a_x, rc + 2, rc + 12), a_y - rc - 2, str(cs + 1))
    p.drawText(_side_text_x(b_x, rc + 2, rc + 12), b_y - rc - 2, str(cs + 2))


def _ec_rspdt(p, label, cs, positie_c=False, flipped=False):
    _ec_spdt(p, label, cs, positie_c=positie_c, flipped=flipped)


def _ec_relaisspoel(p, label, cs, actief=False):
    kleur = C_YELLOW if actief else C_PEACH
    p.setPen(QPen(QColor(kleur), 2))
    p.setBrush(QBrush(QColor(kleur + "33") if actief else Qt.transparent))
    p.drawLine(-CONN, 0, -11, 0)
    p.drawLine(11, 0, CONN, 0)
    p.drawRect(-11, -7, 22, 14)
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    p.drawText(-len(label) * 4, 5, label)
    p.setFont(QFont("Courier New", 12))
    p.drawText(-CONN + 2, 10, str(cs))
    p.drawText(CONN - 10, 10, str(cs + 1))


def _ec_relaiscontact(p, label, cs, gesloten=False):
    kleur = C_GREEN if gesloten else C_MAUVE
    p.setPen(QPen(QColor(kleur), 2))
    p.drawLine(-CONN, 0, -9, 0)
    p.drawLine(9, 0, CONN, 0)
    if gesloten:
        p.drawLine(-9, 0, 9, 0)
    else:
        p.drawLine(-9, 0, 9, -7)
    p.setBrush(QBrush(QColor(kleur)))
    p.drawEllipse(-12, -3, 5, 5)
    p.drawEllipse(7, -3, 5, 5)
    p.setBrush(QBrush(Qt.transparent))
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    p.drawText(-len(label) * 3, -12, label)
    p.setFont(QFont("Courier New", 12))
    p.drawText(-CONN + 2, 10, str(cs))
    p.drawText(CONN - 10, 10, str(cs + 1))


def _ec_motor(p, label, cs, actief=False):
    kleur = C_GREEN if actief else C_RED
    p.setPen(QPen(QColor(kleur), 2))
    p.setBrush(QBrush(QColor(kleur + "33") if actief else Qt.transparent))
    p.drawLine(-CONN, 0, -11, 0)
    p.drawLine(11, 0, CONN, 0)
    p.drawEllipse(-11, -11, 22, 22)
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 10, QFont.Bold))
    p.drawText(-5, 4, label if label else "M")
    p.setFont(QFont("Courier New", 12))
    p.drawText(-CONN + 2, 14, str(cs))
    p.drawText(CONN - 10, 14, str(cs + 1))


def _ec_lamp(p, label, cs, actief=False):
    kleur = C_LAMP_ON if actief else C_YELLOW
    p.setPen(QPen(QColor(kleur), 2))
    p.setBrush(QBrush(QColor(C_LAMP_ON + "66") if actief else Qt.transparent))
    p.drawLine(-CONN, 0, -7, 0)
    p.drawLine(7, 0, CONN, 0)
    p.drawEllipse(-7, -7, 14, 14)
    if not actief:
        p.drawLine(-4, -4, 4, 4)
        p.drawLine(4, -4, -4, 4)
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    p.drawText(-len(label) * 3, -10, label)
    p.setFont(QFont("Courier New", 12))
    p.drawText(-CONN + 2, 14, str(cs))
    p.drawText(CONN - 10, 14, str(cs + 1))


def _ec_voeding(p, label, cs):
    kleur = "#ff9966"
    p.setPen(QPen(QColor(kleur), 2))
    p.setBrush(QBrush(QColor(kleur)))
    p.drawEllipse(-4, -4, 8, 8)
    p.setBrush(QBrush(Qt.transparent))
    p.drawLine(-8, 10, 8, 10)
    p.drawLine(0, 4, 0, 16)
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    p.drawText(-20, -8, label if label else "+24VDC")


def _ec_massa(p, label, cs):
    kleur = "#a6adc8"
    p.setPen(QPen(QColor(kleur), 2))
    p.setBrush(QBrush(QColor(kleur)))
    p.drawEllipse(-4, -4, 8, 8)
    p.setBrush(QBrush(Qt.transparent))
    p.drawLine(-10, 6, 10, 6)
    p.drawLine(-6, 11, 6, 11)
    p.drawLine(-3, 16, 3, 16)
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9))
    p.drawText(-12, -8, label if label else "GND")


def _ec_netlabel(p, label, cs):
    kleur = C_SKY
    tekst = label if label else "NET"

    p.setPen(QPen(QColor(kleur), 2))
    p.drawLine(0, 0, 14, 0)

    p.setPen(QPen(QColor(kleur), 1))
    p.setBrush(QBrush(QColor(kleur + "22")))
    p.drawRoundedRect(14, -10, max(34, len(tekst) * 8 + 10), 20, 4, 4)

    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    p.drawText(20, 5, tekst)


EC_DRAW_BASE = {
    TOOL_SWITCH: lambda p, l, c: _ec_schakelaar(p, l, c),
    TOOL_SW2P_NO: lambda p, l, c: _ec_schakelaar2p(p, l, c, nc=False),
    TOOL_SW2P_NC: lambda p, l, c: _ec_schakelaar2p(p, l, c, nc=True),
    TOOL_SPDT: lambda p, l, c: _ec_spdt(p, l, c, flipped=True),
    TOOL_RCOIL: lambda p, l, c: _ec_relaisspoel(p, l, c),
    TOOL_RCONT: lambda p, l, c: _ec_relaiscontact(p, l, c),
    TOOL_RSPDT: lambda p, l, c: _ec_rspdt(p, l, c, flipped=True),
    TOOL_MOTOR: lambda p, l, c: _ec_motor(p, l, c),
    TOOL_LAMP: lambda p, l, c: _ec_lamp(p, l, c),
    TOOL_POWER: lambda p, l, c: _ec_voeding(p, l, c),
    TOOL_GND: lambda p, l, c: _ec_massa(p, l, c),
    TOOL_NETLABEL: lambda p, l, c: _ec_netlabel(p, l, c),
}
