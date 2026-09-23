# Der Configurator

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

---
**Der Installer**

mit wenigen Klicks zur lokalen Steuerung deiner Zendure Flotte.

[diverse Installer hier runterladen](https://github.com/surfer1264/Zendure-Stuff/releases/latest) (macOS, Windows, Windows-x86 (32Bit))

oder [Windows-Exe:](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows.exe) direkt.

oder [Windows-Exe: 32Bit](https://github.com/surfer1264/Zendure-Stuff/releases/download/6.6.5/zendure_local_helper-windows-x86.exe) direkt.

oder [MACOS](https://github.com/surfer1264/Zendure-Stuff/releases/download/6.6.5/zendure_local_helper-macos) direkt.

Der **Installer** startet den Web-Configurator automatisch im Browser — **dann ist auch zusätzlich das direkte Hochladen und die Speicherprüfung freigeschaltet**

**Alternativ (ohne Shelly Upload Funktion) der Web-Configurator PUR**

[Multi Language Multi-Tool-Konfigurator ohne Shelly-Upload](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html)

## Was richtet der Configurator ein?

Für alle drei Tools erstellt der Configurator in einem einzigen Durchgang eine passende Konfiguration:

* **Controller** – die Regelmaschine
* **Watchdog** – meldet sich bei Regel- und Ausnahmesituationen
* **zenDash-API** – das kleine Dashboard mit Live-Überblick und der Möglichkeit, das Verhalten des Controllers zu ändern

Jedes der drei Tools kann eigenständig laufen oder zusammen mit den anderen eingesetzt werden. Jedes braucht dafür seine eigene Konfiguration – vieles darin ist aber gleich (z. B. die Geräteliste). Der Configurator fragt die wichtigsten, vor allem geräteabhängigen Angaben deshalb nur einmal ab und erstellt daraus passend für jedes ausgewählte Tool eine eigene Konfiguration.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/487e63fb-734d-4bb1-b795-19f81921acb6" />


## Ersteinrichtung

Am Ende bietet dir der Configurator für jedes ausgewählte Tool mehrere Wege an:

**Speichern der eigenen Config**

Die Konfiguration zum Kopieren in die Zwischenablage oder als kleine Datei zum Speichern – für alle, die ein Shelly-Script bereits selbst angepasst haben oder lieber von Hand arbeiten. Die vorhandene (Platzhalter-)Konfiguration im eigenen Script wird damit ersetzt.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/1ccd9b90-9d83-42b8-892b-932ad12df4db" />

**Speichern des gesamten Scripts**

Ein Klick auf den Button lädt das passende Original-Script direkt von GitHub herunter, trägt deine Konfiguration automatisch darin ein und bietet dir das fertige, sofort einsatzbereite Script zum Speichern an. Du musst es danach nur noch auf deinen Shelly hochladen – fertig. Dafür brauchst du kurz eine Internetverbindung.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/d839f5b2-7433-4941-977c-a7c173ab7af2" />

**Uploadfunktion auf den Shelly**

Läuft der [lokale Helfer](#der-lokale-helfer), entfällt auch dieser letzte manuelle Schritt: Ziel-IP eintragen, „Direkt hochladen" klicken – fertig, kein Copy & Paste im Shelly-eigenen Skripteditor mehr nötig. Jedes der drei Scripts kann dabei auf ein eigenes Zielgerät gehen. Ohne laufenden Helfer bleibt im Configurator selbst eine aufklappbare Schritt-für-Schritt-Anleitung für den manuellen Weg verfügbar.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/5082cdf4-1a6c-43a1-825c-8fc51bf18173" />

**Speicherprüffunktion eines Shelly**

Ebenfalls über den lokalen Helfer: IP eines beliebigen Shelly eintragen, „Speicher prüfen" klicken – zeigt, wie viel freier Skript-/Laufzeitspeicher (`mem_free`) auf dem Gerät noch da ist, bevor man ein weiteres Script hochlädt. Mehr dazu unter [Restriktionen](#restriktionen).

<img width="800" alt="image" src="https://github.com/user-attachments/assets/49d74a5d-cfd2-4541-932f-54c40b60ff5b" />

### Der lokale Helfer

Ein optionales, separat herunterladbares Programm (Windows/macOS), das lokal auf dem eigenen Rechner läuft, den Configurator automatisch im Browser öffnet und Direct-Upload sowie Speicherprüfung erst ermöglicht (löst das CORS-Problem der Shelly-Firmware). Kein Python-Setup nötig – einmal von der [Releases-Seite](https://github.com/surfer1264/Zendure-Stuff/releases/latest) herunterladen und starten.

* **Windows:** Meldet der Download beim ersten Start „Windows hat den Computer geschützt" (SmartScreen), auf „Weitere Informationen“ → „Trotzdem ausführen“ klicken.
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

**macOS (Terminal):**

```bash
shasum -a 256 -c zendure_local_helper-macos.sha256
```

Prüft automatisch gegen die mitgelieferte `.sha256`-Datei. `OK` bedeutet: passt genau, `FAILED` bedeutet: nicht ausführen, Datei neu herunterladen.

## Update

**Übernahme der eigenen Konfiguration**

Eine bestehende Konfiguration lässt sich jederzeit wieder in den Configurator einlesen, statt alles neu einzugeben. Dabei bleiben nicht nur die im Wizard sichtbaren Angaben erhalten, sondern auch von Hand feinjustierte Werte, die der Configurator selbst gar nicht direkt abfragt (z. B. `hysteresis`, `dampingFactor`, die `discharge`-/`charge`-Schwellen) – sie werden übernommen statt auf ihren Standardwert zurückgesetzt. Gleiche Angaben (z. B. die Geräteliste) bleiben dabei automatisch über alle drei Tools hinweg konsistent, und die `hysteresis` von zenDash-API folgt dabei immer der des Controllers, falls beide gemeinsam konfiguriert werden.

**Wichtig:** Bei jedem Update eines Shelly-Scripts sollte dieser Schritt wiederholt werden, damit deine Konfiguration erhalten bleibt.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/e23c3b85-03a4-4502-9868-81c742d8e7c5" />


## Restriktionen

**Speicher des Shelly**

Shelly-Geräte sind unterschiedlich mit Skript- und Laufzeitspeicher ausgestattet. Mit der Speicherprüffunktion lässt sich das vorab checken: `mem_free` ab 25200 Bytes bedeutet, der volle Standard-Heap ist frei – dann ist alles gut.

**Controller läuft nur allein**

Aus Speichergründen darf der Controller nie zusammen mit Watchdog oder zenDash-API auf demselben Shelly laufen. Watchdog und zenDash-API dürfen sich dagegen problemlos ein zweites Gerät teilen. Der Configurator weist direkt auf der ersten Seite (Produktauswahl) darauf hin.
