# Changelog – Zendure Multi-Configurator (Home-Assistant-App)

Ausführliche Historie inklusive EXE:
https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Multiconfigurator/CHANGELOG.md

## 2.9.3.0

- Multi-Configurator 2.9.3: Eine neue Version wird gleich beim Öffnen oben auf der Seite angezeigt, mit dem Weg zum Update in Home Assistant statt eines Download-Links für die EXE

## 2.9.2.1

- Helfer: Upload robuster. Schlägt ein Block fehl, beginnt die ganze Übertragung neu, statt nur den Block zu wiederholen; ein wiederholter Block konnte sonst doppelt im Script landen. Auch ein Verbindungsabbruch wird jetzt wiederholt und als „Upload unvollständig“ gemeldet, falls er dreimal auftritt
- Configurator: Fortschrittsanzeige beim Direkt-Upload. Balken und Text zeigen die Phase (prüfen, stoppen/entfernen/anlegen, „Übertrage Block 23 von 46 …“, starten), auch einen Neustart der Übertragung nach einem Verbindungsabbruch

## 2.9.2.0

- Multi-Configurator 2.9.2: Regel-Intervall nach Geräteanzahl (3000 ms + 500 ms je Gerät) als Standard bei neuer Einrichtung; beim Update Hinweis mit Auswahl, wenn der bisherige Wert abweicht

## 2.9.1.0

- Multi-Configurator 2.9.1: Aussehen wie das Dashboard (Farben, Schrift, Kopfzeile „ZENDURE // SHELLY MULTI DEVICE SUITE“) mit Tag-/Nachtsicht und Sprachwahl im Menü „Ansicht“

## 2.9.0.0

- Erste Version der App: Multi-Configurator 2.9.0 mit Upload-Helfer in Home Assistant
- Aufruf über „Web-UI öffnen“ (Ingress) bzw. optional in der Seitenleiste; Port 8787 standardmäßig aus
- Gemerkte Shelly-IPs liegen in `/data` und überstehen Updates der App
