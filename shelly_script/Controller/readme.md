# Getting Started – in 10 Minuten startklar

Diese Kurzanleitung deckt nur das ab, was für einen **funktionierenden ersten
Lauf** nötig ist. 
Einen perfekten EINstieg erhälst Du hier 
[Benutzerdokumentation](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-SMDC-‐-Benutzerdokumentation)

Alles Weitere (mehrere Geräte, Signal-/WhatsApp-Meldungen, KVS-Live-Override, Debug, Feinabstimmung) ist bewusst ausgeklammert und wird
in der [Gesamtdokumentation](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController)
verlinkt.



---

## Checkliste, bevor du anfängst (~1 Min)

- [ ] Shelly Gen2/3/4 mit Script-Engine vorhanden [Kapitel 3](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#3-voraussetzungen)
- [ ] Zendure-Gerät(e) im selben LAN, feste IP-Adresse bekannt, **nur zenSDK fähige Geräte (ab SF800)**
- [ ] **Wichtig:** Zendure-Gerät(e) in der Zendure-App aus dem **HEMS**
      (Home Energy Management System) entfernt – sonst sendet die Cloud
      parallel eigene Steuerbefehle und kollidiert mit dem Script
- [ ] Ein Smartmeter für den aktuellen Netz-Leistungswert vorhanden (ein
      Shelly Pro 3EM lokal auf demselben Gerät ist der einfachste Fall)

---

## Schritt 1 – Script installieren (~2 Min)

1. [bis Version 3.x.x Script herunterladen](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs.js)
2. [ab Version 4.x.x Script herunterladen](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs_mini.js) Minifyer eingesetzt
3. Im Shelly Web-UI: **Scripts → Add Script**
4. Code einfügen, **Save**
5. Noch **nicht** starten – erst nach Schritt 2.

---

## Schritt 2 – Minimalkonfiguration (~5 Min)

Der Konfigurator hilft zur Ersteinrichtung (Empfehlung). Weiter dann mit Schritt 3,

[Konfigurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/zendure-config-wizard.html)



### 2a) Geräteblock

Vollständiger Geräteeintrag (ein Feld pro Zeile, Kommentar dahinter) – pro
Zendure-Gerät ein solcher Block in `CONFIG.devices[]`:

Für den ersten Lauf reicht es, `ip` korrekt zu setzen – die übrigen Werte
oben sind bereits sinnvolle, geräte-typische Startwerte. 
Mehrere Geräte:
Block kopieren, mit Komma trennen [Kapitel 4b](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#4b-mehrere-solarflow-geräte-einpflegen).

### 2b) Smartmeter

`gridSource` passend wählen:

- **`"local"`** (Standard) – das Script läuft direkt auf einem **Shelly Pro
  3EM**, keine Änderung nötig.
- **Anderer Smartmeter oder Script läuft auf einem anderen Shelly?** Dann
  reicht `"local"` **nicht** – bitte im Detail in [Kapitel 5](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#5-smartmeter-anbindung---die-drei-grid-quellen-im-überblick)
  nachschauen (`"remote"` für einen entfernten Pro 3EM, `"http_json"` für
  generische JSON-Smartmeter wie das Zendure Smart Meter 3CT).

### 2c) Schwellwerte
Entweder die Standardwerte (erstmal) verwenden (für den Start Gut Genug), oder

`discharge`/`charge` → `concentrateBelow`/`spreadAbove` nach Faustformel
[Kapitel 7b](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#7b-empfehlung-für-ersteinstellung) folgen:

- `spreadAbove` ≈ Nennleistung eines Geräts (z. B. 800 W für ein SF800, 2400
  W für ein SF2400)
- `concentrateBelow` ≈ 0,6 × `spreadAbove`

---

## Schritt 3 – Starten & prüfen (~2 Min)

1. Script **Start** + **„Run on startup"** aktivieren
2. Log öffnen, Start-Banner prüfen [Kapitel 8.7](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#87-startprotokoll-banner) –
   zeigt alle aktiven Werte auf einen Blick
3. Läuft die Zeile `Grid: ... | Kombiniertes Ziel (gedaempft): ...`
   regelmäßig durch? ✅ Fertig.

---

## Danach optional vertiefen

- Mehrere Geräte einpflegen – [Kapitel 4b](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#4b-mehrere-solarflow-geräte-einpflegen)
- Testmodus `dryRun` – [Kapitel 4c](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#4c-testmodus-dryrun)
- Signal-/WhatsApp-Benachrichtigung – [Kapitel 8.5](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#85-signal-benachrichtigung-callmebot--inkl-whatsapp)
- Live-Override der Regelparameter per KVS (z. B. Home Assistant) – [Kapitel 13](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-‐-Zendure-‐-MultiController#13-live-override-der-regelparameter-per-kvs-z-b-home-assistant)

---

### Wie gehts dem Shelly?

**Befehle zur Statusprüfung** (im Browser aufrufen, `<IP>` durch die
Shelly-Adresse ersetzen):

| Zweck | Befehl |
|---|---|
| Laufende Scripts auflisten (IDs, Name, Status) | `http://<IP>/rpc/Script.List` |
| Speicherverbrauch eines bestimmten Scripts | `http://<IP>/rpc/Script.GetStatus?id=<ID>` |
| Geräte-Betriebszeit, RAM des Gesamtsystems | `http://<IP>/rpc/Sys.GetStatus` |

