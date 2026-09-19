# Zendure Dashboard Proxy – Home Assistant Add-on

Dokumentation zur Einrichtung des lokalen Zendure-Dashboard-Proxys als eigenes
Add-on unter Home Assistant OS (Supervisor). Der Proxy löst das
CORS/Origin-Problem der Shelly-Firmware: der Browser spricht nur noch mit
diesem Add-on, das die Daten serverseitig vom Shelly abruft.

## Voraussetzungen

- Home Assistant OS mit Supervisor
- Zugriff auf `/addons/` per Samba-Freigabe (`\\<ha-ip>\addons`) oder SSH
- Die beiden bestehenden Dateien `zendure_proxy.py` und
  `zendure-dashboard.html`

> **Hinweis zur Benennung:** Seit Home Assistant 2026.2 heißen „Add-ons" im
> Frontend **„Apps"** (Einstellungen → Apps → App Store). Die interne
> Struktur und `config.yaml` sind unverändert. Der frühere
> „Erweiterter Modus"-Schalter im Benutzerprofil wurde ebenfalls entfernt –
> alle Funktionen (inkl. lokale Apps) sind ohne diesen Schalter direkt
> sichtbar.

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
    └── zendure-dashboard.html
```

## Dateien

### config.yaml

```yaml
name: "Zendure Dashboard Proxy"
version: "1.0.0"
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
COPY zendure-dashboard.html /zendure-dashboard.html

COPY run.sh /etc/services.d/zendure_proxy/run
RUN chmod a+x /etc/services.d/zendure_proxy/run
```

Kein eigenes `CMD`/`ENTRYPOINT` – das Skript wird als s6-Service registriert,
den `/init` (aus dem Base-Image) selbst startet.

### run.sh

```bash
#!/usr/bin/env bash
cd /
exec python3 zendure_proxy.py -q
```

**Wichtig:** Datei muss mit **LF**-Zeilenenden gespeichert sein, nicht CRLF
(siehe Troubleshooting).

## Installation

1. Ordner `zendure_proxy` mit allen sechs Dateien unter `/addons/` anlegen
   (per Samba-Freigabe oder SSH).
2. In Home Assistant: **Einstellungen → Apps → App Store** → oben rechts die
   drei Punkte → **Repositories** neu laden (ein voller HA-Neustart erzwingt
   ebenfalls einen Rescan von `/addons/`).
3. Das Add-on **„Zendure Dashboard Proxy"** erscheint im lokalen Bereich →
   auswählen → **Install** (baut das Docker-Image).
4. Starten. In der Add-on-Konfiguration **„Beim Booten starten"** und
   **„Watchdog"** aktivieren, damit der Proxy nach einem HA-Neustart
   automatisch wieder hochkommt bzw. sich nach einem Absturz selbst neu
   startet.
5. Dashboard aufrufen: `http://<ha-ip>:8000/`

**Bei Änderungen an den Add-on-Dateien** (`config.yaml`, `Dockerfile`,
`run.sh` etc.): Add-on **deinstallieren** und **neu installieren** – ein
bloßer Restart liest die geänderten Dateien nicht neu ein, es muss neu
gebaut werden.

## Troubleshooting-Log (aufgetretene Probleme & Lösungen)

| Symptom | Ursache | Lösung |
|---|---|---|
| Lokales Add-on taucht im App Store nicht auf | Store-Daten im Browser gecacht | Hard-Refresh (Strg+Shift+R) bzw. Inkognito-Fenster; Supervisor-Log zeigt bei erfolgreichem Scan `Loading apps from store: ... 1 new` |
| `s6-overlay-suexec: fatal: can only run as pid 1` | Supervisor wrapt den Container standardmäßig zusätzlich mit Docker-Init, kollidiert mit s6-Overlay als PID 1 | `init: false` in `config.yaml` setzen **und Add-on neu bauen** (nicht nur neu starten) |
| `exec: fatal: unable to exec bashio` | `run.sh` nutzte `#!/usr/bin/with-contenv bashio`, obwohl das Skript keine bashio-Funktionen braucht | Shebang auf `#!/usr/bin/env bash` ändern |
| `env: can't execute 'bash\n'` | `run.sh` mit Windows-Zeilenenden (CRLF) statt Unix (LF) gespeichert | Datei mit LF-Zeilenenden neu speichern (z. B. in VS Code unten rechts CRLF → LF umstellen) |

## Konfiguration anpassen

`SHELLY_IP` in `zendure_proxy.py` ggf. an das Netzwerk der HA-Instanz
anpassen, falls sich die IP des Shelly-Geräts ändert oder der Proxy auf
einer anderen Instanz betrieben wird.

Falls der Shelly aus dem Container heraus nicht erreichbar ist (z. B. bei
getrennten Netzwerksegmenten): in der Add-on-Netzwerkkonfiguration im
Supervisor von Bridge- auf **Host-Netzwerk** umstellen.
