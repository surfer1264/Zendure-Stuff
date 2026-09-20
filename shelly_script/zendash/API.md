# ZenDash API

Die drei JSON-Endpunkte von `zendure_dashboard_api.js` (Version 2.5). Sie liefern
Messwerte und Einstellungen für das Dashboard und schreiben Sollwerte in die
Shelly-KVS, aus der das Regel-Script `zerooutput_multi_kvs.js` seine Vorgaben liest.

## Basisadresse

```
http://<shelly-ip>/script/<script-id>/<endpunkt>
```

Die Script-ID steht in der Shelly-Scripts-Übersicht. Direkt im Browser aufgerufen
funktionieren die Endpunkte; ein `fetch()` aus einer Webseite heraus wird von der
Shelly-Firmware mit `403` abgewiesen, unabhängig von den CORS-Headern des Scripts.
Deshalb läuft der Zugriff über `zendure_proxy.py`, der serverseitig abfragt und
same-origin weiterreicht:

```
http://<proxy-host>:8000/<endpunkt>
```

Alle Endpunkte antworten mit `Content-Type: application/json` und
`Access-Control-Allow-Origin: *` und beantworten `OPTIONS`-Preflights.

---

## `status_api`

Messwerte. Ändert sich laufend, wird vom Dashboard alle 4 s geholt.

```json
{
  "grid": { "power": -180, "online": true },
  "hubs": [
    {
      "id": 0,
      "soc": 67,
      "power": 351,
      "acMode": 2,
      "socLimit": 0,
      "gridReverse": 1,
      "pv": 240,
      "minVol": 325,
      "online": true
    }
  ]
}
```

| Feld | Bedeutung |
|---|---|
| `grid.power` | Netzsaldo in W. Positiv = Bezug, negativ = Einspeisung |
| `grid.online` | Netzzähler erreichbar |
| `id` | Index in `CONFIG.devices`, entspricht `{id}` in den KVS-Schlüsseln |
| `soc` | Ladestand in % (`electricLevel`) |
| `power` | Leistung des Hubs in W. Positiv = entlädt, negativ = lädt |
| `acMode` | `1` lädt über den AC-Eingang, `2` speist ins Haus, sonst Standby |
| `socLimit` | `0` frei, `1` voll (Laden gesperrt), `2` leer (Entladen gesperrt) |
| `gridReverse` | `1` Netzladen freigegeben, `2` vom Regel-Script gesperrt |
| `pv` | PV-Gesamteingang in W (`solarInputPower`). **`null`** = Gerät hat keinen PV-Eingang, z. B. reine AC-Lader. Nicht mit `0` verwechseln |
| `minVol` | Niedrigste Zellspannung über alle Packs, Rohwert. Faktor 0,01 V, also `325` → 3,25 V. `null`, wenn kein `packData` geliefert wird |
| `online` | Hub erreichbar. Bei `false` sind alle Messwerte `null` bzw. `0` |

