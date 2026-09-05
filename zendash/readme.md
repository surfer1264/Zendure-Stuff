<img width="1000" alt="image" src="https://github.com/user-attachments/assets/c0d895d6-cf44-4bad-85ff-3d6346015b26" />


# Zendure Grid Dashboard — Inbetriebnahme

Drei Dateien gehören zusammen. Voraussetzung ist ein bereits laufender **Shelly Multi Device Controller** (`zerooutput_multi_kvs.js`) — das Dashboard steuert ihn nur, es ersetzt ihn nicht.

| Datei | Läuft wo | Aufgabe |
|---|---|---|
| `zendure_dashboard_api.js` | als Script auf dem Shelly (eigenes Gerät empfohlen, siehe Schritt 2) | liefert reine JSON-Daten (`config_api` / `status_api` / `kvs_set_api`) für das Dashboard |
| `zendure_proxy.py` | auf eurem PC/Mac/Raspi/NAS | liefert die Dashboard-Seite aus und fragt die Shelly-API stellvertretend ab (löst ein Zugriffsproblem, siehe unten) |
| `zendure-dashboard.html` | im Browser | Anzeige + Regelparameter setzen |

`zendure_proxy.py` und `zendure-dashboard.html` gehören in **ein gemeinsames Verzeichnis** auf einem Rechner mit **Python**.


## Getting Started (für die ganz Schnellen)

* Python installieren (gibt es für jede Plattform; einmal einrichten, danach nie wieder anfassen)
* Der Shelly Multi Device Controller läuft schon? Siehe Schritt 1
* API-Script konfigurieren: Geräte-Config-Block und Smartmeter-Einstellungen **exakt** wie im Controller (Copy/Paste)
* Python-Proxy konfigurieren: Shelly-IP und Script-Nummer des API-Scripts
* Proxy starten, im Browser `http://localhost:8000/` öffnen

Zur Vereinfachung:

* Ladet alle Dateien aus dem GitHub-Ordner herunter
* Schaut euch `deploy.cmd` und `start_proxy.cmd` an — die nehmen euch nach einmaliger Konfiguration einiges ab

---

## 1) Der Shelly Multi Device Controller läuft schon?

Hier nur der Vollständigkeit halber erwähnt, da die Verfügbarkeit dieses Scripts bereits vorausgesetzt wird.

1. Der **Shelly Multi Device Controller** läuft bereits.
2. **Wichtig:** `kvsEnabled: true` setzen — sonst liest das Script die vom Dashboard gesetzten Werte zwar aus der KVS, wendet sie aber nie an.
3. **`kvsForceReseed` muss auf `false` stehen.** Andernfalls überschreibt der Controller bei jedem Start alle Werte, die ihr im Dashboard gesetzt habt.

## 2) Wohin mit dem API-Script?

Zwei Betriebsarten. **Getrennt ist die empfohlene.**

| | Zusammen (`kvsHost: "local"`) | Getrennt (`kvsHost: "<3EM-IP>"`) |
|---|---|---|
| API-Script läuft | auf demselben Shelly wie das Regel-Script | auf einem **eigenen** Shelly (Plus/Pro/Gen3/Gen4 mit Scripting) |
| KVS-Zugriff | direkt per `Shelly.call` | per nativer RPC über HTTP: `http://<3EM-IP>/rpc/KVS.GetMany` bzw. `/rpc/KVS.Set` |
| `gridSource` | wie im Regel-Script | `"remote"`, `gridSourceIp` = Shelly mit der EM-Messung |
| Speicher | **beide Scripte teilen sich einen Variablenpool** | jedes Gerät hat seinen eigenen |

### Warum getrennt besser ist

Espruino stellt pro Gerät einen gemeinsamen Variablenpool von rund 1600 Einträgen für **alle** Scripte bereit. Regel-Script und API-Script fragen dieselben Zendure-Hubs ab; treffen zwei Antworten von je etwa 1,3 kB gleichzeitig ein, reißt der Pool. Der Fehler lautet `out_of_memory`, und es stirbt nicht etwa der Verursacher, sondern wer als Nächstes Speicher anfordert — mal das eine Script, mal das andere. Im Geräte-Log (Settings → Debug) sieht das so aus:

