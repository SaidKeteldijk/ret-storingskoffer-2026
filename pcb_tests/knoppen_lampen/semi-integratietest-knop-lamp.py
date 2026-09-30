#!/usr/bin/env python3
"""
semi-integratietest-knop-lamp.py - Knop bedient de bijbehorende lamp.
RET N.V. | Said Keteldijk (1045604)
"""

import sys
import time

import spidev
import RPi.GPIO as GPIO

MODE = "momentary"

RESET_PIN = 25
SPI_BUS = 0
SPI_CS = 0
MCP_ADDR = 0
SPI_SPEED = 1_000_000

if len(sys.argv) > 1:
    MCP_ADDR = int(sys.argv[1], 0) & 0x07

IDLE = 0xFF
POLL_INTERVAL = 0.01
DEBOUNCE_READS = 3

BUTTON_NAMES = [f"S{i + 1}" for i in range(8)]
LAMP_NAMES = [f"Q{i + 1}" for i in range(8)]

IODIRA = 0x00
IODIRB = 0x01
IPOLA = 0x02
IOCON = 0x0A
GPPUA = 0x0C
GPIOA = 0x12
OLATB = 0x15
HAEN = 0x08


def opcode(addr, read):
    return 0x40 | ((addr & 0x07) << 1) | (1 if read else 0)


class MCP23S17:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(SPI_BUS, SPI_CS)
        self.spi.max_speed_hz = SPI_SPEED
        self.spi.mode = 0

    def write(self, reg, value):
        self.spi.xfer2([opcode(MCP_ADDR, False), reg, value & 0xFF])

    def read(self, reg):
        return self.spi.xfer2([opcode(MCP_ADDR, True), reg, 0x00])[2]

    def close(self):
        self.spi.close()


def hardware_reset():
    if RESET_PIN is None:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RESET_PIN, GPIO.OUT, initial=GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(RESET_PIN, GPIO.HIGH)
    time.sleep(0.01)


def init_mcp(mcp):
    for a in range(8):
        mcp.spi.xfer2([opcode(a, False), IOCON, HAEN])

    mcp.write(OLATB, 0x00)
    mcp.write(IODIRB, 0x00)

    mcp.write(IODIRA, 0xFF)
    mcp.write(IPOLA, 0x00)
    mcp.write(GPPUA, 0x00)
    time.sleep(0.01)

    if mcp.read(IODIRA) != 0xFF or mcp.read(IODIRB) != 0x00:
        raise RuntimeError("MCP niet correct ingesteld, controleer de verbinding")


def read_buttons(mcp):
    """Geeft een debounced masker van ingedrukte knoppen (1 = ingedrukt)."""
    last = mcp.read(GPIOA)
    count = 1
    while count < DEBOUNCE_READS:
        time.sleep(POLL_INTERVAL)
        value = mcp.read(GPIOA)
        if value == last:
            count += 1
        else:
            last, count = value, 1
    return (last ^ IDLE) & 0xFF


def main():
    if MODE not in ("momentary", "toggle"):
        raise ValueError('MODE moet "momentary" of "toggle" zijn')

    hardware_reset()
    mcp = MCP23S17()
    try:
        init_mcp(mcp)
        print(f"Knoppen en lampen op adres {MCP_ADDR:03b} (CE{SPI_CS}).")
        print(f"Modus: {MODE}. Druk op S1..S8 (Ctrl+C om te stoppen)\n")

        previous = 0x00
        lamps = 0x00

        while True:
            pressed = read_buttons(mcp)
            changed = pressed ^ previous

            if changed:
                new_presses = changed & pressed

                if MODE == "momentary":
                    lamps = pressed
                else:
                    lamps ^= new_presses

                mcp.write(OLATB, lamps)

                for i in range(8):
                    if changed & (1 << i):
                        action = "ingedrukt" if pressed & (1 << i) else "losgelaten"
                        lamp = "AAN" if lamps & (1 << i) else "uit"
                        print(f"{BUTTON_NAMES[i]} {action:<10} -> lamp {LAMP_NAMES[i]} {lamp}")

                previous = pressed

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nGestopt.")
    finally:
        try:
            mcp.write(OLATB, 0x00)
        except Exception:
            pass
        mcp.close()
        if RESET_PIN is not None:
            GPIO.cleanup()
        print("Alle lampen uit.")


if __name__ == "__main__":
    main()
