<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

🌐 **Deutsch** · [English](readme_EN.md) · [Français](readme_FR.md)

# Zendure-Speicher lokal steuern – mit zwei Shellys

Deine Zendure-Speicher (zenSDK-fähige Geräte ab SolarFlow 800) werden damit ohne Cloud geregelt: Ein Shelly hält deinen Netzbezug auf null, ein zweiter liefert die Daten für ein Dashboard und meldet sich, wenn etwas nicht stimmt.

## 👉 Hier starten

1. **[Helfer herunterladen](https://github.com/surfer1264/Zendure-Stuff/releases/latest)** (Windows oder Mac mit Apple Silicon) und starten.
2. Im Browser öffnet sich der Configurator. **„Neu konfigurieren“** wählen und die Fragen beantworten.
3. Am Ende **„⚡ Direkt hochladen“** – fertig.

Die ausführliche Anleitung (auch zu Update, Shelly-Wechsel und Fehlermeldungen) steht beim **[Configurator](Multiconfigurator/readme.md)** · [English](Multiconfigurator/readme_EN.md) · [Français](Multiconfigurator/readme_FR.md)

## So ist das System aufgebaut

| Shelly | Script | Aufgabe |
|---|---|---|
| **Controller-Shelly** | [Controller](Controller/readme.md) | regelt Laden und Entladen deiner Speicher |
| **Dashboard-Shelly** | [zenDash-API + Watchdog](zendash_watch_API_ZenSDK/readme.md) | liefert die Daten fürs Dashboard und meldet Akku voll, Übertemperatur, Unterspannung oder Ausfälle |

Auf jedem Shelly läuft **genau ein Script**. Shellys haben wenig Script-Speicher – zwei Scripte auf einem Gerät können sich gegenseitig zum Absturz bringen.

Das **[Dashboard](zendash_watch_API_ZenSDK/dashboard.md)** selbst ist eine Webseite, die du über einen kleinen Proxy auf PC, NAS oder Home Assistant öffnest.

## Weitere Werkzeuge

| Ordner | Wofür |
|---|---|
| [Script_poller](Script_poller/readme.md) | Langzeit-Messung von Speicher und CPU eines Shelly-Scripts, Log-Mitschnitt über Stunden (für Fehlersuche und Entwicklung) |
| [testController](testController/README.md) | Test-Umgebung für den Controller (für Entwickler) |

## Veraltet – bitte nicht mehr verwenden

Diese Ordner bleiben nur zum Nachschlagen erhalten und werden nicht mehr weiterentwickelt:

| Ordner | Ersetzt durch |
|---|---|
| AkkuWatchDogMulti, WatchdogZenSDK | [zenDash-API + Watchdog](zendash_watch_API_ZenSDK/readme.md) |
| zendash | [zenDash-API + Watchdog](zendash_watch_API_ZenSDK/readme.md) |
| Upload_Controller | [Configurator mit Helfer](Multiconfigurator/readme.md) (Direkt-Upload und Update) |
| Datenmonitor | – (rudimentärer Datenmonitor per MQTT und zenSDK, ohne Support) |

## Begriffe

| Begriff | Bedeutung |
|---|---|
| **Speicher** | dein Zendure-Gerät (SolarFlow 800, SolarFlow 2400 Pro …) |
| **Controller** | das Regel-Script `zerooutput_multi_kvs` |
| **Helfer** | kleines Programm für deinen Rechner, das den Configurator startet und die Scripte auf die Shellys lädt |
| **KVS** | Ablage im Shelly für Einstellungen, die du im laufenden Betrieb ändern kannst (z. B. aus dem Dashboard) |

Mehr Hintergrund steht im [Wiki](https://github.com/surfer1264/Zendure-Stuff/wiki).
