<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

# Controller – Getting Started

Der Controller (`zerooutput_multi_kvs`) ist das Regel-Script auf deinem **Controller-Shelly**. Er misst deinen Netzbezug und verteilt Laden und Entladen so auf deine Zendure-Speicher, dass möglichst nichts aus dem Netz kommt und nichts ungenutzt ins Netz geht.

Diese Seite bringt dich zum **ersten funktionierenden Lauf**. Alles Weitere steht in der [Benutzerdokumentation](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-SMDC-‐-Benutzerdokumentation) und der [Gesamtdokumentation](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController) im Wiki. Was sich zuletzt geändert hat, steht im [Changelog](CHANGELOG.md).


---

## Checkliste, bevor du anfängst

- [ ] **Zwei Shellys** Gen2 oder neuer mit Script-Funktion ([kompatible Geräte](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#3-voraussetzungen)) – einer für den Controller, einer für zenDash-API + Watchdog. Der Controller läuft immer **allein** auf seinem Shelly.
- [ ] **Speicher mit zenSDK** (ab SolarFlow 800) im selben Netz, am besten mit fester IP-Adresse (im Router einstellen).
- [ ] **Wichtig:** Die Speicher in der Zendure-App aus dem **HEMS** (Home Energy Management System) entfernen – sonst schickt die Cloud parallel eigene Steuerbefehle. Ausnahme Zendure Smart Meter D0: Dessen lokale Schnittstelle wird einmalig über HEMS freigeschaltet. Das betrifft nur den Zähler, die Speicher bleiben trotzdem aus dem HEMS draußen.
- [ ] Ein **Smartmeter** für den Netzbezug. Am einfachsten: Der Controller läuft direkt auf einem Shelly Pro 3EM.

---

## Einrichten mit dem Configurator (empfohlen)

1. **[Helfer herunterladen](https://github.com/surfer1264/Zendure-Stuff/releases/latest)** und starten. Der Configurator öffnet sich im Browser.
2. **„Neu konfigurieren“** wählen und die Fragen beantworten: Speicher, Netzquelle, Benachrichtigungen, Regelparameter.
3. Im Ergebnis **„⚡ Direkt hochladen“**. Das Script landet auf dem Controller-Shelly, startet und ist für den Autostart eingerichtet.
4. Weiter mit [Starten & prüfen](#starten--prüfen).

Die komplette Anleitung – auch für Update, Shelly-Wechsel und Fehlermeldungen – steht beim [Configurator](../Multiconfigurator/readme.md).

---

## Ohne Configurator (von Hand)

Nur für alle, die ihr Script selbst pflegen wollen.

### 1. Script holen

Lade die **minifizierte** Fassung [`zerooutput_multi_kvs_mini.js`](zerooutput_multi_kvs_mini.js). Nur diese lässt sich in den Shelly laden. Die Quellfassung `zerooutput_multi_kvs_src.js` ist zum Lesen gedacht – sie ist zu groß für den Shelly.

### 2. CONFIG-Block anpassen

Oben im Script steht der Block `let CONFIG = { ... };`. Mindestens diese Teile musst du anpassen:

**Speicher** – pro Zendure-Gerät ein Eintrag in `devices`, mit Komma getrennt:

```js
devices: [
  {
    ip: "192.168.178.143",   // IP-Adresse des Speichers
    label: "SF2400",         // kurzer Name für Log und Meldungen
    minSoc: 15,              // Reserve in %
    maxSoc: 100,             // Ladeziel in %
    dischargeAllowed: true,  // darf entladen
    reverse: true,           // darf Überschuss aus dem Netz aufnehmen
    maxInputPower: 1000,     // max. Ladeleistung in W
    maxOutput: 800,          // max. Entladeleistung in W
    dryRun: false            // true = nur rechnen, nichts schreiben (Test)
  },
  // ... weitere Speicher
],
```

Für den ersten Lauf reicht es meist, `ip`, `label`, `maxInputPower` und `maxOutput` passend zu deinem Gerät zu setzen. Mehr dazu: [Kapitel 4b](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#4b-mehrere-solarflow-geräte-einpflegen).

**Smartmeter** – `gridSource`:

- `"local"` (Standard): Das Script läuft direkt auf einem **Shelly Pro 3EM**. Nichts weiter zu tun.
- `"remote"`: ein **anderer** Shelly Pro 3EM im Netz, dazu `gridSourceIp` setzen.
- `"http_json"`: ein Messgerät mit JSON-Schnittstelle (z. B. Zendure Smart Meter 3CT oder D0, everHome EcoTracker, Tasmota, Shelly 3EM ohne Pro), dazu `gridSourceUrl` und `gridSourceField`. Verschachtelte Felder als Array, z. B. `["StatusSNS","DVS7420","power"]`. Der Configurator hat dafür fertige Vorlagen.

Details: [Kapitel 5](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#5-smartmeter-anbindung---die-drei-grid-quellen-im-überblick).

**Schwellwerte** – für den Start reichen die Standardwerte. Sie stehen zweimal im CONFIG-Block, getrennt für Entladen (`discharge: { ... }`) und Laden (`charge: { ... }`). Wer es gleich passend haben will ([Kapitel 7b](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#7b-empfehlung-für-ersteinstellung)):

- `spreadAbove` ≈ Nennleistung eines Speichers (z. B. 800 W für ein SF800, 2400 W für ein SF2400)
- `concentrateBelow` ≈ 0,6 × `spreadAbove`

### 3. Hochladen

1. Weboberfläche des Controller-Shelly öffnen (`http://<IP-des-Shelly>`) → **Scripts**.
2. Andere Scripte auf diesem Shelly stoppen und löschen – der Controller braucht den Speicher allein.
3. Neues Script anlegen („Create script“, bei älterer Firmware „Add script“), Namen vergeben, Code einfügen, **Save**.

Wie das im Detail aussieht: [Install and Run Shelly Script](https://github.com/surfer1264/Zendure-Stuff/wiki/Install-and-Run-Shelly-Script).

### Für Fortgeschrittene: mit `deploy.cmd`

Im Ordner [Deploy](Deploy) liegen Werkzeuge (Windows, Python 3 nötig), die deine eigene Konfiguration einsetzen, das Script verkleinern und hochladen:

1. Im Ordner `Deploy` (neben `deploy.cmd`) die Datei **`myconfig.js` selbst anlegen** – sie liegt bewusst nicht im Repository. Sie enthält nur deinen Block `let CONFIG = { ... };`. Am einfachsten bekommst du ihn aus dem [Configurator](../Multiconfigurator/readme.md#die-funktionen-im-ergebnis-schritt) über „💾 Nur CONFIG-Block speichern“; alternativ den Block aus `zerooutput_multi_kvs_src.js` kopieren und anpassen. Kommentarzeilen davor oder danach stören nicht.

   ```js
   // myconfig.js – nur der CONFIG-Block
   let CONFIG = {
     devices: [ /* deine Speicher */ ],
     gridSource: "local",
     // ... alle weiteren Einstellungen
   };
   ```

   `myconfig.js` steht in der `.gitignore` des Repositorys. Deine IPs und Zugangsdaten landen damit nicht versehentlich in einem Commit.
2. In `deploy.cmd` eintragen: `SHELLY_IP` (Controller-Shelly) und `SKRIPTNAME` (Standard `ctrl`). `MEINE_CONFIG` steht schon auf `myconfig.js` – nur ändern, wenn deine Datei anders heißt.
3. `deploy.cmd` starten. Ablauf: CONFIG einsetzen (`swap_config.py`) → verkleinern (`minify_keep_config.py`) → hochladen und starten (`upload_shelly.py`).

> **Wichtig:** `deploy.cmd` nimmt immer den CONFIG-Block aus **deiner** Datei. Die verkleinerte Fassung schreibt es nach `..\zerooutput_multi_kvs_mini.js` – also über die Datei aus dem Repository. Wer den Ordner per Git aktualisiert, sollte diese Änderung nicht committen oder `FERTIG` auf eine eigene Datei umstellen. `minify.cmd` erzeugt nur die verkleinerte Fassung ohne eigene Konfiguration.

---

## Starten & prüfen

1. Script **Start** und **„Run on startup“** aktivieren (beim Direkt-Upload passiert das automatisch).
2. Log öffnen und das Start-Banner prüfen: Es beginnt mit `Version …` und `Multi-Device Controller gestartet` und zeigt alle aktiven Werte auf einen Blick ([Kapitel 8.7](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#87-startprotokoll-banner)).
3. Erscheint regelmäßig eine Zeile wie

   ```
   Netzsaldo: 12 W | Ist-Summe: 340 W | Regelsignal: 352 W | Ladekorrektur: 0 W
   ```

   ✅ Fertig – der Controller regelt.

Bleibt der Netzbezug länger ruhig, meldet der Controller „Sparmodus“ und fragt die Speicher seltener ab. Das ist normal.

---

## Danach optional vertiefen

- Live-Einstellungen per KVS, z. B. aus dem [Dashboard](../zendash_watch_API_ZenSDK/dashboard.md) oder Home Assistant – [Kapitel 13](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#13-live-override-der-regelparameter-per-kvs-z-b-home-assistant)
- Signal-/WhatsApp-Benachrichtigung – [Kapitel 8.5](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#85-signal-benachrichtigung-callmebot--inkl-whatsapp)
- Testmodus `dryRun` – [Kapitel 4c](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#4c-testmodus-dryrun)
- Meldungen und Dashboard: [zenDash-API + Watchdog](../zendash_watch_API_ZenSDK/readme.md) auf dem zweiten Shelly

---

## Wie geht's dem Shelly?

Im Browser aufrufen, `<IP>` durch die Shelly-Adresse ersetzen:

| Zweck | Aufruf |
| --- | --- |
| Scripte auflisten (Nummer, Name, Status) | `http://<IP>/rpc/Script.List` |
| Speicherverbrauch eines Scripts | `http://<IP>/rpc/Script.GetStatus?id=<Nummer>` |
| Betriebszeit, RAM des Gesamtsystems | `http://<IP>/rpc/Sys.GetStatus` |

Bequemer geht es mit dem Helfer: „🔍 Speicher prüfen“ und „Log aufzeichnen“ im [Configurator](../Multiconfigurator/readme.md#7-how-tos).

---

## Was sonst noch im Ordner liegt

| Datei / Ordner | Wofür |
|---|---|
| [`zerooutput_multi_kvs_src.js`](zerooutput_multi_kvs_src.js) | lesbare Quellfassung des Controllers |
| [`zerooutput_multi_kvs_mini.js`](zerooutput_multi_kvs_mini.js) | verkleinerte Fassung zum Hochladen |
| [`CHANGELOG.md`](CHANGELOG.md) | Änderungen je Version |
| [`Deploy`](Deploy) | eigene Deploy-Pipeline, siehe [oben](#für-fortgeschrittene-mit-deploycmd) |
| [`yaml`](yaml) | Beispiel für Home Assistant: liest die KVS-Werte des Controllers per REST (`rest.yaml`), schreibt sie per `rest_command` zurück (`rest_commands.yaml`) und stellt sie als Regler bereit (`template/kvs.yaml`). Die IP `192.168.178.117` durch die deines Controller-Shellys ersetzen. `configuration.yaml` bindet in Home Assistant den Ordner `templates/` ein (`!include_dir_merge_list templates/`) – dorthin gehört die Datei `kvs.yaml` aus dem Repository-Ordner `template`. Hintergrund: [Kapitel 13.6](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly---Zendure---MultiController#136-nutzung-über-home-assistant) |
| [`zendure-config-wizard.html`](zendure-config-wizard.html) | früherer Konfigurations-Assistent nur für den Controller. Ersetzt durch den [Configurator](../Multiconfigurator/readme.md), bleibt nur zum Nachschlagen. |
| [`perf`](perf) | Arbeitsstand für Speicher- und Laufzeitmessungen (Entwicklung), nicht zum Hochladen |
