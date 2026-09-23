# zenDash-API + Watchdog v3.1

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

## Umstieg von den alten Scripten

Wenn du bisher **zenDash-API 2.x** und den **AkkuVolt-Watchdog 1.x** getrennt genutzt hast:

1. Installiere v3.1 wie oben beschrieben, am besten auf dem Shelly, auf dem bisher die zenDash-API lief.
2. **Stoppe die alte zenDash-API** auf diesem Shelly. Zwei Scripte mit denselben Endpunkten vertragen sich nicht.
3. Lass den **alten Watchdog** ruhig noch einen Tag parallel laufen. Du bekommst die Meldungen dann doppelt und kannst vergleichen. Danach stoppst du ihn und schaltest bei ihm **Run on startup** aus.

Die Adresse für das Dashboard bleibt gleich, sofern das neue Script auf demselben Shelly läuft. Beachte dabei, dass die Script-Nummer in der Adresse (`/script/<Nummer>/...`) zum neuen Script passen muss.

### Wo landen meine alten Einstellungen?

| Alte Einstellung | Neu |
|---|---|
| API: `kvsHost`, `hysteresis`, `dischargeStartupPower`, `gridSource…`, `pollIntervalSec` | in den Block `api: { ... }` verschieben |
| API: Geräteblock | bleibt `devices`, pro Gerät `watch` ergänzen, `dryRun` kann weg |
| Watchdog: Gerät `enabled: true/false` | wird zu `watch: true/false` im gemeinsamen Geräteblock |
| Watchdog: `vollSchwelle`, `entladeReset`, `minVolt…`, `temp…`, `sunriseOffset`, `sunsetOffset` | in den Block `watchdog: { ... }` |
| Watchdog: `pollIntervalMs: 120000` | `watchdog.intervalSec: 120` (Sekunden statt Millisekunden) |
| Watchdog: `errorThreshold: 5` | `watchdog.offlineAlarmMin: 10`. Jetzt in Minuten statt Fehlversuchen: 5 Fehlversuche à 2 Minuten ≈ 10 Minuten. |
| Watchdog: `signal: { ... }` | heißt jetzt `notify: { ... }`. Ein alter `signal`-Block wird notfalls noch erkannt (Hinweis im Log). |
| Watchdog: `maxMessageLength` | `notify.maxMessageLength` |
| Watchdog: `watchdog` (Timer), `bannerVerbose`, `version` | entfallen |

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
