# ret-storingskoffer-2026

# Inleiding (Dutch)

Deze Github repository dient als handleiding en technische documentatie voor de software van de storingskoffer. De informatie die in deze repository te vinden is, is bedoeld voor het technische personeel van firma Rotterdam Elektrische Tram (RET).

De storingskoffer is een trainingsmiddel dat ontwikkeld is om deelschakelingen uit de gelijkrichterstations van de RET na te bootsen. Hiermee kunnen onderhouds- en storingsmonteurs in-house getraind worden in het opsporen en verhelpen van elektrotechnische storingen, zonder dat hiervoor een externe cursus bij het Railcenter nodig is.

De software in deze repository vormt deelsysteem 3 (centrale control unit), deelsysteem 4 (gebruikersinterface instructeur) en deelsysteem 5 (gebruikersinterface monteur) uit het architectuurontwerp.

De functionaliteiten van de software zijn:

- Het tekenen en bewerken van deelschakelingen op een rasteroppervlak.
- Het opslaan en laden van deelschakelingen als JSON-bestand.
- Het simuleren van de elektrische werking van een deelschakeling (stroomvoering, relaiswerking en schakelaarstanden).
- Het instellen van storingen per component, waarbij de storing tijdens het examen verborgen blijft voor de monteur.
- Het instellen van de examentijd die de monteur krijgt om de storing te zoeken.
- Het koppelen van componenten aan de GPIO-pinnen van de Raspberry Pi, zodat de fysieke schakelaars en lampen in de koffer meelopen met de simulatie.
- Het weergeven van de schakeling op twee gescheiden schermen: een bedieningsscherm voor de instructeur en een examenscherm voor de monteur.

# Intro (English)

This GitHub repository serves as a manual and technical documentation for the software of the fault simulation case. The information provided in this repository is intended for the technical staff of the Rotterdam Electric Tram (RET) company.

The fault simulation case is a training tool developed to reproduce sub-circuits from the rectifier stations of the RET. This allows maintenance and fault-finding technicians to be trained in-house in locating and resolving electrical faults, without requiring an external course at the Railcenter.

The functionalities of the software are:

- Drawing and editing sub-circuits on a grid surface.
- Saving and loading sub-circuits as a JSON file.
- Simulating the electrical behaviour of a sub-circuit (current flow, relay operation and switch positions).
- Configuring faults per component, where the fault remains hidden from the technician during the examination.
- Setting the examination time the technician is given to find the fault.
- Linking components to the GPIO pins of the Raspberry Pi, so that the physical switches and lamps in the case follow the simulation.
- Displaying the circuit on two separate screens: a control screen for the instructor and an examination screen for the technician.

The English translated documentation of this page can be found below the dutch documentation.

# De elektronica

De elektronica van de storingskoffer bestaat uit een Raspberry Pi 5, een Raspberry Pi Touch Display 2, een externe HDMI-monitor en een aantal door de RET ontwikkelde printplaten.

De twee schermen hebben elk een eigen taak:

| Scherm | Aansluiting | Gebruiker | Inhoud |
|-------------------------|-------------|-------------|--------------------------------------------------|
| Externe monitor | HDMI0 | Instructeur | Volledig dashboard: ontwerpen, storing, examen |
| Raspberry Pi Touch 2 | DSI | Monteur | Statische schakeling en examentijd |

De printplaten die op de Raspberry Pi worden aangesloten zijn:

- De voedingsbeveiliging (deelsysteem 2), die de 24 VDC van de hoofdvoeding omzet naar een 5 VDC- en een 48 VDC-busrail, en die de kortsluitbeveiliging en de noodstop bevat.
- De digitale outputmodule (deelsysteem 6), die de digitale signalen van de Raspberry Pi omzet naar schakelspanningen van 48 V. Omdat de nagebootste deelschakelingen tussen de 50 en 100 contacten bevatten en de Raspberry Pi zelf maar 28 bruikbare GPIO-pinnen heeft, wordt gebruikgemaakt van MCP23S17 I/O-expanders op de SPI-bus. Acht expanders leveren samen 128 digitale uitgangen.

De volledige onderbouwing van de printplaten, inclusief de schematische tekeningen, de componentkeuzes en de berekeningen, is te vinden in het projectdocument.

