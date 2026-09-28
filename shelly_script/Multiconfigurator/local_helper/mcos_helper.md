# Den Helfer unter macOS starten

[← zurück zur Configurator-Anleitung](../readme.md)

**Voraussetzung:** Die macOS-Datei ist ein reines arm64-Programm. Sie läuft nur auf Macs mit **Apple Silicon** (M1 oder neuer), nicht auf älteren Macs mit Intel-Prozessor. Dort bleibt nur der [Web-Configurator](../readme.md#alternative-nur-der-web-configurator).

Die Datei (`zendure_local_helper-macos`) hat keine Dateiendung und wird vom Browser meist ohne Ausführungsrecht gespeichert. Ein Doppelklick allein reicht deshalb oft nicht.

## Mit dem Terminal (am zuverlässigsten)

1. **Terminal öffnen** (Programme → Dienstprogramme → Terminal).
2. **In den Download-Ordner wechseln:**
   ```bash
   cd ~/Downloads
   ```
3. **Ausführbar machen:**
   ```bash
   chmod +x zendure_local_helper-macos
   ```
4. **Quarantäne-Markierung entfernen** (sonst blockiert Gatekeeper die unsignierte Datei):
   ```bash
   xattr -d com.apple.quarantine zendure_local_helper-macos
   ```
5. **Starten:**
   ```bash
   ./zendure_local_helper-macos
   ```

Der Helfer öffnet dann den Configurator im Browser (`http://127.0.0.1:8787`). Das Terminal-Fenster muss offen bleiben, solange du einrichtest oder aktualisierst. Beenden kannst du ihn mit `Ctrl+C`.

## Ohne Terminal

Der Weg „Rechtsklick → Öffnen → erneut Öffnen“ funktioniert ab macOS Sequoia oft nicht mehr. Dann versuchst du die Datei einmal zu öffnen und gehst anschließend zu **Systemeinstellungen → Datenschutz & Sicherheit**. Dort klickst du ganz unten bei der blockierten Datei auf **„Dennoch öffnen“**.

Erkennt macOS die Datei gar nicht als Programm, brauchst du trotzdem das Ausführungsrecht aus Schritt 3 oben.

## Download prüfen (optional)

Vor dem ersten Start kannst du die Datei prüfen:

```bash
shasum -a 256 -c zendure_local_helper-macos.sha256
```

Die `.sha256`-Datei von der [Releases-Seite](https://github.com/surfer1264/Zendure-Stuff/releases/latest) muss dafür im selben Ordner liegen. `OK` = alles in Ordnung, `FAILED` = Datei **nicht** ausführen, neu herunterladen.
