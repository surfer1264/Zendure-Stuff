# Zendure Grid Dashboard — Inbetriebnahme

Vier Teile gehören zusammen (nicht mehr drei — das Dashboard hat jetzt einen eigenen, schlanken API-Endpunkt auf dem Shelly, getrennt vom Regel-Script):

| Datei | Läuft wo | Aufgabe |
|---|---|---|
| `zerooutput_multi_kvs.js` | als Script auf dem Shelly | balanciert die Zendure-Hubs gegen den Netzzähler |
| `zendure_dashboard_api.js` | als **zweites, separates** Script auf dem Shelly | liefert reine JSON-Daten (`config_api`/`status_api`/`kvs_set_api`) für das Dashboard |
| `zendure_proxy.py` | auf eurem PC/Mac/Raspi/NAS | liefert die Dashboard-Seite aus + fragt die Shelly-API stellvertretend ab (löst ein Zugriffsproblem, siehe unten) |
| `zendure-dashboard.html` | im Browser | Anzeige + Regelparameter setzen |

`zendure_proxy.py` und `zendure-dashboard.html` gehören in **ein gemeinsames Verzeichnis** auf einem Rechner mit **Python** .

Es wird **nur** `zendure-dashboard.html` gepflegt. Die frühere Variante mit Direktabfrage (`zendure-grid-dashboard.html`) ist abgelöst und kann gelöscht werden.

## Getting Started (für die ganz schnellen)

* Python-Umgebung (gibt es für jede Plattform, einfach installieren, müsst ihr nie wieder anfassen: FERTIG)
* Der Shelly Multi Device Controller läuft schon? siehe (1)
* Das API Script konfigurieren (mit dem exakt gleichen Geräte-Config-Block, wei beim Controller => Copy/Paste), Smartmeter konfigurieren (exakt so wie im Controller)
* Python Proxy konfigurieren (nur Shelly-IP auf dem die API läuft) und Script Nummer des API-Scriptes
* Python Proxy starten: `http://localhost:8000/`

Zur Vereinfachung für alle
* ladet alle Daten aus dem Github-Ordner herunter 
* schaut Euch die `deply.cmd` und die `start_proxy.cmd` an
* die vereinfacht nach einmaliger Konfiguration einiges.

---

## 1) Der Shelly Multi Device Controller läuft schon?

Hier der Vollständigkeit erwähnt, da die Vewrfügbarkeit dieses Scriptes berteits vorausgesetzt wird. 

1. der **Shelly Multi Device Controller** läuft bereits !!
2. **Wichtig:** `kvsEnabled: true` setzen — sonst liest das Script zwar die vom Dashboard gesetzten Werte aus der KVS, wendet sie aber nie an.


## 2) API-Script auf dem Shelly (zweites, eigenständiges Script!)

1. **Settings → Scripts** → **neues, zusätzliches** Script anlegen (nicht das Regel-Script überschreiben), Inhalt von `zendure_dashboard_api.js` einfügen. Das Script muss auf dem gleichen Shelly laufen, auf dem auch das Regel-Script läuft
2. Im `CONFIG`-Block **exakt dieselben** Werte eintragen wie im Regel-Script:
   - `devices` — den kompletten Block 1:1 kopieren, gleiche Reihenfolge, gleiche IPs (Index `i` entspricht `zdmc_dev{i}_...` in der KVS). `minSoc`, `maxSoc` und `maxInputPower` bestimmen zusätzlich die Regler-Grenzen im Dashboard.
   - `gridSource` + zugehörige `gridSource*`-Felder (unterstützt `"local"`, `"remote"`, `"http_json"` — 1:1 dieselbe Struktur wie im Regel-Script)
