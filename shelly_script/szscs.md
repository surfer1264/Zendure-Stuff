:de: **Deutsch** · [:gb: English](szscs_EN.md) · [:fr: Français](szscs_FR.md)

# Simple Zendure Shelly Cloudless System

**Buy me a coffee!**

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

<img width="800" alt="image" src="https://github.com/user-attachments/assets/0267db3d-7941-472e-87de-e134ada66dea" />

* Du hast **einen** oder **mehrere** SolarFlow (SF800 oder neuer, zenSDK-fähig)?
* Du hast einen Shelly Pro 3EM oder ein anderes Smartmeter mit lokaler Schnittstelle?, siehe [Kompatible Geräte](kompatible_geraete.md)
* Du willst eine lokale Regelung – ohne Cloud?
* Du willst wenig Aufwand und etwas, das einfach funktioniert?
* Home Assistant & Co. sind (noch) keine Option für dich?

_Prinzip_: **Install** – **Run** – **Forget**

🎉 HERE YOU ARE 🎉

---

## Drei Funktionen auf zwei Shellys – ohne Cloud

Auf dem **Controller-Shelly** läuft die Regelung, auf dem **Dashboard-Shelly** zenDash-API und Watchdog – beide Funktionen dort einzeln abschaltbar. Welches Script wohin gehört: [So ist das System aufgebaut](readme.md#so-ist-das-system-aufgebaut).

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

## 👉 So startest du

Helfer herunterladen, Fragen beantworten, hochladen – nach 10 Minuten läuft deine Regelung. Die drei Schritte stehen auf der **[Startseite](readme.md#-hier-starten)**, die ausführliche Anleitung beim **[Configurator](Multiconfigurator/readme.md)**.

## Du bist Dir noch unsicher?

Lies diese Prinzipien, an die sich das Projekt hält:

[Prinzipien](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-Multi-Device-Controller-%E2%80%90-Prinzipien-erkl%C3%A4rt)

und wie ich Qualität sicherstelle

[Insight Development](https://github.com/surfer1264/Zendure-Stuff/wiki/Multi-Controller-Development-%E2%80%90-Inside-%E2%80%90)

---

## Was du brauchst

Zwei Shellys (idealerweise einer davon ein **Shelly Pro 3EM**, der gleich den Netzbezug misst), ein Smartmeter und zenSDK-fähige SolarFlow im selben Netz. Welche Geräte passen und was sonst noch nötig ist, steht unter **[Kompatible Geräte](kompatible_geraete.md)**.

**Wichtig:** Die SolarFlow in der Zendure-App aus dem **HEMS** entfernen, sonst schickt die Cloud parallel eigene Steuerbefehle.

---

## Downloads

Alle Programme liegen auf der **[Releases-Seite](https://github.com/surfer1264/Zendure-Stuff/releases/latest)**. Was du wofür brauchst und wie du die Dateien beim ersten Start freigibst:

- **Helfer mit Configurator** – richtet alles ein, lädt die Scripte auf die Shellys, macht Updates: [Configurator → Download](Multiconfigurator/readme.md#empfohlen-der-lokale-helfer-exe-installer)
- **Dashboard-Proxy** – öffnet das Dashboard im Browser, ohne Python-Installation: [Dashboard → Als Programm](zendash_watch_API_ZenSDK/dashboard.md#als-programm-unter-windows-oder-macos)
- **Ohne Helfer:** der [Web-Configurator](Multiconfigurator/readme.md#alternative-nur-der-web-configurator) im Browser – hochladen musst du das Script dann selbst.

---

## Update

Helfer starten, **„Updaten“** wählen – deine Einstellungen bleiben erhalten. Details, auch zum Umstieg von den alten Einzelscripten: [Configurator → Update](Multiconfigurator/readme.md#4-update). Nutzt du das Dashboard, müssen Dashboard-Seite und Script dieselbe Versionsnummer haben ([Dashboard](zendash_watch_API_ZenSDK/dashboard.md)).

---

**Achtung:** Der Configurator ersetzt nicht den Blick in die Dokumentation – vor allem bei den Regelparametern.

## Shelly und Smartmeter

Getestete Shellys, unterstützte Smartmeter und wie du den Speicher deines Shelly selbst prüfst: **[Kompatible Geräte](kompatible_geraete.md)**.

## Fazit

* Alles lokal
* Flexibel
* keine Cloud
* keine Ausreden mehr: „Mein System geht nicht, die Cloud ist wieder kaputt“
* für alle Hubs mit zenSDK
