# Zendure Multi-Configurator – Home Assistant App

[← zurück zur Configurator-Anleitung](../readme.md)

Der Multi-Configurator mit Upload-Helfer als eigene App (früher „Add-on“) unter
Home Assistant OS (Supervisor). Damit lassen sich die Shelly-Scripte direkt aus
Home Assistant heraus konfigurieren, hochladen und aktualisieren – ohne EXE auf
dem PC und auch vom Tablet oder Handy aus.

Es ist derselbe `zendure_local_helper.py` wie in der EXE. Die App setzt in
`run.sh` nur Umgebungsvariablen: im Netz lauschen, keinen Browser öffnen,
gemerkte IPs nach `/data`, Anfragen vom Ingress-Proxy von Home Assistant
zulassen.

Die Bedienung nach der Installation beschreibt [DOCS.md](DOCS.md) – dieselbe Seite
erscheint in Home Assistant im Reiter **Dokumentation** der App.

## Voraussetzungen

- Home Assistant OS mit Supervisor
- Zugriff auf `/addons/` per Samba-Freigabe (`\\<ha-ip>\addons`) oder SSH
- die Dateien aus [diesem Ordner](.), siehe [Verzeichnisstruktur](#verzeichnisstruktur)

> **Hinweis zur Benennung:** Seit Home Assistant 2026.2 heißen „Add-ons“ im
> Frontend **„Apps“** (Einstellungen → Apps → App Store).

## Verzeichnisstruktur

Alle Dateien liegen in einem Ordner unter `/addons/`:

```text
/addons/
└── zendure_installer/
    ├── config.yaml
    ├── build.yaml
    ├── Dockerfile
    ├── run.sh
    ├── zendure_local_helper.py
    ├── zendure-multi-configurator_multilang.html
    ├── README.md
    ├── DOCS.md
    ├── CHANGELOG.md
    └── translations/
        ├── de.yaml
        └── en.yaml
```

Die ersten sechs Dateien braucht der Bau der App. Die übrigen zeigt Home Assistant
nur an und sind optional:

| Datei | Wo sie erscheint |
|---|---|
| `README.md` | Kurzbeschreibung im App Store (Seite der App vor der Installation) |
| `DOCS.md` | Reiter **Dokumentation** der App |
| `CHANGELOG.md` | Änderungen, die Home Assistant beim Update anzeigt |
| `translations/de.yaml`, `translations/en.yaml` | Beschreibung des Ports 8787 im Reiter **Konfiguration** (Netzwerk) |

`zendure_local_helper.py` und `zendure-multi-configurator_multilang.html` sind Kopien
aus [`../local_helper/`](../local_helper/zendure_local_helper.py) bzw.
[`../`](../zendure-multi-configurator_multilang.html). Beide müssen dieselbe Version
haben: Der Helfer liest seine Versionsnummer aus der HTML.

## Installation

1. Ordner `zendure_installer` mit den Dateien aus der
   [Verzeichnisstruktur](#verzeichnisstruktur) unter `/addons/` anlegen
   (per Samba-Freigabe oder SSH). `run.sh` muss Unix-Zeilenenden (LF) haben.
2. In Home Assistant: **Einstellungen → Apps → App Store** → oben rechts die
   drei Punkte → **Repositories** neu laden (ein voller HA-Neustart erzwingt
   ebenfalls einen Rescan von `/addons/`).
3. Die App **„Zendure Multi-Configurator“** erscheint im lokalen Bereich →
   auswählen → **Install** (baut das Docker-Image).
4. Starten und **„Web-UI öffnen“** wählen. Optional **„In Seitenleiste anzeigen“**
   einschalten.

Anders als der Dashboard-Proxy muss die App nicht dauerhaft laufen. Sie startet
deshalb nicht automatisch mit Home Assistant (`boot: manual`); zum Einrichten oder
Aktualisieren starten, danach stoppen.

Ob die gemerkten IPs am richtigen Ort liegen, zeigt das Protokoll der App nach dem
ersten Upload: Dort muss `-> IP gemerkt in /data/zendure_helper_config.json` stehen.

## Änderungen an den App-Dateien

Bei Änderungen an den App-Dateien muss die App neu gebaut werden – ein bloßer
Restart liest die geänderten Dateien nicht neu ein.

1. Geänderte Dateien in `/addons/zendure_installer/` ablegen.
2. In `config.yaml` die `version` anheben – bei neuer Configurator-Version die ersten
   drei Stellen (z. B. `2.9.0.0` → `2.10.0.0`), bei Änderungen nur an der App die
   vierte (z. B. `2.9.0.0` → `2.9.0.1`).
3. **Repositories** im App Store neu laden (wie Installationsschritt 2).
4. Auf der Seite der App erscheint **Aktualisieren** → ausführen. `/data` bleibt
   erhalten.

**Nicht** deinstallieren – das löscht `/data` und damit die gemerkten IPs.

## Wie der Zugriff geprüft wird

Der Helfer prüft bei jeder Anfrage den `Origin`-Header des Browsers, damit keine
fremde Webseite Scripte auf die Shellys schreiben kann. In der App gilt:

| Zugriff | Erlaubt, weil |
|---|---|
| „Web-UI öffnen“ (Ingress) | Anfrage kommt vom Ingress-Proxy `172.30.32.2`, Home Assistant hat den Benutzer angemeldet (`ZENDURE_HELPER_TRUSTED_PEERS`) |
| `http://<ha-ip>:8787/` (nur mit freigegebenem Port) | Seite und Helfer auf demselben Origin; nur mit IP-Adresse, nicht mit Hostnamen (Schutz vor DNS-Rebinding) |
| Anfragen ohne `Origin` (curl, Scripte) | wie bei der EXE |

Der Configurator erkennt am Meta-Tag `zendure-helper`, das der Helfer beim
Ausliefern der Seite einfügt, dass er den Helfer relativ ansprechen soll – das
funktioniert auch unter dem Pfad-Präfix des Ingress.

## Troubleshooting

| Symptom | Ursache | Lösung |
|---|---|---|
| Lokale App taucht im App Store nicht auf | Store-Daten im Browser gecacht | Hard-Refresh (Strg+Shift+R) bzw. Inkognito-Fenster |
| `env: can't execute 'bash\r'` | `run.sh` mit Windows-Zeilenenden (CRLF) gespeichert | Datei mit LF-Zeilenenden neu speichern |
| `s6-overlay-suexec: fatal: can only run as pid 1` | Docker-Init kollidiert mit s6-Overlay | `init: false` in `config.yaml` **und App neu bauen** |
| Direkt-Upload wird nicht angeboten | alte HTML ohne Meta-Tag-Erkennung, oder Helfer- und HTML-Version passen nicht | beide Dateien aus diesem Ordner verwenden, App aktualisieren |
| „origin not allowed“ im Protokoll | Zugriff über freigegebenen Port mit Hostnamen (z. B. `homeassistant.local:8787`) | über „Web-UI öffnen“ oder mit IP-Adresse aufrufen |
| „Shelly nicht erreichbar“ | falsche IP, oder der Container erreicht das Netz des Shelly nicht | IP prüfen; bei getrennten Netzsegmenten siehe unten |

## Netzwerk

Falls der Shelly aus dem Container heraus nicht erreichbar ist (z. B. bei
getrennten Netzwerksegmenten): in der App-Netzwerkkonfiguration im
Supervisor von Bridge- auf **Host-Netzwerk** umstellen.

## Sicherheit

Der Helfer kann Scripte auf jeden Shelly im Heimnetz schreiben und löschen.
Deshalb ist Port 8787 standardmäßig aus. Wird er freigegeben, gibt es keinen
Passwortschutz – nur bei Bedarf einschalten, danach wieder aus, und **nie** per
Portweiterleitung ins Internet freigeben.
