:de: **Deutsch** · [:gb: English](architektur_EN.md) · [:fr: Français](architektur_FR.md)

# So arbeiten die Teile zusammen

Die Suite trennt fünf Bereiche – im Bild hat jeder seine eigene Farbe:

| Farbe | Bereich | Was gehört dazu |
|---|---|---|
| Bernstein | **Hardware, die gesteuert wird** | deine Zendure-Speicher |
| Blau | **Hardware für den Betrieb** | Shelly 1, Shelly 2, Smartmeter |
| Türkis | **Software für den Betrieb** | Controller-Script, zendash_watch-Script |
| Lila | **Software zur Bedienung** | Dashboard, Dashboard-Proxy, Home Assistant, Statistik, Meldungen |
| Grau | **Software zur Installation** | Configurator mit Helfer |

Für die Regelung braucht es nur Bernstein, Blau und Türkis. Alles Lilane ist Komfort und darf ausfallen. Grau wird nur beim Einrichten und bei Updates gebraucht. Alles läuft in deinem Heimnetz – eine Cloud brauchst du nicht.

![Architektur der Shelly Suite](img/architektur.svg)

## Hardware, die gesteuert wird: die Speicher

Deine Zendure-Speicher haben eine eingebaute lokale Schnittstelle, das **zenSDK**. Die Scripte sprechen sie direkt über die IP-Adresse an:

- `/properties/report` liefert Ladestand, Leistungen, Zellspannung, Temperatur und Grenzen wie `minSoc`.
- `/properties/write` nimmt Vorgaben an, z. B. Laden oder Entladen und mit wie viel Watt. Der Controller setzt dabei `smartMode: 1`, damit die häufigen Vorgaben nicht in den Flash-Speicher des Geräts geschrieben werden.

Für den laufenden Betrieb brauchen die Speicher kein Internet. Du kannst ihnen den Zugang im Router sperren.

## Hardware für den Betrieb: Shellys und Smartmeter

**Smartmeter** – Der Controller muss wissen, wie viel gerade aus dem Netz kommt oder hineingeht. Am einfachsten ist ein **Shelly Pro 3EM** – dann sind Smartmeter und Shelly 1 dasselbe Gerät. Alternativ wird ein anderes Smartmeter über das Netzwerk gelesen (`http_json`), siehe [Controller](Controller/readme.md).

**Shelly 1 (Controller-Shelly)** – trägt das Controller-Script und dessen Einstellungen (KVS).

**Shelly 2 (Dashboard-Shelly)** – trägt das zendash_watch-Script.

Auf jedem Shelly läuft **genau ein Script**. Shellys haben wenig Script-Speicher; zwei Scripte auf einem Gerät können sich gegenseitig zum Absturz bringen. Deshalb sind es immer zwei Shellys.

Tipp: Gib Speichern und Shellys im Router feste IP-Adressen.

### Zwei Varianten

**Mit Shelly Pro 3EM** – Der Pro 3EM ist Smartmeter und Shelly 1 zugleich. Dazu kommt Shelly 2.

<img width="350" alt="IMG_1246" src="https://github.com/user-attachments/assets/c8821089-7e87-437f-ad29-6715f1554cfb" />

**Mit einem anderen Smartmeter** – Shelly 1 ist ein beliebiger Shelly und liest das Smartmeter über das Netzwerk. Dazu kommt Shelly 2 – auch hier also zwei Shellys.

<img width="600" alt="IMG_1247" src="https://github.com/user-attachments/assets/4758a842-f361-47d7-8260-c23fc1ae1bde" />

## Software für den Betrieb: zwei Scripte

**Controller-Script** (auf Shelly 1) regelt. Es liest alle paar Sekunden die Netzleistung vom Smartmeter und verteilt Laden und Entladen auf deine Speicher, sodass möglichst nichts eingespeist und nichts bezogen wird. Es arbeitet völlig selbstständig.

