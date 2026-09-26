# zenDash-API + Watchdog v3.1 + Dashboard

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>


Ein Shelly-Script, das zwei Aufgaben rund um deine Zendure-Speicher übernimmt:

- **API für das Dashboard** – Das zenDash-Dashboard zeigt darüber Netzbezug, Ladestand und Leistung deiner Speicher an. Außerdem kannst du Einstellungen des Regel-Scripts ändern und manuelles Laden starten.
- **Watchdog** – Das Script meldet dir per Signal, WhatsApp oder Webhook, wenn ein Akku voll ist, zu warm wird, eine Zelle zu wenig Spannung hat oder ein Speicher nicht mehr erreichbar ist. Morgens und abends kommt zusätzlich eine kurze Übersicht.

Beide Teile lassen sich einzeln ein- und ausschalten. Früher waren es zwei getrennte Scripte (zenDash-API 2.x und AkkuVolt-Watchdog 1.x). Jetzt fragt ein einziges Script die Speicher ab und teilt die Daten zwischen beiden Aufgaben. Das spart Speicher auf dem Shelly und entlastet deine Zendure-Geräte.

Die Zusammenfassung war nötig, da beide (alte) Scripte auf einem Shelly sehr nahe an der verfügbaren Speichergrenze operierten. Je nach Ausbaustufe (Anzahl Geräte und Anzahl Akkus) war ein "out of memory" möglich. 

---

## Inhalt