> **Let op:** de software in deze repository stuurt op dit moment de GPIO-pinnen van de Raspberry Pi rechtstreeks aan via de bibliotheek `RPi.GPIO`. De aansturing via de MCP23S17 I/O-expanders is nog niet in de software verwerkt. Het aantal beschikbare uitgangen is daarmee voorlopig beperkt tot de 26 pinnen die in `constants.py` onder `VALID_GPIO_PINS` staan.

# De software

De software die op de Raspberry Pi van de storingskoffer draait is als volgt opgebouwd. Voor het besturingssysteem wordt een Linux kernel gebruikt (Raspberry Pi OS). Hierin wordt een virtuele omgeving opgebouwd in Python. In deze virtuele omgeving VENV (Virtual Environment) wordt de Python app opgestart die de grafische interface beheert en de GPIO-pinnen aanstuurt.

De grafische interface is gebouwd met PyQt5. De schakelingen worden niet als afbeelding ingeladen maar in de app zelf getekend, zodat elke schakeling in de editor aangepast kan worden zonder de broncode te wijzigen.

## De opbouw van de repository

| Bestand | Functie |
|------------------|--------------------------------------------------------------------------|
| `main.py` | Opstartpunt. Maakt beide vensters aan en verdeelt ze over de schermen. |
| `canvas.py` | De tekenlaag (`CircuitCanvas`), de dialoogvensters en het instructeursvenster (`MainWindow`). |
| `monteur.py` | Het examenscherm voor de monteur (`MonteurCanvas` en `MonteurWindow`). |
| `display.py` | Bepaalt op welk scherm welk venster terechtkomt. |
| `schermtest.py` | Diagnose: toont welke schermen Qt ziet en hoe ze verdeeld worden. |
| `simulator.py` | De elektrische simulatie van de schakeling. |
| `gpio_manager.py`| De koppeling tussen de simulatie en de GPIO-pinnen. |
| `models.py` | De dataklassen `Component` en `Wire` en de nummering van de contacten. |
| `draw.py` | De tekenroutines van de elektrotechnische symbolen. |
| `constants.py` | Alle constanten, kleuren en gereedschapsdefinities. |
| `circuits/` | De opgeslagen deelschakelingen als JSON-bestand. |
| `pcb_tests/` | Losse testscripts per printplaat, onafhankelijk van de app. |

## Het handmatig starten van de app

Voor het handmatig starten van de Python app met VENV (Virtual Environment) zijn de volgende commando's nodig. Deze commando's dienen ingevuld te worden in de terminal van Linux:

```console
cd ~/Github/ret-storingskoffer-2026
source venv-rpi/bin/activate  << start de VENV
python3 main.py               << start de App
```

Op Windows wordt de app op dezelfde manier gestart, maar met de commando's van PowerShell:

```console
.\env\Scripts\Activate.ps1
python main.py
```

## Het aanmaken van de virtuele omgeving

De virtuele omgeving is platformafhankelijk en moet daarom op elk apparaat opnieuw aangemaakt worden. Op de Raspberry Pi gebeurt dit met de volgende commando's:

```console
sudo apt update
sudo apt install python3-venv python3-pyqt5 python3-rpi.gpio
python3 -m venv venv-rpi --system-site-packages
source venv-rpi/bin/activate
```

PyQt5 wordt hier bewust via `apt` geïnstalleerd en niet via `pip`. Voor de ARM-processor van de Raspberry Pi zijn geen kant-en-klare PyQt5 pakketten beschikbaar op pip, waardoor pip het volledige Qt framework vanuit de broncode gaat compileren. Dit duurt meerdere uren en mislukt vaak alsnog. De optie `--system-site-packages` zorgt ervoor dat de virtuele omgeving bij de via apt geïnstalleerde pakketten kan.

Op Windows is dit niet nodig en volstaat het volgende:

```console
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
```

# De gebruikersinterface

## Het scherm van de instructeur

Het instructeursscherm heeft drie modi die linksboven omgeschakeld kunnen worden:

