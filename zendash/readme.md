# Zendure Grid Dashboard — Inbetriebnahme

Drei Teile gehören zusammen:

| Datei | Läuft wo | Aufgabe |
|---|---|---|
| `zerooutput_multi_kvs.js` | auf dem Shelly | balanciert die Zendure-Hubs gegen den Netzzähler |
| `zendure_proxy.py` | auf eurem PC | liefert das Dashboard aus + fragt Shelly/Hubs CORS-frei ab |
| `zendure-grid-dashboard.html` | im Browser | Anzeige + Regelparameter setzen |

`zendure_proxy.py` und `zendure-grid-dashboard.html` in EIN Verzeichnis kopieren auf PC/MAC/RASPI/NAS.... mit einer gültigen Python Umgebung (leicht nachzuinstallieren)


---

## 1) Shelly-Script

1. Im Shelly-Webinterface: **Settings → Scripts** → neues Script anlegen, Inhalt von `zerooutput_multi_kvs.js` einfügen.
2. Im `CONFIG`-Block oben im Script anpassen: `devices` (IP/Label/SoC-Grenzen je Hub), `gridSource` + zugehörige `gridSource*`-Felder.
3. **Wichtig:** `kvsEnabled: true` setzen — sonst liest das Script zwar die vom Dashboard gesetzten Werte aus der KVS, wendet sie aber nicht an.
4. Script speichern, **"Run on startup"** aktivieren, Script starten.

## 2) Dashboard konfigurieren

Ganz oben in `zendure-grid-dashboard.html` im `<script>`-Block steht der Konfigurationsblock — dort genügt Copy-paste aus dem Shelly-Script:

- **`DEVICES`**: den kompletten `CONFIG.devices`-Array 1:1 hineinkopieren (zusätzliche Felder wie `dryRun` stören nicht).
- **`GRID_SOURCE*`**: die `gridSource`/`gridSourceIp`/`gridSourceEmId`-Zeilen 1:1 aus `CONFIG` übernehmen.
- **`SHELLY_IP`**: IP des Shelly-Geräts, auf dem das Script läuft.

Alles unterhalb von *„Ab hier normalerweise nichts mehr anpassen"* ist reine Verdrahtung.

## 3) Proxy starten

Beide Dateien `zendure_proxy.py` und `zendure-grid-dashboard.html` müssen **im selben Ordner** liegen.

```bash
python3 zendure_proxy.py
```

Danach im Browser öffnen:

```
http://localhost:8000/zendure-grid-dashboard.html
```

Server beenden: `Strg+C` im Terminal.

### Warum ein Proxy?

Weder die Zendure-Hubs noch (je nach Firmware) die Shelly-RPC-Antworten senden einen `Access-Control-Allow-Origin`-Header. Ein direkter Aufruf im Browser (Adresszeile) funktioniert trotzdem, weil das eine normale Seiten-Navigation ist — ein `fetch()` aus dem Dashboard heraus ist dagegen eine Cross-Origin-Anfrage und wird ohne diesen Header vom Browser blockiert (CORS). Der Proxy fragt stellvertretend serverseitig ab (dort gilt CORS nicht) und reicht die Antwort same-origin ans Dashboard weiter.

## 4) Von einem anderen Rechner im selben Netz zugreifen

Der Proxy lauscht bereits auf allen Netzwerkschnittstellen. Auf dem PC, der den Proxy ausführt, die lokale IP ermitteln (z. B. `ipconfig` unter Windows → „IPv4-Adresse") und auf dem anderen Rechner öffnen:

```
http://<IP-des-PCs>:8000/zendure-grid-dashboard.html
```

Falls beim ersten Start ein Windows-Firewall-Dialog erscheint: **"Zugriff zulassen"** (privates Netzwerk) bestätigen, sonst kommen andere Rechner nicht durch.

⚠️ Kein Login/Zugriffsschutz — jeder im selben Netz kann mit der URL das Dashboard öffnen und Regelparameter ändern. Für ein Heimnetz meist unproblematisch; **nicht** per Portweiterreichung offen ins Internet stellen.

## 5) Bedienung

- **Sollwert / Hysterese**: schreiben per Shelly-KVS, wirken beim nächsten Regelzyklus des Scripts (Standard: alle 4 s).
- **Entladen erlaubt / Laden vom Netz erlaubt** (je Hub): gleiches Prinzip.
- **Poll-Intervall**: rein lokal im Dashboard, bestimmt nur, wie oft Hubs/Netzzähler abgefragt werden — hat keinen Einfluss auf das Script.
- Regler-Grenzen (Sollwert ±50 W/10er-Schritte, Hysterese 5–50 W/5er-Schritte, Poll 5–60 s/5er-Schritte) sind an das Clamping im Script angepasst.

## 6) Kurz-Troubleshooting

| Symptom | Ursache | Lösung |
|---|---|---|
| Weißes/leeres Fenster | Datei per Doppelklick geöffnet (`file://`) statt über den Proxy | Immer über `http://localhost:8000/...` öffnen |
| „Failed to fetch" / CORS-Fehler in der Konsole (F12) | Direkter Fetch ohne Proxy | `shellyProxyEnabled`/`hubProxyEnabled` im Dashboard-Config auf `true` lassen |
| Netzbezug bleibt „n/a" | `GRID_SOURCE_IP`/`SHELLY_IP` falsch oder Gerät ohne EM-Kanal | Direkt im Browser `http://<IP>/rpc/EM.GetStatus?id=0` testen |
| Regler/Schalter wirken nicht im Script | `kvsEnabled` im Script-CONFIG steht auf `false` | Auf `true` setzen, Script neu starten |
| 404 beim Öffnen der HTML-Datei | Datei liegt nicht im selben Ordner wie `zendure_proxy.py` | Beide Dateien zusammenlegen, Proxy neu starten |

## Impressionen
![alt text](<2026-07-25 21-24-16.PNG>)
![alt text](<2026-07-25 21-24-24.PNG>)
![alt text](<2026-07-25 21-24-31.PNG>)
![alt text](<2026-07-25 21-49-18-1.PNG>)