```
JS Error [5] out_of_memory used=1135 peak=1368 total=1617
UserScript.HandleError (script:1) [5] out_of_memory
```

Auf einem eigenen Gerät entfällt das. Die RPC-Anfragen an die KVS bedient drüben die **Firmware**, nicht ein Script — sie kosten dort also keine Variablen.

Voraussetzung für den getrennten Betrieb: auf dem KVS-Gerät ist keine Authentifizierung aktiv (Settings → Authentication).

Ist kein zweiter Shelly verfügbar, läuft die zusammengelegte Variante weiter. Dann hilft ein höherer `pollIntervalSec` (Vorgabe 8 s), weil er die Wahrscheinlichkeit gleichzeitiger Hub-Antworten senkt. Ganz ausschließen lässt sie sich so nicht.

## 2b) API-Script einrichten

1. **Settings → Scripts** → **neues, zusätzliches** Script anlegen (nicht das Regel-Script überschreiben), Inhalt von `zendure_dashboard_api.js` einfügen. Das Script muss auf demselben Shelly laufen wie das Regel-Script.
2. Im `CONFIG`-Block **exakt dieselben** Werte eintragen wie im Regel-Script:
   - `devices` — den kompletten Block 1:1 kopieren, gleiche Reihenfolge, gleiche IPs (Index `i` entspricht `zdmc_dev{i}_...` in der KVS). `minSoc`, `maxSoc` und `maxInputPower` bestimmen zusätzlich die Regler-Grenzen im Dashboard.
   - `gridSource` + zugehörige `gridSource*`-Felder (unterstützt `"local"`, `"remote"`, `"http_json"` — 1:1 dieselbe Struktur wie im Regel-Script)
   - `hysteresis` — denselben Wert wie im Regel-Script eintragen. Reine Anzeigegröße, siehe Schritt 5.
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
<img width="749" alt="image" src="https://github.com/user-attachments/assets/6e57b539-54f3-43a7-ad06-765ef67f1262" />

Danach im Browser öffnen:

```
http://localhost:8000/
```

(**Nicht** `.../zendure-dashboard.html` anhängen — der Proxy liefert die Seite direkt unter `/` aus.)

Server beenden: `Strg+C` im Terminal. Das Terminal-Fenster muss offen bleiben, solange das Dashboard genutzt wird.

### Warum ein Proxy?

Ein direkter Aufruf der API-URL im Browser (Adresszeile) funktioniert, weil das eine normale Seiten-Navigation ist. Ein `fetch()` **aus** der Dashboard-Seite heraus ist dagegen eine Cross-Origin-Anfrage — und die Shelly-Firmware weist solche Anfragen bereits **unterhalb** des Scripts mit `403 Forbidden` ab, unabhängig davon, welche CORS-Header das Script selbst setzt. Betroffen sind sowohl `file://`-Seiten als auch andere `http://`-Ursprünge (z. B. `localhost`). Der Proxy fragt stattdessen **serverseitig** ab (dort gelten keine Browser-CORS-Regeln) und reicht die Antwort same-origin ans Dashboard weiter — das umgeht das Problem vollständig, unabhängig von der genauen Ursache auf Shelly-Seite.

## 4) Von einem anderen Rechner im selben Netz zugreifen

Der Proxy lauscht standardmäßig auf allen Netzwerkschnittstellen (`BIND_ADDRESS = "0.0.0.0"`) und zeigt beim Start direkt die passende Adresse an:

```
Lokal:    http://localhost:8000/
Im Netz:  http://192.168.178.21:8000/   (IP-Adresse des Rechners, auf dem der Proxy läuft)
```

Nehmt genau die Adresse aus der Zeile „Im Netz" — am besten per Copy/Paste. Zwei Stolpersteine, die dabei regelmäßig auftreten:

