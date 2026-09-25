# Changelog zendash API - WatchDog

## Changelog 3.3

- Letzte Vollladung: echte 100 % SoC werden je Geraet als Datum (JJJJMMTT) in `zdmc_dev{i}_lastFull` gespeichert, hoechstens ein KVS-Schreibvorgang pro Geraet und Tag
- Schutz: harte Obergrenze von 3 Schreibversuchen je Geraet und 24 h Laufzeit; Datum in der Zukunft gilt als ungueltig und wird ueberschrieben; KVS-Wert wird immer uebernommen (auch aeltere, von Hand gesetzte Werte)
- config_api liefert je Geraet `lastFull` (0 = noch nie erfasst)
- Dashboard: Zeile "100 %: vor N Tagen" je Geraet, gruen < 7 Tage, gelb 7-20 Tage, rot darueber; Antippen zeigt das Datum
- Watchdog: einmalige Meldung "Geraet seit N Tagen nicht voll" ab 20 Tagen
- Watchdog-only-Betrieb liest beim Start ebenfalls die KVS

## Changelog 3.2

- FullScreenMode

## Changelog 3.1

- Zusammenlegung von Watchdog und zenDash API