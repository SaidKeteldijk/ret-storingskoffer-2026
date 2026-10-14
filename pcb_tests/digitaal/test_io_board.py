#!/usr/bin/env python3
"""
test_io_board.py - Testgereedschap voor losse MCP23S17 I/O-kaarten.
RET N.V. | Said Keteldijk (1045604)
"""

import argparse
import time

import spidev
from gpiozero import DigitalOutputDevice

IODIRA, IODIRB = 0x00, 0x01
DEFVALA = 0x06
IOCON = 0x0A
GPPUA, GPPUB = 0x0C, 0x0D
GPIOA, GPIOB = 0x12, 0x13
OLATA, OLATB = 0x14, 0x15

IOCON_HAEN = 0x08

RESET_PIN = 25
SPI_HZ = 1_000_000

OLAT = {"A": OLATA, "B": OLATB}
IODIR = {"A": IODIRA, "B": IODIRB}
GPPU = {"A": GPPUA, "B": GPPUB}


class Bus:
    def __init__(self, bus=0, device=0, hz=SPI_HZ):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = hz
        self.spi.mode = 0
        self.reset = DigitalOutputDevice(RESET_PIN, initial_value=True)
        self.gebruikt = set()

    def write(self, addr, reg, value):
        self.spi.xfer2([0x40 | (addr << 1), reg, value & 0xFF])

    def read(self, addr, reg):
        return self.spi.xfer2([0x41 | (addr << 1), reg, 0x00])[2]

    def init_haen(self):
        for addr in range(8):
            self.write(addr, IOCON, IOCON_HAEN)

    def uitgang(self, addr, poort):
        self.gebruikt.add(addr)
        self.write(addr, OLAT[poort], 0x00)
        self.write(addr, IODIR[poort], 0x00)

    def ingang(self, addr, poort, pullup=True):
        self.gebruikt.add(addr)
        self.write(addr, IODIR[poort], 0xFF)
        self.write(addr, GPPU[poort], 0xFF if pullup else 0x00)

    def opruimen(self):
        for addr in self.gebruikt:
            self.write(addr, IODIRA, 0xFF)
            self.write(addr, IODIRB, 0xFF)

    def close(self):
        self.spi.close()
        self.reset.close()


def scan(bus):
    gevonden = []
    for addr in range(8):
        ok = True
        for patroon in (0x55, 0xAA):
            bus.write(addr, DEFVALA, patroon)
            if bus.read(addr, DEFVALA) != patroon:
                ok = False
                break
        bus.write(addr, DEFVALA, 0x00)
        if ok:
            gevonden.append(addr)
    return gevonden


def argumenten():
    p = argparse.ArgumentParser(description="MCP23S17-test storingskoffer")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scan", help="zoek kaarten op adres 0..7")

    w = sub.add_parser("walk", help="loop 1 bit langs alle 16 pinnen")
    w.add_argument("addr", type=int)
    w.add_argument("--delay", type=float, default=0.3)

    s = sub.add_parser("write", help="schrijf een byte naar een poort")
    s.add_argument("addr", type=int)
    s.add_argument("poort", choices=["A", "B"])
    s.add_argument("waarde")

    r = sub.add_parser("read", help="lees beide poorten als ingang")
    r.add_argument("addr", type=int)
    r.add_argument("--continu", action="store_true")

    b = sub.add_parser("blink", help="knipper een pin, een poort of alle 16")
    b.add_argument("addr", type=int)
    b.add_argument("poort", choices=["A", "B", "AB"])
    b.add_argument("pin", type=int, nargs="?", default=None,
                   help="pinnummer 0..7; weglaten = de hele poort")
    b.add_argument("--delay", type=float, default=0.5)

    o = sub.add_parser("allon", help="zet alle 16 pinnen hoog en houd ze vast")
    o.add_argument("addr", type=int, nargs="?", default=None)
    o.add_argument("--alle", action="store_true",
                   help="alle gevonden kaarten in plaats van een enkel adres")
    return p, p.parse_args()


def main():
    p, a = argumenten()
    bus = Bus()
    bus.init_haen()

    try:
        if a.cmd == "scan":
            kaarten = scan(bus)
            print(" ".join(f"{x} ({x:03b})" for x in kaarten) if kaarten
                  else "geen kaarten gevonden")

        elif a.cmd == "walk":
            for poort in ("A", "B"):
                bus.uitgang(a.addr, poort)
            while True:
                for poort in ("A", "B"):
                    for bit in range(8):
                        bus.write(a.addr, OLAT[poort], 1 << bit)
                        print(f"\rGP{poort}{bit}   ", end="", flush=True)
                        time.sleep(a.delay)
                    bus.write(a.addr, OLAT[poort], 0x00)

        elif a.cmd == "write":
            waarde = int(a.waarde, 0)
            bus.uitgang(a.addr, a.poort)
            bus.write(a.addr, OLAT[a.poort], waarde)
            print(f"GP{a.poort} = 0b{waarde:08b}")

        elif a.cmd == "read":
            for poort in ("A", "B"):
                bus.ingang(a.addr, poort)
            while True:
                ga = bus.read(a.addr, GPIOA)
                gb = bus.read(a.addr, GPIOB)
                print(f"\rGPA 0b{ga:08b}   GPB 0b{gb:08b}", end="", flush=True)
                if not a.continu:
                    print()
                    break
                time.sleep(0.2)

        elif a.cmd == "blink":
            if a.pin is not None and a.poort == "AB":
                p.error("geef bij AB geen pinnummer op")
            if a.pin is not None and not 0 <= a.pin <= 7:
                p.error("pin moet tussen 0 en 7 liggen")

            poorten = ["A", "B"] if a.poort == "AB" else [a.poort]
            masker = 0xFF if a.pin is None else (1 << a.pin)
            for poort in poorten:
                bus.uitgang(a.addr, poort)
            while True:
                for poort in poorten:
                    bus.write(a.addr, OLAT[poort], masker)
                time.sleep(a.delay)
                for poort in poorten:
                    bus.write(a.addr, OLAT[poort], 0x00)
                time.sleep(a.delay)

        elif a.cmd == "allon":
            if a.alle:
                doelen = scan(bus)
            elif a.addr is None:
                p.error("geef een adres op, of gebruik --alle")
            else:
                doelen = [a.addr]

            if not doelen:
                print("geen kaarten gevonden")
            else:
                for addr in doelen:
                    for poort in ("A", "B"):
                        bus.uitgang(addr, poort)
                    bus.write(addr, OLATA, 0xFF)
                    bus.write(addr, OLATB, 0xFF)
                print("hoog op " + ", ".join(str(x) for x in doelen))
                while True:
                    time.sleep(0.5)

    except KeyboardInterrupt:
        print()
    finally:
        bus.opruimen()
        bus.close()


if __name__ == "__main__":
    main()
