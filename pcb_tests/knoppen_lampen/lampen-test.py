#!/usr/bin/env python3
"""
lampen-test.py - Lampen Q1..Q8 los aansturen.
RET N.V. | Said Keteldijk (1045604)
"""

import sys
import time

import spidev
import RPi.GPIO as GPIO

RESET_PIN = 25
SPI_BUS = 0
SPI_CS = 0
MCP_ADDR = 0
SPI_SPEED = 1_000_000

if len(sys.argv) > 1:
    MCP_ADDR = int(sys.argv[1], 0) & 0x07

IODIRB = 0x01
IOCON = 0x0A
GPIOB = 0x13
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


def init_lamps(mcp):
    for a in range(8):
        mcp.spi.xfer2([opcode(a, False), IOCON, HAEN])

    mcp.write(OLATB, 0x00)
    mcp.write(IODIRB, 0x00)

    if mcp.read(IODIRB) != 0x00:
        raise RuntimeError("IODIRB niet correct ingesteld, controleer de verbinding")


def show_status(state):
    lamps = "  ".join(f"L{i}:{'AAN' if state & (1 << i) else 'uit'}" for i in range(8))
    print(f"[{state:08b}]  {lamps}")


def main():
    hardware_reset()
    mcp = MCP23S17()
    try:
        init_lamps(mcp)
        state = 0x00
        print(f"Lampen aansturen op adres {MCP_ADDR:03b} (CE{SPI_CS}).")
        print("Alle lampen uit. Typ 0-7 = aan, u0-u7 = uit, x = alles uit, q = stoppen")
        show_status(state)

        while True:
            cmd = input("> ").strip().lower()

            if cmd == "q":
                break
            elif cmd == "x":
                state = 0x00
            elif cmd.isdigit() and 0 <= int(cmd) <= 7:
                state |= 1 << int(cmd)
            elif cmd.startswith("u") and cmd[1:].isdigit() and 0 <= int(cmd[1:]) <= 7:
                state &= ~(1 << int(cmd[1:])) & 0xFF
            else:
                print("Ongeldige invoer. Gebruik 0-7, u0-u7, x of q.")
                continue

            mcp.write(OLATB, state)
            show_status(mcp.read(OLATB))

    except KeyboardInterrupt:
        print()
    finally:
        try:
            mcp.write(OLATB, 0x00)
        except Exception:
            pass
        mcp.close()
        if RESET_PIN is not None:
            GPIO.cleanup()
        print("Alle lampen uit, programma gestopt.")


if __name__ == "__main__":
    main()