* **`http://`, nicht `https://`.** Der Proxy spricht kein TLS. Bei `localhost` korrigiert der Browser das oft stillschweigend, bei einer IP-Adresse nicht.
* **Die richtige IP.** Hat der Rechner mehrere Schnittstellen (WLAN und LAN gleichzeitig, VPN, Docker), gibt es auch mehrere Adressen. `ipconfig` bzw. `ip addr` schafft Klarheit.

Falls beim ersten Start ein Windows-Firewall-Dialog erscheint: **„Zugriff zulassen"** (privates Netzwerk) bestätigen, sonst kommen andere Rechner nicht durch. Der Dialog erscheint **nur einmal** — wurde er weggeklickt, hilft nur eine manuelle Freigabe (siehe Troubleshooting).

⚠️ **Kein Login/Zugriffsschutz** — jeder im selben Netz kann mit der URL das Dashboard öffnen und Regelparameter ändern. Im Heimnetz meist unproblematisch; **nicht** per Portweiterleitung offen ins Internet stellen.

Für dauerhaften Zugriff eignet sich ein immer laufendes Gerät (Raspberry Pi, NAS, Mini-PC) besser als ein Laptop, den man zuklappt.

## 5) Bedienung

Alle Regelparameter werden per Shelly-KVS gesetzt und wirken beim nächsten Regelzyklus des Regel-Scripts. Die Grenzen entsprechen exakt dem Clamping in `readKvsOverrides()` von `zerooutput_multi_kvs.js` — Werte außerhalb dieser Bereiche verwirft das Regel-Script kommentarlos.

| Bedienelement | KVS-Key | Bereich |
|---|---|---|
| Sollwert (obere Reihe, links) | `zdmc_setpoint` | −40 bis +40 W, 10er-Schritte |
| Entladen erlaubt | `zdmc_dev{id}_dischargeAllowed` | Schalter (0/1) |
| Laden vom Netz erlaubt | `zdmc_dev{id}_reverse` | Schalter (0/1) |
| Reserve (min. SoC) | `zdmc_dev{id}_minSoc` | 10–98 %, 2er-Schritte |
| Ladeleistung aus dem Netz | `zdmc_dev{id}_inputLimit` | 0 bis `maxInputPower`, 50er-Schritte |

### Was die Regler bewirken

* **Reserve (min. SoC)** wird vom Regel-Script zusätzlich als Schutzgrenze auf die Hardware geschrieben (`syncMinSocDevice`) — der Wert ändert also nicht nur die Verteilrechnung, sondern das Gerät selbst.
* **Manuelles Laden** ist eine Aktion, kein einzelner Schalter. Der Regler „Ladeleistung aus dem Netz" wählt nur die Leistung aus und schreibt für sich genommen nichts; der Knopf darunter führt drei Schreibvorgänge in der richtigen Reihenfolge aus:
  1. `dischargeAllowed = 0`
  2. `reverse = 0`
  3. `inputLimit = <gewählte Leistung>`

  Beim Beenden umgekehrt: erst `inputLimit = 0`, dann die Schalter zurück auf den Stand vor dem Start. Die Reihenfolge ist nicht kosmetisch — wird `inputLimit` gesetzt, solange das Gerät noch in der Regelung hängt, überschreibt das Regel-Script den Wert im nächsten Zyklus. Umgekehrt würde ein stehengebliebenes Ladelimit mit der wieder aktiven Regelung kollidieren.

  Während der Kette pausiert der Seiten-Poll, zwischen den Schritten liegen 500 ms (`STEP_PAUSE_MS`), und danach vergehen weitere 1,5 s (`SETTLE_MS`), bevor wieder abgefragt wird. Ohne diese Entzerrung treffen drei `KVS.Set`, der laufende Hintergrund-Poll und die Reaktion des Regel-Scripts — das bei geändertem `inputLimit` sofort aufs Gerät schreibt — innerhalb weniger hundert Millisekunden auf demselben Shelly zusammen. Der ganze Vorgang dauert dadurch rund 2,5 s.

  Bricht die Kette in der Mitte ab (Shelly nicht erreichbar), erscheint ein Warnbanner — der Zustand ist dann unvollständig und gehört auf der Karte geprüft.

  Ob manuelles Laden läuft, leitet die Seite aus dem Live-Zustand ab (beide Schalter aus **und** `inputLimit > 0`). Das überlebt einen Reload und stimmt auch dann, wenn jemand anders die Werte gesetzt hat. Nur der Schalterzustand *vor* dem Start geht bei einem Reload verloren; das Beenden schaltet dann beide Schalter wieder ein.