3. Speichern, **„Run on startup"** aktivieren, Script starten.
4. **Die Script-ID notieren** (steht in der Shelly-Scripts-Übersicht, z. B. `id: 2`) — die braucht der Proxy gleich.
5. Kurzer Test direkt im Browser (Adresszeile, keine Datei nötig):
   ```
   http://<shelly-ip>/script/<script-id>/config_api
   http://<shelly-ip>/script/<script-id>/status_api
   ```
   Beide sollten JSON liefern. Falls nicht: siehe Troubleshooting unten.

## 3) Proxy konfigurieren und starten

Im Kopf von `zendure_proxy.py` anpassen:

```python
SHELLY_IP = "192.168.178.117"   # IP des Shelly mit dem API-Script
SHELLY_SCRIPT_ID = 1            # Script-ID aus Schritt 2.4
PORT = 8000                     # lokaler Port, an dem der Proxy lauscht
```

Beide Dateien (`zendure_proxy.py`, `zendure-dashboard.html`) müssen im selben Ordner liegen. Dann:

```bash
python3 zendure_proxy.py
```

Danach im Browser öffnen:

```
http://localhost:8000/
```

(**Nicht** `.../zendure-dashboard.html` anhängen — der Proxy liefert die Seite direkt unter `/` aus.)

Server beenden: `Strg+C` im Terminal. Das Terminal-Fenster muss offen bleiben, solange das Dashboard genutzt wird.

### Warum ein Proxy?

Ein direkter Aufruf der API-URL im Browser (Adresszeile) funktioniert, weil das eine normale Seiten-Navigation ist. Ein `fetch()` **aus** der Dashboard-Seite heraus ist dagegen eine Cross-Origin-Anfrage — und die Shelly-Firmware weist solche Anfragen bereits **unterhalb** des Scripts mit `403 Forbidden` ab (unabhängig davon, welche CORS-Header das Script selbst setzt). Betroffen sind sowohl `file://`-Seiten als auch andere `http://`-Ursprünge (z. B. `localhost`). Der Proxy fragt stattdessen **serverseitig** ab (dort gelten keine Browser-CORS-Regeln) und reicht die Antwort same-origin ans Dashboard weiter — das umgeht das Problem vollständig, unabhängig von der genauen Ursache auf Shelly-Seite.

## 4) Von einem anderen Rechner im selben Netz zugreifen

Der Proxy lauscht standardmäßig auf allen Netzwerkschnittstellen (`BIND_ADDRESS = "0.0.0.0"`) und zeigt beim Start direkt die passende Adresse an:

```
Lokal:    http://localhost:8000/
Im Netz:  http://192.168.178.121:8000/   (von jedem Rechner im selben Netzwerk, das ist die IP-Adresse des Rechners auf dem der Proxy läuft)
```

Einfach die „Im Netz"-Adresse auf einem anderen Gerät im selben WLAN/LAN öffnen.

Falls beim ersten Start ein Windows-Firewall-Dialog erscheint: **„Zugriff zulassen"** (privates Netzwerk) bestätigen, sonst kommen andere Rechner nicht durch.

⚠️ **Kein Login/Zugriffsschutz** — jeder im selben Netz kann mit der URL das Dashboard öffnen und Regelparameter ändern. Für ein Heimnetz meist unproblematisch; **nicht** per Portweiterleitung offen ins Internet stellen.

Für dauerhaften Zugriff eignet sich ein immer laufendes Gerät (Raspberry Pi, NAS, Mini-PC) besser als ein Laptop, den man zuklappt.

## 5) Bedienung

Alle Regelparameter werden per Shelly-KVS gesetzt und wirken beim nächsten Regelzyklus des Regel-Scripts. Die Grenzen entsprechen exakt dem Clamping in `readKvsOverrides()` von `zerooutput_multi_kvs.js` — Werte außerhalb dieser Bereiche verwirft das Regel-Script kommentarlos.

