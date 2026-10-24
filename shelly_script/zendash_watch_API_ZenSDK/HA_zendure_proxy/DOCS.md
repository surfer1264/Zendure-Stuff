# Zendure Dashboard Proxy – Bedienung

Die App stellt das Zendure-Dashboard im Heimnetz bereit und holt die Daten vom
Dashboard-Shelly (zenDash-API + Watchdog). Optional sendet sie die Messwerte jede
Minute an ThingSpeak und/oder ThingsBoard.

## Erste Einrichtung

1. App starten, dann **„Web-UI öffnen“** (oder `http://<ha-ip>:8000/`).
2. Auf der Einrichtungsseite eintragen:
   - **Shelly-IP** des Dashboard-Shelly (nicht des Controller-Shelly)
   - **Script-ID** des API-Scripts (in der Shelly-Weboberfläche unter *Scripts*, Name `zd`)
3. **„Speichern & testen“** – bei Erfolg geht es direkt zum Dashboard.

Empfohlen auf der Seite *Info* der App: **„Beim Booten starten“** und **„Watchdog“** einschalten.

## Seiten der App

| Adresse | Inhalt |
|---|---|
| `http://<ha-ip>:8000/` | Dashboard (Standard-Layout) |
| `http://<ha-ip>:8000/setup` | Shelly-IP und Script-ID ändern |
| `http://<ha-ip>:8000/thingspeak` | ThingSpeak-Upload einrichten |
| `http://<ha-ip>:8000/thingsboard` | ThingsBoard-Upload einrichten, Werte auswählen, Speicherverbrauch abschätzen |

Änderungen auf diesen Seiten wirken sofort – kein Neustart nötig.

Über **„Web-UI öffnen“** erreichst du dieselben Seiten über die Links im Fuß des
Dashboards: **„Dashboard-Shelly: IP / Script-ID ändern“** sowie
**„Cloud-Upload einrichten: ThingSpeak · ThingsBoard“**.

## Cloud-Upload

- **ThingSpeak:** ein Channel pro Speicher, Write-API-Key je Channel.
  Anleitung: [ThingSpeak-Upload](https://surfer1264.github.io/Zendure-Stuff/zendash_watch_API_ZenSDK/thingspeak/)
- **ThingsBoard:** ein Gerät pro Speicher plus ein Gerät „Netz“, Access Token je Gerät.
  Die Werte je Speicher sind auf `/thingsboard` per Häkchen wählbar.
  Anleitung: [ThingsBoard-Upload](https://surfer1264.github.io/Zendure-Stuff/zendash_watch_API_ZenSDK/thingsboard/)

Die App braucht dafür Internetzugang zum jeweiligen Dienst, der Shelly nicht.

## Wo die Einstellungen liegen

Alles liegt im dauerhaften Speicher der App (`/data`): Shelly-IP, Script-ID,
ThingSpeak-Keys und ThingsBoard-Tokens. Das übersteht Neustarts und **Updates**.

**Nicht deinstallieren**, um zu aktualisieren – das löscht `/data`, danach muss alles
neu eingetragen werden.

## Protokoll

Im Normalbetrieb stehen im Reiter *Protokoll* nur Fehler (Start mit `-q`).
Ob Werte ankommen, siehst du direkt in ThingSpeak bzw. ThingsBoard – oder oben auf
der Seite `/thingsboard` („Heute gesendet …“).

## Häufige Probleme

| Problem | Lösung |
|---|---|
| Statt des Dashboards erscheint die Einrichtungsseite | App wurde neu installiert – Shelly-IP und Script-ID erneut eintragen |
| „Shelly nicht erreichbar“ | IP prüfen; Test im Browser: `http://<shelly-ip>/script/<id>/status_api` |
| Antwort falsch / Status 404 | Falsche Script-ID |
| Shelly aus der App nicht erreichbar, obwohl IP stimmt | Getrennte Netzsegmente: in der Netzwerk-Einstellung der App auf Host-Netzwerk umstellen |
| Nach einem Update fehlt eine neue Funktion | Update wurde nicht neu gebaut – im App-Store über ⋮ „Nach Updates suchen“ und **Aktualisieren** |

## Sicherheit

Dashboard und Einrichtungsseiten haben **keinen Passwortschutz**. Jeder im Heimnetz
kann Einstellungen ändern. Port 8000 **nie** per Portweiterleitung ins Internet freigeben.

## Links

- [Projekt auf GitHub](https://github.com/surfer1264/Zendure-Stuff)
- [Dokumentation](https://surfer1264.github.io/Zendure-Stuff/)
- [Live-Dashboard](https://surfer1264.github.io/Zendure-Stuff/zendash_watch_API_ZenSDK/dashboard/)
- [Installation dieser App (für Fortgeschrittene)](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/zendash_watch_API_ZenSDK/HA_zendure_proxy/INSTALLATION.md)
- [Fehler melden / Fragen](https://github.com/surfer1264/Zendure-Stuff/issues)