* **Hysterese** ist im Regel-Script **nicht** über die KVS änderbar und taucht im Dashboard deshalb nicht als Bedienelement auf. `config_api` liefert den Wert trotzdem mit; die Seite braucht ihn nur intern, um den Netzbezug als Import, Export oder ausgeglichen einzustufen. Gepflegt wird er in `CONFIG.hysteresis` beider Scripte, die denselben Wert tragen müssen.
* Die Seite startet **gesperrt**. Das Schloss-Symbol oben rechts gibt die Bedienung frei; nach 60 s ohne Eingabe (`RELOCK_MS`) sperrt sie sich von selbst wieder. Der Zustand wird absichtlich nicht gespeichert — jeder Reload beginnt gesperrt. Gedacht ist das für Dashboards, die dauerhaft auf einem Tablet oder Zweitmonitor offen liegen.
* Jedes Bedienelement **sperrt sich nach einer Eingabe für 4 s** (`LOCK_MS`). Das verhindert mehrfaches Auslösen und schützt den frisch gesetzten Wert vor dem nächsten `config_api`-Abgleich. Schlägt das Schreiben fehl, wird sofort wieder freigegeben.

### Was die Anzeige zeigt

* **acMode / socLimit / gridReverse** stehen als Rohstatus auf jeder Hub-Karte. Sie erklären die häufigsten „Warum tut der Hub nichts?"-Fälle: `socLimit 1` = Akku voll, Laden gesperrt; `socLimit 2` = Entladen gesperrt; `gridReverse 2` = Netzladen vom Regel-Script flottenweit gesperrt.
* **PV-Eingang und schwächste Zelle** stehen als kleine Zeile unter der Leistung jeder Hub-Karte:
  * Der PV-Wert ist `solarInputPower`, also der Gesamteingang des Geräts. Fehlt das Feld — etwa bei reinen AC-Ladern —, entfällt die Angabe komplett, statt fälschlich „0 W" zu zeigen.
  * Die Zellspannung ist das Minimum über `packData[].minVol` aller Packs, umgerechnet mit Faktor 0,01 (325 → 3,25 V). Packs, die 0 melden, werden übersprungen. Unter 3,0 V wird der Wert amber, unter 2,8 V rot. Aussagekräftig ist er nur unter Last — im Ruhezustand liegen alle Zellen dicht beieinander.
* **Der Verlauf** steckt als kompakte Kurve in den beiden Kacheln oben: Netzsaldo links, Hub-Summe rechts. Beide skalieren auf ihr eigenes Maximum und sind daher nicht gegeneinander ablesbar — die Nulllinie liegt jeweils in der Mitte, Amber oben, Teal unten.
* Der Verlauf wird **in der Seite** geführt (`MAX_POINTS`, Standard 30 Werte à 4 s = 2 Minuten). Ein Ringpuffer im API-Script wäre komfortabler — er würde einen Reload überleben —, sprengte aber den Heap des Shelly. Nach einem Reload beginnen die Kurven deshalb wieder von vorn.
* Die Seite startet immer in der **Nachtsicht**; der Schalter oben rechts wechselt zur Tagsicht. Die Systemeinstellung des Geräts spielt keine Rolle.
* In der Fußzeile stehen die Versionen von Seite und API-Script. Laufen sie auseinander, wird der Hinweis amber — typischer Fall: HTML aktualisiert, das Script auf dem Shelly aber nicht.
* Geräteliste, Sollwert, Reglerstände und Schalterstellungen kommen bei jedem Laden/Poll frisch von `config_api` — es gibt **keine** Geräte-Konfiguration mehr in der HTML-Datei selbst. Das vermeidet Doppelpflege.