- **Bekijken** – hier kiest de instructeur een opgeslagen deelschakeling uit de lijst. De schakeling wordt weergegeven zonder dat er iets gewijzigd kan worden.
- **Bewerken** – hier tekent de instructeur een nieuwe deelschakeling of past hij een bestaande aan. In deze modus kunnen ook de storingen en de GPIO-koppelingen ingesteld worden.
- **Examen** – hier stelt de instructeur de examentijd in en start hij het examen.

In de Bewerken-modus zijn de volgende componenten beschikbaar:

| Gereedschap | Symbool | Aantal contacten |
|-----------------------------|---------|------------------|
| Draad | – | – |
| Net Label | – | 0 |
| Schakelaar (1P) | S | 2 |
| Schakelaar 2P NO | S | 4 |
| Schakelaar 2P NC | S | 4 |
| 2-weg wisselschakelaar | S | 3 |
| Relaisspoel | K | 2 |
| Relaiscontact | K | 2 |
| 2-weg relaiscontact | K | 3 |
| Motor | M | 2 |
| Lamp | H | 2 |
| Voeding (+V) | +V | 0 |
| Massa (GND) | GND | 0 |

Componenten met hetzelfde label worden automatisch aan elkaar gekoppeld. Een relaiscontact met label `K1` volgt dus de relaisspoel met label `K1`. Net Labels met dezelfde naam worden in de simulatie als één knooppunt behandeld, zodat een schakeling over meerdere bladen verdeeld kan worden zonder dat er een draad tussen getekend hoeft te worden.

## Het scherm van de monteur

Het monteursscherm toont uitsluitend de schakeling die de instructeur heeft klaargezet, plus de resterende examentijd. Er is bewust geen menu, geen weergave van de stroomvoering en geen markering van de storing: de monteur ziet een statische tekening, zoals hij die in de praktijk ook op papier zou krijgen.

Het scherm kent drie toestanden:

- **Wachten op de instructeur** – er is nog geen examen gestart.
- **Examen** – de schakeling en de aftellende examentijd zijn zichtbaar.
- **Einde examen** – de tijd is verstreken of de instructeur heeft het examen gestopt.

Op het moment dat de instructeur op "Start Examen" drukt, wordt een kopie van de schakeling naar het monteursscherm gestuurd. In die kopie wordt de storingsmarkering gewist, zodat de storing niet in het geheugen van het monteursvenster terechtkomt. Wanneer de examentijd verstreken is, verschijnt op het instructeursscherm een overzicht van de ingestelde storingen en op het monteursscherm alleen de melding "Einde examen".

# De simulatie

De simulator werkt met een vereenvoudigd aan/uit-model. Vanuit elk voedingscomponent (+V) en elk massacomponent (GND) wordt met een breadth-first search bepaald welke knooppunten onder spanning staan en welke aan massa liggen. Een component is actief wanneer de ene aansluiting onder spanning staat en de andere aan massa ligt.

Omdat een relaisspoel een relaiscontact kan bekrachtigen dat op zijn beurt weer een andere spoel voedt, wordt deze berekening herhaald tot de toestand stabiel is, met een maximum van twintig stappen.

## De beschikbare storingen

Per component kan de instructeur een storing instellen. Het gedrag per componenttype is als volgt:

| Component | Gedrag bij storing |
|--------------------------|-----------------------------------------------|
| Schakelaar (1P en 2P) | Sluit nooit, blijft altijd open |
| 2-weg wisselschakelaar | Blijft vast staan op positie B |
| Relaisspoel | De koppeling tussen spoel en contact is verbroken |
| Relaiscontact | Het contact sluit nooit |
| 2-weg relaiscontact | De koppeling is verbroken, blijft vast op B |
| Motor | Draait niet, ook al staat er spanning op |
| Lamp | Gaat niet branden, ook al staat er spanning op |

# De GPIO-koppeling

Elk component kan aan een GPIO-pin van de Raspberry Pi gekoppeld worden. Dit gebeurt in de Bewerken-modus via de knop "GPIO". Er zijn twee richtingen:

- **INPUT** (`IN`) – de fysieke schakelaar in de koffer stuurt de simulatie aan. Een hoog signaal op de pin sluit de schakelaar in de simulatie.
- **OUTPUT** (`OUT`) – de simulatie stuurt de fysieke koffer aan. Wanneer een lamp, motor of relaisspoel in de simulatie actief wordt, gaat de bijbehorende pin hoog.

