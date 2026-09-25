# Der Configurator

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

Mit wenigen Klicks zur lokalen Steuerung deiner Zendure-Flotte – einrichten, aktualisieren, fertig.

**Inhalt**

1. [Was richtet der Configurator ein?](#1-was-richtet-der-configurator-ein)
2. [Wo finde ich den Configurator?](#2-wo-finde-ich-den-configurator)
3. [Ersteinrichtung](#3-ersteinrichtung)
4. [Update](#4-update)
5. [Wechsel eines Shelly](#5-wechsel-eines-shelly)
6. [Fehlermeldungen und Problemsituationen](#6-fehlermeldungen-und-problemsituationen)
7. [How-Tos](#7-how-tos)

Was sich zuletzt geändert hat, steht im [Changelog](CHANGELOG.md).

---

## 1. Was richtet der Configurator ein?

Der Configurator ist ein Assistent, der dich Schritt für Schritt durch die Einrichtung deiner Zendure-Steuerung führt. Du beantwortest ein paar Fragen zu deinen Geräten – am Ende laufen die passenden Scripte fertig konfiguriert auf deinen Shellys.

Dein System besteht immer aus **zwei Shellys**:

| Shelly | Script | Aufgabe |
|---|---|---|
| **Controller-Shelly** | Controller (`zerooutput_multi_kvs`) | die Regelmaschine – steuert Laden und Entladen deiner Speicher und hält die live änderbaren Einstellungen (KVS) |
| **Dashboard-Shelly** | zenDash-API + Watchdog (`zendash_watch`) | ein gemeinsames Script mit zwei einzeln abschaltbaren Funktionen |

Darauf laufen drei Funktionen:

* **Controller** – regelt deinen Netzbezug bzw. -export über deine Zendure-Speicher
* **zenDash-API** – liefert die Daten für das Dashboard mit Live-Überblick; darüber kannst du auch das Verhalten des Controllers ändern
* **Watchdog** – meldet sich bei Ausnahmesituationen (Akku voll, Temperatur, Zellspannung, Gerät nicht erreichbar) und schickt morgens und abends eine Übersicht

Die Funktionen sind frei kombinierbar – zenDash-API und Watchdog lassen sich zum Beispiel auch nachträglich einrichten, wenn der Controller schon läuft. Angaben, die mehrere Funktionen brauchen (Geräteliste, Netzquelle, Benachrichtigungen), fragt der Configurator nur **einmal** ab und trägt sie passend in beide Scripte ein.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/487e63fb-734d-4bb1-b795-19f81921acb6" />

Der Configurator ist auf **Deutsch, Englisch und Französisch** verfügbar.

---

## 2. Wo finde ich den Configurator?

Es gibt zwei Wege. Empfohlen ist der **lokale Helfer** (=EXE-Datei), denn nur damit funktionieren Direkt-Upload, Update und Speicherprüfung.

### Empfohlen: der lokale Helfer (Exe-Installer)

Ein kleines Programm für deinen Rechner. Es startet den Configurator automatisch im Browser und übernimmt die Verbindung zu deinen Shellys. Keine Installation, kein Python nötig – herunterladen, starten, fertig.

👉 **[Aktuelle Version (latest release)](https://github.com/surfer1264/Zendure-Stuff/releases/latest)**

Direkt-Downloads:

* [Windows (64 Bit)](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows.exe)
* [Windows (32 Bit)](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows-x86.exe)
* [macOS](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-macos)

Beim ersten Start warnt dein Betriebssystem, weil die Datei nicht signiert ist:

* **Windows:** Bei „Windows hat den Computer geschützt“ (SmartScreen) auf „Weitere Informationen“ → „Trotzdem ausführen“ klicken.
* **macOS:** Rechtsklick auf die Datei → „Öffnen“ → im Dialog erneut „Öffnen“ bestätigen.

Wer sichergehen will, dass die Datei unverändert ist, kann sie [prüfen](#integrität-des-downloads-prüfen).

**Wichtig:** Das Fenster des Helfers muss offen bleiben, solange du einrichtest oder aktualisierst. Danach kannst du es schließen (oder `Strg+C`).

**Was der Helfer macht – und was nicht:** Er läuft nur auf deinem eigenen Rechner (`http://127.0.0.1:8787`) und ist aus deinem Netzwerk nicht erreichbar. Er merkt sich nach einem erfolgreichen Upload nur die **IP-Adressen** deiner beiden Shellys – keine Konfiguration, keine Passwörter.

### Alternative: nur der Web-Configurator

Läuft direkt im Browser, ohne Download:

👉 [Web-Configurator öffnen](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html)

Damit kannst du alles konfigurieren und das fertige Script herunterladen – **hochladen musst du es dann aber selbst** über die Weboberfläche des Shelly ([Anleitung](#script-von-hand-hochladen)). Update und Speicherprüfung stehen ohne Helfer nicht zur Verfügung.

> Tipp: Läuft der Helfer im Hintergrund, erkennt ihn auch der Web-Configurator und schaltet die zusätzlichen Funktionen frei.

---

## 3. Ersteinrichtung

Starte den Helfer. Im Startdialog wählst du **„Neu konfigurieren“**.

### Der Ablauf

1. **Start** – „Neu konfigurieren“ wählen
2. **Funktionen** – Controller, zenDash-API und/oder Watchdog auswählen und die **IP-Adressen deiner beiden Shellys** eintragen. Hast du schon eine Konfiguration, kannst du sie hier [einlesen](#bestehende-konfiguration-einlesen), statt alles neu einzugeben.
3. **Geräte** – deine Zendure-Speicher mit IP, maximaler Leistung und minSoc/maxSoc; je Gerät, ob der Watchdog es überwachen soll
4. **Netzquelle** – woher die Netzleistung kommt: Controller läuft direkt auf einem Shelly Pro 3EM, ein anderer Pro 3EM im Netzwerk oder ein Messgerät mit JSON-Schnittstelle (z. B. Zendure Smart Meter 3CT, Tasmota, Shelly 3EM ohne Pro)
5. **Laden vom Netz** – welche Geräte Überschuss aus anderen Anlagen aufnehmen dürfen
6. **Benachrichtigungen** – Webhook, Signal oder WhatsApp; gilt für Controller und Watchdog gemeinsam
7. **Bei vollem Akku / KVS** – wie mit Netzexport umgegangen wird, wenn die Akkus voll sind, und ob du Einstellungen später live (z. B. aus dem Dashboard oder Home Assistant) ändern möchtest
8. **Regelparameter** – Sollwert, Hysterese und die Schwellen fürs Verteilen der Leistung, bereits sinnvoll vorausgefüllt
9. **Ergebnis** – Zusammenfassung deiner Angaben mit den Versionsnummern und die fertigen Scripte

Schritte, die für deine Auswahl nicht nötig sind, werden übersprungen.

**Zu den Regelparametern:** Die Werte werden aus deiner eingelesenen Konfiguration übernommen bzw. per Faustformel aus deiner Geräteliste berechnet. Änderst du später Geräte oder Leistungen, werden sie **nicht** automatisch angepasst – bitte selbst prüfen. Bedeutung und Empfehlungen stehen in der [Controller-Dokumentation](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/readme.md).

**Ohne KVS:** Schaltest du die Live-Einstellungen (KVS) aus, kann das Dashboard nur noch anzeigen – Änderungen aus dem Dashboard wirken dann nicht auf den Controller.

### Die Funktionen im Ergebnis-Schritt

Für jeden der beiden Shellys bekommst du mehrere Möglichkeiten:

**⚡ Direkt hochladen** *(nur mit Helfer)*

Der bequemste Weg: ein Klick, fertig. Das Script geht automatisch auf den richtigen Shelly (Controller-Script auf den Controller-Shelly, zenDash-API + Watchdog auf den Dashboard-Shelly), wird gestartet und für den Autostart eingerichtet. Liegen auf dem Shelly schon andere Scripte, fragt der Configurator vorher nach – siehe [Mehrere Scripte auf einem Shelly](#mehrere-scripte-auf-einem-shelly).

Nach dem ersten erfolgreichen Upload merkt sich der Helfer die IPs und trägt sie beim nächsten Start automatisch ein.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/5082cdf4-1a6c-43a1-825c-8fc51bf18173" />

**🔗 Komplettes Script von GitHub speichern**

Lädt das aktuelle Original-Script von GitHub, trägt deine Konfiguration ein und bietet dir das fertige Script als Datei an. Das musst du dann nur noch [von Hand hochladen](#script-von-hand-hochladen). Braucht kurz eine Internetverbindung.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/d839f5b2-7433-4941-977c-a7c173ab7af2" />

**📋 Kopieren / 💾 Nur CONFIG-Block speichern**

Nur die Konfiguration – für alle, die ihr Script selbst angepasst haben oder lieber von Hand arbeiten. Damit ersetzt du den Block `let CONFIG = { ... };` in deinem Script. Außerdem ist das deine **Sicherungskopie**: Speichere sie ab, dann kannst du sie jederzeit wieder einlesen.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/1ccd9b90-9d83-42b8-892b-932ad12df4db" />

**🔍 Speicher prüfen** *(nur mit Helfer)*

Zeigt, wie viel Script-Speicher auf einem Shelly noch frei ist – siehe [Speicher eines Shelly prüfen](#speicher-eines-shelly-prüfen).

<img width="800" alt="image" src="https://github.com/user-attachments/assets/49d74a5d-cfd2-4541-932f-54c40b60ff5b" />

---

## 4. Update

Gibt es eine neue Version eines Scripts, bringst du deine Shellys mit wenigen Klicks auf den neuesten Stand – **deine Einstellungen bleiben dabei erhalten**. Das Update funktioniert nur mit dem [lokalen Helfer](#empfohlen-der-lokale-helfer-installer).

### So geht's

1. Helfer starten, im Startdialog **„Updaten“** wählen.
2. Die IPs deiner Shellys sind normalerweise schon eingetragen (vom letzten Upload gemerkt). Falls nicht, trägst du sie einmal ein – mindestens eine.
3. Der Configurator vergleicht die installierten Versionen mit GitHub und zeigt eine Tabelle:

   | Status | Bedeutung |
   |---|---|
   | **Update verfügbar** | Es gibt eine neuere Version – die Änderungen werden direkt darunter aufgelistet. Ist automatisch angehakt. |
   | **aktuell** | Nichts zu tun. |
   | **neuer als GitHub** | Du hast eine Test- oder Vorabversion – nichts zu tun. |
   | **nicht installiert** / **kein eindeutiges Script** | Update nicht möglich, bitte [„Neu konfigurieren“](#3-ersteinrichtung). |
   | **Shelly nicht erreichbar** | siehe [Fehlermeldungen](#6-fehlermeldungen-und-problemsituationen) |

   Darunter steht außerdem, ob es eine neue Version des Configurators/Helfers selbst gibt – mit Download-Link.
4. Gewünschte Scripte anhaken → **„Jetzt updaten“**. Der Configurator liest deine aktuelle Konfiguration direkt vom Shelly und springt zum Ergebnis.
5. Dort **„⚡ Direkt hochladen“** klicken. Das neue Script ersetzt das alte an derselben Stelle (die Script-Nummer bleibt gleich – wichtig z. B. für den Dashboard-Proxy) und wird wieder gestartet.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/28f6d1bf-8f5f-4311-8cd9-2e441b986157" />

### Was beim Update mit deinen Einstellungen passiert

Übernommen wird alles – auch Werte, die der Assistent gar nicht abfragt (z. B. `dampingFactor`, `interval` oder die Warnschwellen des Watchdog). Neue Einstellungen, die es in deiner alten Version noch nicht gab, bekommen ihren Standardwert.

### Update ohne Helfer

Ohne Helfer gehst du über **„Neu konfigurieren“**: Konfiguration [einlesen](#bestehende-konfiguration-einlesen), durchklicken, neues Script speichern und [von Hand hochladen](#script-von-hand-hochladen).

<img width="800" alt="image" src="https://github.com/user-attachments/assets/e23c3b85-03a4-4502-9868-81c742d8e7c5" />

### Umstieg von den alten Einzelscripten

zenDash-API und Watchdog sind inzwischen **ein** Script (`zendash_watch`). Konfigurationen der alten Einzelscripte (zenDash-API 2.x, Watchdog 1.x) lassen sich **nicht** einlesen. So steigst du um:

1. „Neu konfigurieren“ wählen und die **Controller-Konfiguration** einlesen – sie liefert Geräte, Netzquelle und Benachrichtigungen. Den Rest ergänzt du im Assistenten.
2. Beim Direkt-Upload auf den Dashboard-Shelly erkennt der Configurator die alten Scripte und fragt, ob sie gelöscht werden sollen → **„Ja, andere löschen und installieren“**.
3. Liegen alte Scripte auf einem anderen Shelly (oder lädst du von Hand hoch): dort **stoppen und den Autostart ausschalten** – sonst laufen sie parallel weiter und Meldungen kommen doppelt.

---

## 5. Wechsel eines Shelly

Du tauschst einen Shelly aus (defekt, neues Modell) oder er hat eine neue IP-Adresse bekommen? So nimmst du deine Konfiguration mit:

1. **Konfiguration sichern.** Hast du den CONFIG-Block schon gespeichert, nimm den. Sonst in der Weboberfläche des alten Shelly unter „Scripts“ das Script öffnen und den kompletten Block `let CONFIG = { ... };` kopieren.
2. Helfer starten und **„Neu konfigurieren“** wählen (das Update funktioniert hier nicht, weil auf dem neuen Shelly noch nichts installiert ist).
3. Im Schritt „Funktionen“ die Konfiguration **einlesen** – am besten Controller und zenDash-API + Watchdog nacheinander.
4. **Erst danach** die IP-Adresse des neuen Shelly eintragen. Beim Einlesen werden die IPs aus der alten Konfiguration übernommen und würden eine vorher eingegebene IP überschreiben.
5. Durch den Assistenten klicken und auf den neuen Shelly **direkt hochladen**. Der Helfer merkt sich ab jetzt die neue IP.
6. Auf dem **alten** Shelly das Script stoppen und den Autostart ausschalten (oder das Script löschen), falls er weiter im Netz bleibt.

Worauf du achten solltest:

* **Controller-Shelly ist gleichzeitig dein Pro 3EM?** Dann wandert mit dem Wechsel auch die Netzmessung mit. Im Schritt „Netzquelle“ prüfen, ob die Einstellung noch stimmt.
* **Neue IP des Controller-Shelly:** Die zenDash-API liest ihre Werte vom Controller-Shelly. Deshalb auch das Script auf dem Dashboard-Shelly neu hochladen, damit es die neue Adresse kennt.
* **Neue IP eines Zendure-Speichers:** Das ist kein Shelly-Wechsel, aber genauso schnell erledigt – „Neu konfigurieren“, Konfiguration einlesen, im Schritt „Geräte“ die IP ändern, beide Scripte neu hochladen.
* Tipp: Gib deinen Shellys und Speichern im Router eine **feste IP-Adresse**, dann passiert das gar nicht erst.

---

## 6. Fehlermeldungen und Problemsituationen

### Mehrere Scripte auf einem Shelly

⚠️ **Pro Shelly sollte genau ein Script laufen.** Shellys haben nur wenig Script-Speicher. Liegen weitere Scripte darauf – auch gestoppte, alte oder Testscripte – kann es passieren, dass das neue Script nicht startet oder im Betrieb abstürzt. Beim Controller heißt das: **deine Regelung steht**.

Der Configurator prüft das deshalb vor jedem Direkt-Upload. Findet er weitere Scripte, zeigt er dir die Liste (mit Status „läuft“/„gestoppt“) und fragt:

* **„Ja, andere löschen und installieren“** – empfohlen. Die übrigen Scripte werden entfernt.
* **„Nein, andere behalten und installieren“** – nur wenn du genau weißt, dass der Speicher reicht. Prüfe ihn vorher mit [Speicher prüfen](#speicher-eines-shelly-prüfen).
* **„Abbrechen“** – auf dem Shelly wird nichts verändert.

Liegen mehrere Scripte **desselben Typs** auf dem Shelly (z. B. zwei Controller), ist „Behalten“ nicht möglich, weil unklar wäre, welches aktualisiert werden soll.

Controller und zenDash-API + Watchdog laufen aus demselben Grund **nie** gemeinsam auf einem Shelly. Der Configurator prüft schon im ersten Schritt, dass zwei verschiedene IP-Adressen eingetragen sind.

### Meldungen im Überblick

| Meldung | Was bedeutet das? | Was tun? |
|---|---|---|
| „Updaten“ ist ausgegraut: *Nur mit dem lokalen Helfer möglich* | Der Helfer läuft nicht. | [Helfer](#empfohlen-der-lokale-helfer-installer) starten – er öffnet den Configurator selbst. |
| *Dein lokaler Helfer ist älter als diese Seite …* | Es läuft noch eine alte Version des Helfers. | Helfer schließen, aktuelle Version herunterladen und neu starten. |
| *Shelly nicht erreichbar* / *Shelly … nicht erreichbar* | Der Shelly antwortet nicht. | IP prüfen (in der Shelly-App oder im Router), Shelly eingeschaltet? Rechner im selben Netz (nicht im Gast-WLAN)? |
| *Der Shelly … verlangt ein Passwort* | Der Passwortschutz des Shelly ist aktiv. | Passwortschutz vorübergehend ausschalten, hochladen, danach wieder einschalten. |
| *nicht installiert – bitte „Neu konfigurieren“* | Auf dem Shelly liegt kein passendes Script. | Über [„Neu konfigurieren“](#3-ersteinrichtung) einrichten. |
| *kein eindeutiges Script – bitte „Neu konfigurieren“* | Auf dem Shelly liegen mehrere Scripte desselben Typs. | „Neu konfigurieren“ – beim Hochladen die anderen Scripte löschen lassen. |
| *Config konnte nicht vom Shelly gelesen werden* | Die Konfiguration im Script ist nicht auffindbar (z. B. von Hand verändert). | „Neu konfigurieren“ und die Konfiguration aus deiner Sicherung einlesen. |
| *Versionen auf GitHub nicht abrufbar* / *GitHub-Version unbekannt* | Keine Verbindung zu GitHub. | Internetverbindung prüfen, später erneut „Versionen prüfen“. |
| *Auf … ist bereits das Script „…“ installiert – dieses Gerät ist hier aber für „…“ eingetragen. Sind die IP-Adressen vertauscht?* | Controller- und Dashboard-IP sind wahrscheinlich vertauscht. | **Abbrechen** und die IPs prüfen. Nur löschen, wenn du den Shelly wirklich umwidmen willst. |
| *Auf … sind n Scripte vorhanden* / *ein anderes Script installiert* | Weitere Scripte auf dem Shelly. | siehe [Mehrere Scripte](#mehrere-scripte-auf-einem-shelly) |
| *Upload abgebrochen – das Script auf dem Shelly ist unvollständig* | Die Verbindung ist während des Hochladens abgerissen. **Das Script läuft jetzt nicht.** | Sofort erneut „Direkt hochladen“. |
| *Hochgeladen …, aber das Script läuft nicht* | Das Script wurde übertragen, startet aber nicht. | In der Shelly-Weboberfläche unter „Scripts“ das Log ansehen. Häufig: zu wenig Speicher (andere Scripte entfernen) oder falsche Geräte-IPs. |
| *⚠️ Nur … Bytes frei* | Der Speicher ist knapp. | Andere Scripte auf dem Shelly entfernen. |
| *Das ist eine Config im alten Format …* | Konfiguration der alten Einzelscripte. | siehe [Umstieg](#umstieg-von-den-alten-einzelscripten) |
| *Konnte nicht erkennen, zu welchem Produkt diese Config gehört* | Unvollständig kopiert. | Den kompletten Block von `let CONFIG = {` bis `};` einfügen. |
| *Controller-Shelly und Dashboard-Shelly müssen zwei verschiedene Geräte sein* | Zweimal dieselbe IP eingetragen. | Zwei verschiedene Shellys verwenden. |
| *Fehler: … Internetverbindung prüfen …* beim Script-Download | GitHub nicht erreichbar. | Internetverbindung prüfen. |

### Probleme mit dem Helfer

| Situation | Was tun? |
|---|---|
| Das Fenster des Helfers geht sofort wieder zu bzw. meldet *konnte nicht auf 127.0.0.1:8787 lauschen* | Der Helfer läuft schon (anderes Fenster, evtl. minimiert) – diesen verwenden oder schließen und neu starten. |
| Der Browser öffnet sich nicht | Im Browser `http://127.0.0.1:8787` aufrufen. |
| Windows/macOS blockiert den Start | siehe [Wo finde ich den Configurator?](#empfohlen-der-lokale-helfer-installer) |
| Der Configurator schlägt falsche Shelly-IPs vor | IP einfach im Feld überschreiben – oder die gemerkten IPs [zurücksetzen](#gemerkte-ips-zurücksetzen). |

---

## 7. How-Tos

### Bestehende Konfiguration einlesen

Im Schritt „Funktionen“ unter **„Bestehende Config einlesen“** einen kompletten Block `let CONFIG = { ... };` einfügen und „Einlesen & übernehmen“ klicken. Der Configurator erkennt selbst, ob es der Controller oder zenDash-API + Watchdog ist. Am besten beide nacheinander einlesen – die Reihenfolge ist egal. Die Shelly-IPs werden dabei gleich mit übernommen.

### Script von Hand hochladen

Ohne Helfer (die Anleitung gibt es auch aufklappbar im Configurator):

1. Im Ergebnis-Schritt „🔗 Komplettes Script von GitHub speichern“ klicken.
2. Die IP des Shelly im Browser öffnen (z. B. `http://192.168.178.151`) und zu „Scripts“ wechseln.
3. Ein altes Script gleichen Namens stoppen und löschen. **Andere Scripte ebenfalls entfernen** (siehe [Mehrere Scripte](#mehrere-scripte-auf-einem-shelly)).
4. „Add script“, Namen vergeben, speichern.
5. Die heruntergeladene Datei mit einem Texteditor öffnen, alles kopieren und in den Code-Editor einfügen.
6. „Save“, dann „Start“ und **„Enable on boot“** aktivieren.
7. Im Log prüfen, ob das Script fehlerfrei läuft.

### Speicher eines Shelly prüfen

Mit laufendem Helfer im Ergebnis-Schritt die IP eines beliebigen Shelly eintragen und **„🔍 Speicher prüfen“** klicken. Ab **25 200 Bytes** freiem Speicher ist alles gut. Das funktioniert auch bei einem neuen Shelly ohne Script.

Zur Orientierung: Das Script zenDash-API + Watchdog belegt mit zwei Speichern im Betrieb rund 13,5 kB, in der Spitze rund 17,8 kB.

### Konfiguration sichern

Nach jeder Änderung im Ergebnis-Schritt „💾 Nur CONFIG-Block speichern“ klicken und die Datei aufbewahren. Damit bist du bei einem Shelly-Defekt oder -Wechsel in wenigen Minuten wieder startklar.

### Gemerkte IPs zurücksetzen

Der Helfer speichert die IPs in der Datei `zendure_helper_config.json` – entweder neben der Helfer-Datei oder, falls dort nicht geschrieben werden darf, hier:

* **Windows:** `%APPDATA%\ZendureHelper\`
* **macOS:** `~/Library/Application Support/ZendureHelper/`

Datei löschen, und der Configurator fragt beim nächsten Start wieder nach den IPs.

### Integrität des Downloads prüfen

Zu jeder Datei liegt auf der [Releases-Seite](https://github.com/surfer1264/Zendure-Stuff/releases/latest) eine gleichnamige `.sha256`-Datei. Damit prüfst du, dass dein Download genau die Datei ist, die der Build erzeugt hat.

**Windows (PowerShell)** – gibt `True` oder `False` aus:

```powershell
(Get-FileHash .\zendure_local_helper-windows.exe -Algorithm SHA256).Hash -eq (Get-Content .\zendure_local_helper-windows.exe.sha256).Split(' ')[0]
```

Für die 32-Bit-Version `zendure_local_helper-windows-x86.exe` einsetzen.

**macOS (Terminal):**

```bash
shasum -a 256 -c zendure_local_helper-macos.sha256
```

`OK` = alles in Ordnung. `FAILED` = Datei **nicht** ausführen, neu herunterladen.
