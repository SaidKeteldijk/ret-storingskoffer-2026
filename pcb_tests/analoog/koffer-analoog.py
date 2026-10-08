#!/usr/bin/env python3
"""
koffer-analoog.py - De acht analoge uitgangen van de koffer, over twee DAC-printen.
RET N.V. | Said Keteldijk (1045604)
"""

import spidev

SPI_BUS = 0
SPI_CS = 1
SPI_SPEED = 1_000_000
SPI_MODE = 1

VFS = 2.5

CHANNELS = {"A": 0b00, "B": 0b01, "C": 0b10, "D": 0b11}

ADRESSEN = {
    1: {"stroom": 0b00, "spanning": 0b01},
    2: {"stroom": 0b10, "spanning": 0b11},
}

SPANNING = {"soort": "spanning", "unit": "V", "min": 0.0, "max": 48.0,
            "scale": 19.2, "v_max": 2.5}
STROOM = {"soort": "stroom", "unit": "mA", "min": 4.0, "max": 20.0,
          "scale": 10.0, "v_max": 2.0}

KLEMMEN = {}
for _i in range(8):
    _print = 1 if _i < 4 else 2
    _kanaal = "ABCD"[_i % 4]
    KLEMMEN[f"U{_i + 1}"] = (_print, "spanning", _kanaal, SPANNING)
    KLEMMEN[f"I{_i + 1}"] = (_print, "stroom", _kanaal, STROOM)


def volts_to_code(volts):
    return round(max(0.0, min(VFS, volts)) / VFS * 0xFFFF)


def code_to_volts(code):
    return code / 0xFFFF * VFS


class DAC8564:
    def __init__(self, spi, address):
        self.spi = spi
        self.address = address & 0x03

    def write_code(self, channel, code):
        """LD1=0, LD0=1: schrijven en dit kanaal direct bijwerken (LDAC ligt vast aan GND)."""
        code = max(0, min(0xFFFF, int(code)))
        byte0 = (self.address << 6) | (1 << 4) | ((channel & 0x03) << 1)
        self.spi.xfer2([byte0, (code >> 8) & 0xFF, code & 0xFF])
        return code

    def write_volts(self, channel, volts):
        return self.write_code(channel, volts_to_code(volts))

    def all_zero(self):
        for ch in CHANNELS.values():
            self.write_code(ch, 0x0000)


def toon_lijst():
    print("Klem  print  DAC            adres  kanaal  bereik")
    for naam, (prt, soort, kanaal, cfg) in KLEMMEN.items():
        adres = ADRESSEN[prt][soort]
        dac = "DAC 2 (U3)" if soort == "spanning" else "DAC 1 (U1)"
        print(f"{naam:<5} {prt:^5}  {dac:<14} {adres:02b}     {kanaal}"
              f"       {cfg['min']:.0f}..{cfg['max']:.0f} {cfg['unit']}")


def toon_status(standen):
    spanning = "  ".join(f"U{i + 1}={standen[f'U{i + 1}']:5.1f}V" for i in range(8))
    stroom = "  ".join(f"I{i + 1}={standen[f'I{i + 1}']:5.1f}mA" for i in range(8))
    print(spanning)
    print(stroom)


def print_help():
    print("Commando's:")
    print("  U<n> <volt>       klem U1..U8 op 0..48 V        bv. U3 24")
    print("  I<n> <mA>         lus I1..I8 op 4..20 mA        bv. I5 12")
    print("  U<n> raw <volt>   DAC-spanning direct (kalibratie)")
    print("  alles <volt>      alle acht klemmen U1..U8 tegelijk")
    print("  lijst             de verdeling klem naar DAC en adres")
    print("  status            laatst ingestelde waarde per klem")
    print("  nul               alle zestien kanalen naar 0 V DAC")
    print("  q                 stoppen (alles naar 0 V)")


def main():
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_CS)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = SPI_MODE

    dacs = {(prt, soort): DAC8564(spi, adres)
            for prt, soorten in ADRESSEN.items()
            for soort, adres in soorten.items()}
    standen = {naam: 0.0 for naam in KLEMMEN}

    def zet(naam, waarde, raw=False):
        prt, soort, kanaal, cfg = KLEMMEN[naam]
        dac = dacs[(prt, soort)]
        if raw:
            if waarde > cfg["v_max"]:
                print(f"Geweigerd: maximaal {cfg['v_max']:.2f} V DAC voor {naam}")
                return
            code = dac.write_volts(CHANNELS[kanaal], waarde)
            benadering = code_to_volts(code) * cfg["scale"]
            print(f"{naam}: DAC {code_to_volts(code):.4f} V (code 0x{code:04X})"
                  f" -> ongeveer {benadering:.3f} {cfg['unit']}")
            standen[naam] = benadering
            return
        if not (cfg["min"] <= waarde <= cfg["max"]):
            print(f"Buiten bereik: {cfg['min']:.0f}..{cfg['max']:.0f} {cfg['unit']}")
            return
        dac_volts = min(waarde / cfg["scale"], cfg["v_max"])
        code = dac.write_volts(CHANNELS[kanaal], dac_volts)
        werkelijk = code_to_volts(code) * cfg["scale"]
        standen[naam] = werkelijk
        print(f"{naam} (print {prt}, adres {ADRESSEN[prt][soort]:02b}, kanaal "
              f"{kanaal}): {werkelijk:.3f} {cfg['unit']}  "
              f"(DAC {code_to_volts(code):.4f} V, code 0x{code:04X})")

    try:
        for dac in dacs.values():
            dac.all_zero()
        print(f"Verbonden op CE{SPI_CS}, SPI-mode {SPI_MODE}.")
        print("Vier DAC8564's op adres 00, 01, 10 en 11; alle kanalen op 0 V DAC.")
        print_help()

        while True:
            cmd = input("> ").strip()
            if not cmd:
                continue
            low = cmd.lower()

            if low == "q":
                break
            if low in ("h", "help", "?"):
                print_help()
                continue
            if low == "lijst":
                toon_lijst()
                continue
            if low == "status":
                toon_status(standen)
                continue
            if low == "nul":
                for dac in dacs.values():
                    dac.all_zero()
                for naam in standen:
                    standen[naam] = 0.0
                print("Alle zestien kanalen op 0 V DAC")
                continue

            parts = cmd.split()

            if parts[0].lower() == "alles" and len(parts) == 2:
                try:
                    waarde = float(parts[1])
                except ValueError:
                    print("Ongeldige waarde")
                    continue
                for i in range(8):
                    zet(f"U{i + 1}", waarde)
                continue

            naam = parts[0].upper()
            if naam not in KLEMMEN:
                print("Onbekende klem, kies U1..U8 of I1..I8")
                continue

            if len(parts) == 3 and parts[1].lower() == "raw":
                try:
                    zet(naam, float(parts[2]), raw=True)
                except ValueError:
                    print("Ongeldige spanning")
                continue

            if len(parts) != 2:
                print("Ongeldige invoer, typ 'help'")
                continue

            try:
                zet(naam, float(parts[1]))
            except ValueError:
                print("Ongeldige waarde")

    except KeyboardInterrupt:
        print()
    finally:
        try:
            for dac in dacs.values():
                dac.all_zero()
        except Exception:
            pass
        spi.close()
        print("Alle uitgangen op 0 V DAC, programma gestopt.")


if __name__ == "__main__":
    main()