| Bedienelement | KVS-Key | Bereich |
|---|---|---|
| Sollwert (obere Reihe, links) | `zdmc_setpoint` | −40 bis +40 W, 10er-Schritte |
| Entladen erlaubt | `zdmc_dev{id}_dischargeAllowed` | Schalter (0/1) |
| Laden vom Netz erlaubt | `zdmc_dev{id}_reverse` | Schalter (0/1) |
| Reserve (min. SoC) | `zdmc_dev{id}_minSoc` | 10–98 %, 2er-Schritte |
| Laden aus dem Netz | `zdmc_dev{id}_inputLimit` | 0 bis `maxInputPower`, 50er-Schritte |

- **Reserve (min. SoC)** wird vom Regel-Script zusätzlich als Schutzgrenze auf die Hardware geschrieben (`syncMinSocDevice`) — der Wert ändert also nicht nur die Verteilrechnung, sondern auch das Gerät selbst.
- **Laden aus dem Netz** (`inputLimit`) ist eine Zusatzschnittstelle für manuelles AC-Laden. Das Regel-Script schreibt den Wert unverändert aufs Gerät; sinnvoll ist das nur, wenn der Hub vorher über die beiden Schalter aus der Regelung genommen wurde. Das Dashboard prüft das **nicht** — der Regler steht immer zur Verfügung.
- **Hysterese** ist im Regel-Script **nicht** über die KVS änderbar und taucht im Dashboard deshalb auch nicht mehr als Bedienelement auf. `config_api` liefert den Wert weiterhin mit — die Seite braucht ihn nur intern, um Netzbezug als Import, Export oder ausgeglichen einzustufen. Gepflegt wird er in `CONFIG.hysteresis` beider Scripte, die denselben Wert tragen müssen.
- **acMode / socLimit / gridReverse** stehen als Rohstatus auf jeder Hub-Karte. Sie erklären die häufigsten „warum tut der Hub nichts"-Fälle: `socLimit 1` = Akku voll, Laden gesperrt; `socLimit 2` = Entladen gesperrt; `gridReverse 2` = Netzladen vom Regel-Script flottenweit gesperrt.
- **Auffrischung der Seite**: fest alle 4 s (`POLL_SEC`), kein Bedienelement mehr. Der Wert muss unter `IDLE_MS` (15 s) im API-Script bleiben, sonst pausiert dort die Hintergrundabfrage zwischen zwei Seitenaufrufen und die Anzeige hängt hinterher.
- `status_api` wird bei jedem Durchlauf geholt, `config_api` nur jeden dritten (`CONFIG_EVERY`, also alle 12 s) — dieser Endpunkt macht auf dem Shelly jedes Mal ein `KVS.GetMany`. Eigene Eingaben wirken trotzdem sofort; nur eine Änderung von außen erscheint entsprechend später.
- Jedes Bedienelement sperrt sich nach einer Eingabe für 4 s (`LOCK_MS`). Das verhindert mehrfaches Auslösen und schützt den frisch gesetzten Wert vor dem nächsten `config_api`-Abgleich. Schlägt das Schreiben fehl, wird sofort wieder freigegeben.
- Geräteliste, Sollwerte, Reglerstände und Schalterstellungen kommen bei jedem Laden/Poll frisch von `config_api` — es gibt **keine** Geräte-Konfiguration mehr in der HTML-Datei selbst (vermeidet Doppelpflege).
- Der Verlauf steckt als kompakte Kurve direkt in den beiden Kacheln oben: Netzsaldo in der linken, Hub-Summe in der rechten. Beide skalieren auf ihr eigenes Maximum und sind daher nicht gegeneinander ablesbar — die Nulllinie liegt jeweils in der Mitte, Amber oben, Teal unten.
- Der Verlauf wird in der Seite geführt (`MAX_POINTS`, Standard 30 Werte à 4 s = 2 Minuten). Ein Ringpuffer im API-Script wäre komfortabler — er würde einen Reload überleben —, sprengte aber den Heap des Shelly. Nach einem Reload beginnen die Kurven deshalb wieder von vorn.
- Die Seite startet immer in der Nachtsicht; der Schalter oben rechts wechselt zur Tagsicht, die Systemeinstellung des Geräts spielt keine Rolle mehr.
- Unabhängig vom Browser-Poll-Intervall fragt das API-Script auf dem Shelly selbst alle 5 s (`pollIntervalSec`) Netzzähler und Hubs ab — aber nur, solange in den letzten 15 s (`IDLE_MS`) tatsächlich ein Dashboard-Aufruf einging. Ist kein Dashboard offen, pausiert diese Hintergrundabfrage automatisch (kein unnötiger Traffic zu den Zendure-Hubs).
- Im API-Script sorgt ein `busy`-Flag dafür, dass Hintergrundabfrage und `config_api` nie gleichzeitig laufen. Beide sind speicherintensiv (Parsen der mehrere kB großen Hub-Antwort bzw. `KVS.GetMany`); zusammen trieben sie `memPeak` unnötig hoch. Kollidieren sie, lässt der Hintergrund-Timer den Takt aus und `config_api` wartet bis zu 2 s auf einen freien Slot. Ein hängendes Flag wird nach 15 s (`BUSY_TIMEOUT_MS`) automatisch zurückgesetzt.

