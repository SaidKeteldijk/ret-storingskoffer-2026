#!/usr/bin/env python3
"""
dac-tester.py - Analoge uitgangen via twee DAC8564's.
RET N.V. | Said Keteldijk (1045604)
"""

import spidev

SPI_BUS = 0
SPI_CS = 1
SPI_SPEED = 1_000_000
SPI_MODE = 1

VREF = 2.5
GAIN = 2
VFS = 2.5

CHANNELS = {"A": 0b00, "B": 0b01, "C": 0b10, "D": 0b11}

OUTPUTS = {
    "1": {
        "name": "DAC 1 (U1, XTR117 stroomlus)",
        "address": 0b00,
        "unit": "mA",
        "min": 4.0,
        "max": 20.0,
        "scale": 10.0,
        "v_max": 2.0,
    },
    "2": {
        "name": "DAC 2 (U3, MCP6002 booster)",
        "address": 0b01,
        "unit": "V",
        "min": 0.0,
        "max": 48.0,
        "scale": 19.2,
        "v_max": 2.5,
    },
}


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


def print_help():
    print("Commando's:")
    for key, cfg in OUTPUTS.items():
        naam = cfg["name"]
        eenheid = cfg["unit"]
        print(f"  {key} <kanaal> <waarde>    {naam}: "
              f"{cfg['min']:.0f}..{cfg['max']:.0f} {eenheid}"
              f"   bv. {key} A {cfg['max'] / 2:.0f}")
    print("  <dac> <kanaal> raw <volt>  DAC-spanning direct zetten (kalibratie)")
    print("  nul                        alle kanalen naar 0 V DAC")
    print("  q                          stoppen (alles naar 0 V)")


def main():
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_CS)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = SPI_MODE

    dacs = {key: DAC8564(spi, cfg["address"]) for key, cfg in OUTPUTS.items()}

    try:
        for dac in dacs.values():
            dac.all_zero()
        print(f"Verbonden op CE{SPI_CS}, SPI-mode {SPI_MODE}.")
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
            if low == "nul":
                for dac in dacs.values():
                    dac.all_zero()
                print("Alle kanalen op 0 V DAC")
                continue

            parts = cmd.split()
            if len(parts) not in (3, 4):
                print("Ongeldige invoer, typ 'help'")
                continue

            key, ch = parts[0], parts[1].upper()
            if key not in OUTPUTS:
                print(f"Onbekende DAC '{key}', kies 1 of 2")
                continue
            if ch not in CHANNELS:
                print("Kanaal moet A, B, C of D zijn")
                continue

            cfg, dac = OUTPUTS[key], dacs[key]

            if len(parts) == 4 and parts[2].lower() == "raw":
                try:
                    volts = float(parts[3])
                except ValueError:
                    print("Ongeldige spanning")
                    continue
                if volts > cfg["v_max"]:
                    grens = cfg["v_max"]
                    naam = cfg["name"]
                    print(f"Geweigerd: maximaal {grens:.2f} V DAC voor {naam}")
                    continue
                code = dac.write_volts(CHANNELS[ch], volts)
                naam = cfg["name"]
                eenheid = cfg["unit"]
                print(f"{naam} kanaal {ch}: DAC {code_to_volts(code):.4f} V "
                      f"(code 0x{code:04X}) -> ongeveer "
                      f"{code_to_volts(code) * cfg['scale']:.3f} {eenheid}")
                continue

            try:
                value = float(parts[2])
            except ValueError:
                print("Ongeldige waarde")
                continue

            if not (cfg["min"] <= value <= cfg["max"]):
                print(f"Buiten bereik: {cfg['min']:.0f}..{cfg['max']:.0f} "
                      f"{cfg['unit']}")
                continue

            dac_volts = min(value / cfg["scale"], cfg["v_max"])
            code = dac.write_volts(CHANNELS[ch], dac_volts)
            werkelijk = code_to_volts(code) * cfg["scale"]
            naam = cfg["name"]
            eenheid = cfg["unit"]
            print(f"{naam} kanaal {ch}: {werkelijk:.3f} {eenheid}  "
                  f"(DAC {code_to_volts(code):.4f} V, code 0x{code:04X})")

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
