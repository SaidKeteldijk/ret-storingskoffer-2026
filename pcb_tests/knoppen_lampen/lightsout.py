#!/usr/bin/env python3
"""
lightsout.py - Zet de lampen op de knoppen/lampen-PCB uit.
RET N.V. | Said Keteldijk (1045604)
"""

import spidev

SPI_BUS = 0
SPI_CS = 0
MCP_ADDR = 0b000
SPI_SPEED = 1_000_000

IODIRA = 0x00
IODIRB = 0x01
IOCON = 0x0A
GPPUA = 0x0C
OLATB = 0x15
HAEN = 0x08


def opcode(addr, read):
    return 0x40 | ((addr & 0x07) << 1) | (1 if read else 0)


def main():
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_CS)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = 0

    def write(reg, value):
        spi.xfer2([opcode(MCP_ADDR, False), reg, value & 0xFF])

    def read(reg):
        return spi.xfer2([opcode(MCP_ADDR, True), reg, 0x00])[2]

    try:
        write(IOCON, HAEN)

        write(OLATB, 0x00)
        write(IODIRB, 0x00)

        write(IODIRA, 0xFF)
        write(GPPUA, 0x00)

        if read(IODIRB) != 0x00 or read(OLATB) != 0x00:
            raise RuntimeError("MCP op adres 000 reageert niet zoals verwacht")

        print("Lampen H1..H8 uit, GPB0..GPB7 als uitgang laag gezet.")
        print("Knoppen S1..S8 (GPA0..GPA7) staan als ingang klaar.")

    finally:
        spi.close()


if __name__ == "__main__":
    main()
