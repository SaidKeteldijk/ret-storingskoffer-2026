#!/usr/bin/env python3
"""
koffer-diag.py - Controleert koffer_io.py van de app rechtstreeks op de hardware.
RET N.V. | Said Keteldijk (1045604)
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from koffer_io import (GPIOA, GPPUA, IOCON, IODIRA, IODIRB, IPOLA, OLATB,
                       KofferIO, ON_RPI, SPI_AANWEZIG)

REGISTERS = (("IOCON", IOCON), ("IODIRA", IODIRA), ("IODIRB", IODIRB),
             ("IPOLA", IPOLA), ("GPPUA", GPPUA), ("OLATB", OLATB))


def main():
    print(f"spidev aanwezig : {SPI_AANWEZIG}")
    print(f"RPi.GPIO actief : {ON_RPI}")

    koffer = KofferIO()
    gelukt = koffer.init()
    print(f"init geslaagd   : {gelukt}")
    if koffer.fout:
        print(f"melding         : {koffer.fout}")

    if not gelukt:
        print("")
        print("De app doet in deze toestand niets met de koffer. Controleer:")
        print("  - staat SPI aan?            ls /dev/spidev0.*")
        print("  - is de print gevoed?")
        print("  - staat de RESET-lijn hoog? meet GPIO25, fysieke pin 22")
        print("  - zit de print op adres 000? python3 ../scan.py")
        return 1

    print("")
    print("Registers na init:")
    for naam, reg in REGISTERS:
        print(f"  {naam:<7} = 0x{koffer._lees(reg):02X}")

    print("")
    print("Lamptest: H1 tot en met H8 gaan een voor een aan.")
    for i in range(8):
        koffer.schrijf_lampen({i: True})
        time.sleep(0.25)
    koffer.schrijf_lampen({})

    print("")
    print("Druk nu knoppen in. Ctrl-C om te stoppen.")
    vorige = None
    try:
        while True:
            rauw = koffer._lees(GPIOA)
            if rauw != vorige:
                knoppen = koffer.lees_knoppen()
                namen = [f"S{i + 1}" for i in range(8) if knoppen.get(i)]
                print(f"  GPIOA = 0b{rauw:08b}   ingedrukt: {', '.join(namen) or 'geen'}")
                vorige = rauw
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("")
    finally:
        koffer.cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
