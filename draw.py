"""
draw.py - Tekenfuncties voor alle elektrotechnische symbolen.
RET N.V. | Said Keteldijk (1045604)

Alle functies tekenen gecentreerd op (0,0); de canvas past translate en
rotate toe voor de aanroep.
"""

import math

from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtCore import QRectF, Qt

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


def _draaihoek(p) -> float:
    """De rotatie die op dit moment in de transformatie van de painter zit."""
    t = p.transform()
    return math.degrees(math.atan2(t.m12(), t.m11()))


def _tekst(p, x, y, inhoud):
    """
    Zet tekst horizontaal neer, ook als het symbool gedraaid staat.

    Het anker (x, y) ligt in het assenstelsel van het symbool, zodat de tekst
    met het symbool meedraait van plaats. De rotatie wordt er vlak voor het
    tekenen weer uitgehaald, waardoor componentnummers en contactnummers
    altijd leesbaar blijven. De tekst wordt op het anker gecentreerd.
    """
    inhoud = "" if inhoud is None else str(inhoud)
    if not inhoud:
        return
    p.save()
    p.translate(x, y)
    p.rotate(-_draaihoek(p))
    vak = QRectF(-150, -60, 300, 120)
    p.drawText(vak, Qt.AlignCenter | Qt.TextDontClip, inhoud)
    p.restore()


def _zijkant(x, afstand):
    """Anker op afstand van een aansluitpunt, aan de kant waar het punt ligt."""
    return x + afstand if x > 0 else x - afstand


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
    _tekst(p, 0, -17, label)
    p.setFont(QFont("Courier New", 12))
    _tekst(p, -CONN + 7, 22, cs)
    _tekst(p, CONN - 7, 22, cs + 1)


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
        _tekst(p, -CONN + 7, y - 22, cs + ci)
        _tekst(p, CONN - 7, y - 22, cs + ci + 1)
    p.setPen(QPen(QColor(kleur), 1, Qt.DashLine))
    p.drawLine(0, -CONN - 7, 0, CONN - 7)
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    _tekst(p, 0, -CONN - 17, label)
    badge = "NC" if nc else "NO"
    p.setFont(QFont("Courier New", 14))
    _tekst(p, CONN + 16, 0, badge)


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
    _tekst(p, _zijkant(a_x, rc + 13), a_y, "A")
    _tekst(p, _zijkant(b_x, rc + 13), b_y, "B")
    # Naast de aansluitdraad van COM, anders loopt de draad door de tekst.
    _tekst(p, _zijkant(com_x, rc + 22), com_y + 26, "COM")

    p.setFont(QFont("Courier New", 9, QFont.Bold))
    _tekst(p, 0, -CONN - 22, label)

    p.setFont(QFont("Courier New", 12))
    # Naast de letter van het aansluitpunt, weg van het midden van het
    # symbool, zodat nummer en letter elkaar niet raken.
    _tekst(p, com_x, com_y - 26, cs)
    _tekst(p, a_x, _zijkant(a_y, 26), cs + 1)
    _tekst(p, b_x, _zijkant(b_y, 26), cs + 2)


def _ec_rspdt(p, label, cs, positie_c=False, flipped=False):
    _ec_spdt(p, label, cs, positie_c=positie_c, flipped=flipped)


def _ec_relaisspoel(p, label, cs, actief=False):
    kleur = C_YELLOW if actief else C_PEACH
    tekst = label if label else "K"

    # De spoel is een staand kader. De breedte groeit mee met het label, zodat
    # een horizontaal gezet label er altijd in past.
    p.setFont(QFont("Courier New", 9, QFont.Bold))
    fm = p.fontMetrics()
    breedte = max(22, min(fm.horizontalAdvance(tekst) + 10, CONN * 2 - 16))
    hoogte = 44
    half_b = breedte // 2
    half_h = hoogte // 2

    p.setPen(QPen(QColor(kleur), 2))
    p.setBrush(QBrush(QColor(kleur + "33") if actief else Qt.transparent))
    p.drawLine(-CONN, 0, -half_b, 0)
    p.drawLine(half_b, 0, CONN, 0)
    p.drawRect(-half_b, -half_h, breedte, hoogte)
    p.setBrush(QBrush(Qt.transparent))
    p.setPen(QColor(kleur))
    _tekst(p, 0, 0, tekst)
    p.setFont(QFont("Courier New", 12))
    _tekst(p, -CONN + 7, 22, cs)
    _tekst(p, CONN - 7, 22, cs + 1)


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
    _tekst(p, 0, -17, label)
    p.setFont(QFont("Courier New", 12))
    _tekst(p, -CONN + 7, 22, cs)
    _tekst(p, CONN - 7, 22, cs + 1)


def _ec_motor(p, label, cs, actief=False):
    kleur = C_GREEN if actief else C_RED
    p.setPen(QPen(QColor(kleur), 2))
    p.setBrush(QBrush(QColor(kleur + "33") if actief else Qt.transparent))
    p.drawLine(-CONN, 0, -11, 0)
    p.drawLine(11, 0, CONN, 0)
    p.drawEllipse(-11, -11, 22, 22)
    p.setPen(QColor(kleur))
    p.setFont(QFont("Courier New", 10, QFont.Bold))
    _tekst(p, 0, 0, label if label else "M")
    p.setFont(QFont("Courier New", 12))
    _tekst(p, -CONN + 7, 22, cs)
    _tekst(p, CONN - 7, 22, cs + 1)


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
    _tekst(p, 0, -15, label)
    p.setFont(QFont("Courier New", 12))
    _tekst(p, -CONN + 7, 22, cs)
    _tekst(p, CONN - 7, 22, cs + 1)


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
    _tekst(p, 0, -26, label if label else "+24VDC")


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
    _tekst(p, 0, -26, label if label else "GND")


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
    _tekst(p, 14 + max(34, len(tekst) * 8 + 10) / 2, 0, tekst)


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