### Wer wie oft fragt

* Die **Seite** frischt fest alle 4 s auf (`POLL_SEC`), es gibt kein Bedienelement dafür. Der Wert muss unter `IDLE_MS` (15 s) im API-Script bleiben, sonst pausiert dort die Hintergrundabfrage zwischen zwei Seitenaufrufen und die Anzeige hängt hinterher.
* `status_api` wird bei jedem Durchlauf geholt, `config_api` nur jeden dritten (`CONFIG_EVERY`, also alle 12 s) — dieser Endpunkt macht auf dem Shelly jedes Mal ein `KVS.GetMany`. Eigene Eingaben wirken trotzdem sofort; nur eine Änderung von außen erscheint entsprechend später.
* Das **API-Script** fragt Netzzähler und Hubs alle 5 s ab (`pollIntervalSec`) — aber nur, solange in den letzten 15 s (`IDLE_MS`) tatsächlich ein Dashboard-Aufruf einging. Ist kein Dashboard offen, pausiert diese Hintergrundabfrage automatisch. Kein unnötiger Traffic zu den Zendure-Hubs.
* Ein **Zähler** (früher ein Flag) sorgt dafür, dass Hintergrundabfrage und `config_api` nie gleichzeitig laufen. Beide sind speicherintensiv — Parsen der mehrere kB großen Hub-Antwort bzw. `KVS.GetMany`. Kollidieren sie, lässt der Hintergrund-Timer den Takt aus, und `config_api` wartet bis zu 2 s auf einen freien Slot. Zusätzlich hat der Hintergrund-Durchlauf mit `bgRunning` einen eigenen Riegel gegen sich selbst.
* Die Notbremse (`BUSY_TIMEOUT_MS`) richtet sich nach der Gerätezahl: `(Geräte + 1) × httpTimeout + 5 s`. Sie muss länger sein als der längstmögliche Durchlauf, in dem jede einzelne Abfrage in den Timeout läuft — sonst greift sie mitten im Normalbetrieb und erlaubt genau die Überlappung, die sie verhindern soll.
* `status_api` liefert eine fertig serialisierte Antwort, die einmal je Hintergrund-Durchlauf gebaut wird. `config_api` hat einen 1-Sekunden-Cache und sammelt gleichzeitige Anfragen zu einem einzigen `KVS.GetMany`. Bei einem Dashboard ändert das nichts; bei mehreren offenen Seiten oder einem Reload-Sturm fällt der Aufwand auf ein Zehntel. Ein Schreibvorgang verwirft den Cache sofort.

## 6) Kurz-Troubleshooting

### Dashboard