De pinnen worden aangesproken via de BCM-nummering. De bruikbare pinnen zijn GPIO 2 tot en met GPIO 27. Bij het opstarten en bij het afsluiten van de app worden alle pinnen als OUTPUT LOW gezet, zodat er geen enkele pin blijft zweven.

Tijdens de simulatie worden de ingangen elke 50 ms uitgelezen. Wanneer de app op een computer zonder Raspberry Pi hardware draait, wordt automatisch een `MockGPIO` geladen. De volledige app blijft dan werken en de ingangen kunnen met de muis omgeschakeld worden via het GPIO-monitorpaneel onderin het scherm. Hierdoor kan de software volledig op een laptop ontwikkeld en getest worden.

# De schermverdeling

Bij het opstarten bepaalt `display.py` zelf hoeveel schermen er aangesloten zijn:

- **Twee of meer schermen** – het monteursvenster wordt op het DSI-scherm gezet en het instructeursvenster op het HDMI-scherm. Beide vensters gaan schermvullend.
- **Eén scherm** – beide vensters worden naast elkaar op hetzelfde scherm gezet. Het monteursvenster krijgt hierbij exact 1280 x 720 pixels, de afmeting van de Raspberry Pi Touch Display 2, zodat tijdens het ontwikkelen op een laptop meteen zichtbaar is of de schakeling op het uiteindelijke scherm past.

Onder Wayland worden de schermen niet altijd met hun echte naam doorgegeven. In plaats van `DSI-1` en `HDMI-A-1` kunnen zij ook als `XWAYLAND0` en `XWAYLAND1` verschijnen, waarbij de volgorde per keer kan wisselen. Wanneer de automatische herkenning de vensters verkeerd verdeelt, kan de verdeling met de volgende omgevingsvariabelen afgedwongen worden:

```console
STORINGSKOFFER_LAYOUT=dev        << beide vensters op één scherm
STORINGSKOFFER_LAYOUT=pi         << verdeel over twee schermen
STORINGSKOFFER_MONTEUR=DSI-1     << schermnaam of index voor de monteur
STORINGSKOFFER_INSTRUCTEUR=0     << schermnaam of index voor de instructeur
```

Met de toets `F11` kan in beide vensters de schermvullende weergave in- en uitgeschakeld worden. Met `Escape` verlaat het monteursvenster de schermvullende weergave. Dit is nodig omdat de vensters op de Raspberry Pi zonder titelbalk draaien.

# Het opslaan van een deelschakeling

Een deelschakeling wordt opgeslagen als JSON-bestand in de map `circuits`. Het bestand heeft de volgende opbouw:

```json
{
  "components": [
    {
      "type": "lamp",
      "col": 5,
      "row": 12,
      "label": "H1",
      "rotation": 0,
      "contact_start": 7,
      "manual_contact_start": false,
      "gpio_pin": 17,
      "gpio_dir": "OUT",
      "defect": false
    }
  ],
  "wires": [
    { "c1": 5, "r1": 10, "c2": 5, "r2": 12 }
  ],
  "exam_time_minutes": 10,
  "naam": "plusverdeler"
}
```

De velden `col` en `row` zijn rastercoördinaten, geen pixels. De contactnummering (`contact_start`) wordt bij het laden automatisch opnieuw berekend, tenzij het nummer handmatig is vastgezet met `manual_contact_start`.

Om een nieuwe deelschakeling aan de koffer toe te voegen hoeft er dus geen code aangepast te worden. De schakeling wordt in de Bewerken-modus getekend en met de knop "Opslaan" in de map `circuits` weggeschreven, waarna hij direct in de lijst van de Bekijken-modus verschijnt.

# Software buggs

Er staan nog een aantal aandachtspunten (softwarefouten die niet destructief zijn voor de werking van de gehele module) in de Python code van de storingskoffer.

De aandachtspunten zijn:

