#!/usr/bin/env python3
"""
scan.py - Zoekt MCP23S17's op de SPI-bus.
RET N.V. | Said Keteldijk (1045604)
"""

import time
import spidev
import RPi.GPIO as GPIO

RESET_PIN = 25
SPI_BUS = 0
SPI_CS_LIST = [0]
SPI_SPEED = 1_000_000

IODIRA = 0x00
IPOLA = 0x02
IOCON = 0x0A
HAEN = 0x08


def opcode(addr, read):
    """Bouw de SPI-opcode: 0100 A2 A1 A0 R/W."""
    return 0x40 | ((addr & 0x07) << 1) | (1 if read else 0)


def write_reg(spi, addr, reg, value):
    spi.xfer2([opcode(addr, False), reg, value & 0xFF])


def read_reg(spi, addr, reg):
    return spi.xfer2([opcode(addr, True), reg, 0x00])[2]


def hardware_reset():
    """Trek RESET kort laag. Wordt overgeslagen als RESET_PIN None is."""
    if RESET_PIN is None:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RESET_PIN, GPIO.OUT, initial=GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(RESET_PIN, GPIO.HIGH)
    time.sleep(0.01)


def enable_haen(spi):
    """
    Zet HAEN aan. De schrijfactie gaat naar alle 8 adressen, zodat elke chip
    het ontvangt, ook als HAEN al aan stond of de chip afwijkend reageert
    (bekende errata rond pin A2 bij HAEN = 0).
    """
    for addr in range(8):
        write_reg(spi, addr, IOCON, HAEN)


def probe(spi, addr):
    """Geeft True terug als er een MCP23S17 op dit adres reageert."""
    original = read_reg(spi, addr, IPOLA)
    found = True
    for pattern in (0xA5, 0x5A):
        write_reg(spi, addr, IPOLA, pattern)
        if read_reg(spi, addr, IPOLA) != pattern:
            found = False
            break
    write_reg(spi, addr, IPOLA, original)
    return found


def scan():
    """
    Scant alle opgegeven chip-selects en adressen.
    Geeft een dict terug: {cs: [adres, ...]}
    """
    results = {}
    hardware_reset()

    for cs in SPI_CS_LIST:
        spi = spidev.SpiDev()
        try:
            spi.open(SPI_BUS, cs)
        except FileNotFoundError:
            print(f"/dev/spidev{SPI_BUS}.{cs} bestaat niet, is SPI ingeschakeld?")
            continue

        spi.max_speed_hz = SPI_SPEED
        spi.mode = 0

        enable_haen(spi)
        found = [addr for addr in range(8) if probe(spi, addr)]
        results[cs] = found

        for addr in found:
            iocon = read_reg(spi, addr, IOCON)
            iodira = read_reg(spi, addr, IODIRA)
            print(f"  Gevonden: CE{cs}, adres {addr} "
                  f"(A2A1A0 = {addr:03b}, opcode 0x{opcode(addr, False):02X}) "
                  f"| IOCON = 0x{iocon:02X}, IODIRA = 0x{iodira:02X}")

        spi.close()

    return results


if __name__ == "__main__":
    print("MCP23S17 scan gestart...")
    try:
        results = scan()
    finally:
        if RESET_PIN is not None:
            GPIO.cleanup()

    total = sum(len(v) for v in results.values())
    if total == 0:
        print("\nGeen MCP23S17 gevonden. Controleer:")
        print("  - Gemeenschappelijke GND tussen Pi en externe 3V3-voeding")
        print("  - SI -> MOSI (GPIO10) en SO -> MISO (GPIO9), niet omgewisseld")
        print("  - RESET hoog (pull-up of GPIO)")
        print("  - Externe 3V3 aan en A0..A2 niet zwevend")
    else:
        print(f"\n{total} MCP23S17('s) gevonden.")
