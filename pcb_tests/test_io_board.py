#!/usr/bin/env python3
"""
Testtool voor de MCP23S17 I/O-kaarten van de storingskoffer.

Bus:  SCK=pin23, SI=pin19, SO=pin21, CS=pin24 (CE0), RESET=pin22 (GPIO25),
      INT-NET=pin18 (GPIO24), 3V3=pin17, GND=pin20.

Gebruik:
    python test_io_board.py scan
    python test_io_board.py walk 0            # loopt 1 bit langs A0..A7, B0..B7
    python test_io_board.py write 0 A 0x0F
    python test_io_board.py read 0
    python test_io_board.py blink 0 A 3       # knippert alleen GPA3

Voorzichtig: 'walk' en 'write' zetten de pinnen van die kaart als uitgang.
Doe dat niet op een kaart waar iets op de ingangen is aangesloten.
"""

import argparse
import time

import spidev
from gpiozero import DigitalOutputDevice

# --- registers (BANK = 0) ---------------------------------------------------
IODIRA, IODIRB = 0x00, 0x01
IPOLA = 0x02
GPINTENA = 0x04
DEFVALA, DEFVALB = 0x06, 0x07
INTCONA = 0x08
IOCON = 0x0A
GPPUA, GPPUB = 0x0C, 0x0D
GPIOA, GPIOB = 0x12, 0x13
OLATA, OLATB = 0x14, 0x15

# --- IOCON-bits -------------------------------------------------------------
IOCON_MIRROR = 0x40   # INTA en INTB samenvoegen
IOCON_HAEN = 0x08     # hardware-adressering aan
IOCON_ODR = 0x04      # INT open-drain, nodig voor de gedeelde INT-NET

RESET_PIN = 25
SPI_HZ = 1_000_000


class Bus:
    def __init__(self, bus=0, device=0, hz=SPI_HZ):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = hz
        self.spi.mode = 0                      # MCP23S17 werkt in mode 0
        self.reset = DigitalOutputDevice(RESET_PIN, initial_value=False)
        time.sleep(0.001)
        self.reset.on()                        # RESET is actief-laag
        time.sleep(0.001)

    def write(self, addr, reg, value):
        self.spi.xfer2([0x40 | (addr << 1), reg, value & 0xFF])

    def read(self, addr, reg):
        return self.spi.xfer2([0x41 | (addr << 1), reg, 0x00])[2]

    def init_haen(self):
        """Zet HAEN aan op alle kaarten tegelijk.

        Na een reset staat HAEN uit en luistert elke MCP naar elk adres, dus
        deze ene schrijfactie op adres 0 bereikt de hele keten. Daarna
        reageert elke kaart alleen nog op zijn eigen DIP-stand.
        """
        self.write(0, IOCON, IOCON_MIRROR | IOCON_HAEN | IOCON_ODR)

    def close(self):
        self.spi.close()
        self.reset.close()


def scan(bus):
    """Zoekt kaarten door een testpatroon in DEFVALA te schrijven en terug te lezen."""
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


def zet_uitgang(bus, addr, poort):
    reg = IODIRA if poort == "A" else IODIRB
    olat = OLATA if poort == "A" else OLATB
    bus.write(addr, olat, 0x00)
    bus.write(addr, reg, 0x00)          # 0 = uitgang


def zet_ingang(bus, addr, poort, pullup=True):
    iodir = IODIRA if poort == "A" else IODIRB
    gppu = GPPUA if poort == "A" else GPPUB
    bus.write(addr, iodir, 0xFF)        # 1 = ingang
    bus.write(addr, gppu, 0xFF if pullup else 0x00)


def main():
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

    b = sub.add_parser("blink", help="knipper een pin")
    b.add_argument("addr", type=int)
    b.add_argument("poort", choices=["A", "B"])
    b.add_argument("pin", type=int)
    b.add_argument("--delay", type=float, default=0.5)

    o = sub.add_parser("allon", help="zet alle 16 pinnen hoog en houd ze vast")
    o.add_argument("addr", type=int, nargs="?", default=None)
    o.add_argument("--alle", action="store_true",
                   help="alle gevonden kaarten in plaats van een enkel adres")

    a = p.parse_args()
    bus = Bus()
    bus.init_haen()

    try:
        if a.cmd == "scan":
            kaarten = scan(bus)
            if kaarten:
                for addr in kaarten:
                    print(f"kaart gevonden op adres {addr} (A2:A0 = {addr:03b})")
            else:
                print("geen kaarten gevonden - check voeding, RESET en de DIP-standen")

        elif a.cmd == "walk":
            for poort in ("A", "B"):
                zet_uitgang(bus, a.addr, poort)
            olat = {"A": OLATA, "B": OLATB}
            print("Ctrl-C om te stoppen")
            while True:
                for poort in ("A", "B"):
                    for bit in range(8):
                        bus.write(a.addr, olat[poort], 1 << bit)
                        print(f"\rGP{poort}{bit}   ", end="", flush=True)
                        time.sleep(a.delay)
                    bus.write(a.addr, olat[poort], 0x00)

        elif a.cmd == "write":
            waarde = int(a.waarde, 0)
            zet_uitgang(bus, a.addr, a.poort)
            bus.write(a.addr, OLATA if a.poort == "A" else OLATB, waarde)
            print(f"GP{a.poort} = 0b{waarde:08b}")

        elif a.cmd == "read":
            for poort in ("A", "B"):
                zet_ingang(bus, a.addr, poort)
            while True:
                ga = bus.read(a.addr, GPIOA)
                gb = bus.read(a.addr, GPIOB)
                print(f"\rGPA 0b{ga:08b}   GPB 0b{gb:08b}", end="", flush=True)
                if not a.continu:
                    print()
                    break
                time.sleep(0.2)

        elif a.cmd == "blink":
            zet_uitgang(bus, a.addr, a.poort)
            olat = OLATA if a.poort == "A" else OLATB
            print("Ctrl-C om te stoppen")
            while True:
                bus.write(a.addr, olat, 1 << a.pin)
                time.sleep(a.delay)
                bus.write(a.addr, olat, 0x00)
                time.sleep(a.delay)

        elif a.cmd == "allon":
            if a.alle:
                doelen = scan(bus)
            elif a.addr is None:
                p.error("geef een adres op, of gebruik --alle")
            else:
                doelen = [a.addr]

            if not doelen:
                print("geen kaarten gevonden - er is niets aangezet")
            else:
                for addr in doelen:
                    for poort in ("A", "B"):
                        zet_uitgang(bus, addr, poort)
                    bus.write(addr, OLATA, 0xFF)
                    bus.write(addr, OLATB, 0xFF)
                lijst = ", ".join(str(x) for x in doelen)
                print("alle 16 pinnen hoog op kaart " + lijst)
                # Vasthouden: bij het afsluiten gaan de pinnen terug naar
                # ingang, dus zonder deze lus valt de uitgang direct weg.
                print("Ctrl-C om te stoppen")
                while True:
                    time.sleep(0.5)

    except KeyboardInterrupt:
        print()
    finally:
        for addr in range(8):
            bus.write(addr, IODIRA, 0xFF)     # alles terug naar ingang
            bus.write(addr, IODIRB, 0xFF)
        bus.close()


if __name__ == "__main__":
    main()