| Bug | Impact | Status |
|---------------------------------------------------------|-------------------------------|--------|
| Een defecte motor of lamp onderbrak het circuit niet | Simulatie week af van de praktijk | Closed |
| Relaislabels wisselden om bij toevoegen of verwijderen | Schakeling gedroeg zich anders dan getekend | Closed |
| De Bekijken-modus liet het canvas bewerkbaar | Schakeling kon ongemerkt wijzigen | Closed |
| Twee componenten konden dezelfde GPIO-pin krijgen | Pin kreeg twee richtingen tegelijk | Closed |
| Klikken en verwijderen kozen een ander component | Verkeerd symbool verdween | Closed |
| Beide vensters startten op hetzelfde scherm | Tweeschermopstelling werkte niet | Closed |
| De MCP23S17 I/O-expanders worden nog niet aangestuurd | Aantal uitgangen beperkt tot 26 | Open |
| De virtuele omgeving en `__pycache__` staan in de repository | Repository onnodig groot | Open |
| Het instructeursvenster heeft een minimum van 1400 x 800 | Past niet op kleine schermen | Open |
| Er zijn vier van de tien deelschakelingen opgenomen | Voldoet nog niet aan F-REQ-1.0 | Open |

Twee van de gesloten punten verdienen een toelichting, omdat zij de uitkomst van een examen raakten.

Een defecte lamp of motor bleef in het simulatiemodel stroom geleiden. De component werd wel als inactief getekend en de GPIO-uitgang bleef laag, maar een monteur die de schakeling doormat vond achter een doorgebrande lamp nog steeds spanning. Een defect onderbreekt het circuit nu wel.

Relaislabels werden bij elke toevoeging of verwijdering opnieuw genummerd op volgorde in de lijst. Omdat de koppeling tussen spoel en contact uitsluitend op label werkt, konden twee relaiscontacten daardoor stilzwijgend van spoel wisselen. Labels die de instructeur zelf instelt worden nu vastgelegd met de vlag `manual_label` en niet meer automatisch hernummerd.

# Linux configuratie

Om bij het opstarten van de Raspberry Pi ook de VENV (Virtuele omgeving) en de Python app op te starten kan er een `storingskoffer.service` routine aangemaakt worden. Het `.service` bestand hoort in `/etc/systemd/system/storingskoffer.service` te staan.

```console
[Unit]
Description=Storingskoffer Dashboard
After=graphical.target

[Service]
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=GDK_BACKEND=x11
Environment=QT_QPA_PLATFORM=xcb
ExecStart=/bin/bash /home/pi/Github/ret-storingskoffer-2026/start_app.sh
Restart=always
RestartSec=4
KillMode=process
TimeoutSec=infinity

[Install]
WantedBy=graphical.target
```
> storingskoffer.service

In deze routine wordt er gewacht tot dat de grafische omgeving is opgestart. Zodra dit gebeurd is wordt het bestand `start_app.sh` opgestart. In dit bestand staan de Linux commando's die nodig zijn om de VENV (virtuele omgeving) en de Python app op te starten.

```console
#!/bin/bash
cd /home/pi/Github/ret-storingskoffer-2026
source venv-rpi/bin/activate
python3 main.py
```
> start_app.sh

De regel `Environment=QT_QPA_PLATFORM=xcb` is belangrijk. Zonder deze regel valt de app terug op het `offscreen` platform wanneer de variabele `DISPLAY` niet gezet is. De app start dan zonder foutmelding op, maar er verschijnt nooit iets op een van beide schermen.

De service wordt met de volgende commando's ingeschakeld:

```console
sudo systemctl daemon-reload
sudo systemctl enable storingskoffer.service
sudo systemctl start storingskoffer.service
```

Met het commando `journalctl -u storingskoffer.service -f` kunnen de meldingen van de app live meegelezen worden.

# Inloggegevens

Om in te loggen op de Raspberry Pi zelf om de achterliggende code aan te passen kan er verbinding worden gemaakt met de Raspberry Pi via SSH, VNC of WinSCP. Het wachtwoord hiervoor is te vinden bij de Energievoorziening van de RET (EV).

Voor het ophalen van de code op de Raspberry Pi wordt een SSH-sleutel gebruikt. Deze wordt op de Raspberry Pi aangemaakt met `ssh-keygen -t ed25519` en de publieke sleutel (`~/.ssh/id_ed25519.pub`) wordt toegevoegd aan het Github account. Daarna kan de repository met `git pull` bijgewerkt worden zonder dat er een wachtwoord ingevuld hoeft te worden.
