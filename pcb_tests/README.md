# Losse PCB-testen

Deze map bevat testgereedschap waarmee elke printplaat afzonderlijk getoetst
kan worden, los van het dashboard. Dit hoort bij de unittesten uit hoofdstuk 6
van het projectdocument: elk deelsysteem wordt eerst zelfstandig aan zijn
specificaties getoetst voordat het aan de rest gekoppeld wordt.

De scripts zijn bewust losgekoppeld van de app. Zij importeren niets uit
`canvas.py`, `simulator.py` of `gpio_manager.py`, zodat een printplaat ook
getest kan worden als de app zelf nog niet werkt.

| Script | Deelsysteem | Test |
|-----------------------|-------------|------------------------------------------|
| `test_io_board.py` | 6 | MCP23S17 I/O-kaarten via de SPI-bus |

## Voorbereiding

De SPI-bus moet op de Raspberry Pi ingeschakeld zijn:

```console
sudo raspi-config
```

Ga naar Interface Options, kies SPI en zet die op Enabled. Controleer daarna
of het apparaat bestaat:

```console
ls /dev/spidev0.*
```

De scripts hebben twee bibliotheken nodig die de app zelf niet gebruikt:

```console
sudo apt install python3-spidev python3-gpiozero
```

Draai je in de virtuele omgeving, dan zijn deze pakketten alleen zichtbaar als
die met `--system-site-packages` is aangemaakt. Anders installeer je ze in de
omgeving zelf:

```console
source ../venv-rpi/bin/activate
pip install spidev gpiozero
```

## test_io_board.py

Test de MCP23S17 I/O-expanders van deelsysteem 6. De aansluiting op de
Raspberry Pi header is:

| Signaal | Header | GPIO |
|-----------|--------|--------|
| SCK | pin 23 | GPIO11 |
| SI (MOSI) | pin 19 | GPIO10 |
| SO (MISO) | pin 21 | GPIO9 |
| CS (CE0) | pin 24 | GPIO8 |
| RESET | pin 22 | GPIO25 |
| INT-NET | pin 18 | GPIO24 |
| 3V3 | pin 17 | - |
| GND | pin 20 | - |

Elke kaart krijgt met de DIP-schakelaars een eigen adres van 0 tot en met 7.
Het script zet bij het opstarten hardware-adressering (HAEN) aan; direct na een
reset luistert elke kaart namelijk nog naar elk adres, waardoor die ene
schrijfactie de hele keten bereikt.

De beschikbare commando's:

```console
python3 test_io_board.py scan              # zoek kaarten op adres 0 t/m 7
python3 test_io_board.py walk 0            # loop 1 bit langs GPA0..GPB7
python3 test_io_board.py write 0 A 0x0F    # schrijf een byte naar poort A
python3 test_io_board.py read 0            # lees beide poorten als ingang
python3 test_io_board.py read 0 --continu  # blijf lezen tot Ctrl-C
python3 test_io_board.py blink 0 A 3       # knipper alleen GPA3
python3 test_io_board.py blink 0 A         # knipper de hele poort A
python3 test_io_board.py blink 0 AB --delay 2   # alle 16 pinnen, 2 s aan / 2 s uit
python3 test_io_board.py allon 0           # alle 16 pinnen hoog, vasthouden
python3 test_io_board.py allon --alle      # idem op alle gevonden kaarten
```

Begin altijd met `scan`. Worden er geen kaarten gevonden, controleer dan de
voeding, de RESET-lijn en de DIP-standen voordat je verder zoekt.

### Uitgangen blijven alleen staan zolang het script draait

Bij het afsluiten zet het script alle pinnen van alle acht adressen terug naar
ingang. Dat is bewust zo: een testtool mag geen uitgangen laten staan waar
niemand meer zicht op heeft.

Het gevolg is wel dat `write` geen blijvend effect heeft. Dat commando zet de
byte weg en sluit meteen daarna af, waardoor de uitgang direct weer wegvalt.
Gebruik `write` dus alleen samen met een oscilloscoop, en gebruik `allon`,
`walk` of `blink` wanneer je rustig met een multimeter wilt meten: die blijven
lopen tot je Ctrl-C geeft.

> **Voorzichtig:** `walk`, `write`, `blink` en `allon` zetten de pinnen van de gekozen
> kaart als uitgang. Doe dat niet op een kaart waar iets op de ingangen is
> aangesloten: twee uitgangen die elkaar tegenwerken beschadigen de MCP23S17.
> Het script zet bij het afsluiten alle pinnen terug naar ingang, ook na Ctrl-C.

## Meetresultaten

Noteer de uitkomst van elke test in het unittestformulier van het betreffende
deelsysteem in het projectdocument, zodat de resultaten herleidbaar blijven bij
de acceptatietest.