- [Was du brauchst](#was-du-brauchst)
- [So arbeitet das Script](#so-arbeitet-das-script)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Dashboard einrichten (Python-Proxy)](#dashboard-einrichten-python-proxy)
- [Dashboard Bedienung](#dashboard-bedienung)    
- [Nachrichten](#nachrichten)
- [Manuelles Laden und Auto-Stop](#manuelles-laden-und-auto-stop)
- [Umstieg von den alten Scripten](#umstieg-von-den-alten-scripten)
- [Speicherbedarf](#speicherbedarf)
- [Fehlersuche](#fehlersuche)
- [Änderungen](#änderungen)

---

## Was du brauchst

- **Einen Shelly mit Script-Funktion**, also Generation 2 oder neuer (Plus, Pro, Gen3 …). Am besten läuft das Script auf einem eigenen Shelly, getrennt vom Regel-Script.
- **Zendure-Speicher mit lokaler Schnittstelle**, erreichbar unter `http://<IP-des-Speichers>/properties/report`. Getestet mit SolarFlow 2400 Pro und SolarFlow 800.
- **Das Regel-Script** (`zerooutput_multi_kvs`) auf deinem Regel-Shelly. Das Dashboard liest und schreibt dessen Einstellungen. Wenn du nur den Watchdog nutzt, brauchst du es nicht.
- **Für Nachrichten** (optional):
  - Signal oder WhatsApp: einen kostenlosen API-Key von [CallMeBot](https://www.callmebot.com)
  - oder einen Webhook, zum Beispiel in Home Assistant

> **Hinweis:** Auf dem Shelly mit dem Regel-Script darf **keine Passwort-Abfrage** (Authentifizierung) aktiv sein. Sonst kann dieses Script die Einstellungen dort nicht lesen und schreiben.

---

## So arbeitet das Script

Das Script richtet sein Tempo danach, ob gerade jemand zuschaut:

| Situation | Was passiert |
|---|---|
| **Dashboard ist geöffnet** | Alle 8 Sekunden werden Netzmessung und alle Speicher abgefragt. Der Watchdog prüft diese Werte gleich mit. |
| **Manuelles Laden läuft** | Ebenfalls alle 8 Sekunden, auch wenn das Dashboard geschlossen ist. So erkennt das Script, wann der Akku voll ist. |
| **Niemand schaut zu** | Nur der Watchdog fragt alle 120 Sekunden die überwachten Speicher ab. Die Netzmessung ruht. |

Abfragen, Schreibvorgänge und Nachrichten laufen immer **nacheinander**, nie gleichzeitig. Das hält den Speicherbedarf auf dem Shelly niedrig.

---

## Installation

### Variante A: Über die Shelly-Weboberfläche

1. Öffne die Weboberfläche des Shelly, auf dem das Script laufen soll (`http://<IP-des-Shelly>`).
2. Gehe zu **Scripts** → **Create script** und gib ihm einen Namen, zum Beispiel `zenDash_watch`.
3. Kopiere den Inhalt von `zendash_watch_src.js` hinein.
4. Passe oben im Script den Block `let CONFIG = { ... }` an (siehe [Konfiguration](#konfiguration)).
5. **Speichern**, dann **Start**.
6. Schalte **Run on startup** ein, damit das Script nach einem Stromausfall von selbst wieder startet.

### Variante B: Mit `deploy.cmd` (für Fortgeschrittene)

Wenn du die Deploy-Werkzeuge aus diesem Repository nutzt:

1. Lege deine eigene Konfiguration in einer eigenen Datei ab, zum Beispiel `myconfig_zenDash_watch.js`. Sie enthält nur den `let CONFIG = { ... };`-Block.
2. Trage in `deploy.cmd` ein: IP des Shelly, Script-Name, `QUELLE=..\zendash_watch_src.js` und `MEINE_CONFIG=myconfig_zenDash_watch.js`.
3. Starte `deploy.cmd`. Das Werkzeug setzt deine Konfiguration ein, verkleinert das Script und lädt es hoch.

> **Wichtig:** `deploy.cmd` nimmt immer den CONFIG-Block aus **deiner** Datei. Änderungen, die du direkt in `zendash_watch_src.js` machst, werden dabei überschrieben.

### Nach dem Start

Im Log des Scripts erscheint eine Übersicht. Prüfe dort, ob alles so eingestellt ist, wie du es willst:

```
--------------------------------
zenDash-API + Watchdog v3.1 (API-Schnittstelle 2.7)
Module     : API AN | Watchdog AN
Geraete    : SF2400[W] SF800[W]
Watchdog   : alle 120 s, Offline-Alarm nach 10 min
Nachrichten: SIGNAL -> callmebot | Debug: AUS
--------------------------------
```

`[W]` hinter einem Gerät bedeutet: Der Watchdog überwacht es.

Wenn Nachrichten eingeschaltet sind, bekommst du außerdem die Meldung **„✅ zenDash/Watchdog v3.1 gestartet“**. So weißt du sofort, dass der Nachrichtenweg funktioniert.

---

## Konfiguration

Alle Einstellungen stehen oben im Script im Block `let CONFIG = { ... }`. Er ist in Abschnitte gegliedert.

### Geräte (`devices`)

Übernimm den Geräteblock **1:1 aus deinem Regel-Script**, mit gleichen IP-Adressen und **in der gleichen Reihenfolge**. Die Reihenfolge ist wichtig: Das erste Gerät ist im Regel-Script „Gerät 0“, das zweite „Gerät 1“ und so weiter.

Ergänze bei jedem Gerät nur `watch`:

```js
devices: [
  {
    ip: "192.168.178.143",
    label: "SF2400",
    minSoc: 15,
    maxSoc: 100,
    dischargeAllowed: true,
    reverse: true,
    maxInputPower: 1000,
    maxOutput: 800,
    inputLimit: 0,
    watch: true          // true = Watchdog ueberwacht dieses Geraet
  },
  // ... weitere Geraete
],
```

| Einstellung | Bedeutung |
|---|---|
| `ip` | IP-Adresse des Zendure-Speichers |
| `label` | Name für Anzeige und Nachrichten. Im Morgen-/Abend-Update erscheinen nur die ersten 6 Zeichen. |
| `minSoc`, `maxSoc`, `maxInputPower`, `maxOutput`, `inputLimit`, `dischargeAllowed`, `reverse` | wie im Regel-Script. Das Dashboard nutzt sie als Startwerte und Grenzen für die Regler. |
| `watch` | `true`: Der Watchdog überwacht dieses Gerät. `false`: Es erscheint nur im Dashboard. Fehlt der Eintrag, gilt `true`. |

Steht in deiner alten Konfiguration noch `dryRun`, stört das nicht, der Eintrag wird ignoriert.

### Dashboard-Teil (`api`)

```js
api: {
  enabled: true,
  kvsHost: "192.168.178.117",
  hysteresis: 12,
  dischargeStartupPower: 35,
  gridSource: "remote",
  gridSourceIp: "192.168.178.117",
  gridSourceEmId: 0,
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  gridSourceField: "total_power",
  gridSourceInvert: false,
  pollIntervalSec: 8
},
```

| Einstellung | Bedeutung |
|---|---|
| `enabled` | `true`: Dashboard-Schnittstelle an. `false`: nur Watchdog. |
| `kvsHost` | Wo liegen die Einstellungen des Regel-Scripts? Die **IP des Regel-Shelly**, wenn dieses Script auf einem anderen Shelly läuft (empfohlen), oder `"local"`, wenn beide auf demselben Shelly laufen. |
| `hysteresis` | Nur zur Anzeige im Dashboard. Wert aus dem Regel-Script übernehmen. |
| `dischargeStartupPower` | Kleinster erlaubter Wert für die Fix-Entladung (außer 0). Wert aus dem Regel-Script übernehmen. |
| `gridSource` | Woher kommt die Netzmessung? `"remote"`: ein anderer Shelly Pro 3EM, `"local"`: dieser Shelly selbst misst, `"http_json"`: ein anderes Messgerät mit JSON-Schnittstelle. |
| `gridSourceIp`, `gridSourceEmId` | bei `"remote"`: IP des Messgeräts und Kanal (meist 0) |
| `gridSourceUrl`, `gridSourceField`, `gridSourceInvert` | bei `"http_json"`: Adresse, Feldname der Gesamtleistung, Vorzeichen umdrehen ja/nein |
| `pollIntervalSec` | Abfragetakt bei geöffnetem Dashboard in Sekunden. Standard 8. |

### Watchdog (`watchdog`)

```js
watchdog: {
  enabled: true,
  intervalSec: 120,
  vollSchwelle: 99,
  entladeReset: 90,
  minVoltWarn: 2.9,
  minVoltReset: 3.1,
  tempWarn: 45.0,
  tempReset: 30.0,
  offlineAlarmMin: 10,
  sunriseOffset: 0,
  sunsetOffset: 0
},
```

| Einstellung | Bedeutung |
|---|---|
| `enabled` | Watchdog an oder aus |
| `intervalSec` | Wie oft der Watchdog ohne geöffnetes Dashboard nachschaut, in Sekunden (mindestens 60) |
| `vollSchwelle` / `entladeReset` | Meldung „voll“ ab diesem Ladestand. Die nächste Meldung kommt erst, wenn der Akku zwischendurch unter `entladeReset` gefallen ist. |
| `minVoltWarn` / `minVoltReset` | Warnung, wenn eine Zelle unter diese Spannung (Volt) fällt. Erneute Warnung erst, wenn sie zwischendurch wieder über `minVoltReset` lag. |
| `tempWarn` / `tempReset` | Warnung bei Gerätetemperatur über `tempWarn` (°C). Erneute Warnung erst, wenn sie zwischendurch unter `tempReset` lag. |
| `offlineAlarmMin` | Meldung, wenn ein Speicher so viele **Minuten** nicht erreichbar ist |
| `sunriseOffset` / `sunsetOffset` | Verschiebung des Morgen- und Abend-Updates gegenüber Sonnenauf- und -untergang in Minuten, z. B. `30` = eine halbe Stunde später |

> Damit die Uhrzeiten für Sonnenauf- und -untergang stimmen, muss im Shelly der **Standort** eingestellt sein (Einstellungen → Standort bzw. Zeitzone).

### Nachrichten (`notify`)

```js
notify: {
  enabled: true,
  typ: "SIGNAL",
  phone: "+4917XXXXXXXX",
  apiKey: "DEIN_CALLMEBOT_KEY",
  webhookUrl: "http://192.168.178.50:8123/api/webhook/DEINE_ID",
  maxMessageLength: 900,
  apiEvents: true
},
```

| Einstellung | Bedeutung |
|---|---|
| `enabled` | Nachrichten an oder aus. Auch wenn sie aus sind, erscheinen alle Meldungen im Log des Scripts. |
| `typ` | `"SIGNAL"`, `"WHATSAPP"` oder `"WEBHOOK"` |
| `phone`, `apiKey` | nur für Signal und WhatsApp: deine Nummer mit Ländervorwahl und der CallMeBot-Key |
| `webhookUrl` | nur für Webhook: vollständige Adresse |
| `maxMessageLength` | Längere Nachrichten werden gekürzt |
| `apiEvents` | `true`: auch Meldungen zum Auto-Stop beim manuellen Laden verschicken |

**Webhook-Format:** Das Script schickt einen POST-Request mit dem Inhalt `{"message": "…"}`. In Home Assistant steht der Text dann in einer Automation mit Webhook-Auslöser unter `{{ trigger.json.message }}`.

### Allgemein

| Einstellung | Bedeutung |
|---|---|
| `httpTimeout` | Wie viele Sekunden das Script höchstens auf eine Antwort wartet. Standard 5. |
| `debug` | `false`: normale Ausgabe. `true`: ausführliches Log zur Fehlersuche (siehe [Fehlersuche](#fehlersuche)). |

---

## Dashboard einrichten (Python-Proxy)

Das Dashboard ist eine Webseite, die ihre Daten von diesem Script holt. Der Browser darf die Daten aber nicht direkt beim Shelly abfragen – die Shelly-Firmware lehnt solche Zugriffe aus einer fremden Webseite ab. Deshalb läuft auf einem Rechner im Heimnetz ein kleiner **Python-Proxy**: Er liefert die Dashboard-Seite aus und fragt den Shelly stellvertretend ab.

```
Browser  ──►  Python-Proxy (PC/NAS/HA/Raspi)  ──►  Dashboard-Shelly (zenDash-API)  ──►  Controller-Shelly (KVS)
```

### Welche Variante passt zu dir?

Es gibt **einen** Proxy (`zendure_proxy.py`), der überall gleich funktioniert. Nur die Art, wie du ihn startest, unterscheidet sich:

| Variante | Geeignet für | Start | Browser öffnet sich von selbst |
|---|---|---|---|
| **Python-Script** | PC, Laptop, Raspberry Pi | `python3 zendure_proxy.py` | ja (nur mit Bildschirm) |
| **EXE** | Windows ohne Python-Installation | Doppelklick | ja |
| **Synology** | Dauerbetrieb auf dem NAS | Aufgabenplaner | nein |
| **Home Assistant** | wer ohnehin Home Assistant OS betreibt | als eigene App | nein |

Die Einrichtung ist in allen Fällen gleich: Proxy starten, im Browser aufrufen, auf der Einrichtungsseite IP und Script-ID des Dashboard-Shelly eintragen. Ein Texteditor ist dafür nicht nötig.

### Was du dafür brauchst

- **`api.enabled: true`** in diesem Script (siehe [Konfiguration](#konfiguration))
- einen **Rechner, der dauerhaft läuft** – PC, NAS (z. B. Synology), Home Assistant, Raspberry Pi, Mini-PC
- **Python 3.7 oder neuer** ([python.org](https://www.python.org/downloads/)). Es muss nichts zusätzlich installiert werden. Entfällt bei der EXE und bei Home Assistant.
- die zwei Dateien aus dem [Dashboard-Ordner](https://github.com/surfer1264/Zendure-Stuff/tree/main/shelly_script/zendash_watch_API_ZenSDK):
  - `zendure_proxy.py` – der Proxy
  - `zendure-dashboard.html` – die Dashboard-Seite

  Die HTML-Datei darf **im selben Ordner** wie der Proxy liegen oder **eine Ebene höher**. Liegt an beiden Stellen eine, gewinnt die im selben Ordner.

Damit du im Dashboard auch **einstellen** kannst (Sollwert, Reserve, manuelles Laden …), muss im Controller `kvsEnabled: true` und `kvsForceReseed: false` gesetzt sein. Ohne KVS zeigt das Dashboard nur an.

### In 4 Schritten zum Dashboard

**1. Script-ID nachsehen**

Der Proxy muss wissen, unter welcher IP-Adresse der Dashboard-Shelly erreichbar ist und welche Nummer das Script dort hat.

In der Weboberfläche des Dashboard-Shelly unter **Scripts** steht die Nummer des Scripts (z. B. `id: 1`). Über den Configurator hochgeladen, heißt das Script `zd`.

**2. Kurz testen, ob das Script antwortet**

Im Browser direkt aufrufen (IP und Nummer einsetzen):

```
http://<IP-des-Dashboard-Shelly>/script/<Script-ID>/status_api
```

Es sollte eine Zeile mit Daten (JSON) erscheinen. Kommt ein Fehler, läuft das Script nicht oder die Nummer stimmt nicht. Funktioniert es, hast du die richtige IP-Adresse und Script-Nummer.

**3. Proxy starten**

Im Ordner mit den Dateien ein Terminal (Windows: Eingabeaufforderung) öffnen und starten:

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

Ein Klick auf **„Speichern & testen“** prüft sofort, ob unter dieser Adresse wirklich das API-Script antwortet. Bei einem Tippfehler erscheint eine Fehlermeldung, und nichts wird gespeichert. Klappt der Test, leitet die Seite direkt zum Dashboard weiter.

Die Einstellungen landen in der Datei `zendure_proxy_config.json` neben dem Proxy (bzw. neben der EXE). Beim nächsten Start sind sie wieder da – die Einrichtung ist also nur einmal nötig. Ändern kannst du sie jederzeit unter:

```
http://<Proxy-Adresse>:8000/setup
```

Danach ist das Dashboard auch von jedem anderen Gerät im Heimnetz erreichbar – mit der Adresse aus der Zeile **„Im Netz“**, z. B. `http://192.168.178.21:8000/`.

- immer `http://`, nicht `https://`
- die Seite startet **gesperrt** – das Schloss oben rechts gibt die Bedienung frei
- fragt Windows beim ersten Start nach der Firewall: **„Zugriff zulassen“** (privates Netzwerk)

### Startoptionen

| Option | Wirkung |
|---|---|
| *(keine)* | normal, mit einer Protokollzeile je Aufruf |
| `-q` | leise: Startübersicht ja, Protokoll nein – praktisch im Dauerbetrieb, die Seite fragt alle 4 Sekunden an |
| `-s` | still: gar keine Ausgabe (Fehler erscheinen trotzdem) |
| `--browser` | Browser beim Start immer öffnen |
| `--no-browser` | Browser beim Start nie öffnen |
| `-h` | Hilfe anzeigen |

Ohne `--browser`/`--no-browser` entscheidet der Proxy selbst: Unter Windows, macOS und auf einem Linux-Desktop öffnet er den Browser, auf einer Synology, in Home Assistant oder in einer SSH-Sitzung nicht.

Port (`PORT`, Standard 8000) und Netzwerk-Schnittstelle (`BIND_ADDRESS`) stehen bei Bedarf oben im Script.

### Gut zu wissen

- **Dauerbetrieb:** Der Proxy muss laufen, solange du das Dashboard nutzen willst. Ein Laptop, der zugeklappt wird, eignet sich dafür schlecht – besser eine Synology oder Home Assistant (siehe unten).
- **Kein Passwortschutz:** Jeder im Heimnetz, der die Adresse kennt, kann das Dashboard öffnen und Einstellungen ändern – auch die Shelly-Adresse unter `/setup`. Den Proxy deshalb **nie** per Portweiterleitung ins Internet stellen.
- **Nach einem Script-Update:** Wird das Script neu angelegt (z. B. beim Hochladen über den Configurator), kann sich die **Script-ID ändern**. Geht das Dashboard danach nicht mehr, unter `http://<Proxy-Adresse>:8000/setup` die neue Nummer eintragen. Ein Neustart des Proxys ist nicht nötig.
- **Neue Dashboard-Version:** Beim Python-Script und auf der Synology einfach `zendure-dashboard.html` austauschen und die Seite im Browser neu laden – der Proxy liest die Datei bei jedem Aufruf frisch ein. Bei der EXE ist die Seite eingebaut, dort kommt sie mit einer neuen EXE. In Home Assistant muss die App neu gebaut werden.

### Wenn es nicht klappt

| Symptom | Lösung |
|---|---|
| Seite leer, „Failed to fetch“ | Die HTML-Datei wurde per Doppelklick geöffnet. Immer über `http://localhost:8000/` öffnen. |
| Statt des Dashboards erscheint die Einrichtungsseite | Der Proxy ist noch nicht eingerichtet, oder `zendure_proxy_config.json` fehlt bzw. ist beschädigt. Einfach neu einrichten. |
| „Speichern & testen“ meldet einen Fehler | IP oder Script-ID stimmen nicht – mit dem Test aus Schritt 2 prüfen. Die IP muss die des **Dashboard-Shelly** sein. |
| Roter Hinweis „Fehler beim Laden der Konfiguration“ | Der Shelly ist nicht (mehr) erreichbar oder die Script-ID hat sich geändert – unter `/setup` prüfen. |
| 404 unter `http://localhost:8000/` | `zendure-dashboard.html` liegt weder neben dem Proxy noch eine Ebene höher. Beim Start listet der Proxy alle Orte auf, an denen er gesucht hat. |
| Einrichtung lässt sich nicht speichern | Der Proxy darf in seinem Ordner nicht schreiben (z. B. EXE unter `C:\Programme`). Ordner mit Schreibrecht wählen. |
| Einstellungen wirken nicht | Im Controller `kvsEnabled: true` setzen. |
| Einstellungen nach Neustart des Controllers weg | Im Controller `kvsForceReseed: false` setzen. |
| Vom Handy nicht erreichbar | `http://` statt `https://`, richtige IP aus der Zeile „Im Netz“, Firewall-Freigabe prüfen. |
| Nichts lässt sich bedienen | Die Seite ist gesperrt – Schloss oben rechts antippen. |
| „Konnte Port 8000 nicht oeffnen“ | Der Proxy läuft schon (z. B. in einem zweiten Fenster), oder ein anderes Programm belegt den Port. |

### Als EXE unter Windows

Für Windows-Rechner ohne Python gibt es den Proxy als fertige EXE. Die Dashboard-Seite ist darin bereits eingebaut – du brauchst also nur diese eine Datei.

1. Die EXE in einen **eigenen Ordner** legen, in dem du Schreibrecht hast, z. B. `C:\Users\<name>\zendure\`. Nicht unter `C:\Programme`, dort kann der Proxy seine Einstellungen nicht speichern.
2. Per **Doppelklick** starten. Ein Konsolenfenster öffnet sich (offen lassen), dazu der Browser mit der Einrichtungsseite.
3. Warnt Windows SmartScreen vor einer unbekannten App: **„Weitere Informationen“ → „Trotzdem ausführen“**.
4. Fragt die Windows-Firewall nach: **„Zugriff zulassen“** (privates Netzwerk), sonst ist das Dashboard vom Handy aus nicht erreichbar.
5. Einrichten wie in [Schritt 4](#in-4-schritten-zum-dashboard) beschrieben. Die Datei `zendure_proxy_config.json` entsteht neben der EXE.

Beenden: Konsolenfenster schließen oder `Strg+C`.

### Dauerbetrieb auf einer Synology

Ein Laptop, den man zuklappt, taugt nicht als Dauerläufer. Auf einer Synology geht es so:

1. **Python prüfen.** DSM bringt meist schon eines mit:
   ```bash
   which python3 && python3 --version
   ```
   Ab 3.7 reicht es – der Proxy nutzt nur die Standardbibliothek, es muss nichts nachinstalliert werden. Häufig liegt der Interpreter unter `/bin/python3`. Kommt gar nichts, im Paketzentrum **Python 3** installieren; der Pfad ist dann `/var/packages/Python3*/target/bin/python3`.
2. **Dateien ablegen.** `zendure_proxy.py` in einen eigenen Ordner, z. B. `/volume1/homes/<benutzer>/zendure`, und `zendure-dashboard.html` daneben oder eine Ebene höher. Nicht in den `web`-Ordner – der gehört der Web Station.
3. **Aufgabe anlegen.** Systemsteuerung → Aufgabenplaner → Erstellen → **Ausgelöste Aufgabe** → Benutzerdefiniertes Skript. Ereignis **Hochfahren**, Benutzer **root**, als Befehl der volle Pfad:
   ```bash
   /bin/python3 /volume1/homes/<benutzer>/zendure/zendure_proxy.py -q
   ```
4. **Sofort starten**, ohne Neustart: Aufgabe markieren → **Ausführen**.
5. **Firewall.** Ist sie unter Systemsteuerung → Sicherheit → Firewall aktiv, eine Regel für TCP **8000** anlegen. Port 8000 kollidiert nicht mit DSM selbst (5000/5001).
6. **Einrichten.** Von einem PC oder Handy aus `http://<IP-der-Synology>:8000/` aufrufen und wie in [Schritt 4](#in-4-schritten-zum-dashboard) IP und Script-ID eintragen. Einen Browser auf der Synology selbst braucht es nicht, der Proxy versucht dort auch keinen zu öffnen.

Die Aufgabe bleibt dauerhaft als „läuft“ stehen, weil der Proxy nicht endet. Das ist richtig so.

Weil die Aufgabe als `root` läuft, gehört die entstehende `zendure_proxy_config.json` ebenfalls `root`. Das ist für den Betrieb egal; nur wer die Datei später von Hand löschen oder ändern will, braucht dafür Administratorrechte.

Der Aufgabenplaner startet die Aufgabe beim Hochfahren, aber **nicht neu, wenn der Prozess abstürzt**. Wer das möchte, nimmt statt der Aufgabe einen Container im Container Manager (`python:3-slim`, Ordner als Volume, Port 8000, Neustartrichtlinie „immer“). Die Einstellungen landen dann im eingebundenen Ordner und überstehen auch ein Neuanlegen des Containers.

### Als App in Home Assistant

Wer Home Assistant OS betreibt, kann den Proxy dort als eigene App laufen lassen. Er startet dann mit Home Assistant und wird bei einem Absturz automatisch neu gestartet. Die Anleitung dazu steht in der eigenen Readme im Ordner der Home-Assistant-App.

Kurz gesagt: App aus dem lokalen Ordner installieren, starten, `http://<IP-von-Home-Assistant>:8000/` aufrufen und einrichten wie in [Schritt 4](#in-4-schritten-zum-dashboard).

> **Achtung:** Die Einstellungen liegen in Home Assistant im Container der App. Wird die App deinstalliert und neu installiert (z. B. für eine neue Dashboard-Version), ist die Einrichtung einmal zu wiederholen.

---

## Dashboard Bedienung

Alle Regelparameter werden per Shelly-KVS gesetzt und wirken beim nächsten Regelzyklus des Regel-Scripts. Die Grenzen entsprechen exakt dem Clamping in `readKvsOverrides()` von `zerooutput_multi_kvs.js` — Werte außerhalb dieser Bereiche verwirft das Regel-Script kommentarlos.

| Bedienelement | KVS-Key | Bereich |
|---|---|---|
| Sollwert (obere Reihe, links) | `zdmc_setpoint` | −40 bis +40 W, 5er-Schritte |
| Fix-Entladung (Zahleneingabe) | `zdmc_dischargeFixed` | 0 (= aus) oder ≥ `dischargeStartupPower` |
| Entladen erlaubt | `zdmc_dev{id}_dischargeAllowed` | Schalter (0/1) |
| Laden vom Netz erlaubt | `zdmc_dev{id}_reverse` | Schalter (0/1) |
| Reserve (min. SoC) | `zdmc_dev{id}_minSoc` | 10 % bis `maxSoc` − 1, 1er-Schritte |
| Ladeleistung aus dem Netz | `zdmc_dev{id}_inputLimit` | 0 bis `maxInputPower`, 50er-Schritte |

### Was die Regler bewirken

* **Reserve (min. SoC)** wird vom Regel-Script zusätzlich als Schutzgrenze auf die Hardware geschrieben (`syncMinSocDevice`) — der Wert ändert also nicht nur die Verteilrechnung, sondern das Gerät selbst.
* Die **Obergrenze der Reserve** leitet das Dashboard aus `maxSoc` ab und hält einen Prozentpunkt Abstand. Das ist kein Schoenheitsfehler, sondern ein Schutz: Das Regel-Script gleicht `minSoc` und `maxSoc` nur beim **Start** gegeneinander ab, nicht beim Live-Override über die KVS. Rutschte `minSoc` über `maxSoc`, dürfte das Gerät weder unter die Reserve entladen noch bis dorthin laden — es fiele dauerhaft aus der Regelung, und `syncSocLimits()` schriebe das verdrehte Wertepaar zusätzlich auf die Hardware, wo es einen Scriptstopp überdauert. Wer den Wert direkt in der KVS setzt, umgeht diesen Schutz; dagegen hülfe nur eine Prüfung im Regel-Script selbst (`v < dev.maxSoc` statt `v <= 99`).
* **Manuelles Laden** ist eine Aktion, kein einzelner Schalter. Der Regler „Ladeleistung aus dem Netz" wählt nur die Leistung aus und schreibt für sich genommen nichts; der Knopf darunter führt drei Schreibvorgänge in der richtigen Reihenfolge aus:
  1. `dischargeAllowed = 0`
  2. `reverse = 0`
  3. `inputLimit = <gewählte Leistung>`

  Beim Beenden umgekehrt: erst `inputLimit = 0`, dann die Schalter zurück auf den Stand vor dem Start. Die Reihenfolge ist nicht kosmetisch — wird `inputLimit` gesetzt, solange das Gerät noch in der Regelung hängt, überschreibt das Regel-Script den Wert im nächsten Zyklus. Umgekehrt würde ein stehengebliebenes Ladelimit mit der wieder aktiven Regelung kollidieren.

  Während der Kette pausiert der Seiten-Poll, zwischen den Schritten liegen 500 ms (`STEP_PAUSE_MS`), und danach vergehen weitere 1,5 s (`SETTLE_MS`), bevor wieder abgefragt wird. Ohne diese Entzerrung treffen drei `KVS.Set`, der laufende Hintergrund-Poll und die Reaktion des Regel-Scripts — das bei geändertem `inputLimit` sofort aufs Gerät schreibt — innerhalb weniger hundert Millisekunden auf demselben Shelly zusammen. Der ganze Vorgang dauert dadurch rund 2,5 s.

  Bricht die Kette in der Mitte ab (Shelly nicht erreichbar), erscheint ein Warnbanner — der Zustand ist dann unvollständig und gehört auf der Karte geprüft.

  Ob manuelles Laden läuft, leitet die Seite aus dem Live-Zustand ab (beide Schalter aus **und** `inputLimit > 0`). Das überlebt einen Reload und stimmt auch dann, wenn jemand anders die Werte gesetzt hat. Nur der Schalterzustand *vor* dem Start geht bei einem Reload verloren; das Beenden schaltet dann beide Schalter wieder ein.
* **Fix-Entladung** (`zdmc_dischargeFixed`) ist ein globaler, geräteübergreifender Wert — anders als die übrigen Regler, die pro Gerät (`zdmc_dev{id}_...`) wirken. Sie ist eine Zahleneingabe statt eines Reglers, weil nur zwei Zustände gültig sind: `0` (aus) oder ≥ `dischargeStartupPower`. Werte dazwischen verwirft schon `kvs_set_api` mit einer Fehlermeldung, bevor sie in der KVS landen — das Regel-Script würde sie ohnehin kommentarlos ignorieren. `dischargeStartupPower` kommt aus `config_api` (Spiegel von `CONFIG.dischargeStartupPower` im API-Script) und steht als Hinweistext unter dem Feld (`0 = aus · sonst ≥ NN W`). Ein ungültiger Wert wird beim Verlassen des Felds sofort auf den zuletzt gültigen zurückgesetzt.
* **Hysterese** ist im Regel-Script **nicht** über die KVS änderbar und taucht im Dashboard deshalb nicht als Bedienelement auf. `config_api` liefert den Wert trotzdem mit; die Seite braucht ihn nur intern, um den Netzbezug als Import, Export oder ausgeglichen einzustufen. Gepflegt wird er in `CONFIG.hysteresis` beider Scripte, die denselben Wert tragen müssen.
* Die Seite startet **gesperrt**. Das Schloss-Symbol oben rechts gibt die Bedienung frei; nach 60 s ohne Eingabe (`RELOCK_MS`) sperrt sie sich von selbst wieder. Der Zustand wird absichtlich nicht gespeichert — jeder Reload beginnt gesperrt. Gedacht ist das für Dashboards, die dauerhaft auf einem Tablet oder Zweitmonitor offen liegen.
* Jedes Bedienelement **sperrt sich nach einer Eingabe für 4 s** (`LOCK_MS`). Das verhindert mehrfaches Auslösen und schützt den frisch gesetzten Wert vor dem nächsten `config_api`-Abgleich. Schlägt das Schreiben fehl, wird sofort wieder freigegeben.

### Was die Anzeige zeigt

* Unter dem SoC steht das **Arbeitsfenster** des Geräts in Kurzform, z. B. `SoC · 15–100 %`: von der Reserve (`minSoc`, einstellbar) bis zum Ladeziel (`maxSoc`, nur Anzeige — der Wert kommt aus der Konfiguration und ist nicht über die KVS änderbar).
* Neben dem Sollwert steht die **Hysterese** als Toleranzangabe. Sie ist nicht einstellbar, gehört aber dorthin: Sie sagt, wie weit der Netzsaldo abweichen darf, bevor das Regel-Script überhaupt nachsteuert. Ohne sie wirkt ein Sollwert exakter, als er ist.
* **acMode / socLimit / gridReverse** stehen als Rohstatus auf jeder Hub-Karte. Sie erklären die häufigsten „Warum tut der Hub nichts?"-Fälle: `socLimit 1` = Akku voll, Laden gesperrt; `socLimit 2` = Entladen gesperrt; `gridReverse 2` = Netzladen vom Regel-Script flottenweit gesperrt.
* **PV-Eingang und schwächste Zelle** stehen als kleine Zeile unter der Leistung jeder Hub-Karte:
  * Der PV-Wert ist `solarInputPower`, also der Gesamteingang des Geräts. Fehlt das Feld — etwa bei reinen AC-Ladern —, entfällt die Angabe komplett, statt fälschlich „0 W" zu zeigen.
  * Die Zellspannung ist das Minimum über `packData[].minVol` aller Packs, umgerechnet mit Faktor 0,01 (325 → 3,25 V). Packs, die 0 melden, werden übersprungen. Unter 3,0 V wird der Wert amber, unter 2,8 V rot. Aussagekräftig ist er nur unter Last — im Ruhezustand liegen alle Zellen dicht beieinander.
* **Der Verlauf** steckt als kompakte Kurve in den beiden Kacheln oben: Netzsaldo links, Hub-Summe rechts. Beide skalieren auf ihr eigenes Maximum und sind daher nicht gegeneinander ablesbar — die Nulllinie liegt jeweils in der Mitte, Amber oben, Teal unten.
* Der Verlauf wird **in der Seite** geführt (`MAX_POINTS`, Standard 30 Werte à 4 s = 2 Minuten). Ein Ringpuffer im API-Script wäre komfortabler — er würde einen Reload überleben —, sprengte aber den Heap des Shelly. Nach einem Reload beginnen die Kurven deshalb wieder von vorn.
* Die Seite folgt beim Start der **Systemeinstellung des Geräts** (`prefers-color-scheme`) — Nachtmodus am Handy schaltet auch hier die Nachtsicht ein, sonst startet sie in der Tagsicht, und ein späterer Systemwechsel wird live nachgezogen. Der Schalter oben rechts schaltet manuell um; ab dem ersten Antippen wird die Systemeinstellung ignoriert, damit ein automatischer Wechsel am Abend die bewusste Wahl nicht wieder überschreibt. Das gilt nur für die laufende Sitzung — ein Reload startet wieder bei der Systemeinstellung.
* Der dritte Knopf oben rechts (**A**) schaltet die **Schriftgröße** in drei Stufen um: Normal, Groß (115 %) und Sehr groß (130 %). Vorgabe beim Laden ist „Groß". Wie beim Theme wird der Zustand nicht gespeichert; ein Reload beginnt wieder bei „Groß".
* In der Fußzeile stehen die Versionen von Seite und API-Script. Laufen sie auseinander, wird der Hinweis amber — typischer Fall: HTML aktualisiert, das Script auf dem Shelly aber nicht.
* Geräteliste, Sollwert, Reglerstände und Schalterstellungen kommen bei jedem Laden/Poll frisch von `config_api` — es gibt **keine** Geräte-Konfiguration mehr in der HTML-Datei selbst. Das vermeidet Doppelpflege.

### Wer wie oft fragt

* Die **Seite** frischt fest alle 4 s auf (`POLL_SEC`), es gibt kein Bedienelement dafür. Der Wert muss unter `IDLE_MS` (15 s) im API-Script bleiben, sonst pausiert dort die Hintergrundabfrage zwischen zwei Seitenaufrufen und die Anzeige hängt hinterher.
* `status_api` wird bei jedem Durchlauf geholt, `config_api` nur jeden dritten (`CONFIG_EVERY`, also alle 12 s) — dieser Endpunkt macht auf dem Shelly jedes Mal ein `KVS.GetMany`. Eigene Eingaben wirken trotzdem sofort; nur eine Änderung von außen erscheint entsprechend später.
* Das **API-Script** fragt Netzzähler und Hubs alle 8 s ab (`pollIntervalSec`) — aber nur, solange in den letzten 15 s (`IDLE_MS`) tatsächlich ein Dashboard-Aufruf einging. Ist kein Dashboard offen, pausiert diese Hintergrundabfrage automatisch. Kein unnötiger Traffic zu den Zendure-Hubs.
* Ein **Zähler** (früher ein Flag) sorgt dafür, dass Hintergrundabfrage und `config_api` nie gleichzeitig laufen. Beide sind speicherintensiv — Parsen der mehrere kB großen Hub-Antwort bzw. `KVS.GetMany`. Kollidieren sie, lässt der Hintergrund-Timer den Takt aus, und `config_api` wartet bis zu 2 s auf einen freien Slot. Zusätzlich hat der Hintergrund-Durchlauf mit `bgRunning` einen eigenen Riegel gegen sich selbst.
* Die Notbremse (`BUSY_TIMEOUT_MS`) richtet sich nach der Gerätezahl: `(Geräte + 1) × httpTimeout + 5 s`. Sie muss länger sein als der längstmögliche Durchlauf, in dem jede einzelne Abfrage in den Timeout läuft — sonst greift sie mitten im Normalbetrieb und erlaubt genau die Überlappung, die sie verhindern soll.
* `status_api` liefert eine fertig serialisierte Antwort, die einmal je Hintergrund-Durchlauf gebaut wird. `config_api` sammelt gleichzeitige Anfragen zu einem einzigen `KVS.GetMany` — bei einem Dashboard ändert das nichts, bei einem Reload-Sturm fällt der Aufwand auf ein Zehntel. Einen Ergebnis-Cache gibt es bewusst nicht: ein dauerhaft gehaltener Antwort-String kostet im knappen Variablenpool mehr, als er einspart.
* Die Antworten der Hubs werden **ohne `JSON.parse`** ausgewertet. Die benötigten Zahlen holt das Script per `indexOf`/`slice` aus dem Rohtext. Eine geparste `/properties/report`-Antwort (~1,3 kB, 60+ Felder) belegt mehrere hundert Variablen, der Rohtext allein nur einen Bruchteil davon. Preis dafür: ändert Zendure die Feldnamen, fällt das erst im Betrieb auf — deshalb liefert jede Extraktion `null` statt zu raten, und ein fehlendes `electricLevel` gilt als „Hub nicht auswertbar".

---

## Nachrichten

Diese Nachrichten kann das Script verschicken:

| Nachricht | Wann |
|---|---|
| ✅ zenDash/Watchdog v3.1 gestartet (2/2 ueberwacht) | nach jedem Start des Scripts |
| 🔋 SF2400 voll (99%) | Ladestand hat die `vollSchwelle` erreicht |
| 🔥 SF800 Temp hoch: 46.2C | Gerätetemperatur über `tempWarn` |
| ⚠️ SF800 Zelle BO1234… nur 2.85V | eine Zelle unter `minVoltWarn`, mit Seriennummer des Akkupacks |
| ❌ SF800: nicht erreichbar seit 10 min | Speicher antwortet nicht mehr |
| ❌ SF800: Report unlesbar seit 10 min | Speicher antwortet, aber mit unvollständigen oder unbrauchbaren Daten |
| ✅ SF800: wieder erreichbar | nach einer der beiden vorigen Meldungen |
| 🌅 Morgen-Update / 🌇 Abend-Update | zu Sonnenauf- und -untergang: Ladestand, Temperatur und niedrigste Zellspannung je Gerät |
| ✅ SF2400: manuelles Laden beendet (voll) … | Auto-Stop hat funktioniert (bei `apiEvents: true`) |
| ⚠️ SF2400: Auto-Stop fehlgeschlagen … | Auto-Stop konnte die Einstellungen nicht zurücksetzen. Bitte im Dashboard prüfen. |

Jede Warnung kommt **einmal**, nicht bei jeder Abfrage. Erst wenn sich der Wert wieder normalisiert hat, kann sie erneut kommen.

Im Morgen- und Abend-Update steht `n/a`, wenn für ein Gerät keine aktuellen Werte vorliegen, zum Beispiel weil es gerade nicht erreichbar ist.

> **Tipp:** Das Morgen- und Abend-Update ist gleichzeitig ein Lebenszeichen. Bleibt es aus, läuft das Script vermutlich nicht mehr.

---

## Manuelles Laden und Auto-Stop

Im Dashboard kannst du einen Speicher manuell aus dem Netz laden lassen. Das Script schaltet dafür im Regel-Script für dieses Gerät Entladen und Rückspeisung ab und setzt eine Ladeleistung.

**Auto-Stop:** Sobald der Speicher meldet, dass er voll ist, beendet das Script das manuelle Laden selbstständig und stellt den vorherigen Zustand wieder her. Das funktioniert auch, wenn das Dashboard geschlossen ist.

Gut zu wissen:
- Den vorherigen Zustand merkt sich das Script nur im Arbeitsspeicher. Startet der Shelly während des manuellen Ladens neu, werden beim Beenden Entladen und Rückspeisung wieder **eingeschaltet**.
- Du kannst das manuelle Laden jederzeit im Dashboard selbst beenden.

---

## Speicherbedarf

Ein Shelly-Script hat rund **25 kB** Arbeitsspeicher. Gemessen auf einem echten Gerät mit zwei Speichern:

| | belegt im Ruhezustand | höchster Wert |
|---|---|---|
| v3.1, Dashboard geschlossen | ca. 13,5 kB | ca. 17,8 kB |
| v3.1, Dashboard geöffnet | ca. 13,5 kB | ca. 17,7–18,0 kB |

Es bleiben also im ungünstigsten Moment noch gut **7 kB** frei. Zum Vergleich: Die beiden alten Scripte zusammen brauchten in der Spitze bereits nahezu 25kB. 

---

## Fehlersuche

### Debug-Ausgabe einschalten

Setze `debug: true` und starte das Script neu. Im Log erscheinen dann zusätzlich:

- jeder Aufruf der Dashboard-Schnittstelle mit den übergebenen Werten
- jeder Schreibvorgang in die Einstellungen des Regel-Scripts mit Ergebnis
- Beginn und Ende des manuellen Ladens
- Wechsel zwischen schnellem Takt (Dashboard offen) und Ruhezustand
- Versand jeder Nachricht
- bei jeder Watchdog-Runde eine Zeile je Speicher mit allen Akkupacks, zum Beispiel:
  ```
  [DEBUG] SF800: SoC 91%, 26.0C | Packs: CO1234…:91%/3.31V, BO5678…:91%/3.31V
  ```

Schalte `debug` danach wieder auf `false`. Das Log wird sonst sehr lang.

### Häufige Probleme

**Im Log steht bei „Nachrichten“ ein anderer Typ, als ich eingestellt habe.**
Das Script übernimmt Änderungen erst nach einem **Neustart** (Stop → Start). Wenn du `deploy.cmd` nutzt: Die Einstellung muss in **deiner** Config-Datei stehen, nicht im Script selbst. Prüfe außerdem, dass `notify:` im CONFIG-Block nur **einmal** vorkommt.

**Ich bekomme gar keine Nachrichten.**
Schau in die Banner-Zeile „Nachrichten“:
- `aus` bedeutet: `notify.enabled` ist `false`, oder `typ` ist unbekannt. Im zweiten Fall steht direkt darüber eine WARNUNG.
- Bei Signal/WhatsApp: Stimmen Telefonnummer (mit `+49…`) und API-Key?
- Bei Webhook: Ist die Adresse vom Shelly aus erreichbar?

Mit `debug: true` siehst du im Log, ob und wie jede Nachricht verschickt wurde.

**Ich bekomme jede Nachricht doppelt.**
Der alte Watchdog läuft noch. Stoppe ihn und schalte bei ihm „Run on startup“ aus.

**Das Dashboard zeigt einen Verbindungsfehler.**
- Läuft das Script? (Weboberfläche → Scripts)
- Stimmt im Dashboard die Adresse mit IP **und** Script-Nummer?
- Ist `api.enabled` auf `true`?

**Im Dashboard stehen nur Standardwerte, Änderungen werden nicht übernommen.**
Das Script erreicht die Einstellungen des Regel-Scripts nicht. Prüfe `api.kvsHost` und ob auf dem Regel-Shelly eine Passwort-Abfrage aktiv ist. Mit `debug: true` erscheint im Log `KVS NICHT lesbar` bzw. `KVS.Set … -> FEHLER`.

**Meldung „Report unlesbar“.**
Der Speicher hat geantwortet, aber die Daten waren unvollständig oder hatten ein unerwartetes Format. Das kommt vereinzelt vor und verschwindet meist von selbst. Bleibt es dauerhaft, hat sich eventuell nach einem Firmware-Update des Speichers dessen Datenformat geändert. Bitte dann ein Issue mit der Antwort von `http://<IP-des-Speichers>/properties/report` anlegen. Entferne vorher die Seriennummern.

**Das Morgen- und Abend-Update kommt zur falschen Zeit oder gar nicht.**
Prüfe Standort und Zeitzone in den Shelly-Einstellungen. Das Script legt beim Start zwei Zeitpläne an. Andere Zeitpläne auf dem Shelly bleiben dabei unberührt.

---

## Änderungen

### v3.1
- Debug-Ausgabe (`debug: true`) für die Dashboard-Schnittstelle: Aufrufe mit Werten, Schreibvorgänge, manuelles Laden, Nachrichtenversand
- Akkupack-Übersicht je Speicher im Debug-Log, nur bei der Watchdog-Runde
- Nachrichtentyp wird unabhängig von Groß-/Kleinschreibung erkannt. Unbekannte Typen führen zu einer Warnung.
- Alter `signal`-Block aus dem Watchdog wird erkannt
- Banner zeigt das Nachrichtenziel

### v3.0
- zenDash-API 2.7 und AkkuVolt-Watchdog 1.4 zu einem Script zusammengeführt
- eine gemeinsame Abfrage je Speicher für beide Teile
- Abfragen, Schreibvorgänge und Nachrichten laufen strikt nacheinander
- Nachrichten-Warteschlange
- Offline-Alarm nach Zeit (`offlineAlarmMin`) statt nach Anzahl Fehlversuchen, mit Entwarnung
- neue Meldungen zum Auto-Stop beim manuellen Laden
- Dashboard-Schnittstelle unverändert (API-Version 2.7)
