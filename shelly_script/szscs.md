🌐 **Deutsch** · [English](szscs_EN.md) · [Français](szscs_FR.md)

# Simple Zendure Shelly Cloudless System

**Buy me a coffee!**

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

<img width="800" alt="image" src="https://github.com/user-attachments/assets/0267db3d-7941-472e-87de-e134ada66dea" />

* Du hast **einen** oder **mehrere** SolarFlow (SF800 oder neuer, zenSDK-fähig)?
* Du hast einen Shelly Pro 3EM oder ein anderes Smartmeter mit lokaler Schnittstelle?, siehe [Kompatibil?](#shelly-und-smartmeter)
* Du willst eine lokale Regelung – ohne Cloud?
* Du willst wenig Aufwand und etwas, das einfach funktioniert?
* Home Assistant & Co. sind (noch) keine Option für dich?

_Prinzip_: **Install** – **Run** – **Forget**

🎉 HERE YOU ARE 🎉

---

## 👉 So startest du

1. **Helfer/Installer herunterladen** (siehe [Downloads](#downloads)) und starten. Der Configurator öffnet sich im Browser.
2. **„Neu konfigurieren“** wählen und die Fragen zu deinen Speichern, deinem Smartmeter und den Benachrichtigungen beantworten.
3. Am Ende **„⚡ Direkt hochladen“** – die Scripte landen fertig eingerichtet auf deinen beiden Shellys.

Nach 10 Minuten läuft Deine Regelung!

Ausführliche Anleitung: **[Configurator](Multiconfigurator/readme.md)**

## Du bist Dir noch unsicher?

Lies diese Prinzipien, an die sich das Projekt hält:

[Prinzipien](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-Multi-Device-Controller-%E2%80%90-Prinzipien-erkl%C3%A4rt)

und wie ich Qualität sicherstelle

[Insight Development](https://github.com/surfer1264/Zendure-Stuff/wiki/Multi-Controller-Development-%E2%80%90-Inside-%E2%80%90)



---

## Was du brauchst

* **Zwei Shellys** (Gen2 oder neuer). Idealerweise ist einer davon ein **Shelly Pro 3EM** – der misst dann gleich den Netzbezug. Alternativ ein anderes Smartmeter mit JSON-Schnittstelle, z. B. Zendure Smart Meter 3CT, ein Tasmota-Lesekopf oder ein Shelly 3EM (ohne Pro).
* Die **IP-Adressen** deiner SolarFlow und Shellys – am besten im Router fest vergeben.
* Einen **Windows-PC oder Mac** für den Helfer. Ohne Helfer reicht jeder Browser.
* **Optional für Benachrichtigungen:** einen kostenlosen API-Key von [CallMeBot](https://www.callmebot.com) für Signal oder WhatsApp – oder einen Webhook, z. B. in Home Assistant.

**Wichtig:** Die SolarFlow in der Zendure-App aus dem **HEMS** entfernen, sonst schickt die Cloud parallel eigene Steuerbefehle.

---

## Drei Funktionen auf zwei Shellys – ohne Cloud

| Shelly | Script | Aufgabe |
|---|---|---|
| **Controller-Shelly** | Controller (`zerooutput_multi_kvs`) | regelt Laden und Entladen deiner SolarFlow |
| **Dashboard-Shelly** | zenDash-API + Watchdog (`zendash_watch`) | liefert die Daten fürs Dashboard und verschickt Meldungen – beide Funktionen einzeln abschaltbar |

Auf jedem Shelly läuft **genau ein Script**. Shellys haben wenig Script-Speicher – deshalb laufen Controller und Dashboard-Script immer auf zwei getrennten Geräten.

### 1. Der Controller – die Regelung

* regelt auf einen **Sollwert** (z. B. 0 W Netzbezug)
* mit **Hysterese** und **Dämpfung**, damit nichts pendelt
* **Laden & Entladen**, verteilt auf alle SolarFlow
* Einstellungen im laufenden Betrieb änderbar (KVS) – aus dem Dashboard oder z. B. aus Home Assistant

📖 [Getting Started](Controller/readme.md) · [Benutzerdokumentation](Controller/benutzerdoku.md) · [Alle Details](Controller/gesamtdoku.md)


### 2. Das Dashboard – der Überblick

* **Live-Anzeige** von Netzbezug, Ladestand und Leistung je SolarFlow
* **Eingreifen:** Sollwert, Reserve (minSoc), Entladen/Laden erlauben, feste Entladeleistung
* **Manuelles Laden mit Auto-Stop** – ist der Akku voll, geht der SolarFlow von selbst zurück in die Regelung (auch bei geschlossenem Dashboard)
* **„100 %: vor N Tagen“** – zeigt, wann jeder Akku zuletzt ganz voll war
* auf Deutsch, Englisch und Französisch, am PC, Tablet oder Handy

Das Dashboard ist eine Webseite, die über einen kleinen **Proxy** läuft – als fertiges Programm für Windows und Mac (siehe [Downloads](#downloads)), als Python-Script, auf einer Synology oder als App in Home Assistant.

📖 [Dashboard einrichten und bedienen](zendash_watch_API_ZenSDK/dashboard.md)

### 3. Der Watchdog – die Meldungen

* **Morgen- und Abend-Übersicht** mit Ladestand, Temperatur und Zellspannung
* Meldung bei **Akku voll**
* **Warnung** bei zu niedriger Zellspannung oder zu hoher Temperatur
* Meldung, wenn ein SolarFlow **nicht erreichbar** ist – und Entwarnung, sobald er wieder da ist
* Hinweis, wenn ein Akku **seit 20 Tagen nicht mehr voll** war
* Versand per **Signal**, **WhatsApp** oder **Webhook**; je SolarFlow einstellbar, ob er überwacht wird

📖 [zenDash-API + Watchdog](zendash_watch_API_ZenSDK/readme.md)

---

## Aufbau

### Mit Shelly Pro 3EM

Der Pro 3EM ist gleichzeitig der Controller-Shelly. Dazu kommt ein zweiter Shelly als Dashboard-Shelly.

<img width="350" alt="IMG_1246" src="https://github.com/user-attachments/assets/c8821089-7e87-437f-ad29-6715f1554cfb" />

### Mit einem anderen Smartmeter

Der Controller läuft auf einem beliebigen Shelly und liest das Smartmeter über das Netzwerk. Dazu kommt der Dashboard-Shelly – auch hier also zwei Shellys.

<img width="600" alt="IMG_1247" src="https://github.com/user-attachments/assets/4758a842-f361-47d7-8260-c23fc1ae1bde" />

---

## Downloads

**Helfer mit Configurator** – richtet alles ein, lädt die Scripte auf die Shellys, macht Updates, prüft den Speicher und zeichnet bei Problemen ein Log auf. Keine Installation nötig: herunterladen, starten, fertig.

| Helfer | für |
|---|---|
| **[⬇️ zendure_local_helper-windows.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows.exe)** | Windows 64 Bit |
| **[⬇️ zendure_local_helper-windows-x86.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows-x86.exe)** | Windows 32 Bit |
| **[⬇️ zendure_local_helper-macos](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-macos)** | Mac mit Apple Silicon (M1 oder neuer) |

**Dashboard-Proxy** – öffnet das Dashboard im Browser, ohne Python-Installation.

| Dashboard-Proxy | für |
|---|---|
| **[⬇️ zendure_proxy-windows.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-windows.exe)** | Windows 64 Bit |
| **[⬇️ zendure_proxy-macos](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-macos)** | Mac mit Apple Silicon (M1 oder neuer) |

Beim ersten Start warnt dein Betriebssystem, weil die Dateien nicht signiert sind – wie du sie trotzdem startest, steht im [Configurator](Multiconfigurator/readme.md#empfohlen-der-lokale-helfer-exe-installer). Alle Dateien und Prüfsummen: [Releases](https://github.com/surfer1264/Zendure-Stuff/releases/latest).

**Ohne Helfer:** Der [Web-Configurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html) läuft direkt im Browser. Damit konfigurierst du alles und speicherst das fertige Script – hochladen musst du es dann selbst über die Weboberfläche des Shelly. Update, Speicherprüfung und Log-Aufzeichnung gibt es nur mit dem Helfer.

---

## Update

Gibt es eine neue Version, startest du den Helfer und wählst **„Updaten“**. Er vergleicht die Versionen auf deinen Shellys mit GitHub, liest deine Einstellungen direkt vom Shelly und spielt die neue Version ein – deine Einstellungen bleiben erhalten.

Nutzt du das Dashboard, hol dir nach einem Update auch den neuen Dashboard-Proxy bzw. die neue Dashboard-Seite: Beide müssen dieselbe Versionsnummer haben wie das Script.

**Umstieg von den alten Einzelscripten:** Früher waren zenDash-API und Watchdog zwei getrennte Scripte. Wie du auf das gemeinsame Script umsteigst, steht im [Configurator](Multiconfigurator/readme.md#umstieg-von-den-alten-einzelscripten).

---

**Achtung:** Der Configurator ersetzt nicht den Blick in die Dokumentation – vor allem bei den Regelparametern.

## Shelly und Smartmeter

- **Shelly-Gen2/4-Geräten** mit Script-Engine und ausreichendem Script-Speicher
  - Shelly 3EMPro - erfolgreich getestet
  - Shelly 3EM-63W Gen3 - erfolgreich getestet
  - Shelly 3EM 3ct63 - erfolgreich getestet
  - Shelly 1PM Gen4 - erfolgreich getestet
  - Shelly PM1Plus - erfolgreich getestet (Vorgänger von 1PM Gen3)
  - Shelly Plus PlugS - erfolgreich getestet
  - Shelly PlugS Gen3 - **nicht** erfolgreich getestet (out of memory)
  - Shelly 1PM Gen3 - **nicht** erfolgreich getestet (out of memory)
  - Shelly Mini gen3 - **nicht** erfolgreich getestet (out of memory)
- Einen **Smartmeter** für den aktuellen Netz-Leistungswert (siehe **Kapitel 5** für Details
  je Betriebsart).
  - Shelly 3EMPro (beste Wahl, weil der lokal ohne Netzwerkrequest ausgelesen wird , wenn der Controller zeigleich auf dem Shelly läuft)
  - Zendure D0
  - Zendure CT
  - Tasmota
  - alle Shelly 3EM (mit und ohne Pro)
  - alle **REST API** fähigen Smartmeter, **Ecotracker**….  
- **HEMS-Kopplung entfernen:** Alle Zendure-Geräte müssen in der Zendure-App
  **aus dem HEMS (Home Energy Management System)** entfernt werden, da sonst
  die App/Cloud parallel eigene Steuerbefehle sendet und mit diesem Script
  kollidiert.

## Fazit

* Alles lokal
* Flexibel
* keine Cloud
* keine Ausreden mehr: „Mein System geht nicht, die Cloud ist wieder kaputt“
* für alle Hubs mit zenSDK
