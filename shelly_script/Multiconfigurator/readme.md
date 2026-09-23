# Der Configurator

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

---
**Der Installer**

mit wenigen Klicks zur lokalen Steuerung deiner Zendure Flotte.

[diverse Installer hier runterladen](https://github.com/surfer1264/Zendure-Stuff/releases/latest) (macOS, Windows, Windows-x86 (32Bit))

oder [Windows-Exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows.exe) direkt.

oder [Windows-Exe 32Bit](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows-x86.exe) direkt.

oder [macOS](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-macos) direkt.

Der **Installer** startet den Web-Configurator automatisch im Browser — **dann ist auch zusätzlich das direkte Hochladen und die Speicherprüfung freigeschaltet**

**Alternativ (ohne Shelly Upload Funktion) der Web-Configurator PUR**

[Multi Language Multi-Tool-Konfigurator ohne Shelly-Upload](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html)

## Was richtet der Configurator ein?

Das System besteht immer aus **zwei Shellys**:

| Shelly | Script | Aufgabe |
|---|---|---|
| **Controller-Shelly** | Controller (`zerooutput_multi_kvs`) | die Regelmaschine – hält außerdem die KVS mit den live änderbaren Einstellungen |
| **Dashboard-Shelly** | zenDash-API + Watchdog (`zendash_watch`) | ein gemeinsames Script mit zwei einzeln abschaltbaren Funktionen |

Darauf laufen drei Funktionen:

* **Controller** – die Regelmaschine
* **zenDash-API** – liefert die Daten für das kleine Dashboard mit Live-Überblick und der Möglichkeit, das Verhalten des Controllers zu ändern
* **Watchdog** – meldet sich bei Regel- und Ausnahmesituationen (Akku voll, Temperatur, Zellspannung, Gerät nicht erreichbar) und schickt morgens und abends eine Übersicht

Die drei Funktionen sind frei kombinierbar – zenDash-API und Watchdog lassen sich zum Beispiel auch ohne Controller einrichten, wenn dieser schon läuft. Vieles in den Konfigurationen ist gleich (z. B. die Geräteliste, die Netzquelle, die Benachrichtigungen). Der Configurator fragt diese Angaben deshalb nur einmal ab und erstellt daraus passend die Konfiguration für den Controller-Shelly und für den Dashboard-Shelly.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/487e63fb-734d-4bb1-b795-19f81921acb6" />

### Der Ablauf

1. **Start** – Funktionen auswählen, die **IP-Adressen beider Shellys** eintragen, optional eine bestehende Konfiguration einlesen
2. **Geräte** – deine Zendure-Speicher, je Gerät mit Häkchen „Watchdog überwacht dieses Gerät“
3. **Netzquelle** – woher die Netzleistung kommt (Pro 3EM am Controller-Shelly, ein anderer Pro 3EM oder ein JSON-Messgerät)
4. **Laden vom Netz** – welche Geräte Überschuss aufnehmen dürfen
5. **Benachrichtigungen** – Webhook, Signal oder WhatsApp, gilt für Controller und Watchdog gemeinsam
6. **Controller-Einstellungen** – Verhalten bei vollem Akku, KVS-Fernsteuerung
7. **Regelparameter** – Sollwert, Hysterese sowie `concentrateBelow`/`spreadAbove` für Entladen und Laden, vorausgefüllt
8. **Ergebnis** – Zusammenfassung mit den **Versionsnummern** von Controller, zenDash-API und Watchdog sowie die fertigen Konfigurationen

Schritte, die für deine Auswahl nicht nötig sind, werden übersprungen.

**Die beiden Shelly-IPs** landen in beiden Konfigurationen im Block `runtime`. Beim nächsten Einlesen musst du sie nicht erneut eingeben, und der Direkt-Upload weiß automatisch, welches Script auf welchen Shelly gehört.

**Zu den Regelparametern:** Die Werte werden aus deiner eingelesenen Controller-Konfiguration bzw. per Faustformel aus deiner Geräteliste vorbelegt. Sie werden danach **nicht** automatisch nachgeführt, wenn du Geräte oder Leistungen änderst – Änderungen liegen in deiner Verantwortung. Bedeutung und Empfehlungen stehen in der [Controller-Dokumentation](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/readme.md).

**Ohne KVS:** Schaltest du die KVS-Fernsteuerung des Controllers aus, kann das Dashboard nur noch anzeigen – Einstellungen aus dem Dashboard wirken dann nicht auf den Controller.


## Ersteinrichtung

Am Ende bietet dir der Configurator für jeden der beiden Shellys mehrere Wege an:

**Speichern der eigenen Config**

Die Konfiguration zum Kopieren in die Zwischenablage oder als kleine Datei zum Speichern – für alle, die ein Shelly-Script bereits selbst angepasst haben oder lieber von Hand arbeiten. Die vorhandene (Platzhalter-)Konfiguration im eigenen Script wird damit ersetzt.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/1ccd9b90-9d83-42b8-892b-932ad12df4db" />

**Speichern des gesamten Scripts**

Ein Klick auf den Button lädt das passende Original-Script direkt von GitHub herunter, trägt deine Konfiguration automatisch darin ein und bietet dir das fertige, sofort einsatzbereite Script zum Speichern an. Du musst es danach nur noch auf deinen Shelly hochladen – fertig. Dafür brauchst du kurz eine Internetverbindung.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/d839f5b2-7433-4941-977c-a7c173ab7af2" />

**Uploadfunktion auf den Shelly**

Läuft der [lokale Helfer](#der-lokale-helfer), entfällt auch dieser letzte manuelle Schritt: „Direkt hochladen“ klicken – fertig. Das Ziel ist die IP aus dem ersten Schritt: das Controller-Script geht auf den Controller-Shelly, zenDash-API + Watchdog auf den Dashboard-Shelly. Das Script wird angelegt (bzw. ein gleichnamiges ersetzt), gestartet und für den Autostart eingerichtet – kein Copy & Paste im Shelly-eigenen Skripteditor mehr nötig. Ohne laufenden Helfer bleibt im Configurator eine aufklappbare Schritt-für-Schritt-Anleitung für den manuellen Weg verfügbar.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/5082cdf4-1a6c-43a1-825c-8fc51bf18173" />

**Speicherprüffunktion eines Shelly**

Ebenfalls über den lokalen Helfer: IP eines beliebigen Shelly eintragen, „Speicher prüfen“ klicken – zeigt, wie viel freier Skript-/Laufzeitspeicher (`mem_free`) auf dem Gerät noch da ist, bevor man ein weiteres Script hochlädt. Mehr dazu unter [Restriktionen](#restriktionen).

<img width="800" alt="image" src="https://github.com/user-attachments/assets/49d74a5d-cfd2-4541-932f-54c40b60ff5b" />

### Der lokale Helfer

Ein optionales, separat herunterladbares Programm (Windows/macOS), das lokal auf dem eigenen Rechner läuft, den Configurator automatisch im Browser öffnet und Direct-Upload sowie Speicherprüfung erst ermöglicht (löst das CORS-Problem der Shelly-Firmware). Kein Python-Setup nötig – einmal von der [Releases-Seite](https://github.com/surfer1264/Zendure-Stuff/releases/latest) herunterladen und starten. Das Fenster des Helfers muss offen bleiben, solange du hochlädst.

* **Windows:** Meldet der Download beim ersten Start „Windows hat den Computer geschützt“ (SmartScreen), auf „Weitere Informationen“ → „Trotzdem ausführen“ klicken.
* **macOS:** Rechtsklick auf die Datei → „Öffnen“ → im Dialog erneut „Öffnen“ bestätigen (Gatekeeper), da die Datei nicht signiert ist.

#### Integrität prüfen (optional)

Zu jeder `.exe`/`macos`-Datei liegt auf der [Releases-Seite](https://github.com/surfer1264/Zendure-Stuff/releases/latest) eine gleichnamige `.sha256`-Datei als eigenes Asset. Damit lässt sich nachprüfen, dass die heruntergeladene Datei wirklich unverändert die ist, die der Build-Workflow erzeugt hat – unabhängig von SmartScreen/Gatekeeper.

**Windows (PowerShell):**

```powershell
Get-FileHash .\zendure_local_helper-windows.exe -Algorithm SHA256
Get-Content .\zendure_local_helper-windows.exe.sha256
```

Die ersten 64 Zeichen aus beiden Ausgaben vergleichen (Groß-/Kleinschreibung egal) – oder als Ein-Zeiler, der direkt `True`/`False` ausgibt:

```powershell
(Get-FileHash .\zendure_local_helper-windows.exe -Algorithm SHA256).Hash -eq (Get-Content .\zendure_local_helper-windows.exe.sha256).Split(' ')[0]
```

Für die 32-Bit-Version entsprechend `zendure_local_helper-windows-x86.exe` einsetzen.

**macOS (Terminal):**

```bash
shasum -a 256 -c zendure_local_helper-macos.sha256
```

Prüft automatisch gegen die mitgelieferte `.sha256`-Datei. `OK` bedeutet: passt genau, `FAILED` bedeutet: nicht ausführen, Datei neu herunterladen.

## Update

**Übernahme der eigenen Konfiguration**

Eine bestehende Konfiguration lässt sich jederzeit wieder in den Configurator einlesen, statt alles neu einzugeben. Eingelesen werden die Konfiguration des **Controllers** und die von **zenDash-API + Watchdog** – am besten beide nacheinander; die Reihenfolge ist egal. Die Shelly-IPs kommen dabei aus dem Block `runtime`.

Dabei bleiben nicht nur die im Wizard sichtbaren Angaben erhalten, sondern auch Werte, die der Configurator gar nicht abfragt (z. B. `dampingFactor`, `interval` oder die Warnschwellen des Watchdog) – sie werden aus der eingelesenen Konfiguration übernommen; fehlt ein Wert dort, gilt der Standardwert. Gleiche Angaben (z. B. die Geräteliste) bleiben automatisch über beide Konfigurationen hinweg konsistent, und die `hysteresis` der zenDash-API folgt immer der des Controllers, falls beide gemeinsam konfiguriert werden.

**Wichtig:** Bei jedem Update eines Shelly-Scripts sollte dieser Schritt wiederholt werden, damit deine Konfiguration erhalten bleibt.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/e23c3b85-03a4-4502-9868-81c742d8e7c5" />

**Umstieg von den alten Einzelscripten**

zenDash-API und Watchdog sind jetzt **ein** Script (`zendash_watch`). Konfigurationen der alten Einzelscripte (zenDash-API 2.x, Watchdog 1.x) lassen sich **nicht** mehr einlesen – lies stattdessen die Controller-Konfiguration ein, sie liefert Geräte, Netzquelle und Benachrichtigungen; den Rest ergänzt du im Assistenten.

Nach dem Hochladen die **alten Scripte stoppen und deren Autostart ausschalten** – sonst laufen sie parallel weiter und Meldungen kommen doppelt. Der Direkt-Upload ersetzt automatisch nur eine alte zenDash-API, die früher ebenfalls über den Helfer (Script-Name `zd`) installiert wurde.


## Restriktionen

**Speicher des Shelly**

Shelly-Geräte sind unterschiedlich mit Skript- und Laufzeitspeicher ausgestattet. Mit der Speicherprüffunktion lässt sich das vorab checken: `mem_free` ab 25200 Bytes bedeutet, der volle Standard-Heap ist frei – dann ist alles gut.

Zur Orientierung, gemessen mit zwei Speichern: Das gemeinsame Script zenDash-API + Watchdog belegt im Betrieb rund 13,5 kB, in der Spitze rund 17,8 kB.

**Immer zwei Shellys**

Aus Speichergründen läuft der Controller immer allein auf dem Controller-Shelly – nie zusammen mit zenDash-API oder Watchdog auf demselben Gerät. zenDash-API und Watchdog laufen gemeinsam in einem Script auf dem Dashboard-Shelly. Der Configurator prüft im ersten Schritt, dass zwei verschiedene IP-Adressen eingetragen sind.