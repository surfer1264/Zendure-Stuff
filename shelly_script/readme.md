:de: **Deutsch** · [:gb: English](readme_EN.md) · [:fr: Français](readme_FR.md)

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

# Die Suite - Zendure-Speicher lokal steuern

Deine Zendure-Speicher (zenSDK-fähige Geräte ab SolarFlow 800) werden damit ohne Cloud geregelt: Ein Shelly hält deinen Netzbezug auf null, ein zweiter liefert die Daten für ein Dashboard und meldet sich, wenn etwas nicht stimmt. Was die Suite im Einzelnen kann: **[Was die Suite kann](szscs.md)**.

## 👉 Hier starten

1. **[Helfer herunterladen](https://github.com/surfer1264/Zendure-Stuff/releases/latest)** (Windows oder Mac mit Apple Silicon) und starten.
2. Im Browser öffnet sich der Configurator. **„Neu konfigurieren oder manuell updaten“** wählen und die Fragen beantworten.
3. Am Ende **„⚡ Direkt hochladen“** – fertig.

Die ausführliche Anleitung (auch zu Update, Shelly-Wechsel und Fehlermeldungen) steht beim **[Configurator](Multiconfigurator/readme.md)** · [English](Multiconfigurator/readme_EN.md) · [Français](Multiconfigurator/readme_FR.md)

## Was du brauchst

Zwei Shellys, ein Smartmeter und zenSDK-fähige Speicher – welche Geräte passen, steht unter **[Kompatible Geräte](kompatible_geraete.md)**. Wie viele Speicher das Dashboard-Script verkraftet, zeigt die [Speicherbedarfsbetrachtung](zendash_speichermodell.md).

## So ist das System aufgebaut

| Shelly | Script | Aufgabe |
|---|---|---|
| **Controller-Shelly** | [Controller](Controller/readme.md) | regelt Laden und Entladen deiner Speicher |
| **Dashboard-Shelly** | [zenDash-API + Watchdog](zendash_watch_API_ZenSDK/readme.md) | liefert die Daten fürs Dashboard und meldet Akku voll, Übertemperatur, Unterspannung oder Ausfälle |

Dazu kommt der **[Configurator](Multiconfigurator/readme.md)** mit Helfer auf deinem Rechner: Er übernimmt Erstkonfiguration, Update und Log-Aufzeichnung für beide Shellys.

Auf jedem Shelly läuft **genau ein Script**. Shellys haben wenig Script-Speicher – zwei Scripte auf einem Gerät können sich gegenseitig zum Absturz bringen.

Das **[Dashboard](zendash_watch_API_ZenSDK/dashboard.md)** selbst ist eine Webseite, die du über einen kleinen Proxy auf PC, NAS oder Home Assistant öffnest.

## Weitere Werkzeuge

| Ordner | Wofür |
|---|---|
| [Script_poller](Script_poller/readme.md) | Langzeit-Messung von Speicher und CPU eines Shelly-Scripts, Log-Mitschnitt über Stunden (für Fehlersuche und Entwicklung) |
| [thingsboard](thingsboard) | fertige Dashboards und Regelketten zum Import in ThingsBoard, passend zum [ThingsBoard-Upload](zendash_watch_API_ZenSDK/thingsboard.md) |
| [Einordnung](Einordnung.md) | Vergleich mit anderen Multi-Device-Lösungen (ioBroker, Z-HA, EMS SolarFlow …) |

## Begriffe

| Begriff | Bedeutung |
|---|---|
| **Speicher** | dein Zendure-Gerät (SolarFlow 800, SolarFlow 2400 Pro …) |
| **Controller** | das Regel-Script `zerooutput_multi_kvs` |
| **Helfer** | kleines Programm für deinen Rechner, das den Configurator startet und die Scripte auf die Shellys lädt |
| **KVS** | Ablage im Shelly für Einstellungen, die du im laufenden Betrieb ändern kannst (z. B. aus dem Dashboard) |

Mehr Hintergrund steht im [Systemüberblick (S-Z-S-C-S)](szscs.md).
