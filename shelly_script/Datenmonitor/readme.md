<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

> ⚠️ **Veraltet – ohne Support.** Rudimentäre Hilfsscripte aus der Anfangszeit, die nicht weiterentwickelt werden. Für Live-Daten und Meldungen gibt es [zenDash-API + Watchdog](../zendash_watch_API_ZenSDK/readme.md) mit [Dashboard](../zendash_watch_API_ZenSDK/dashboard.md). Diese Seite bleibt nur zum Nachschlagen.

# Datenmonitor

Zwei kleine Shelly-Scripte, um sich die Rohdaten eines Zendure-Speichers anzusehen – etwa um herauszufinden, welche Felder ein Gerät überhaupt liefert.

| Datei | Was es macht |
|---|---|
| [`HubControl`](HubControl) | „ZendureLens“: fragt den Report eines zenSDK-Speichers (`http://<IP-des-Speichers>/properties/report`) regelmäßig ab (Standard: alle 60 s) und schreibt die Werte gegliedert ins Script-Log. Optional Signal-Nachricht über CallMeBot, höchstens einmal pro Stunde. |
| [`HubDatenShellyScript`](HubDatenShellyScript) | „MQTT Inspector“: abonniert ein MQTT-Topic (`<AppKey>/#`) und listet alle Felder auf, die in den empfangenen Daten vorkommen. Der Shelly muss dafür mit dem passenden MQTT-Broker verbunden sein. |

## Verwenden

1. Inhalt der Datei als neues Script auf einem Shelly (Gen2 oder neuer) anlegen.
2. Oben im Script die Einstellungen anpassen: bei `HubControl` die IP in `CONFIG.url` (und bei Bedarf die Signal-Angaben), bei `HubDatenShellyScript` das Topic in `mqttTopic`.
3. Script starten und die Ausgabe im Log ansehen.

Die Scripte nicht dauerhaft neben dem Controller oder zenDash-API + Watchdog auf demselben Shelly laufen lassen – der Script-Speicher reicht dafür nicht.