**KVS** – Die Einstellungen, die du im laufenden Betrieb änderst (Sollwert, Reserve, Entladen erlaubt …), liegen in der KVS von Shelly 1. Das Controller-Script liest sie in jedem Regelzyklus – Änderungen wirken also nach wenigen Sekunden, ohne Neustart. Die KVS ist die einzige Stelle, an der die Bedienung in die Regelung eingreift.

**zendash_watch-Script** (auf Shelly 2) zeigt an und passt auf. Es liest die Reports der Speicher, liefert die Daten fürs Dashboard und schreibt Änderungen aus dem Dashboard in die KVS des Controllers (`KVS.Set`). Als Watchdog überwacht es deine Speicher und meldet Akku voll, Übertemperatur, Unterspannung oder Ausfall. Fällt die Zellspannung unter die Schwelle, sperrt es zusätzlich das Entladen.

## Software zur Bedienung

**Dashboard-Proxy** – ein kleines Programm auf PC, Raspberry Pi, NAS oder als Home-Assistant-App. Es stellt das [Dashboard](zendash_watch_API_ZenSDK/dashboard.md) bereit und leitet dessen Anfragen an das zendash_watch-Script weiter. Der Browser spricht also nie direkt mit den Shellys.

**Dashboard (SMDC)** – die Webseite im Browser oder als App auf dem Handy-Startbildschirm: Live-Werte, Sollwert, Reserve, manuelles Laden.

**Meldungen** – Das zendash_watch-Script schickt Warnungen per Signal, WhatsApp oder Webhook.

**Cloud-Statistik (optional)** – Der Proxy schickt auf Wunsch jede Minute die Messwerte an [ThingSpeak](zendash_watch_API_ZenSDK/thingspeak.md) und/oder [ThingsBoard](zendash_watch_API_ZenSDK/thingsboard.md) – auch selbst betrieben im Heimnetz. Übertragen werden nur Messwerte, keine Namen, Adressen oder Seriennummern. Ist kein Upload eingeschaltet, fragt der Proxy nichts ab. Für lückenlose Verläufe muss er dauerhaft laufen (NAS oder Home Assistant).

**Home Assistant (optional)** – liest und schreibt die KVS des Controllers direkt per REST (`KVS.GetMany`, `KVS.Set`). So kannst du Sollwert, Reserve & Co. auch aus Automationen steuern.

## Software zur Installation

Der **[Configurator](Multiconfigurator/readme.md)** mit Helfer läuft auf deinem Rechner. Er prüft den freien Speicher der Shellys, erzeugt die Einstellungen, lädt die Scripte von GitHub und spielt sie auf beide Shellys. Für Updates vergleicht er die Versionen auf den Shellys mit den aktuellen auf GitHub. Im Alltag wird er nicht gebraucht.

## Was passiert, wenn etwas ausfällt?

| Fällt aus … | Bereich | Folge |
|---|---|---|
| Proxy oder PC | Bedienung | Kein Dashboard, keine Statistik. **Die Regelung läuft weiter.** |
| Internet | – | Keine Statistik, keine Meldungen per Signal/WhatsApp. Regelung und Dashboard laufen weiter. |
| Shelly 2 (zendash_watch) | Betrieb | Kein Dashboard, keine Meldungen. **Die Regelung läuft weiter.** |
| Ein Speicher | gesteuert | Der Controller regelt mit den übrigen weiter, der Watchdog meldet den Ausfall. |
| Shelly 1 (Controller) | Betrieb | Keine Regelung mehr. Das Dashboard kann keine Einstellungen mehr ändern. |

## Weiterlesen

- [Was die Suite kann](szscs.md)
- [Controller](Controller/readme.md) · [Controller im Alltag](Controller/benutzerdoku.md)
- [zenDash-API + Watchdog](zendash_watch_API_ZenSDK/readme.md) · [API-Referenz](zendash_watch_API_ZenSDK/API.md)
- [Kompatible Geräte](kompatible_geraete.md) · [Speicherbedarf](zendash_speichermodell.md)