## 6) Kurz-Troubleshooting

| Symptom | Ursache | Lösung |
|---|---|---|
| Weißes/leeres Fenster, Konsole zeigt „Failed to fetch" | Datei per Doppelklick geöffnet (`file://`) statt über den Proxy | Immer über `http://localhost:8000/` öffnen, nicht die `.html`-Datei direkt |
| Roter Hinweis-Banner „Fehler beim Laden der Konfiguration" | Proxy läuft nicht, oder `SHELLY_IP`/`SHELLY_SCRIPT_ID` im Proxy falsch | Proxy-Konsole prüfen; `config_api`/`status_api` direkt im Browser testen (Schritt 2.5) |
| `config_api`/`status_api` liefern direkt im Browser JSON, aber die Seite bleibt trotzdem leer | CORS/Origin-Block der Shelly-Firmware bei `fetch()` (siehe „Warum ein Proxy?") | Sicherstellen, dass die Seite tatsächlich über den Proxy läuft (`localhost:8000`), nicht per `file://` |
| 404 beim Öffnen von `http://localhost:8000/` | `zendure-dashboard.html` liegt nicht im selben Ordner wie `zendure_proxy.py` | Beide Dateien zusammenlegen, Proxy neu starten |
| Netzbezug bleibt „n/a" | `gridSource`/`gridSourceIp` im API-Script falsch, oder Gerät ohne EM-Kanal | `gridSource`-Werte im API-Script gegen das Regel-Script abgleichen |
| Regler/Schalter wirken nicht auf die Hubs | `kvsEnabled` im Regel-Script steht auf `false` | Im Regel-Script auf `true` setzen, Script neu starten |
| Schalter/Regler zeigen falschen oder alten Wert an | API-Script und Regel-Script haben unterschiedliche `devices`-Konfiguration (Reihenfolge/IP) | Beide `CONFIG.devices`-Blöcke exakt abgleichen (siehe Schritt 2.2) |
| Shelly-Script stürzt ab / „out of memory" o. ä. | Passiert nur beim (mittlerweile entfernten) HTML-Endpunkt direkt auf dem Shelly — nicht mehr relevant, seit das Dashboard als eigenständige Datei läuft | Sicherstellen, dass auf dem Shelly wirklich `zendure_dashboard_api.js` läuft (keine HTML-Auslieferung mehr an Bord) |

## Impressionen

*(Screenshots aus einer früheren Version der Oberfläche — bei Gelegenheit gegen aktuelle ersetzen.)*

![alt text](<2026-07-25 21-24-16.PNG>)
![alt text](<2026-07-25 21-24-24.PNG>)
![alt text](<2026-07-25 21-24-31.PNG>)
![alt text](<2026-07-25 21-49-18-1.PNG>)