#!/usr/bin/env python3
"""
knoppen-test.py - Knoppen S1..S8 uitlezen.
RET N.V. | Said Keteldijk (1045604)
"""

import time
import spidev
import RPi.GPIO as GPIO

RESET_PIN = 25
SPI_BUS = 0
SPI_CS = 0
MCP_ADDR = 1
SPI_SPEED = 1_000_000

USE_PULLUP = False
POLL_INTERVAL = 0.01
DEBOUNCE_READS = 3

NAMES = [f"S{i + 1}" for i in range(8)]

IODIRA = 0x00
IPOLA = 0x02
IOCON = 0x0A
GPPUA = 0x0C
GPIOA = 0x12
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


def init_buttons(mcp):
    for a in range(8):
        mcp.spi.xfer2([opcode(a, False), IOCON, HAEN])
    mcp.write(IODIRA, 0xFF)
    mcp.write(IPOLA, 0x00)
    mcp.write(GPPUA, 0xFF if USE_PULLUP else 0x00)
    time.sleep(0.01)

    if mcp.read(IODIRA) != 0xFF:
        raise RuntimeError("IODIRA niet correct ingesteld, controleer de verbinding")


def read_stable(mcp):
    """Leest GPIOA tot DEBOUNCE_READS keer achter elkaar dezelfde waarde komt."""
    last = mcp.read(GPIOA)
    count = 1
    while count < DEBOUNCE_READS:
        time.sleep(POLL_INTERVAL)
        value = mcp.read(GPIOA)
        if value == last:
            count += 1
        else:
            last, count = value, 1
    return last


def pressed_list(pressed_mask):
    return [NAMES[i] for i in range(8) if pressed_mask & (1 << i)]


def main():
    hardware_reset()
    mcp = MCP23S17()
    try:
        init_buttons(mcp)

        print("Laat alle knoppen los, rusttoestand wordt gemeten...")
        time.sleep(0.5)
        idle = read_stable(mcp)
        print(f"Rusttoestand GPA = {idle:08b} (bit 7 = S8 ... bit 0 = S1)")
        if idle not in (0x00, 0xFF):
            print("Let op: niet alle pinnen hebben dezelfde rustwaarde. "
                  "Controleer of er een knop ingedrukt was of een ingang zweeft.")
        print("Druk op een knop (Ctrl+C om te stoppen)\n")

        previous = 0x00
        while True:
            raw = read_stable(mcp)
            pressed = (raw ^ idle) & 0xFF
            changed = pressed ^ previous

            if changed:
                for i in range(8):
                    if changed & (1 << i):
                        state = "INGEDRUKT" if pressed & (1 << i) else "losgelaten"
                        print(f"{NAMES[i]} (GPA{i}) {state}")
                now = pressed_list(pressed)
                nu = ", ".join(now) if now else "geen"
                print(f"  Nu ingedrukt: {nu}\n")
                previous = pressed

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nGestopt.")
    finally:
        mcp.close()
        if RESET_PIN is not None:
            GPIO.cleanup()


if __name__ == "__main__":
    main()
