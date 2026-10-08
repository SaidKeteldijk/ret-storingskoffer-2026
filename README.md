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
| `koffer_io.py` | De aansturing van de knoppen- en lampenprint via SPI. |
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

Componenten met hetzelfde label worden automatisch aan elkaar gekoppeld. Een relaiscontact met label `K1` volgt dus de relaisspoel met label `K1`. De automatische nummering loopt per labelgroep door: alle soorten schakelaars tellen samen op als `S1`, `S2`, `S3`, ongeacht of het een eenpolige, tweepolige of wisselschakelaar is. Relaisspoelen en relaiscontacten houden juist een eigen telling, zodat spoel `K1` en contact `K1` standaard bij elkaar horen. Een label dat je zelf instelt wordt niet meer hernummerd en houdt zijn nummer bezet. Net Labels met dezelfde naam worden in de simulatie als één knooppunt behandeld, zodat een schakeling over meerdere bladen verdeeld kan worden zonder dat er een draad tussen getekend hoeft te worden.

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

# De koppeling met de koffer

Elk component kan aan een kanaal van de knoppen- en lampenprint gekoppeld worden. Dit gebeurt in de Bewerken-modus via de knop "GPIO". Het componenttype bepaalt zelf om wat voor kanaal het gaat:

| Component | Kanaal | Werking |
|------------------------------------------|----------|-----------------------------------------|
| Schakelaar, wisselschakelaar, relaiscontact | S1 .. S8 | De fysieke knop stuurt de simulatie aan |
| Lamp, motor, relaisspoel | Q1 .. Q8 | De simulatie stuurt de fysieke lamp aan |

Elk kanaal hoort bij één component; de dialoog weigert te sluiten zolang twee componenten hetzelfde kanaal delen.

De koppeling hoort bij de tekening en wordt daarom in het schakelingbestand bewaard. Zodra je het venster met OK sluit, wordt die koppeling meteen weggeschreven naar het bestand waar de schakeling uit komt. Je hoeft dus niet apart op te slaan, en na het opnieuw laden staat de koppeling er nog. De statusbalk meldt hoeveel kanalen er gekoppeld zijn en in welk bestand dat is vastgelegd.

Heeft de schakeling nog geen bestand, bijvoorbeeld na "Nieuw", dan kan er niets vastgelegd worden. De statusbalk zegt dat dan, zodat je weet dat je eerst "Opslaan als" moet gebruiken.

De print zit op de SPI-bus (CE0) op hardware-adres `000`. De lampen Q1 tot en met Q8 hangen aan GPB0 tot en met GPB7 en zijn niet geïnverteerd: een hoge bit laat de lamp branden. De knoppen S1 tot en met S8 hangen aan GPA0 tot en met GPA7 en zijn actief laag, met een externe pull-up op de print.

De aansturing zit in `koffer_io.py` en doet bewust **geen** hardware-reset: de RESET-lijn is gedeeld met de digitale 48V-kaarten en zou hun uitgangen laten zweven. Bij het starten van de simulatie wordt de print ingesteld met de latch eerst laag en pas daarna de richting op uitgang, zodat er geen lamp kort aanflitst. Bij het stoppen gaan alle lampen uit.

Tijdens de simulatie worden de knoppen elke 50 ms uitgelezen. Draait de app op een computer zonder `spidev`, dan wordt automatisch een mockversie van de print geladen. De volledige app blijft dan werken en de knoppen kunnen met de muis omgeschakeld worden via het monitorpaneel onderin het scherm. Hierdoor kan de software volledig op een laptop ontwikkeld en getest worden.

> **Let op:** de oude koppeling aan losse BCM-pinnen via `gpio_manager.py` bestaat nog voor bestanden van vóór deze wijziging, maar de dialoog biedt die niet meer aan. Zodra je een schakeling via de dialoog opnieuw koppelt, vervalt de pinkoppeling.

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

Om een nieuwe deelschakeling aan de koffer toe te voegen hoeft er dus geen code aangepast te worden. De schakeling wordt in de Bewerken-modus getekend en in de map `circuits` weggeschreven, waarna hij direct in de lijst van de Bekijken-modus verschijnt.

Er zijn twee knoppen om op te slaan:

- **Opslaan** schrijft naar het bestand waar de schakeling uit komt, zonder iets te vragen. De statusbalk meldt in welk bestand het terecht is gekomen.
- **Opslaan als** vraagt om een naam en een bestand. Dit is de enige route voor een schakeling die nog nergens staat, en de manier om een bestaande schakeling onder een nieuwe naam af te splitsen.

Na "Opslaan als" en na het laden van een bestand is dat bestand het huidige, zodat "Opslaan" daarna meteen de juiste plek raakt. Na "Nieuw" is er geen huidig bestand en gedraagt "Opslaan" zich als "Opslaan als".

> De koppeling aan de kanalen van de koffer hoort bij de tekening en wordt meteen in het bestand vastgelegd zodra je het koppelvenster met OK sluit. Opslaan is daarvoor niet nodig.

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

# Automatisch starten op de Raspberry Pi

Om de storingskoffer na het inschakelen vanzelf te laten opstarten, staan er twee
bestanden in de repository: `start_app.sh` en `storingskoffer.service`.

`start_app.sh` wacht tot de grafische sessie beschikbaar is, activeert de virtuele
omgeving en start de app. Dat wachten is nodig: zonder scherm valt `main.py` terug
op het offscreen-platform en verschijnt er nooit iets, zonder foutmelding.

```console
#!/bin/bash
cd "$(dirname "$0")" || exit 1

for _ in $(seq 1 30); do
    [ -e /tmp/.X11-unix/X0 ] && break
    sleep 1
done

source venv-rpi/bin/activate
exec python3 -u main.py
```
> start_app.sh

De service is een gebruikersservice, geen systeemservice. Dat is bewust: de app
heeft de grafische sessie van de gebruiker nodig, en een gebruikersservice start
mee met die sessie. De `%h` laat systemd zelf de thuismap invullen, zodat er geen
pad hardgecodeerd staat.

```console
[Unit]
Description=Storingskoffer Dashboard
After=default.target

[Service]
Type=simple
WorkingDirectory=%h/Github/ret-storingskoffer-2026
ExecStart=/bin/bash %h/Github/ret-storingskoffer-2026/start_app.sh
Environment=DISPLAY=:0
Environment=QT_QPA_PLATFORM=xcb
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```
> storingskoffer.service

## Installeren

```console
mkdir -p ~/.config/systemd/user
cp storingskoffer.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now storingskoffer.service
```

De regel `Environment=QT_QPA_PLATFORM=xcb` is belangrijk. De Raspberry Pi draait
Wayland, maar de app positioneert zijn eigen vensters en heeft daarvoor XWayland
nodig. Zonder deze regel kan de verdeling over de twee schermen mislukken.

## Beheren

```console
systemctl --user status storingskoffer.service     # draait hij?
journalctl --user -u storingskoffer.service -f     # meldingen live meelezen
systemctl --user restart storingskoffer.service    # opnieuw starten
systemctl --user stop storingskoffer.service       # tijdelijk stoppen
systemctl --user disable --now storingskoffer.service
```

In het journaal zie je de opstartmeldingen terug, zoals `[KOFFER] print 000 klaar`
en `[SCHERM] Instructeur op HDMI-A-1, monteur op DSI-1`. Dat is de eerste plek om
te kijken als er iets niet goed gaat.

> **Let op tijdens het ontwikkelen:** door `Restart=always` start de app vanzelf
> opnieuw zodra je hem afsluit. Zet de service stil met `systemctl --user stop`
> voordat je handmatig gaat testen.

# Inloggegevens

Om in te loggen op de Raspberry Pi zelf om de achterliggende code aan te passen kan er verbinding worden gemaakt met de Raspberry Pi via SSH, VNC of WinSCP. Het wachtwoord hiervoor is te vinden bij de Energievoorziening van de RET (EV).

Voor het ophalen van de code op de Raspberry Pi wordt een SSH-sleutel gebruikt. Deze wordt op de Raspberry Pi aangemaakt met `ssh-keygen -t ed25519` en de publieke sleutel (`~/.ssh/id_ed25519.pub`) wordt toegevoegd aan het Github account. Daarna kan de repository met `git pull` bijgewerkt worden zonder dat er een wachtwoord ingevuld hoeft te worden.