| Symptom | Ursache | Lösung |
|---|---|---|
| Weißes/leeres Fenster, Konsole zeigt „Failed to fetch" | Datei per Doppelklick geöffnet (`file://`) statt über den Proxy | Immer über `http://localhost:8000/` öffnen, nicht die `.html`-Datei direkt |
| Roter Hinweis-Banner „Fehler beim Laden der Konfiguration" | Proxy läuft nicht, oder `SHELLY_IP`/`SHELLY_SCRIPT_ID` im Proxy falsch | Proxy-Konsole prüfen; `config_api`/`status_api` direkt im Browser testen (Schritt 2.5) |
| `config_api`/`status_api` liefern im Browser JSON, die Seite bleibt trotzdem leer | CORS/Origin-Block der Shelly-Firmware bei `fetch()` (siehe „Warum ein Proxy?") | Sicherstellen, dass die Seite über den Proxy läuft (`localhost:8000`), nicht per `file://` |
| 404 beim Öffnen von `http://localhost:8000/` | `zendure-dashboard.html` liegt nicht im selben Ordner wie `zendure_proxy.py` | Beide Dateien zusammenlegen, Proxy neu starten |
| Netzbezug bleibt „n/a" | `gridSource`/`gridSourceIp` im API-Script falsch, oder Gerät ohne EM-Kanal | `gridSource`-Werte im API-Script gegen das Regel-Script abgleichen |
| Alles ist ausgegraut, nichts lässt sich bedienen | Die Seite ist gesperrt (Standard nach Laden und nach 60 s Ruhe) | Schloss-Symbol oben rechts anklicken |
| „Manuelles Laden" lässt sich nicht starten | Ladeleistung steht auf 0 W | Regler darüber auf einen Wert größer 0 ziehen |
| Regler/Schalter wirken nicht auf die Hubs | `kvsEnabled` im Regel-Script steht auf `false` | Im Regel-Script auf `true` setzen, Script neu starten |
| Eingestellte Werte sind nach einem Shelly-Neustart wieder weg | `kvsForceReseed` im Regel-Script steht auf `true` | Auf `false` setzen |
| Fußzeile zeigt zwei verschiedene Versionen | HTML und API-Script sind nicht auf demselben Stand | Beide Dateien gemeinsam aktualisieren, Shelly-Script neu starten |
| Schalter/Regler zeigen falschen oder alten Wert an | API-Script und Regel-Script haben unterschiedliche `devices`-Konfiguration (Reihenfolge/IP) | Beide `CONFIG.devices`-Blöcke exakt abgleichen (Schritt 2.2) |
| PV-Zeile fehlt bei einem Gerät | Das Gerät liefert kein `solarInputPower` (reine AC-Lader) | Kein Fehler. Zur Kontrolle `http://<hub-ip>/properties/report` im Browser aufrufen |
| Zellspannung fehlt | Kein `packData` in der Antwort, oder alle Packs melden 0 | Wie oben mit `/properties/report` prüfen |

### Zugriff aus dem Netz

| Symptom | Ursache | Lösung |
|---|---|---|
| `localhost` geht, IP-Adresse nicht | `https://` statt `http://` eingegeben | Der Proxy spricht kein TLS — immer `http://` |
| dito | Falsche IP-Adresse | Adresse aus der Zeile „Im Netz" beim Proxy-Start verwenden, oder per `ipconfig` prüfen |
| Aufruf läuft in einen Timeout | Windows-Firewall blockiert; der Freigabedialog kam nur beim ersten Start | Als Administrator: `netsh advfirewall firewall add rule name="Zendure Proxy 8000" dir=in action=allow protocol=TCP localport=8000 profile=private` |
| dito | Netzwerkprofil steht auf „Öffentlich" | `Get-NetConnectionProfile` prüfen, ggf. mit `Set-NetConnectionProfile … -NetworkCategory Private` umstellen |
| dito, alles andere passt | Gast-WLAN oder Client-Isolation im Router | Gerät ins normale Netz holen |
| Verbindung wird sofort abgelehnt | Proxy lauscht nur lokal | `BIND_ADDRESS = "0.0.0.0"` prüfen; `netstat -ano \| findstr :8000` muss `0.0.0.0:8000` zeigen |

### Shelly-Script

| Symptom | Ursache | Lösung |
|---|---|---|
| „out of memory", eines der beiden Scripte stürzt ab | Regel-Script und API-Script teilen sich den Variablenpool und fragen dieselben Hubs ab | API-Script auf einen eigenen Shelly umziehen (`kvsHost` auf die 3EM-IP, `gridSource: "remote"`). Als Zwischenlösung `pollIntervalSec` erhöhen |
| `memPeak` deutlich höher als `memUsed` | Normal | `memPeak` ist der Höchststand seit Scriptstart und sinkt nie von selbst. Werte um 10 kB sind bei 25–30 kB Budget unkritisch. Für eine ehrliche Messung das Script neu starten |

## Impressionen

*(Screenshots aus einer früheren Version der Oberfläche — bei Gelegenheit gegen aktuelle ersetzen.)*

![alt text](<2026-07-25 21-24-16.PNG>)
![alt text](<2026-07-25 21-24-24.PNG>)
![alt text](<2026-07-25 21-24-31.PNG>)
![alt text](<2026-07-25 21-49-18-1.PNG>)
