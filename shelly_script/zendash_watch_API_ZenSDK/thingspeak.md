# ThingSpeak-Upload

[← zurück zu zenDash-API + Watchdog](readme.md) · [Dashboard einrichten](dashboard.md) · [API-Beschreibung](API.md)

Der Dashboard-Proxy `zendure_proxy.py` kann die Messwerte deiner Speicher jede Minute an [ThingSpeak](https://thingspeak.mathworks.com) senden. Dort bekommst du einen dauerhaften Verlauf mit Diagrammen, ohne selbst eine Datenbank betreiben zu müssen.

Der Upload ist optional und steckt in einer eigenen Datei, `ts_bridge.py`. Ohne diese Datei läuft der Proxy ganz normal, nur ohne ThingSpeak.

> **Hinweis zum Datenschutz:** Mit dem Upload verlassen die Messwerte dein Heimnetz. Deine Zendure-Geräte und der Shelly brauchen dafür keinen Internetzugang, nur der Rechner, auf dem der Proxy läuft. Mehr dazu unter [Betreiber und Datenschutz](#betreiber-und-datenschutz).

## Inhalt

- [Was du brauchst](#was-du-brauchst)
- [ThingSpeak vorbereiten](#thingspeak-vorbereiten)
- [Proxy einrichten](#proxy-einrichten)
- [So arbeitet der Upload](#so-arbeitet-der-upload)
- [Feldbelegung](#feldbelegung)
- [Kontingent im Free-Tarif](#kontingent-im-free-tarif)
- [Betreiber und Datenschutz](#betreiber-und-datenschutz)
- [Meldungen im Log](#meldungen-im-log)
- [Fehlersuche](#fehlersuche)

---

## Was du brauchst

- **zendash_watch ab 3.5.0** auf dem Dashboard-Shelly. Ältere Versionen funktionieren auch, liefern aber nur Ladestand, PV und Netzsaldo. Die übrigen Leistungsfelder bleiben dann leer.
- **Den Proxy** `zendure_proxy.py`, eingerichtet wie in der [Dashboard-Anleitung](dashboard.md) beschrieben.
- **`ts_bridge.py`** im selben Ordner wie der Proxy.
- **Einen ThingSpeak-Account.** Der kostenlose Tarif reicht für bis zu 4 Hubs, siehe [Kontingent](#kontingent-im-free-tarif).
- Der Proxy muss dauerhaft laufen, z. B. auf dem NAS oder als Home Assistant App. Läuft er nicht, wird nichts gesendet.

## ThingSpeak vorbereiten

Du brauchst **einen Channel pro Hub**.

1. In ThingSpeak unter *Channels → My Channels → New Channel* einen Channel anlegen, z. B. mit dem Namen des Geräts.
2. **Field 1 bis 7** aktivieren und benennen, siehe [Feldbelegung](#feldbelegung). Field 8 bleibt frei.
3. Speichern und im Tab *API Keys* den **Write API Key** kopieren (16 Zeichen).
4. Für jeden weiteren Hub wiederholen.

Wichtig: Gebraucht wird der **Write API Key des Channels**. Der User API Key deines Accounts funktioniert hier nicht.

## Proxy einrichten

1. `ts_bridge.py` neben `zendure_proxy.py` legen und den Proxy starten. In der Startmeldung steht dann:
   ```
   ThingSpeak: http://localhost:8000/thingspeak
   ```
   Steht dort `nicht verfuegbar (ts_bridge.py fehlt)`, liegt die Datei nicht im richtigen Ordner.
2. `http://<proxy-host>:8000/thingspeak` im Browser öffnen.
3. Auf **„Geräte vom Shelly laden“** tippen. Für jeden Hub erscheint ein Eingabefeld.
4. Die Write API Keys eintragen, **„Upload aktiv“** anhaken und **„Speichern & Keys testen“**.

Beim Speichern schickt der Proxy für jeden neuen Key eine Testmeldung an ThingSpeak. Ist ein Key falsch, siehst du das sofort. Die Testmeldung enthält nur einen Status und erscheint deshalb nicht im Diagramm.

Die Keys landen in `zendure_thingspeak_config.json` neben dem Proxy. Beim Umzug des Proxys, z. B. vom PC aufs NAS, kannst du die Datei einfach mitkopieren.

**Ändern und entfernen:** Ein leeres Feld behält den bisherigen Key, ein `-` entfernt den Channel. Hinterlegte Keys zeigt die Seite nur gekürzt an (`****AB12`).

**Sicherheit:** Die Seite hat kein Passwort, genau wie `/setup`. Jeder in deinem Netz, der den Proxy erreicht, kann den Upload ein- oder ausschalten und Keys ersetzen, aber keine hinterlegten Keys auslesen.

## So arbeitet der Upload

**Fester Minutentakt.** Ist der Upload aktiv, geht zu jeder vollen Minute für jeden Hub ein Eintrag an ThingSpeak. Der Zeitstempel ist genau die volle Minute, egal wann der Proxy gerade gesendet hat.

**Echte Werte, kein Mittelwert.** Gesendet werden die Werte der letzten Antwort von `status_api` vor der vollen Minute. Das Script fragt die Hubs alle 8 s ab, die Werte sind also höchstens so alt.

**Keine Zusatzlast bei offenem Dashboard.** Solange ein Dashboard offen und sichtbar ist, liest der Proxy dessen Abfragen nur mit und fragt selbst nichts ab.

**Ohne Dashboard fragt der Proxy selbst.** Ist kein Dashboard offen oder der Tab im Hintergrund, fragt der Proxy etwa 12 s vor der vollen Minute zweimal `status_api` ab. Die erste Abfrage weckt das Script, das nach 15 s ohne Anfrage schläft. Die zweite liefert 10 s später den frischen Stand. Das sind 2 Abfragen pro Minute.

**Veraltete Antworten werden erkannt.** Eine Antwort gilt nur als frisch, wenn die vorige Anfrage weniger als 14 s zurückliegt, das Script also wach war. Fragt z. B. ein vom Browser gedrosselter alter Tab nur einmal pro Minute, verwirft der Proxy diese Antworten und holt sich selbst einen frischen Stand.

**Upload aus heißt keine Anfragen.** Ist der Upload ausgeschaltet oder kein Key hinterlegt, stellt der Proxy **keine einzige** Anfrage an die zendash-API. Er liest dann auch nicht beim Dashboard mit.

**Fehlende Werte bleiben leer.** Liefert `status_api` einen Wert nicht, sendet der Proxy das Feld nicht mit, statt eine 0 einzutragen. In ThingSpeak entsteht an der Stelle eine Lücke.

| Situation | Was gesendet wird |
|---|---|
| Hub online | Alle vorhandenen Felder |
| Gerät ohne PV-Eingang | Field 2 bleibt leer |
| Netzzähler offline | Field 7 bleibt leer |
| Hub offline | Nur Status `offline`, alle Felder leer |
| Shelly nicht erreichbar | Nur Status `keine Daten`, alle Felder leer |

Lehnt ThingSpeak eine Meldung ab oder ist das Internet weg, versucht der Proxy es nach 5 s noch einmal. Scheitert auch das, fehlt diese Minute. Nachgeliefert wird nichts.

## Feldbelegung

| Feld | Inhalt | Quelle in `status_api` | Zendure-Feld |
|---|---|---|---|
| Field 1 | Ladestand in % | `soc` | `electricLevel` |
| Field 2 | PV-Eingang in W | `pv` | `solarInputPower` |
| Field 3 | Abgabe ans Haus in W | `home` | `outputHomePower` |
| Field 4 | Aufnahme aus dem Netz in W | `gridIn` | `gridInputPower` |
| Field 5 | Entladen aus dem Akku in W | `packIn` | `packInputPower` |
| Field 6 | Laden in den Akku in W | `packOut` | `outputPackPower` |
| Field 7 | Netzsaldo in W (positiv = Bezug) | `grid.power` | – |
| Field 8 | frei | – | – |

Field 7 ist in allen Channels gleich, weil es nur einen Netzzähler gibt.

## Kontingent im Free-Tarif

Der kostenlose ThingSpeak-Tarif erlaubt rund 3 Millionen Meldungen pro Jahr, also etwa 8.200 pro Tag über alle Channels zusammen. Pro Hub fallen 1.440 Meldungen am Tag an.

| Hubs | Meldungen pro Tag |
|---|---|
| 1 | 1.440 |
| 2 | 2.880 |
| 3 | 4.320 |
| 4 | 5.760 |

Die Grenze setzt hier nicht das Kontingent, sondern die Zahl der Channels: Der Free-Tarif erlaubt höchstens 4. Ab dem 5. Hub brauchst du einen kostenpflichtigen Tarif oder einen zweiten Account.

## Betreiber und Datenschutz

**Betreiber:** ThingSpeak ist ein Dienst von MathWorks, dem Hersteller von MATLAB, mit Sitz in Natick, Massachusetts (USA).

**Speicherort:** Eine eigene Angabe zum Speicherort der ThingSpeak-Channel-Daten macht MathWorks nicht. Allgemein speichert MathWorks strukturierte Kundendaten in den USA und in Irland und nutzt externe IT-Infrastruktur-Anbieter. Geh also davon aus, dass deine Messwerte in den USA liegen können.

**Rechtlicher Rahmen:** MathWorks ist unter dem EU-US Data Privacy Framework (DPF) zertifiziert und nutzt für Übermittlungen ins Ausland u. a. die EU-Standardvertragsklauseln. Daten werden laut MathWorks nicht verkauft oder vermietet. Auskunft und Löschung kannst du über privacy@mathworks.com beantragen. Details stehen in der [MathWorks Data Privacy FAQ](https://www.mathworks.com/company/trust-center/privacy-faq.html) und der [Privacy Policy](https://www.mathworks.com/company/trust-center/privacy-policy.html).

**Was übertragen wird:** Nur Leistungswerte, Ladestände und Zeitstempel, keine Namen, Adressen, Geräte-Seriennummern oder IP-Adressen deiner Geräte. Ganz belanglos sind solche Verläufe trotzdem nicht: Am Hausverbrauch über den Tag lässt sich zum Beispiel ablesen, wann jemand zu Hause ist.

**Empfehlung:** Lass deine Channels auf **privat**, das ist die Voreinstellung. Öffentliche Channels kann jeder ohne Key einsehen. Wer seine Daten nicht außer Haus geben möchte, lässt den Upload einfach aus – der Proxy läuft auch ganz ohne `ts_bridge.py`, und ohne aktiven Upload geht nichts nach draußen.

Stand dieser Angaben: September 2026. Maßgeblich sind die aktuellen Seiten von MathWorks.

## Meldungen im Log

Im Normalbetrieb schreibt der Proxy pro Minute und Hub eine Zeile:

```
[thingspeak] Hub 0 2026-09-28T15:14:00Z gesendet (Eintrag 64)
```

Ohne offenes Dashboard kommen davor zwei Zeilen dazu:

```
[thingspeak] kein Dashboard offen - eigene Abfrage status_api (wecken)
[thingspeak] eigene Abfrage status_api (frischer Stand)
```

Mit `-q` oder `-s` fallen diese Zeilen weg. Fehler erscheinen immer:

```
[thingspeak] Hub 0 2026-09-28T15:14:00Z: verworfen (...)
[thingspeak] Shelly nicht erreichbar: ...
```

## Fehlersuche

**`/thingspeak` meldet 404 bzw. die Startmeldung sagt „nicht verfuegbar“.**
`ts_bridge.py` liegt nicht neben `zendure_proxy.py`. Bei der exe: Die Datei muss beim Bauen im selben Ordner liegen, sonst baut PyInstaller ohne ThingSpeak.

**„ThingSpeak lehnt den Key ab“ beim Speichern.**
Meist wurde der User API Key statt des Write API Keys des Channels eingetragen. Im Channel unter *API Keys* nachsehen.

**Field 3 bis 6 bleiben leer.**
Auf dem Dashboard-Shelly läuft noch zendash_watch vor 3.5.0. Das Script aktualisieren, zum Beispiel mit dem [Configurator](../Multiconfigurator/readme.md).

**Regelmäßig „verworfen“ im Log.**
Der Rechner mit dem Proxy hat zeitweise kein Internet, oder das Tageskontingent ist aufgebraucht. Die Antwort `0` von ThingSpeak bedeutet, dass die Meldung abgelehnt wurde.

**Im Log erscheint einmal pro Minute ein Paar aus `status_api` und `config_api`, obwohl kein Dashboard sichtbar ist.**
Irgendwo ist noch ein Dashboard-Tab mit einer Version vor 3.5.0 offen, den der Browser im Hintergrund drosselt. Tab neu laden oder schließen. Der Upload selbst ist davon nicht betroffen, weil der Proxy solche Antworten als veraltet erkennt.
