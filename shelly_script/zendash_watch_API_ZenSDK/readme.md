# zenDash-API + Watchdog

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

Ein Shelly-Script für deinen **Dashboard-Shelly**, das zwei Aufgaben rund um deine Zendure-Speicher übernimmt:

- **API für das Dashboard** – Das [Dashboard](dashboard.md) zeigt darüber Netzbezug, Ladestand und Leistung deiner Speicher an. Außerdem kannst du Einstellungen des Controllers ändern und manuelles Laden starten.
- **Watchdog** – Das Script meldet dir per Signal, WhatsApp oder Webhook, wenn ein Akku voll ist, zu warm wird, eine Zelle zu wenig Spannung hat oder ein Speicher nicht mehr erreichbar ist. Morgens und abends kommt zusätzlich eine kurze Übersicht.

Beide Teile lassen sich einzeln ein- und ausschalten. Ein einziges Script fragt die Speicher ab und teilt die Daten zwischen beiden Aufgaben – das spart Speicher auf dem Shelly und entlastet deine Zendure-Geräte. Früher waren es zwei getrennte Scripte (zenDash-API 2.x und AkkuVolt-Watchdog 1.x), die zusammen je nach Anzahl der Speicher an die Speichergrenze des Shelly stießen.

Die aktuelle Version und alle Änderungen stehen im [Changelog](CHANGELOG.md).

---

## Inhalt