`socLimit` ist auch die Grundlage für den automatischen Stopp des manuellen Ladens
(siehe [„Manuelles Laden“](#manuelles-laden) weiter unten): Meldet ein Gerät im
manuellen Modus `socLimit: 1`, beendet das API-Script den Modus von selbst.

Die Antwort kommt aus einem Zwischenspeicher, der einmal je Hintergrund-Durchlauf
gebaut wird (Standard alle 8 s, `CONFIG.pollIntervalSec`). Der Endpunkt selbst
fragt nichts ab und ist entsprechend billig.

**Alter der Daten:** Fragt längere Zeit niemand an, pausiert der Hintergrund-Durchlauf
(`IDLE_MS`, 15 s). Die erste Antwort nach so einer Pause enthält noch den alten
Stand; frische Werte gibt es erst nach dem nächsten Durchlauf. Ein Altersfeld gibt
es derzeit nicht.

---

## `config_api`

Einstellungen und Stammdaten. Wird vom Dashboard alle 12 s geholt, nach einer
eigenen Eingabe zusätzlich sofort.

```json
{
  "version": "2.5",
  "setpoint": -20,
  "hysteresis": 12,
  "dischargeFixed": 0,
  "dischargeStartupPower": 35,
  "devices": [
    {
      "id": 0,
      "ip": "192.168.178.143",
      "label": "SF2400",
      "minSoc": 15,
      "maxSoc": 100,
      "maxOutput": 800,
      "maxInputPower": 1000,
      "inputLimit": 0,
      "dischargeAllowed": true,
      "reverse": true
    }
  ]
}
```

| Feld | Herkunft |
|---|---|
| `version` | Versionsstand des API-Scripts. Das Dashboard vergleicht ihn mit seinem eigenen |
| `setpoint` | KVS, Zielwert für den Netzsaldo in W |
| `hysteresis` | `CONFIG`, **nicht** über die KVS änderbar. Nur zur Anzeige — muss mit dem Wert im Regel-Script übereinstimmen |
| `dischargeFixed` | KVS, globaler Fix-Sollwert für die Entladeleistung in W. `0` = aus |
| `dischargeStartupPower` | `CONFIG`, **nicht** über die KVS änderbar. Untere Grenze für `dischargeFixed` — muss mit dem Wert im Regel-Script übereinstimmen |
| `ip`, `label`, `maxSoc`, `maxOutput`, `maxInputPower` | `CONFIG`, zur Laufzeit unveränderlich |
| `minSoc`, `inputLimit`, `dischargeAllowed`, `reverse` | KVS, mit den Vorgaben aus `CONFIG` als Rückfallwert |

Ist die KVS nicht erreichbar, antwortet der Endpunkt trotzdem — dann mit den
Vorgabewerten aus `CONFIG`, statt die Anfrage hängen zu lassen.

Mehrere gleichzeitige Anfragen (mehrere offene Dashboards, Reload-Sturm) werden zu
**einem** `KVS.GetMany` zusammengefasst.

---

## `kvs_set_api`

Schreibt Werte in die KVS.

```
GET kvs_set_api?data={"zdmc_setpoint":-20}
```

Der `data`-Parameter ist ein URL-kodiertes JSON-Objekt. Mehrere Schlüssel sind
erlaubt und werden **nacheinander** geschrieben, nicht parallel.

```json
{ "success": true, "written": 1 }
```

| Antwort | Bedeutung |
|---|---|
| `200` mit `success: true` | alle Schlüssel geschrieben |
| `200` mit `written: 0` | kein Schlüssel mit Präfix `zdmc_` dabei, nichts geschrieben |
| `400` | `data` fehlt oder ist kein gültiges JSON-Objekt |
| `500` mit `success: false` | mindestens ein Schreibvorgang fehlgeschlagen |

Nur Schlüssel mit dem Präfix `zdmc_` werden angenommen, alle anderen stillschweigend
übergangen. Werte müssen numerisch sein (Ziffern, Minus, Punkt) — andernfalls wird
nichts geschrieben und `success: false` gemeldet. Das schützt beim entfernten
Schreiben davor, dass ein Wert die URL zerlegt.

### Schlüssel und Wertebereiche

Die Grenzen entsprechen dem Clamping in `readKvsOverrides()` des Regel-Scripts.
Werte außerhalb werden dort **kommentarlos verworfen** — die KVS enthält sie dann,
die Regelung ignoriert sie.

| Schlüssel | Bereich | Wirkung |
|---|---|---|
| `zdmc_setpoint` | −40 … 40 | Zielwert für den Netzsaldo in W |
| `zdmc_dischargeFixed` | `0` oder ≥ `dischargeStartupPower` | Feste Entladeleistung in W statt Netzsaldo-Regelung. `0` schaltet zurück auf die normale Regelung. Werte zwischen `1` und der unteren Grenze verwirft das Regel-Script |
| `zdmc_dev{id}_dischargeAllowed` | `0` / `1` | Entladen erlaubt |
| `zdmc_dev{id}_reverse` | `0` / `1` | Laden aus dem Netz erlaubt |
| `zdmc_dev{id}_minSoc` | 10 … 99 | Reserve in %. Wird zusätzlich als Schutzgrenze auf die Hardware geschrieben |
| `zdmc_dev{id}_inputLimit` | 0 … `maxInputPower` | Manuelle Ladeleistung in W |

**`minSoc` muss unter `maxSoc` bleiben.** Das Regel-Script gleicht beide Werte nur
beim Start gegeneinander ab, nicht beim Live-Override. Rutscht `minSoc` darüber, darf
das Gerät weder unter die Reserve entladen noch bis dorthin laden und fällt dauerhaft
aus der Regelung.

**`inputLimit` setzt eine Reihenfolge voraus.** Erst `dischargeAllowed` und `reverse`
auf `0`, dann die Ladeleistung — sonst überschreibt das Regel-Script den Wert im
nächsten Zyklus. Beim Beenden reicht `inputLimit` auf `0` allein: Ist das Gerät zu
diesem Zeitpunkt im manuellen Modus und werden `dischargeAllowed`/`reverse` nicht im
selben Request mitgeschickt, ergänzt das API-Script sie selbst aus dem gespeicherten
Vorzustand (siehe [„Manuelles Laden"](#manuelles-laden)). Bei einem kombinierten
Aufruf mit mehreren Schlüsseln übernimmt das API-Script die Schreibreihenfolge
selbst — die Schlüssel innerhalb eines `data`-Objekts müssen dafür nicht in einer
bestimmten Reihenfolge stehen.

---

## Manuelles Laden

„Manueller Lademodus" ist kein eigener Schalter, sondern die Kombination
`dischargeAllowed=0`, `reverse=0`, `inputLimit>0` für ein Gerät. Das API-Script
erkennt diesen Zustand an jedem über `kvs_set_api` geschriebenen Wert und hält ihn
in einem eigenen Zustandsspeicher fest (rein im Arbeitsspeicher, nicht in der KVS).

### Aufruf (ein Gerät, ein Request)

Alle drei Schlüssel eines Geräts in einem `data`-Objekt, URL-kodiert:

```
GET kvs_set_api?data={"zdmc_dev1_dischargeAllowed":0,"zdmc_dev1_reverse":0,"zdmc_dev1_inputLimit":500}
```

```bash
curl -g 'http://<shelly-ip>/script/<script-id>/kvs_set_api?data={"zdmc_dev1_dischargeAllowed":0,"zdmc_dev1_reverse":0,"zdmc_dev1_inputLimit":500}'
```

Antwort: `{"success":true,"written":3}`

Beenden — nur noch `inputLimit=0` nötig:

```
GET kvs_set_api?data={"zdmc_dev1_inputLimit":0}
```

```bash
curl -g 'http://<shelly-ip>/script/<script-id>/kvs_set_api?data={"zdmc_dev1_inputLimit":0}'
```

Antwort: `{"success":true,"written":3}` — das API-Script ergänzt `dischargeAllowed`
und `reverse` selbst aus seinem gespeicherten Vorzustand (`preManual`, siehe unten)
und meldet sie im `written`-Zähler mit, auch wenn nur ein Schlüssel geschickt wurde.

Werden `dischargeAllowed`/`reverse` stattdessen explizit mitgeschickt (z. B.
`{"zdmc_dev1_inputLimit":0,"zdmc_dev1_dischargeAllowed":1,"zdmc_dev1_reverse":1}`),
gilt das als bewusste Vorgabe des Aufrufers und wird unverändert übernommen — dann
**nicht** aus `preManual` ergänzt. Für den Normalfall („zurück in die Regelung, wie
davor“) reicht `inputLimit=0` allein.

Das funktioniert unabhängig davon, ob der Aufruf vom Dashboard, curl, einer
Shelly-Automation oder Home Assistant kommt — entscheidend ist nur, dass er über
`kvs_set_api` läuft und nicht die KVS am Script vorbei direkt beschreibt (siehe
Warnung unten).

### Automatischer Stopp bei voller Batterie

Meldet der Hub für ein Gerät im manuellen Modus `socLimit: 1` (siehe `status_api`),
beendet das API-Script den manuellen Modus von selbst — gleiche Schreibreihenfolge
und derselbe Rückfallmechanismus wie beim Beenden mit bloßem `inputLimit=0` (siehe
oben): `inputLimit` zuerst, danach die beiden Schalter, aus `preManual` ergänzt.
Zurückgesetzt wird auf den Zustand unmittelbar vor dem Start des manuellen Modus,
sofern das API-Script seither nicht neu gestartet ist; andernfalls auf
`dischargeAllowed=1` / `reverse=1`.

Damit das funktioniert:

- **Der Start muss über `kvs_set_api` laufen.** Ein Schreiben direkt per Shelly-RPC
  (`KVS.Set`, lokal oder entfernt) am API-Script vorbei wird nicht erkannt — der
  interne Zustandsspeicher bleibt dann auf „automatisch" stehen, und weder der
  automatische Stopp noch die folgende Ausnahme greifen.
- **Die Hintergrundabfrage pausiert nicht mehr,** solange irgendein Gerät im
  manuellen Modus ist — auch wenn 15 s lang kein Dashboard aufgerufen wurde. Ohne
  diese Ausnahme würde die Abfrage (und damit die Kenntnis von `socLimit`) genau
  dann einschlafen, wenn niemand mehr zuschaut.

---

## Betriebsverhalten

**Hintergrundabfrage.** Ein Timer fragt alle `pollIntervalSec` Netzzähler und Hubs ab —
aber nur, solange in den letzten 15 s ein Endpunkt aufgerufen wurde **oder** mindestens
ein Gerät im manuellen Lademodus ist (siehe [„Manuelles Laden“](#manuelles-laden)).
Trifft beides nicht zu, pausiert die Abfrage vollständig.

**Überlappungsschutz.** Ein Zähler verhindert, dass Hintergrundabfrage und `config_api`
gleichzeitig laufen; ein eigener Riegel schützt den Durchlauf gegen sich selbst. Beides
ist keine Kosmetik: Espruino stellt pro Gerät rund 1600 Variablen für **alle** Scripte
zusammen bereit, und zwei gleichzeitig verarbeitete Hub-Antworten von je etwa 1,3 kB
sprengen diesen Pool.

**Keine JSON-Auswertung der Hub-Antworten.** Die benötigten Zahlen werden aus dem
Rohtext gelesen, weil ein `JSON.parse` von `/properties/report` mehrere hundert
Variablen belegt. Ändert Zendure die Feldnamen, fällt das erst im Betrieb auf — jede
Extraktion liefert dann `null`, und ein fehlendes `electricLevel` gilt als „Hub nicht
auswertbar".

**KVS lokal oder entfernt.** Steht `CONFIG.kvsHost` auf `"local"`, greift das Script
direkt per `Shelly.call` zu. Sonst über die native RPC des angegebenen Geräts
(`/rpc/KVS.GetMany`, `/rpc/KVS.Set`). Die entfernte Variante wird empfohlen, weil die
Anfragen dort von der Firmware bedient werden und den Variablenpool des Regel-Scripts
nicht belasten.
