"""
constants.py - Alle constanten, kleuren en gereedschapsdefinities.
RET N.V. | Said Keteldijk (1045604)
"""

from pathlib import Path

GRID = 40
CANVAS_OX = 40
CANVAS_OY = 40
SNAP_R = 36
HW = GRID // 2
CONN = GRID

DEFAULT_DIR = Path.cwd() / "circuits"

C_BG = "#1e1e2e"
C_SIDE = "#11111b"
C_BORDER = "#313244"
C_TEXT = "#cdd6f4"
C_MUTED = "#6c7086"
C_BLUE = "#89b4fa"
C_GREEN = "#a6e3a1"
C_PEACH = "#fab387"
C_MAUVE = "#cba6f7"
C_RED = "#f38ba8"
C_YELLOW = "#f9e2af"
C_TEAL = "#94e2d5"
C_SKY = "#89dceb"
C_LIVE = "#ff9966"
C_LAMP_ON = "#ffe066"

TOOL_SELECT = "selecteer"
TOOL_WIRE = "draad"
TOOL_NETLABEL = "netlabel"
TOOL_SWITCH = "schakelaar"
TOOL_SW2P_NO = "schakelaar2p_no"
TOOL_SW2P_NC = "schakelaar2p_nc"
TOOL_SPDT = "spdt"
TOOL_RCOIL = "relaisspoel"
TOOL_RCONT = "relaiscontact"
TOOL_RSPDT = "relaiswisselcontact"
TOOL_MOTOR = "motor"
TOOL_LAMP = "lamp"
TOOL_POWER = "voeding"
TOOL_GND = "massa"
TOOL_DELETE = "verwijder"

SINGLE_TERMINAL = {TOOL_POWER, TOOL_GND, TOOL_NETLABEL}
FOUR_TERMINAL = {TOOL_SW2P_NO, TOOL_SW2P_NC}
THREE_TERMINAL = {TOOL_SPDT, TOOL_RSPDT}

GPIO_IN_TYPES = {TOOL_SWITCH, TOOL_SW2P_NO, TOOL_SW2P_NC, TOOL_SPDT, TOOL_RCONT}
GPIO_OUT_TYPES = {TOOL_LAMP, TOOL_MOTOR, TOOL_RCOIL}

SPI_GERESERVEERD = [7, 8, 9, 10, 11, 24, 25]
VALID_GPIO_PINS = [p for p in range(2, 28) if p not in SPI_GERESERVEERD]

KOFFER_KNOPPEN = [f"S{i + 1}" for i in range(8)]
KOFFER_LAMPEN  = [f"Q{i + 1}" for i in range(8)]

CONTACTS_PER_TYPE = {
    TOOL_SWITCH: 2,
    TOOL_SW2P_NO: 4,
    TOOL_SW2P_NC: 4,
    TOOL_SPDT: 3,
    TOOL_RCOIL: 2,
    TOOL_RCONT: 2,
    TOOL_RSPDT: 3,
    TOOL_MOTOR: 2,
    TOOL_LAMP: 2,
    TOOL_POWER: 0,
    TOOL_GND: 0,
    TOOL_NETLABEL: 0,
}

TOOL_KLEUREN = {
    TOOL_SELECT: C_TEXT,
    TOOL_WIRE: C_BLUE,
    TOOL_NETLABEL: C_SKY,
    TOOL_SWITCH: C_GREEN,
    TOOL_SW2P_NO: C_GREEN,
    TOOL_SW2P_NC: "#a8d8a8",
    TOOL_SPDT: "#6dd6a8",
    TOOL_RCOIL: C_PEACH,
    TOOL_RCONT: C_MAUVE,
    TOOL_RSPDT: C_MAUVE,
    TOOL_MOTOR: C_RED,
    TOOL_LAMP: C_YELLOW,
    TOOL_POWER: C_PEACH,
    TOOL_GND: C_MUTED,
    TOOL_DELETE: C_RED,
}

TOOL_LABELS = {
    TOOL_SELECT: "Selecteren",
    TOOL_WIRE: "Draad",
    TOOL_NETLABEL: "Net Label",
    TOOL_SWITCH: "Schakelaar (1P)",
    TOOL_SW2P_NO: "Schakelaar 2P NO",
    TOOL_SW2P_NC: "Schakelaar 2P NC",
    TOOL_SPDT: "2-weg wisselschakelaar",
    TOOL_RCOIL: "Relaisspoel",
    TOOL_RCONT: "Relaiscontact",
    TOOL_RSPDT: "2-weg relaiscontact",
    TOOL_MOTOR: "Motor",
    TOOL_LAMP: "Lamp",
    TOOL_POWER: "Voeding (+V)",
    TOOL_GND: "Massa (GND)",
    TOOL_DELETE: "Verwijder",
}

LABEL_PREFIX = {
    TOOL_SWITCH: "S",
    TOOL_SW2P_NO: "S",
    TOOL_SW2P_NC: "S",
    TOOL_SPDT: "S",
    TOOL_RCOIL: "K",
    TOOL_RCONT: "K",
    TOOL_RSPDT: "K",
    TOOL_MOTOR: "M",
    TOOL_LAMP: "H",
    TOOL_POWER: "+V",
    TOOL_GND: "GND",
    TOOL_NETLABEL: "NET",
}
