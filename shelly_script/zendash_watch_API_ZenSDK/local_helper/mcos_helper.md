Die macOS-Datei (`zendure_local_helper-macos`) hat keine Dateiendung und wird vom Browser meist ohne Ausführungsrecht gespeichert. Ein Doppelklick allein reicht deshalb oft nicht. Am zuverlässigsten startest du sie über das Terminal:

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

**Ohne Terminal:** Der Weg aus dem README (Rechtsklick → „Öffnen“ → erneut „Öffnen“) funktioniert auf neueren macOS-Versionen (ab Sequoia) oft nicht mehr. Dann versuchst du die Datei einmal zu öffnen und gehst anschließend zu **Systemeinstellungen → Datenschutz & Sicherheit**. Dort klickst du ganz unten bei der blockierten Datei auf **„Dennoch öffnen“**. Das Ausführungsrecht aus Schritt 3 brauchst du trotzdem, wenn macOS die Datei nicht als Programm erkennt.

Tipp: Vor dem ersten Start kannst du die Datei mit `shasum -a 256 -c zendure_local_helper-macos.sha256` prüfen. Die `.sha256`-Datei muss dafür im selben Ordner liegen.


Sie ist ein reines arm64-Binary. Sie läuft also nur auf Macs mit Apple Silicon (M1, M2, M3, M4
