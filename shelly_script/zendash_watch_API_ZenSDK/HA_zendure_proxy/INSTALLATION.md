# Zendure Dashboard Proxy – Home Assistant App

[← zurück zu Dashboard einrichten](../dashboard.md)

Dokumentation zur Einrichtung des Zendure-Dashboard-Proxys als eigene App
(früher „Add-on“) unter Home Assistant OS (Supervisor). Der Proxy löst das
CORS/Origin-Problem der Shelly-Firmware: Der Browser spricht nur noch mit
dieser App, die die Daten serverseitig vom Shelly abruft.

Es ist derselbe `zendure_proxy.py` wie auf PC, Synology oder als EXE –
unverändert. Shelly-IP und Script-ID werden **nicht** im Script eingetragen,
sondern nach dem Start im Browser auf der Einrichtungsseite. Einziger
Unterschied: `run.sh` legt die Einstellungen im dauerhaften App-Speicher
`/data` ab, damit sie Updates der App überstehen.

Optional sendet die App die Messwerte jede Minute an ThingSpeak und/oder
ThingsBoard, siehe [ThingSpeak- und ThingsBoard-Upload](#thingspeak--und-thingsboard-upload).

Die Bedienung nach der Installation beschreibt [DOCS.md](DOCS.md) – dieselbe Seite
erscheint in Home Assistant im Reiter **Dokumentation** der App.

## Voraussetzungen

- Home Assistant OS mit Supervisor
- IP-Adresse des **Dashboard-Shelly** (auf dem zenDash-API + Watchdog läuft) und die
  **Script-Nummer** dieses Scripts (über den Configurator hochgeladen heißt es `zd`) – beides wird erst nach der Installation
  gebraucht

> **Hinweis zur Benennung:** Seit Home Assistant 2026.2 heißen „Add-ons“ im
> Frontend **„Apps“** (Einstellungen → Apps → App Store).

## Installation

[![Repository zu Home Assistant hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsurfer1264%2Fha-zendure-apps)

1. Auf den Knopf oben klicken und das Repository in Home Assistant hinzufügen.
   Oder von Hand: **Einstellungen → Apps → App Store** → oben rechts die drei
   Punkte → **Repositories** → `https://github.com/surfer1264/ha-zendure-apps`
   eintragen → **Hinzufügen**.
2. Die App **„Zendure Dashboard Proxy“** erscheint im App Store im Bereich
   **Zendure Apps (surfer1264)** → auswählen → **Installieren** (baut das
   Docker-Image).
3. Starten. In der App-Konfiguration **„Beim Booten starten“** und
   **„Watchdog“** aktivieren, damit der Proxy nach einem HA-Neustart
   automatisch wieder hochkommt bzw. sich nach einem Absturz selbst neu
   startet. Siehe Bild 1.
4. **„Web-UI öffnen“** wählen oder im Browser `http://<ha-ip>:8000/` aufrufen. Beim ersten Mal erscheint die
   **Einrichtungsseite**.
5. **Shelly-IP** (Dashboard-Shelly, nicht Controller-Shelly) und
   **Script-ID** eintragen → **„Speichern & testen“**. Der Proxy prüft
   sofort, ob unter dieser Adresse das API-Script antwortet, und leitet bei
   Erfolg zum Dashboard weiter.

Ab jetzt ist das Dashboard unter `http://<ha-ip>:8000/` von jedem Gerät im
Heimnetz erreichbar.

Ob die Einstellungen am richtigen Ort liegen, zeigt die Startübersicht im Log
der App: Dort muss `Konfig: /data/zendure_proxy_config.json` stehen.

Dasselbe Repository enthält auch den
[Zendure Multi-Configurator](../../Multiconfigurator/HA_zendure_installer/INSTALLATION.md).

----

**Bild 1: Nach Installation**

<img width="400" alt="image" src="https://github.com/user-attachments/assets/cb24431a-f998-4aee-ac1b-1aa81445240d" />

----

## Updates

Home Assistant sucht selbst nach neuen Versionen. Gibt es eine, erscheint auf der
Seite der App **Aktualisieren** (und unter **Einstellungen** ein Hinweis). Sofort
prüfen lässt es sich im App Store über die drei Punkte → **Nach Updates suchen**.

Das ist nach jedem Script-Update nötig, denn Dashboard-Seite und Script
müssen dieselbe Versionsnummer haben.

Beim Update bleibt `/data` erhalten. **Nicht** deinstallieren – das löscht
`/data` und damit Shelly-IP sowie ThingSpeak- und ThingsBoard-Zugangsdaten.

## Umstieg von der lokalen App

Wer die App bisher aus einem Ordner unter `/addons/` installiert hatte: Für Home
Assistant sind die lokale App und die App aus dem Repository zwei verschiedene
Apps. Die Einstellungen in `/data` werden **nicht** übernommen.

1. Vorher notieren: Shelly-IP und Script-ID (Seite `/setup`), bei Bedarf die
   Zugangsdaten für ThingSpeak bzw. ThingsBoard.
2. Die lokale App **deinstallieren** und den Ordner `/addons/zendure_proxy/`
   löschen, sonst steht die App zweimal im App Store. Beide Apps zugleich
   laufen lassen geht ohnehin nicht – sie belegen denselben Port 8000.
3. Wie unter [Installation](#installation) beschrieben aus dem Repository
   installieren und die notierten Werte wieder eintragen.

## Aufbau der App

Die App liegt im Repository
[ha-zendure-apps](https://github.com/surfer1264/ha-zendure-apps) im Ordner
`zendure_proxy/`. Das Repository wird bei jeder Änderung automatisch aus
[diesem Ordner](.) gespiegelt – gepflegt wird nur hier.

```text
zendure_proxy/
    ├── config.yaml
    ├── build.yaml
    ├── Dockerfile
    ├── run.sh
    ├── zendure_proxy.py
    ├── ts_bridge.py
    ├── zendure-dashboard.html
    ├── zendure-dashboard-b.html
    ├── README.md
    ├── DOCS.md
    ├── CHANGELOG.md
    └── translations/
        ├── de.yaml
        └── en.yaml
```

Die ersten acht Dateien braucht der Bau der App. Die übrigen zeigt Home Assistant
nur an und sind optional:

| Datei | Wo sie erscheint |
|---|---|
| `README.md` | Kurzbeschreibung im App Store (Seite der App vor der Installation) |
| `DOCS.md` | Reiter **Dokumentation** der App |
| `CHANGELOG.md` | Änderungen, die Home Assistant beim Update anzeigt |
| `translations/de.yaml`, `translations/en.yaml` | Beschreibung des Ports 8000 im Reiter **Konfiguration** (Netzwerk). Home Assistant liest sie nur aus dem Unterordner `translations/`. |

`zendure-dashboard.html` ist das (neue) Standard-Layout, `zendure-dashboard-b.html` das bisherige
Layout des Dashboards (gleiche Funktionen), erreichbar unter `http://<ha-ip>:8000/b`.

`ts_bridge.py` ist nur für den [ThingSpeak- bzw. ThingsBoard-Upload](#thingspeak--und-thingsboard-upload) nötig.
Fehlt die Datei, läuft der Proxy ganz normal, nur ohne ThingSpeak und ThingsBoard. Die
`COPY`-Zeile im `Dockerfile` braucht sie aber – ohne Upload diese Zeile
dort entfernen, sonst bricht der Bau ab.

## Dateien

### config.yaml

```yaml
name: "Zendure Dashboard Proxy"
version: "3.5.9.6"
slug: "zendure_proxy"
description: "Lokaler Proxy für das Zendure-Dashboard (löst CORS-Problem der Shelly-Firmware)"
url: "https://github.com/surfer1264/Zendure-Stuff/tree/main/shelly_script/zendash_watch_API_ZenSDK"
ingress: true
ingress_port: 8000
panel_icon: mdi:solar-power-variant
arch:
  - aarch64
  - amd64
  - armv7
startup: application
boot: auto
init: false
ports:
  8000/tcp: 8000
ports_description:
  8000/tcp: "Zendure Dashboard"
```

`init: false` ist entscheidend (siehe Troubleshooting weiter unten).

`ingress: true` sorgt für den Knopf **„Web-UI öffnen“** auf der Seite der App:
Das Dashboard öffnet sich dann innerhalb von Home Assistant, unter derselben
Adresse wie Home Assistant selbst – auch von unterwegs (z. B. über Nabu Casa) und
mit der Anmeldung von Home Assistant. Auf der Seite der App lässt es sich mit
**„In Seitenleiste anzeigen“** zusätzlich in die Seitenleiste legen
(`panel_icon` ist das Symbol dort). `ingress_port` ist der Port, auf dem der
Proxy im Container lauscht. Der direkte Zugang über `http://<ha-ip>:8000/`
(`ports`) bleibt daneben bestehen.

`url` sorgt für den Link zum Projekt. Der Knopf erscheint nur, solange die App
läuft. Werden `ingress` oder `url` nachträglich eingetragen, übernimmt Home
Assistant sie erst nach einem Update mit höherer `version` (siehe
[Änderungen an den App-Dateien](#änderungen-an-den-app-dateien)).

> Bis 3.5.9.5 stand hier `webui: "http://[HOST]:[PORT:8000]/"`. Der Knopf öffnete
> dann `http://<Name, unter dem HA geöffnet ist>:8000/`. Bei `homeassistant.local`
> löst das oft auf eine IPv6-Adresse auf, unter der der Proxy nicht erreichbar ist.

Die ersten drei Stellen der `version` folgen der Versionsnummer des Dashboards,
die vierte zählt Änderungen an der App selbst (z. B. `3.5.9.5`). Die Version bei
jeder Änderung an den App-Dateien anheben – dann bietet Home
Assistant ein Update an, und die Einstellungen bleiben erhalten (siehe
[Änderungen an den App-Dateien](#änderungen-an-den-app-dateien)).

### build.yaml

```yaml
build_from:
  aarch64: "ghcr.io/home-assistant/aarch64-base:3.19"
  amd64: "ghcr.io/home-assistant/amd64-base:3.19"
  armv7: "ghcr.io/home-assistant/armv7-base:3.19"
```

> Aktuell werden offiziell nur noch Alpine 3.21–3.23 als nicht-EOL geführt.
> Falls künftig Build-Probleme auftreten, die Versionsnummern hier
> entsprechend anheben.

### Dockerfile

```dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3

COPY zendure_proxy.py /zendure_proxy.py
COPY ts_bridge.py /ts_bridge.py
COPY zendure-dashboard.html /zendure-dashboard.html
COPY zendure-dashboard-b.html /zendure-dashboard-b.html

COPY run.sh /etc/services.d/zendure_proxy/run
RUN chmod a+x /etc/services.d/zendure_proxy/run
```

Kein eigenes `CMD`/`ENTRYPOINT` – das Skript wird als s6-Service registriert,
den `/init` (aus dem Base-Image) selbst startet.

Proxy und HTML liegen im Container im selben Ordner (`/`), der Proxy findet
die Seite dort automatisch.

### run.sh

```bash
#!/usr/bin/env bash
cd /
# Einstellungen (Shelly-IP, ThingSpeak-Keys) nach /data - nur das
# uebersteht Updates der App.
export ZENDURE_DATA_DIR=/data
exec python3 zendure_proxy.py -q
```

`ZENDURE_DATA_DIR=/data` legt `zendure_proxy_config.json`,
`zendure_thingspeak_config.json` und `zendure_thingsboard_config.json` in den
dauerhaften Speicher der App.
`/data` bekommt jede App von Home Assistant automatisch, in der `config.yaml`
ist dafür nichts einzutragen. Ohne diese Zeile landen die Einstellungen im
Container selbst und gehen bei jedem Neubau verloren.

`-q` schaltet das Zugriffsprotokoll ab; die Startübersicht erscheint weiterhin
im Log der App. Einen Browser versucht der Proxy im Container nicht zu öffnen.

**Wichtig:** Datei muss mit **LF**-Zeilenenden gespeichert sein, nicht CRLF
(siehe Troubleshooting).

## Einstellungen ändern

Ändert sich die IP des Shelly oder die Script-Nummer (z. B. wenn das Script neu
angelegt wurde – beim Update über den Configurator bleibt sie gleich), einfach

```
http://<ha-ip>:8000/setup
```

aufrufen und die neuen Werte eintragen. Die App muss dafür weder neu gebaut
noch neu gestartet werden.

Die Einstellungen liegen in `/data/zendure_proxy_config.json`, dem dauerhaften
Speicher der App. Sie überstehen Neustarts der App und von Home Assistant
sowie Updates der App. Verloren gehen sie nur, wenn die App **deinstalliert**
wird – Home Assistant löscht dabei auch `/data`. Nach einer Neuinstallation
erscheint deshalb wieder die Einrichtungsseite – einfach Schritt 5
wiederholen.

## Änderungen an den App-Dateien

**Bei Änderungen an den App-Dateien** (`config.yaml`, `Dockerfile`,
`run.sh`, `zendure_proxy.py`, `ts_bridge.py`, `zendure-dashboard.html` usw.)
muss die App neu gebaut werden – ein bloßer Restart liest die geänderten
Dateien nicht neu ein. Der Container enthält eine eigene Kopie.

### Neue Version veröffentlichen

Für Änderungen an der App selbst (hier im Repository Zendure-Stuff):

1. Dateien in [diesem Ordner](.) ändern.
2. In `config.yaml` die `version` anheben – bei neuer Dashboard-Version die ersten drei Stellen (z. B. `3.5.9.5` → `3.6.0.0`), bei Änderungen nur an der App die vierte (z. B. `3.5.9.5` → `3.5.9.6`). Ohne höhere `version` bietet Home Assistant kein Update an.
3. `CHANGELOG.md` ergänzen und auf `main` pushen. Der Workflow
   [HA-Apps spiegeln](https://github.com/surfer1264/Zendure-Stuff/blob/main/.github/workflows/mirror-ha-apps.yml)
   überträgt den Ordner nach `ha-zendure-apps`. Danach bekommen alle Nutzer
   das Update angeboten (siehe [Updates](#updates)).

### Lokale Installation (zum Testen)

Zum Ausprobieren von Änderungen vor dem Veröffentlichen lässt sich die App auch
aus einem Ordner unter `/addons/` installieren (Zugriff per Samba-Freigabe
`\\<ha-ip>\addons` oder SSH). Nicht gleichzeitig mit der App aus dem Repository
nutzen – beide belegen Port 8000.

1. Ordner `/addons/zendure_proxy/` mit den Dateien aus dem
   [Aufbau der App](#aufbau-der-app) anlegen.
2. In Home Assistant: **Einstellungen → Apps → App Store** → oben rechts die
   drei Punkte → **Repositories** neu laden (ein voller HA-Neustart erzwingt
   ebenfalls einen Rescan von `/addons/`). Siehe Bild 2.
3. Die App erscheint im lokalen Bereich → auswählen → **Installieren**, weiter
   wie unter [Installation](#installation) ab Schritt 3.

Bei Änderungen: Dateien in `/addons/zendure_proxy/` ablegen, `version`
anheben, **Repositories** neu laden, auf der Seite der App **Aktualisieren**.
Nur der Austausch der Dateien im Ordner bewirkt gar nichts.

**Bild 2: Lokale App vor der Installation**

<img width="400" alt="image" src="https://github.com/user-attachments/assets/1f669708-a57e-4e73-a7d0-69d4192b50d7" />

**Einmalig beim Umstieg von Version 1.0.x:** Dort lagen die Einstellungen
noch im Container. Nach dem ersten Update auf 1.1.0 erscheint deshalb einmal
die Einrichtungsseite – Schritt 5 der Installation wiederholen. Ab dann
bleiben die Einstellungen erhalten.

## ThingSpeak- und ThingsBoard-Upload

Die App kann die Messwerte der Speicher jede Minute an ThingSpeak und/oder
ThingsBoard senden. Einrichtung und Verhalten stehen ausführlich unter
[ThingSpeak-Upload](../thingspeak.md) und [ThingsBoard-Upload](../thingsboard.md).
Für die App gilt zusätzlich:

- `ts_bridge.py` muss im App-Ordner liegen und im `Dockerfile` kopiert werden.
- Die Einrichtungsseiten sind `http://<ha-ip>:8000/thingspeak` und
  `http://<ha-ip>:8000/thingsboard`.
- Die Zugangsdaten liegen in `/data/zendure_thingspeak_config.json` bzw.
  `/data/zendure_thingsboard_config.json` und überstehen Updates wie die
  übrigen Einstellungen.
- Wegen `-q` erscheinen im Log der App keine Erfolgsmeldungen, nur Fehler.
  Ob Werte ankommen, siehst du direkt im ThingSpeak-Channel bzw. in ThingsBoard.
  Für ThingsBoard zeigt außerdem `/thingsboard` oben, wie viele Datenpunkte heute
  gesendet wurden.
- Home Assistant braucht Internetzugang zu `api.thingspeak.com` bzw. zum
  ThingsBoard-Server (bei eigenem Server im Heimnetz entfällt das). Der Shelly
  und die Zendure-Geräte nicht.

## Troubleshooting-Log (aufgetretene Probleme & Lösungen)

| Symptom | Ursache | Lösung |
|---|---|---|
| App taucht nach dem Hinzufügen des Repositorys nicht auf | Store-Daten im Browser gecacht | im App Store über die drei Punkte **Nach Updates suchen**, dann Hard-Refresh (Strg+Shift+R) bzw. Inkognito-Fenster; Supervisor-Log zeigt bei erfolgreichem Scan `Loading apps from store: ... new` |
| App steht zweimal im App Store | lokale App unter `/addons/` und App aus dem Repository | siehe [Umstieg von der lokalen App](#umstieg-von-der-lokalen-app) |
| Kein Update angeboten, obwohl neue Version auf GitHub | `version` in `config.yaml` nicht angehoben, oder Home Assistant hat noch nicht nachgesehen | im App Store **Nach Updates suchen** |
| `s6-overlay-suexec: fatal: can only run as pid 1` | Supervisor wrapt den Container standardmäßig zusätzlich mit Docker-Init, kollidiert mit s6-Overlay als PID 1 | `init: false` in `config.yaml` setzen **und App neu bauen** (nicht nur neu starten) |
| `exec: fatal: unable to exec bashio` | `run.sh` nutzte `#!/usr/bin/with-contenv bashio`, obwohl das Skript keine bashio-Funktionen braucht | Shebang auf `#!/usr/bin/env bash` ändern |
| `env: can't execute 'bash\r'` | `run.sh` mit Windows-Zeilenenden (CRLF) statt Unix (LF) gespeichert | Datei mit LF-Zeilenenden neu speichern (z. B. in VS Code unten rechts CRLF → LF umstellen) |
| Statt des Dashboards erscheint die Einrichtungsseite | App wurde deinstalliert und neu installiert (löscht `/data`), oder erster Start nach dem Umstieg von 1.0.x | Normal – IP und Script-ID erneut eintragen. Künftig per Update statt Deinstallation aktualisieren |
| Einstellungen gehen nach jedem Update verloren | `run.sh` setzt `ZENDURE_DATA_DIR` nicht, Startübersicht zeigt `Konfig: /zendure_proxy_config.json` | `run.sh` aus diesem Ordner verwenden und App aktualisieren |
| Startübersicht zeigt `Cloud-Upload: nicht verfuegbar (ts_bridge.py fehlt)` | `ts_bridge.py` fehlt im Container | Datei in den App-Ordner legen, `COPY ts_bridge.py` im `Dockerfile` prüfen, App aktualisieren |
| Bau der App bricht mit `COPY failed` ab | `Dockerfile` kopiert eine Datei, die im App-Ordner fehlt (meist `ts_bridge.py`) | Datei ablegen – oder ohne Cloud-Upload die `COPY`-Zeile für `ts_bridge.py` entfernen |
| Kein Knopf „Web-UI öffnen“ | App läuft nicht, oder `ingress` wurde in `config.yaml` ergänzt, ohne die `version` anzuheben | App starten; sonst `version` anheben, Repositories neu laden, App aktualisieren |
| „Web-UI öffnen“ führt auf `http://homeassistant.local:8000` und lädt nicht | alte `config.yaml` mit `webui` statt `ingress`; der Name löst auf IPv6 auf, der Proxy lauscht nur auf IPv4 | `config.yaml` aus diesem Ordner verwenden, App aktualisieren |
| Port 8000 hat im Reiter Konfiguration keine Beschreibung | `de.yaml`/`en.yaml` liegen nicht im Unterordner `translations/` | Dateien nach `translations/` verschieben, App aktualisieren |
| „Speichern & testen“ meldet „Shelly nicht erreichbar“ | falsche IP, oder der Container erreicht das Netz des Shelly nicht | IP prüfen (Test im Browser: `http://<shelly-ip>/script/<id>/status_api`); bei getrennten Netzsegmenten siehe unten |
| „Speichern & testen“ meldet eine falsche Antwort bzw. Status 404 | falsche Script-ID | Script-ID in der Shelly-Weboberfläche unter **Scripts** nachsehen |

## Netzwerk

Falls der Shelly aus dem Container heraus nicht erreichbar ist (z. B. bei
getrennten Netzwerksegmenten): in der App-Netzwerkkonfiguration im
Supervisor von Bridge- auf **Host-Netzwerk** umstellen.

## Sicherheit

Das Dashboard und die Einrichtungsseiten `/setup`, `/thingspeak` und `/thingsboard` haben keinen Passwortschutz.
Jeder im Heimnetz, der die Adresse kennt, kann Einstellungen ändern. Port 8000
deshalb **nie** per Portweiterleitung ins Internet freigeben.
