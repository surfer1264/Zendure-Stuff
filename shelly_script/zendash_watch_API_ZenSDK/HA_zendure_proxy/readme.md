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

Optional sendet die App die Messwerte jede Minute an ThingSpeak, siehe
[ThingSpeak-Upload](#thingspeak-upload).

## Voraussetzungen

- Home Assistant OS mit Supervisor
- Zugriff auf `/addons/` per Samba-Freigabe (`\\<ha-ip>\addons`) oder SSH
- alle sieben Dateien aus [diesem Ordner](.) (`config.yaml`, `build.yaml`, `Dockerfile`, `run.sh`, `zendure_proxy.py`, `ts_bridge.py`, `zendure-dashboard.html`)
- IP-Adresse des **Dashboard-Shelly** (auf dem zenDash-API + Watchdog läuft) und die
  **Script-Nummer** dieses Scripts (über den Configurator hochgeladen heißt es `zd`) – beides wird erst nach der Installation
  gebraucht

> **Hinweis zur Benennung:** Seit Home Assistant 2026.2 heißen „Add-ons“ im
> Frontend **„Apps“** (Einstellungen → Apps → App Store).

## Verzeichnisstruktur

Alle Dateien liegen in einem Ordner unter `/addons/`:

```
/addons/
└── zendure_proxy/
    ├── config.yaml
    ├── build.yaml
    ├── Dockerfile
    ├── run.sh
    ├── zendure_proxy.py
    ├── ts_bridge.py
    └── zendure-dashboard.html
```

`ts_bridge.py` ist nur für den [ThingSpeak-Upload](#thingspeak-upload) nötig.
Fehlt die Datei, läuft der Proxy ganz normal, nur ohne ThingSpeak. Die
`COPY`-Zeile im `Dockerfile` braucht sie aber – ohne ThingSpeak diese Zeile
dort entfernen, sonst bricht der Bau ab.

## Dateien

### config.yaml

```yaml
name: "Zendure Dashboard Proxy"
version: "1.1.0"
slug: "zendure_proxy"
description: "Lokaler Proxy für das Zendure-Dashboard (löst CORS-Problem der Shelly-Firmware)"
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

`version` bei jeder Änderung an den App-Dateien anheben – dann bietet Home
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

`ZENDURE_DATA_DIR=/data` legt `zendure_proxy_config.json` und
`zendure_thingspeak_config.json` in den dauerhaften Speicher der App.
`/data` bekommt jede App von Home Assistant automatisch, in der `config.yaml`
ist dafür nichts einzutragen. Ohne diese Zeile landen die Einstellungen im
Container selbst und gehen bei jedem Neubau verloren.

`-q` schaltet das Zugriffsprotokoll ab; die Startübersicht erscheint weiterhin
im Log der App. Einen Browser versucht der Proxy im Container nicht zu öffnen.

**Wichtig:** Datei muss mit **LF**-Zeilenenden gespeichert sein, nicht CRLF
(siehe Troubleshooting).

## Installation

1. Ordner `zendure_proxy` mit allen sieben Dateien unter `/addons/` anlegen
   (per Samba-Freigabe oder SSH).
2. In Home Assistant: **Einstellungen → Apps → App Store** → oben rechts die
   drei Punkte → **Repositories** neu laden (ein voller HA-Neustart erzwingt
   ebenfalls einen Rescan von `/addons/`). Siehe Bild 1.
3. Die App **„Zendure Dashboard Proxy“** erscheint im lokalen Bereich →
   auswählen → **Install** (baut das Docker-Image).
4. Starten. In der App-Konfiguration **„Beim Booten starten“** und
   **„Watchdog“** aktivieren, damit der Proxy nach einem HA-Neustart
   automatisch wieder hochkommt bzw. sich nach einem Absturz selbst neu
   startet. Siehe Bild 2.
5. Im Browser `http://<ha-ip>:8000/` aufrufen. Beim ersten Mal erscheint die
   **Einrichtungsseite**.
6. **Shelly-IP** (Dashboard-Shelly, nicht Controller-Shelly) und
   **Script-ID** eintragen → **„Speichern & testen“**. Der Proxy prüft
   sofort, ob unter dieser Adresse das API-Script antwortet, und leitet bei
   Erfolg zum Dashboard weiter.

Ab jetzt ist das Dashboard unter `http://<ha-ip>:8000/` von jedem Gerät im
Heimnetz erreichbar.

Ob die Einstellungen am richtigen Ort liegen, zeigt die Startübersicht im Log
der App: Dort muss `Konfig: /data/zendure_proxy_config.json` stehen.

----

**Bild 1: Vor Installation**

<img width="400" alt="image" src="https://github.com/user-attachments/assets/1f669708-a57e-4e73-a7d0-69d4192b50d7" />

**Bild 2: Nach Installation**

<img width="400" alt="image" src="https://github.com/user-attachments/assets/cb24431a-f998-4aee-ac1b-1aa81445240d" />

---

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
erscheint deshalb wieder die Einrichtungsseite – einfach Schritt 6
wiederholen.

## Änderungen an den App-Dateien

**Bei Änderungen an den App-Dateien** (`config.yaml`, `Dockerfile`,
`run.sh`, `zendure_proxy.py`, `ts_bridge.py`, `zendure-dashboard.html` usw.)
muss die App neu gebaut werden – ein bloßer Restart liest die geänderten
Dateien nicht neu ein. Der Container enthält eine eigene Kopie; nur der
Austausch der Datei im Ordner `/addons/zendure_proxy/` bewirkt gar nichts.

Das ist nach jedem Script-Update nötig, denn Dashboard-Seite und Script
müssen dieselbe Versionsnummer haben.

So geht es, ohne die Einstellungen zu verlieren:

1. Geänderte Dateien in `/addons/zendure_proxy/` ablegen.
2. In `config.yaml` die `version` anheben (z. B. `1.1.0` → `1.1.1`).
3. **Repositories** im App Store neu laden (wie Installationsschritt 2).
4. Auf der Seite der App erscheint **Aktualisieren** → ausführen. Home
   Assistant baut die App neu, `/data` bleibt erhalten.

**Nicht** deinstallieren – das löscht `/data` und damit Shelly-IP und
ThingSpeak-Keys.

**Einmalig beim Umstieg von Version 1.0.x:** Dort lagen die Einstellungen
noch im Container. Nach dem ersten Update auf 1.1.0 erscheint deshalb einmal
die Einrichtungsseite – Schritt 6 wiederholen. Ab dann bleiben die
Einstellungen erhalten.

## ThingSpeak-Upload

Die App kann die Messwerte der Speicher jede Minute an ThingSpeak senden.
Einrichtung und Verhalten stehen ausführlich unter
[ThingSpeak-Upload](../thingspeak.md). Für die App gilt zusätzlich:

- `ts_bridge.py` muss im App-Ordner liegen und im `Dockerfile` kopiert werden.
- Die Einrichtungsseite ist `http://<ha-ip>:8000/thingspeak`.
- Die Keys liegen in `/data/zendure_thingspeak_config.json` und überstehen
  Updates wie die übrigen Einstellungen.
- Wegen `-q` erscheinen im Log der App keine Erfolgsmeldungen, nur Fehler.
  Ob Werte ankommen, siehst du direkt im ThingSpeak-Channel.
- Home Assistant braucht Internetzugang zu `api.thingspeak.com`. Der Shelly
  und die Zendure-Geräte nicht.

## Troubleshooting-Log (aufgetretene Probleme & Lösungen)

| Symptom | Ursache | Lösung |
|---|---|---|
| Lokale App taucht im App Store nicht auf | Store-Daten im Browser gecacht | Hard-Refresh (Strg+Shift+R) bzw. Inkognito-Fenster; Supervisor-Log zeigt bei erfolgreichem Scan `Loading apps from store: ... 1 new` |
| `s6-overlay-suexec: fatal: can only run as pid 1` | Supervisor wrapt den Container standardmäßig zusätzlich mit Docker-Init, kollidiert mit s6-Overlay als PID 1 | `init: false` in `config.yaml` setzen **und App neu bauen** (nicht nur neu starten) |
| `exec: fatal: unable to exec bashio` | `run.sh` nutzte `#!/usr/bin/with-contenv bashio`, obwohl das Skript keine bashio-Funktionen braucht | Shebang auf `#!/usr/bin/env bash` ändern |
| `env: can't execute 'bash\r'` | `run.sh` mit Windows-Zeilenenden (CRLF) statt Unix (LF) gespeichert | Datei mit LF-Zeilenenden neu speichern (z. B. in VS Code unten rechts CRLF → LF umstellen) |
| Statt des Dashboards erscheint die Einrichtungsseite | App wurde deinstalliert und neu installiert (löscht `/data`), oder erster Start nach dem Umstieg von 1.0.x | Normal – IP und Script-ID erneut eintragen. Künftig per Update statt Deinstallation aktualisieren |
| Einstellungen gehen nach jedem Update verloren | `run.sh` setzt `ZENDURE_DATA_DIR` nicht, Startübersicht zeigt `Konfig: /zendure_proxy_config.json` | `run.sh` aus diesem Ordner verwenden und App aktualisieren |
| Startübersicht zeigt `ThingSpeak: nicht verfuegbar` | `ts_bridge.py` fehlt im Container | Datei in den App-Ordner legen, `COPY ts_bridge.py` im `Dockerfile` prüfen, App aktualisieren |
| Bau der App bricht mit `COPY failed` ab | `Dockerfile` kopiert `ts_bridge.py`, die Datei fehlt aber im App-Ordner | Datei ablegen – oder ohne ThingSpeak die `COPY`-Zeile entfernen |
| „Speichern & testen“ meldet „Shelly nicht erreichbar“ | falsche IP, oder der Container erreicht das Netz des Shelly nicht | IP prüfen (Test im Browser: `http://<shelly-ip>/script/<id>/status_api`); bei getrennten Netzsegmenten siehe unten |
| „Speichern & testen“ meldet eine falsche Antwort bzw. Status 404 | falsche Script-ID | Script-ID in der Shelly-Weboberfläche unter **Scripts** nachsehen |

## Netzwerk

Falls der Shelly aus dem Container heraus nicht erreichbar ist (z. B. bei
getrennten Netzwerksegmenten): in der App-Netzwerkkonfiguration im
Supervisor von Bridge- auf **Host-Netzwerk** umstellen.

## Sicherheit

Das Dashboard und die Einrichtungsseiten `/setup` und `/thingspeak` haben keinen Passwortschutz.
Jeder im Heimnetz, der die Adresse kennt, kann Einstellungen ändern. Port 8000
deshalb **nie** per Portweiterleitung ins Internet freigeben.