- [Was du brauchst](#was-du-brauchst)
- [So arbeitet das Script](#so-arbeitet-das-script)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Dashboard](#dashboard)
- [Nachrichten](#nachrichten)
- [Manuelles Laden und Auto-Stop](#manuelles-laden-und-auto-stop)
- [Letzte Vollladung](#letzte-vollladung)
- [Umstieg von den alten Scripten](#umstieg-von-den-alten-scripten)
- [Speicherbedarf](#speicherbedarf)
- [Fehlersuche](#fehlersuche)

---

## Was du brauchst

- **Einen eigenen Shelly** mit Script-Funktion (Generation 2 oder neuer: Plus, Pro, Gen3 …). Das Script läuft immer auf einem anderen Shelly als der Controller – beide zusammen passen nicht in den Speicher eines Shelly.
- **Zendure-Speicher mit lokaler Schnittstelle** (zenSDK), erreichbar unter `http://<IP-des-Speichers>/properties/report`. Getestet mit SolarFlow 2400 Pro und SolarFlow 800.
- **Den [Controller](../Controller/readme.md)** auf deinem Controller-Shelly, wenn du das Dashboard nutzen willst. Das Dashboard liest und schreibt dessen Einstellungen. Nutzt du nur den Watchdog, brauchst du ihn nicht.
- **Für Nachrichten** (optional):
  - Signal oder WhatsApp: einen kostenlosen API-Key von [CallMeBot](https://www.callmebot.com)
  - oder einen Webhook, zum Beispiel in Home Assistant

> **Hinweis:** Auf dem Controller-Shelly darf **kein Passwortschutz** aktiv sein. Sonst kann dieses Script die Einstellungen dort nicht lesen und schreiben.

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

### Empfohlen: mit dem Configurator

Der [Configurator](../Multiconfigurator/readme.md) fragt alles ab, übernimmt Geräteliste, Netzquelle und Benachrichtigungen aus der Controller-Konfiguration und lädt das Script mit dem Helfer direkt auf deinen Dashboard-Shelly (Script-Name `zd`). Auch Updates laufen darüber.

### Von Hand über die Shelly-Weboberfläche

1. Die **minifizierte** Fassung [`zendash_watch_mini.js`](zendash_watch_mini.js) herunterladen. Nur diese passt in den Shelly – `zendash_watch_src.js` ist die lesbare Quellfassung.
2. Den Block `let CONFIG = { ... };` anpassen (siehe [Konfiguration](#konfiguration)).
3. Weboberfläche des Dashboard-Shelly öffnen (`http://<IP-des-Shelly>`) → **Scripts**. Andere Scripte auf diesem Shelly stoppen und löschen.
4. Neues Script anlegen („Create script“, bei älterer Firmware „Add script“), Namen vergeben (z. B. `zd`), Code einfügen, **Save**, dann **Start**.
5. **„Run on startup“** einschalten, damit das Script nach einem Stromausfall von selbst wieder startet.

### Für Fortgeschrittene: mit `deploy.cmd`

Im Ordner [Deploy](Deploy) liegen Werkzeuge, die deine eigene Konfiguration einsetzen, das Script verkleinern und hochladen:

1. Deine Konfiguration in eine eigene Datei legen, zum Beispiel `myconfig_zenDash_watch.js`. Sie enthält nur den `let CONFIG = { ... };`-Block.
2. In `deploy.cmd` eintragen: IP des Shelly, Script-Name, `QUELLE=..\zendash_watch_src.js` und `MEINE_CONFIG=myconfig_zenDash_watch.js`.
3. `deploy.cmd` starten.

> **Wichtig:** `deploy.cmd` nimmt immer den CONFIG-Block aus **deiner** Datei. Änderungen, die du direkt in `zendash_watch_src.js` machst, werden dabei überschrieben.

### Nach dem Start

Im Log des Scripts erscheint eine Übersicht. Prüfe dort, ob alles so eingestellt ist, wie du es willst:

```
--------------------------------
zenDash-API + Watchdog v3.4.1 (Dashboard muss ebenfalls v3.4.1 sein)
Module     : API AN | Watchdog AN
Geraete    : SF2400[W] SF800[W]
Watchdog   : alle 120 s, Offline-Alarm nach 10 min
Nachrichten: SIGNAL -> callmebot | Debug: AUS
--------------------------------
```

`[W]` hinter einem Gerät bedeutet: Der Watchdog überwacht es. Die Versionsnummer ist die deines Scripts.

Sind Nachrichten eingeschaltet, bekommst du außerdem die Meldung **„✅ zenDash/Watchdog v… gestartet“**. So weißt du sofort, dass der Nachrichtenweg funktioniert.

---

## Konfiguration

Alle Einstellungen stehen oben im Script im Block `let CONFIG = { ... }`. Nutzt du den Configurator, brauchst du hier nichts von Hand zu ändern.

### Geräte (`devices`)

Trage **dieselben Speicher wie im Controller** ein – gleiche IP-Adressen, **gleiche Reihenfolge**. Die Reihenfolge ist wichtig: Das erste Gerät ist im Controller „Gerät 0“, das zweite „Gerät 1“ und so weiter.

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
| `ip` | IP-Adresse des Speichers |
| `label` | Name für Anzeige und Nachrichten. Im Morgen-/Abend-Update erscheinen nur die ersten 6 Zeichen. |
| `minSoc`, `maxSoc`, `maxInputPower`, `maxOutput`, `dischargeAllowed`, `reverse` | Werte wie im Controller. Das Dashboard nutzt sie als Startwerte und Grenzen für die Regler. |
| `inputLimit` | Ladeleistung aus dem Netz beim Start, normalerweise `0`. Gibt es im Controller-CONFIG nicht – dort kommt der Wert nur über die KVS. |
| `watch` | `true`: Der Watchdog überwacht dieses Gerät. `false`: Es erscheint nur im Dashboard. Fehlt der Eintrag, gilt `true`. |

Kopierst du den Geräteblock aus dem Controller, darf `dryRun` stehen bleiben – der Eintrag wird hier ignoriert.

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
| `kvsHost` | **IP des Controller-Shelly** – dort liegen die Einstellungen des Controllers. |
| `hysteresis` | Nur zur Anzeige im Dashboard. Muss **denselben Wert** haben wie im Controller. |
| `dischargeStartupPower` | Kleinster erlaubter Wert für die Fix-Entladung (außer 0). Muss **denselben Wert** haben wie im Controller. |
| `gridSource` | Woher kommt die Netzmessung? `"remote"`: ein Shelly Pro 3EM im Netz (meist der Controller-Shelly), `"http_json"`: ein anderes Messgerät mit JSON-Schnittstelle, `"local"`: nur wenn dieser Shelly selbst ein Pro 3EM ist. |
| `gridSourceIp`, `gridSourceEmId` | bei `"remote"`: IP des Messgeräts und Kanal (meist 0) |
| `gridSourceUrl`, `gridSourceField`, `gridSourceInvert` | bei `"http_json"`: Adresse, Feldname der Gesamtleistung, Vorzeichen umdrehen ja/nein |
| `pollIntervalSec` | Abfragetakt bei geöffnetem Dashboard in Sekunden. Standard 8. |

Damit du im Dashboard auch **einstellen** kannst, muss im Controller `kvsEnabled: true` und `kvsForceReseed: false` gesetzt sein. Ohne KVS zeigt das Dashboard nur an.

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

Im Controller heißt dieser Block `signal`, hier `notify`. `enabled`, `typ`, `phone`, `apiKey` und `webhookUrl` bedeuten in beiden dasselbe; `maxMessageLength` und `apiEvents` gibt es nur hier. Steht in einer alten Konfiguration noch ein `signal`-Block, verwendet das Script ihn, wenn kein `notify` vorhanden ist.

**Webhook-Format:** Das Script schickt einen POST-Request mit dem Inhalt `{"message": "…"}`. In Home Assistant steht der Text dann in einer Automation mit Webhook-Auslöser unter `{{ trigger.json.message }}`.

### Allgemein

| Einstellung | Bedeutung |
|---|---|
| `httpTimeout` | Wie viele Sekunden das Script höchstens auf eine Antwort wartet. Standard 5. |
| `debug` | `false`: normale Ausgabe. `true`: ausführliches Log zur Fehlersuche (siehe [Fehlersuche](#fehlersuche)). |

---

## Dashboard

Das Dashboard ist eine Webseite, die ihre Daten von diesem Script holt. Du öffnest sie über einen kleinen Proxy auf PC, NAS (z. B. Synology), Home Assistant oder Raspberry Pi – für Windows und Mac gibt es ihn auch als fertiges Programm.

👉 **[Dashboard einrichten und bedienen](dashboard.md)**

Die Schnittstelle für eigene Anbindungen (z. B. Home Assistant, Node-RED) ist in der [API-Beschreibung](API.md) dokumentiert.

### Verlauf in ThingSpeak

Der Proxy kann die Messwerte deiner Speicher zusätzlich jede Minute an ThingSpeak senden. Dort bekommst du einen dauerhaften Verlauf mit Diagrammen. Der Upload ist optional und braucht nur eine zusätzliche Datei neben dem Proxy. Solange ein Dashboard offen ist, liest der Proxy dessen Abfragen nur mit. Ist der Upload ausgeschaltet, stellt er keine einzige Anfrage an das Script.

👉 **[ThingSpeak-Upload einrichten](thingspeak.md)**

---

## Nachrichten

Diese Nachrichten kann das Script verschicken:

| Nachricht | Wann |
|---|---|
| ✅ zenDash/Watchdog v… gestartet (2/2 ueberwacht) | nach jedem Start des Scripts |
| 🔋 SF2400 voll (99%) | Ladestand hat die `vollSchwelle` erreicht |
| 🔥 SF800 Temp hoch: 46.2C | Gerätetemperatur über `tempWarn` |
| ⚠️ SF800 Zelle BO1234… nur 2.85V | eine Zelle unter `minVoltWarn`, mit Seriennummer des Akkupacks |
| ❌ SF800: nicht erreichbar seit 10 min | Speicher antwortet nicht mehr |
| ❌ SF800: Report unlesbar seit 10 min | Speicher antwortet, aber mit unvollständigen oder unbrauchbaren Daten |
| ✅ SF800: wieder erreichbar | nach einer der beiden vorigen Meldungen |
| ⚠️ SF800 seit 20 Tagen nicht voll | einmal täglich beim Morgen-Update geprüft, siehe [Letzte Vollladung](#letzte-vollladung) |
| 🌅 Morgen-Update / 🌇 Abend-Update | zu Sonnenauf- und -untergang: Ladestand, Temperatur und niedrigste Zellspannung je Gerät |
| ✅ SF2400: manuelles Laden beendet (voll) … | Auto-Stop hat funktioniert (bei `apiEvents: true`) |
| ⚠️ SF2400: Auto-Stop fehlgeschlagen … | Auto-Stop konnte die Einstellungen nicht zurücksetzen. Bitte im Dashboard prüfen. |

Jede Warnung kommt **einmal**, nicht bei jeder Abfrage. Erst wenn sich der Wert wieder normalisiert hat, kann sie erneut kommen.

Im Morgen- und Abend-Update steht `n/a`, wenn für ein Gerät keine aktuellen Werte vorliegen, zum Beispiel weil es gerade nicht erreichbar ist.

> **Tipp:** Das Morgen- und Abend-Update ist gleichzeitig ein Lebenszeichen. Bleibt es aus, läuft das Script vermutlich nicht mehr.

---

## Manuelles Laden und Auto-Stop

Im Dashboard kannst du einen Speicher manuell aus dem Netz laden lassen. Das Script schaltet dafür im Controller für dieses Gerät Entladen und Laden vom Netz ab und setzt eine feste Ladeleistung.

**Auto-Stop:** Sobald der Speicher meldet, dass er voll ist, beendet das Script das manuelle Laden selbstständig und stellt den vorherigen Zustand wieder her. Das funktioniert auch, wenn das Dashboard geschlossen ist.

Gut zu wissen:
- Den vorherigen Zustand merkt sich das Script nur im Arbeitsspeicher. Startet der Shelly während des manuellen Ladens neu, werden beim Beenden Entladen und Laden vom Netz wieder **eingeschaltet**.
- Du kannst das manuelle Laden jederzeit im Dashboard selbst beenden.

---

## Letzte Vollladung

Lithium-Akkus sollten ab und zu einmal ganz voll werden, damit der Speicher seinen Ladestand richtig einschätzt. Das Script merkt sich deshalb je Speicher, wann er zuletzt **echte 100 %** erreicht hat:

- Das Datum wird höchstens einmal am Tag im Controller-Shelly gespeichert (KVS-Eintrag `zdmc_dev{Nummer}_lastFull`) und übersteht damit einen Neustart.
- Im **Dashboard** steht je Speicher „100 %: vor N Tagen“ – grün unter 7 Tagen, gelb bis 20 Tage, rot darüber. Antippen zeigt das Datum.
- Der **Watchdog** meldet einmalig, wenn ein überwachter Speicher seit 20 Tagen nicht mehr voll war.

---

## Umstieg von den alten Scripten

Hast du bisher die getrennten Scripte zenDash-API 2.x und AkkuVolt-Watchdog 1.x verwendet:

1. Den Umstieg mit dem Configurator machen – die Schritte stehen dort unter [Umstieg von den alten Einzelscripten](../Multiconfigurator/readme.md#umstieg-von-den-alten-einzelscripten). Alte Konfigurationen dieser Scripte lassen sich nicht direkt einlesen; die Controller-Konfiguration liefert aber den größten Teil.
2. Die alten Scripte **stoppen und „Run on startup“ ausschalten** (oder löschen) – sonst laufen sie weiter und Meldungen kommen doppelt.
3. Nutzt du das Dashboard: Hat das neue Script eine andere Script-Nummer, trag sie im Proxy unter `/setup` ein.

---

## Speicherbedarf

Ein Shelly-Script hat rund **25 kB** Arbeitsspeicher. Gemessen auf einem echten Gerät mit zwei Speichern (Version 3.1):

| | belegt im Ruhezustand | höchster Wert |
|---|---|---|
| Dashboard geschlossen | ca. 13,5 kB | ca. 17,8 kB |
| Dashboard geöffnet | ca. 13,5 kB | ca. 17,7–18,0 kB |

Seit Version 3.4 liegt die Grundlast noch rund 0,9 kB niedriger. Es bleiben also im ungünstigsten Moment gut **7 kB** frei. Zum Vergleich: Die beiden alten Scripte zusammen brauchten in der Spitze bereits fast 25 kB.

Selbst nachmessen kannst du mit „🔍 Speicher prüfen“ im [Configurator](../Multiconfigurator/readme.md#speicher-eines-shelly-prüfen).

---

## Fehlersuche

### Debug-Ausgabe einschalten

Setze `debug: true` und starte das Script neu – oder setze im Configurator beim Update das Häkchen „Debug-Ausgaben“. Im Log erscheinen dann zusätzlich:

- jeder Aufruf der Dashboard-Schnittstelle mit den übergebenen Werten
- jeder Schreibvorgang in die Einstellungen des Controllers mit Ergebnis
- Beginn und Ende des manuellen Ladens
- Wechsel zwischen schnellem Takt (Dashboard offen) und Ruhezustand
- Versand jeder Nachricht
- die Speicherbelegung an den wichtigsten Stellen
- bei jeder Watchdog-Runde eine Zeile je Speicher mit allen Akkupacks, zum Beispiel:
  ```
  [DEBUG] SF800: SoC 91%, 26.0C | Packs: CO1234…:91%/3.31V, BO5678…:91%/3.31V
  ```

Schalte `debug` danach wieder aus. Das Log wird sonst sehr lang. Zum Mitschneiden eignet sich „Log aufzeichnen“ im [Configurator](../Multiconfigurator/readme.md#log-aufzeichnen).

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
- Stimmen im Proxy unter `/setup` IP **und** Script-Nummer des Dashboard-Shelly? Siehe [Dashboard – Wenn es nicht klappt](dashboard.md#wenn-es-nicht-klappt).
- Ist `api.enabled` auf `true`?

**Im Dashboard stehen nur Standardwerte, Änderungen werden nicht übernommen.**
Das Script erreicht die Einstellungen des Controllers nicht. Prüfe `api.kvsHost` (IP des Controller-Shelly), ob im Controller `kvsEnabled: true` gesetzt ist und ob auf dem Controller-Shelly ein Passwortschutz aktiv ist. Mit `debug: true` erscheint im Log `KVS NICHT lesbar` bzw. `KVS.Set … -> FEHLER`.

**Meldung „Report unlesbar“.**
Der Speicher hat geantwortet, aber die Daten waren unvollständig oder hatten ein unerwartetes Format. Das kommt vereinzelt vor und verschwindet meist von selbst. Bleibt es dauerhaft, hat sich eventuell nach einem Firmware-Update des Speichers dessen Datenformat geändert. Bitte dann ein [Issue](https://github.com/surfer1264/Zendure-Stuff/issues) mit der Antwort von `http://<IP-des-Speichers>/properties/report` anlegen. Entferne vorher die Seriennummern.

**Das Morgen- und Abend-Update kommt zur falschen Zeit oder gar nicht.**
Prüfe Standort und Zeitzone in den Shelly-Einstellungen. Das Script legt beim Start zwei Zeitpläne an. Andere Zeitpläne auf dem Shelly bleiben dabei unberührt.
