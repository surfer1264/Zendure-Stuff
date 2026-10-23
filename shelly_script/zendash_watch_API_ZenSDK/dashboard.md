:de: **Deutsch** · [:gb: English](dashboard_EN.md) · [:fr: Français](dashboard_FR.md)

# Dashboard einrichten und bedienen

[← zurück zu zenDash-API + Watchdog](readme.md)

Das Dashboard zeigt dir live Netzbezug, Ladestand und Leistung deiner Speicher. Du kannst darüber auch Einstellungen des Controllers ändern und einen Speicher manuell aus dem Netz laden.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/c4d6f53a-d9d9-4d4f-b597-8a069561e6ec" />

**Inhalt**

- [Wie das zusammenhängt](#wie-das-zusammenhängt)
- [Bedienung](#bedienung)
- [Welche Variante passt zu dir?](#welche-variante-passt-zu-dir)
- [Voraussetzungen](#voraussetzungen)
- [In 4 Schritten zum Dashboard](#in-4-schritten-zum-dashboard)
- [Als Programm unter Windows oder macOS](#als-programm-unter-windows-oder-macos)
- [Dauerbetrieb auf einer Synology](#dauerbetrieb-auf-einer-synology)
- [Als App in Home Assistant](#als-app-in-home-assistant)
- [Startoptionen](#startoptionen)
- [Gut zu wissen](#gut-zu-wissen)
- [Wenn es nicht klappt](#wenn-es-nicht-klappt)

---

## Wie das zusammenhängt

Der Browser darf die Daten nicht direkt beim Shelly abfragen – die Shelly-Firmware lehnt solche Zugriffe aus einer fremden Webseite ab. Deshalb läuft auf einem Rechner im Heimnetz ein kleiner **Proxy**: Er liefert die Dashboard-Seite aus und fragt den Shelly stellvertretend ab.

```
Browser  ──►  Proxy (PC/NAS/HA/Raspi)  ──►  Dashboard-Shelly (zenDash-API)  ──►  Controller-Shelly (KVS)
```

---

## Bedienung

Beschrieben ist das Standard-Layout unter `http://<Proxy-Adresse>:8000/`. Das bisherige Layout unter `/b` hat dieselben Funktionen, nur anders angeordnet.

### Aufbau der Seite

| Bereich | Inhalt |
|---|---|
| **Kopfzeile** | Verbindungsstatus (z. B. „Live · Poll alle 4s“), Uhrzeit und Datum, das **Schloss** und das Menü **⚙ Ansicht** |
| **Übersicht – Jetzt** | Messwerte: Netzbezug/Einspeisung und Solarflow-Leistung (Summe aller Speicher) mit Verlaufskurve |
| **Übersicht – Regelung** | Einstellungen für alle Speicher: Sollwert und Fix-Entladung |
| **Geräte** | je Speicher eine Karte mit Messwerten, Status, „Steuerung“ und „Manuelles Laden“ |
| **Fußzeile** | Versionen, Zeitpunkt der letzten Aktualisierung, Link **Hilfe** (diese Seite), Rohdaten und Cloud-Upload |

Ein Tipp auf die Zeile **„▾ Übersicht“** klappt die Übersicht ein. Eingeklappt steht dort eine Kurzfassung, z. B. `Soll 0 W · Netz 12 W · Speicher 340 W` – praktisch auf kleinen Bildschirmen, wenn nur die Gerätekarten interessieren. Der Zustand wird gemerkt.

### Sperren und Entsperren

Die Seite startet **gesperrt** – sie zeigt dann nur an, Hinweis „Nur Anzeige“ unter der Regelung. Ein Tipp auf das **Schloss** in der Kopfzeile gibt die Bedienung frei, das Symbol wechselt auf ein offenes Schloss. Nach 60 Sekunden ohne Eingabe sperrt sich die Seite von selbst wieder, ebenso nach jedem Neuladen. Gedacht ist das für Dashboards, die dauerhaft auf einem Tablet oder Zweitmonitor offen liegen.

Auf Touch-Geräten hat der Regler **Reserve (min. SoC)** zusätzlich ein eigenes kleines Schloss neben dem Wert. Es gibt immer nur diesen einen Regler frei und sperrt ihn nach 5 Sekunden ohne Berührung, nach dem Speichern oder beim Scrollen wieder. Verstellt wird der Wert nur durch Ziehen am Punkt – Tippen oder Wischen auf der Leiste wird zurückgenommen.

### Menü „Ansicht“

| Eintrag | Wirkung |
|---|---|
| **Ansichtsgröße** (A1–A4) | Schrift und Bedienelemente in vier Stufen: Normal, Groß (Standard), Sehr groß, Maximal |
| **Tag-/Nachtsicht** | helle oder dunkle Darstellung. Ohne Umschalten folgt die Seite der Einstellung des Geräts. |
| **Sprache** | DE → EN → FR. Standard ist die Sprache des Browsers. |
| **Vollbild** | Browserleisten ausblenden; erscheint nur, wenn der Browser das kann |
| **Technische Details** | blendet KVS-Schlüssel (z. B. `zdmc_setpoint`), IP-Adressen und Rohcodes (`acMode`, `socLimit`, `gridReverse`) ein. Ohne diesen Schalter zeigt das Dashboard nur Klartext. |
| **Ansicht zurücksetzen** ↺ | Größe, Tag/Nacht, technische Details und Übersicht auf Standard. Die Sprache bleibt. |

Alle Einträge werden **pro Browser** gemerkt – ein Wandtablet startet nach einem Neuladen also wieder in seiner Ansicht. Die Sperre wird bewusst nicht gemerkt.

### Was du einstellen kannst

Alle Einstellungen gehen an den Controller und wirken bei dessen nächstem Regeltakt. Nach dem Speichern erscheint kurz eine Bestätigung, z. B. „Gespeichert: Akku 1 · Reserve (min. SoC) 20 %“.

**In der Übersicht unter „Regelung“** (für alle Speicher gemeinsam):

| Bedienelement | Wirkung | Bereich |
|---|---|---|
| **Sollwert** | Zielwert für den Netzbezug. Negativ = etwas einspeisen, positiv = etwas beziehen. Darunter steht die Toleranz (Hysterese): so weit darf der Netzbezug abweichen, bevor der Controller nachregelt. | −40 bis +40 W, in 5-W-Schritten |
| **Fix-Entladung** | Feste Entladeleistung statt Regelung. Wert ins Feld eintippen und mit ↵ bzw. „Fertig“ übernehmen. Solange sie aktiv ist, weist die Sollwert-Kachel darauf hin, dass der Sollwert gerade nicht ausgeregelt wird. | `0` = aus, sonst ab `dischargeStartupPower` (z. B. 35 W) |

**Auf jeder Gerätekarte unter „Steuerung“:**

| Bedienelement | Wirkung | Bereich |
|---|---|---|
| **Entladen erlaubt** | Darf dieser Speicher ins Haus abgeben? Hat der Watchdog das Entladen wegen Unterspannung gesperrt, steht der Schalter auf aus und muss von Hand wieder eingeschaltet werden ([Entladesperre](readme.md#entladesperre-bei-unterspannung)). | an/aus |
| **Laden vom Netz erlaubt** | Darf dieser Speicher Überschuss aus dem Netz aufnehmen? | an/aus |
| **Reserve (min. SoC)** | Unter diesen Ladestand wird nicht entladen. Wird zusätzlich im Speicher selbst eingestellt. Die Obergrenze steht unter dem Wert („max … %“). | 10 % bis 1 % unter der kleineren Grenze aus Ladeziel (`maxSoc`) und am Gerät eingestellter Ladegrenze (`socSet`) |

**Auf jeder Gerätekarte unter „Manuelles Laden“:**

| Bedienelement | Wirkung | Bereich |
|---|---|---|
| **Ladeleistung aus dem Netz** | wählt nur die Leistung, noch ohne Wirkung | 0 bis `maxInputPower`, in 50-W-Schritten |
| **Manuelles Laden starten / beenden** | startet bzw. beendet das Laden mit der gewählten Leistung | – |

Beim Start fragt das Dashboard einmal nach und schaltet dann für diesen Speicher „Entladen erlaubt“ und „Laden vom Netz erlaubt“ aus – der Speicher ist damit aus der Regelung genommen, der Hinweis neben dem Knopf zeigt „Aktiv mit … W“. Beim Beenden stellt es den vorherigen Zustand wieder her. Ist der Akku voll, beendet das Script das Laden selbst, auch bei geschlossenem Dashboard ([Auto-Stop](readme.md#manuelles-laden-und-auto-stop)). Bricht der Vorgang mittendrin ab (Shelly nicht erreichbar), erscheint ein Warnhinweis – dann Schalter und Ladeleistung auf der Karte prüfen.

Nach einer Eingabe ist das jeweilige Bedienelement 4 Sekunden gesperrt, damit nichts doppelt ausgelöst wird.

Nicht im Dashboard änderbar sind die **Hysterese** (wird nur unter dem Sollwert angezeigt) und das **Ladeziel** (`maxSoc`). Beides stellst du im Configurator bzw. im CONFIG-Block ein.

### Was die Anzeige zeigt

- **Netzbezug / Einspeisung:** aktueller Netzsaldo mit Richtung („Bezug“ bzw. „Einspeisung“) und Vergleich zum Sollwert, dazu eine Verlaufskurve der letzten 2 Minuten.
- **Solarflow-Leistung:** Summe aller Speicher (+ = geben ab, − = laden), darunter der durchschnittliche Ladestand („Ø Ladestand … %“), ebenfalls mit Verlaufskurve. Beide Kurven haben unterschiedliche Maßstäbe und beginnen nach einem Neuladen der Seite wieder von vorn.
- **Je Speicher eine Karte** mit:
    - Name und Statuspunkt (grün = erreichbar); mit „Technische Details“ zusätzlich `[devN]` und IP-Adresse
    - Ladestand als Batteriesymbol und Zahl, daneben die Leistung mit Richtung („gibt ab“, „lädt“, „Bereitschaft“)
    - darunter das Arbeitsfenster, z. B. `Bereich 15–100 %` (Reserve bis Ladeziel)
    - PV-Eingang, Offgrid-Leistung (nur bei Geräten mit Offgrid-Steckdose), Gerätetemperatur in °C und schwächste Zelle („Zelle min 3,28 V“) – aussagekräftig ist sie nur unter Last. Bei Speichern, die der Watchdog überwacht, steht dahinter die Sperrschwelle, z. B. „Sperre < 2,90 V“, und die Farbe richtet sich nach den Watchdog-Schwellen: gelb unter `minVoltReset`, rot unter `minVoltWarn`. Sonst gilt: gelb unter 3,0 V, rot unter 2,8 V.
    - „100 %: vor N Tagen“ – wann der Speicher zuletzt ganz voll war; Antippen zeigt das Datum ([mehr dazu](readme.md#letzte-vollladung))
    - Status in Klartext, z. B. „speist ein“, „voll, Laden gesperrt“, „leer, Entladen gesperrt“, „Export verboten“. Das erklärt die häufigsten „Warum tut der Speicher nichts?“-Fälle. Mit „Technische Details“ steht der Rohcode davor (`socLimit 1`, `gridReverse 2` …).
    - Hinweise, wenn am Gerät etwas anderes eingestellt ist als in der Konfiguration, z. B. „Ladegrenze 90 % · abweichend, Konfiguration 100 %“ (`socSet` ≠ `maxSoc`) oder „Reserve am Gerät 15 % · abweichend, KVS 20 %“. Meist wurde der Wert von außen geändert (App, Home Assistant).
    - darunter „Entladen: erlaubt · Netzladen: gesperrt“ als Kurzfassung der beiden Schalter
- **Fußzeile:** Versionen von Seite und Script (gelb, wenn sie nicht zusammenpassen), Zeitpunkt der letzten Aktualisierung, Link **Hilfe** auf diese Anleitung. `config_api` und `status_api` öffnen die Rohdaten als JSON in einem neuen Tab. **ThingSpeak** und **ThingsBoard** führen zu den Einrichtungsseiten für den Cloud-Upload ([ThingSpeak](thingspeak.md), [ThingsBoard](thingsboard.md)).

**Erklärungen per Antippen:** Viele Beschriftungen und Werte sind gepunktet unterstrichen – Sollwert, Fix-Entladung, die beiden Übersichtskacheln, Leistung, Arbeitsfenster, Zusatzzeile, Sperrschwelle; dazu die Status-Marken. Antippen (oder mit der Maus darauf zeigen) blendet eine kurze Erklärung ein.

Die Seite frischt die Messwerte alle 4 Sekunden auf. Einstellungen, die jemand anders geändert hat (z. B. über Home Assistant), erscheinen nach spätestens etwa einer halben Minute. Solange der Tab im Hintergrund liegt oder das Fenster minimiert ist, pausieren die Abfragen.

Technische Details zu Abfragetakt, Schnittstelle und Wertebereichen stehen in der [API-Beschreibung](API.md).

---

## Welche Variante passt zu dir?

Es gibt **einen** Proxy (`zendure_proxy.py`), der überall gleich funktioniert. Nur die Art, wie du ihn startest, unterscheidet sich:

| Variante | Geeignet für | Start | Browser öffnet sich von selbst |
|---|---|---|---|
| **Fertiges Programm** | Windows oder Mac mit Apple Silicon, ohne Python | Doppelklick | ja |
| **Python-Script** | PC, Laptop, Raspberry Pi | `python3 zendure_proxy.py` | ja (nur mit Bildschirm) |
| **Synology** | Dauerbetrieb auf dem NAS | Aufgabenplaner | nein |
| **Home Assistant** | wer ohnehin Home Assistant OS betreibt | als eigene App | nein |

Die Einrichtung ist in allen Fällen gleich: Proxy starten, im Browser aufrufen, auf der Einrichtungsseite IP und Script-Nummer des Dashboard-Shelly eintragen. Ein Texteditor ist dafür nicht nötig.

Für die Anzeige nebenbei reicht jeder Rechner. Soll das Dashboard **immer** erreichbar sein, nimm etwas, das dauerhaft läuft: NAS, Home Assistant, Raspberry Pi oder Mini-PC. Ein Laptop, der zugeklappt wird, eignet sich dafür schlecht.

---

## Voraussetzungen

- Das Script [zenDash-API + Watchdog](readme.md) läuft auf deinem Dashboard-Shelly, mit **`api.enabled: true`**.
- Damit du im Dashboard auch **einstellen** kannst (Sollwert, Reserve, manuelles Laden …), muss im Controller `kvsEnabled: true` und `kvsForceReseed: false` gesetzt sein. Ohne KVS zeigt das Dashboard nur an.
- Für das Python-Script und die Synology: **Python 3.7 oder neuer** ([python.org](https://www.python.org/downloads/)). Es muss nichts zusätzlich installiert werden.
- Außer beim fertigen Programm die zwei Dateien aus [diesem Ordner](.):
    - [`zendure_proxy.py`](zendure_proxy.py) – der Proxy
    - [`zendure-dashboard.html`](zendure-dashboard.html) – die Dashboard-Seite

  Die HTML-Datei darf **im selben Ordner** wie der Proxy liegen oder **eine Ebene höher**. Liegt an beiden Stellen eine, gewinnt die im selben Ordner.

> **Wichtig:** Dashboard-Seite und Script auf dem Shelly müssen **dieselbe Versionsnummer** haben. Aktualisierst du das Script, hol dir auch die passende `zendure-dashboard.html` (bzw. das neue Programm). Laufen die Versionen auseinander, wird der Hinweis in der Fußzeile des Dashboards gelb.

---

## In 4 Schritten zum Dashboard

**1. Script-Nummer nachsehen**

Der Proxy muss wissen, unter welcher IP-Adresse der Dashboard-Shelly erreichbar ist und welche Nummer das Script dort hat. In der Weboberfläche des Dashboard-Shelly unter **Scripts** steht die Nummer (z. B. `id: 1`). Über den Configurator hochgeladen, heißt das Script `zd`.

**2. Kurz testen, ob das Script antwortet**

Im Browser direkt aufrufen (IP und Nummer einsetzen):

```
http://<IP-des-Dashboard-Shelly>/script/<Script-Nummer>/status_api
```

Es sollte eine Zeile mit Daten erscheinen. Kommt ein Fehler, läuft das Script nicht oder die Nummer stimmt nicht.

**3. Proxy starten**

Beim fertigen Programm: Doppelklick (siehe [unten](#als-programm-unter-windows-oder-macos)). Beim Python-Script: im Ordner mit den Dateien ein Terminal (Windows: Eingabeaufforderung) öffnen und starten:

```bash
python3 zendure_proxy.py
```

Unter Windows heißt der Befehl oft `python` oder `py` statt `python3`. Das Fenster muss offen bleiben, solange das Dashboard genutzt wird; beenden mit `Strg+C`.

Beim Start zeigt der Proxy eine kurze Übersicht:

```
Zendure Dashboard Proxy
  Shelly:   noch nicht eingerichtet - Einrichtungsseite oeffnet automatisch
  HTML:     /home/pi/zendure/zendure-dashboard.html
  Konfig:   /home/pi/zendure/zendure_proxy_config.json
  Lokal:    http://localhost:8000/
  Im Netz:  http://192.168.178.21:8000/  (von jedem Rechner im selben Netzwerk)
(Strg+C zum Beenden)
```

- **HTML** zeigt, welche Dashboard-Datei gefunden wurde.
- **Konfig** zeigt, wo die Einstellungen gespeichert werden.
- **Im Netz** ist die Adresse für Handy, Tablet und andere Rechner.

Auf einem Rechner mit Bildschirm öffnet sich der Browser automatisch.

**4. Einrichten**

Beim ersten Aufruf von `http://localhost:8000/` erscheint statt des Dashboards die **Einrichtungsseite**. Dort trägst du ein:

- **Shelly-IP** – die IP des **Dashboard-Shelly** (nicht die des Controller-Shelly!)
- **Script-ID** – die Nummer aus Schritt 1

Ein Klick auf **„Speichern & testen“** prüft sofort, ob unter dieser Adresse wirklich das Script antwortet. Bei einem Tippfehler erscheint eine Fehlermeldung, und nichts wird gespeichert. Klappt der Test, leitet die Seite direkt zum Dashboard weiter.

Die Einstellungen landen in der Datei `zendure_proxy_config.json` neben dem Proxy. Beim nächsten Start sind sie wieder da – die Einrichtung ist also nur einmal nötig. Ändern kannst du sie jederzeit unter:

```
http://<Proxy-Adresse>:8000/setup
```

Danach ist das Dashboard auch von jedem anderen Gerät im Heimnetz erreichbar – mit der Adresse aus der Zeile **„Im Netz“**, z. B. `http://192.168.178.21:8000/`.

- immer `http://`, nicht `https://`
- die Seite startet **gesperrt** – das Schloss oben rechts gibt die Bedienung frei
- fragt Windows beim ersten Start nach der Firewall: **„Zugriff zulassen“** (privates Netzwerk)

---

## Als Programm unter Windows oder macOS

Für Rechner ohne Python gibt es den Proxy als fertiges Programm. Die Dashboard-Seite ist darin bereits eingebaut – du brauchst nur diese eine Datei:

- [Windows](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-windows.exe)
- [macOS](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-macos) – nur Macs mit Apple Silicon (M1 oder neuer)

1. Die Datei in einen **eigenen Ordner** legen, in dem du Schreibrecht hast, z. B. `C:\Users\<name>\zendure\`. Nicht unter `C:\Programme`, dort kann der Proxy seine Einstellungen nicht speichern.
2. Per **Doppelklick** starten. Ein Konsolenfenster öffnet sich (offen lassen), dazu der Browser mit der Einrichtungsseite.
3. Warnt Windows SmartScreen vor einer unbekannten App: **„Weitere Informationen“ → „Trotzdem ausführen“**. Unter macOS gelten dieselben Schritte wie beim Helfer – siehe [macOS-Anleitung](../Multiconfigurator/local_helper/mcos_helper.md) (dort den Dateinamen `zendure_proxy-macos` einsetzen).
4. Fragt die Windows-Firewall nach: **„Zugriff zulassen“** (privates Netzwerk), sonst ist das Dashboard vom Handy aus nicht erreichbar.
5. Einrichten wie in [Schritt 4](#in-4-schritten-zum-dashboard) beschrieben. Die Datei `zendure_proxy_config.json` entsteht neben dem Programm.

Beenden: Konsolenfenster schließen oder `Strg+C`.

Zu jeder Datei liegt auf der [Releases-Seite](https://github.com/surfer1264/Zendure-Stuff/releases/latest) eine `.sha256`-Datei zum Prüfen – wie beim Helfer beschrieben unter [Integrität des Downloads prüfen](../Multiconfigurator/readme.md#integrität-des-downloads-prüfen).

---

## Dauerbetrieb auf einer Synology

1. **Python prüfen.** DSM bringt meist schon eines mit:

    ```bash
    which python3 && python3 --version
    ```

    Ab 3.7 reicht es – der Proxy nutzt nur die Standardbibliothek. Häufig liegt der Interpreter unter `/bin/python3`. Kommt gar nichts, im Paketzentrum **Python 3** installieren; der Pfad ist dann `/var/packages/Python3*/target/bin/python3`.

2. **Dateien ablegen.** `zendure_proxy.py` in einen eigenen Ordner, z. B. `/volume1/homes/<benutzer>/zendure`, und `zendure-dashboard.html` daneben oder eine Ebene höher. Nicht in den `web`-Ordner – der gehört der Web Station.
3. **Aufgabe anlegen.** Systemsteuerung → Aufgabenplaner → Erstellen → **Ausgelöste Aufgabe** → Benutzerdefiniertes Skript. Ereignis **Hochfahren**, Benutzer **root**, als Befehl der volle Pfad:

    ```bash
    /bin/python3 /volume1/homes/<benutzer>/zendure/zendure_proxy.py -q
    ```

4. **Sofort starten**, ohne Neustart: Aufgabe markieren → **Ausführen**.
5. **Firewall.** Ist sie unter Systemsteuerung → Sicherheit → Firewall aktiv, eine Regel für TCP **8000** anlegen. Port 8000 kollidiert nicht mit DSM selbst (5000/5001).
6. **Einrichten.** Von einem PC oder Handy aus `http://<IP-der-Synology>:8000/` aufrufen und wie in [Schritt 4](#in-4-schritten-zum-dashboard) IP und Script-Nummer eintragen.

Die Aufgabe bleibt dauerhaft als „läuft“ stehen, weil der Proxy nicht endet. Das ist richtig so.

Weil die Aufgabe als `root` läuft, gehört die entstehende `zendure_proxy_config.json` ebenfalls `root`. Das ist für den Betrieb egal; nur wer die Datei später von Hand löschen oder ändern will, braucht dafür Administratorrechte.

Der Aufgabenplaner startet die Aufgabe beim Hochfahren, aber **nicht neu, wenn der Prozess abstürzt**. Wer das möchte, nimmt statt der Aufgabe einen Container im Container Manager (`python:3-slim`, Ordner als Volume, Port 8000, Neustartrichtlinie „immer“). Die Einstellungen landen dann im eingebundenen Ordner und überstehen auch ein Neuanlegen des Containers.

---

## Als App in Home Assistant

Wer Home Assistant OS betreibt, kann den Proxy dort als eigene App laufen lassen. Er startet dann mit Home Assistant und wird bei einem Absturz automatisch neu gestartet.

👉 **[Anleitung für die Home-Assistant-App](HA_zendure_proxy/INSTALLATION.md)**

[![Repository zu Home Assistant hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsurfer1264%2Fha-zendure-apps)

Kurz gesagt: das Repository `https://github.com/surfer1264/ha-zendure-apps` im App Store hinzufügen (Knopf oben), die App „Zendure Dashboard Proxy“ installieren, starten, `http://<IP-von-Home-Assistant>:8000/` aufrufen und einrichten wie in [Schritt 4](#in-4-schritten-zum-dashboard). Neue Versionen bietet Home Assistant dann selbst als Update an.

> **Achtung:** Die Einstellungen liegen im dauerhaften Speicher der App und überstehen Updates. Neue Versionen deshalb immer per **Aktualisieren** einspielen – wird die App deinstalliert und neu installiert, ist die Einrichtung einmal zu wiederholen.

---

## Startoptionen

Gilt für das Python-Script (und das Programm, wenn du es aus einer Konsole startest):

| Option | Wirkung |
|---|---|
| *(keine)* | normal, mit einer Protokollzeile je Aufruf |
| `-q` | leise: Startübersicht ja, Protokoll nein – praktisch im Dauerbetrieb |
| `-s` | still: gar keine Ausgabe (Fehler erscheinen trotzdem) |
| `--browser` | Browser beim Start immer öffnen |
| `--no-browser` | Browser beim Start nie öffnen |
| `-h` | Hilfe anzeigen |

Ohne `--browser`/`--no-browser` entscheidet der Proxy selbst: Unter Windows, macOS und auf einem Linux-Desktop öffnet er den Browser, auf einer Synology, in Home Assistant oder in einer SSH-Sitzung nicht.

Port (`PORT`, Standard 8000) und Netzwerk-Schnittstelle (`BIND_ADDRESS`) stehen bei Bedarf oben im Python-Script.

---

## Gut zu wissen

- **Kein Passwortschutz:** Jeder im Heimnetz, der die Adresse kennt, kann das Dashboard öffnen und Einstellungen ändern – auch die Shelly-Adresse unter `/setup`. Den Proxy deshalb **nie** per Portweiterleitung ins Internet stellen.
- **Script-Nummer:** Beim **Update** über den Configurator bleibt die Nummer gleich. Wird das Script **neu angelegt** (erste Installation, „andere löschen“, Shelly-Wechsel oder Upload von Hand), bekommt es eine neue Nummer. Geht das Dashboard danach nicht mehr, unter `http://<Proxy-Adresse>:8000/setup` die neue Nummer eintragen. Ein Neustart des Proxys ist nicht nötig.
- **Neues Layout, bisheriges unter `/b`:** Unter `http://<Proxy-Adresse>:8000/` läuft das Dashboard im neuen Aufbau – übersichtlicher gegliedert, Sperrknopf als deutlich markiertes Schloss, Status in Klartext, einklappbare Übersicht, technische Details (KVS-Schlüssel, IP-Adressen) nur auf Wunsch über das Menü „Ansicht“. Dort gewählte Einstellungen werden gemerkt – siehe [Bedienung](#bedienung). Das bisherige Layout mit denselben Funktionen gibt es weiterhin unter `http://<Proxy-Adresse>:8000/b`. Dafür muss `zendure-dashboard-b.html` neben `zendure-dashboard.html` liegen; im fertigen Programm und in der Home-Assistant-App ist sie enthalten.
- **Neue Dashboard-Version:** Beim Python-Script und auf der Synology einfach `zendure-dashboard.html` austauschen und die Seite im Browser neu laden – der Proxy liest die Datei bei jedem Aufruf frisch ein. Beim fertigen Programm ist die Seite eingebaut, dort kommt sie mit einem neuen Download. In Home Assistant muss die App neu gebaut werden.

---

## Wenn es nicht klappt

| Symptom | Lösung |
|---|---|
| Seite leer, „Failed to fetch“ | Die HTML-Datei wurde per Doppelklick geöffnet. Immer über `http://localhost:8000/` öffnen. |
| Statt des Dashboards erscheint die Einrichtungsseite | Der Proxy ist noch nicht eingerichtet, oder `zendure_proxy_config.json` fehlt bzw. ist beschädigt. Einfach neu einrichten. |
| „Speichern & testen“ meldet einen Fehler | IP oder Script-Nummer stimmen nicht – mit dem Test aus [Schritt 2](#in-4-schritten-zum-dashboard) prüfen. Die IP muss die des **Dashboard-Shelly** sein. |
| Roter Hinweis „Fehler beim Laden der Konfiguration“ | Der Shelly ist nicht (mehr) erreichbar oder die Script-Nummer hat sich geändert – unter `/setup` prüfen. |
| Versionshinweis in der Fußzeile ist gelb | Dashboard-Seite und Script haben unterschiedliche Versionen. Passende `zendure-dashboard.html` bzw. das neue Programm holen. |
| 404 unter `http://localhost:8000/` | `zendure-dashboard.html` liegt weder neben dem Proxy noch eine Ebene höher. Beim Start listet der Proxy alle Orte auf, an denen er gesucht hat. |
| Einrichtung lässt sich nicht speichern | Der Proxy darf in seinem Ordner nicht schreiben (z. B. unter `C:\Programme`). Ordner mit Schreibrecht wählen. |
| Einstellungen wirken nicht | Im Controller `kvsEnabled: true` setzen. |
| Einstellungen nach Neustart des Controllers weg | Im Controller `kvsForceReseed: false` setzen. |
| Vom Handy nicht erreichbar | `http://` statt `https://`, richtige IP aus der Zeile „Im Netz“, Firewall-Freigabe prüfen. |
| Nichts lässt sich bedienen | Die Seite ist gesperrt – Schloss in der Kopfzeile antippen. |
| KVS-Schlüssel, IP-Adressen oder `acMode`/`socLimit` fehlen | Im Menü „Ansicht“ die **Technischen Details** einschalten. |
| „Konnte Port 8000 nicht oeffnen“ | Der Proxy läuft schon (z. B. in einem zweiten Fenster), oder ein anderes Programm belegt den Port. |
