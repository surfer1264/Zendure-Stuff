# ThingsBoard-Upload

[← zurück zu zenDash-API + Watchdog](readme.md) · [Dashboard einrichten](dashboard.md) · [API-Beschreibung](API.md) · [ThingSpeak-Upload](thingspeak.md)

Der Dashboard-Proxy `zendure_proxy.py` kann die Messwerte deiner Speicher jede Minute an [ThingsBoard](https://thingsboard.io) senden – an die ThingsBoard Cloud oder an einen eigenen ThingsBoard-Server. Dort bekommst du einen dauerhaften Verlauf und frei gestaltbare Dashboards, in denen du Werte mehrerer Geräte direkt kombinieren kannst.

Der Upload ist optional und läuft **unabhängig vom [ThingSpeak-Upload](thingspeak.md)**: Du kannst beide parallel nutzen, nur einen davon oder keinen. Die Logik steckt in derselben Datei wie bei ThingSpeak, `ts_bridge.py`. Ohne diese Datei läuft der Proxy ganz normal, nur ohne Cloud-Upload.

> **Hinweis zum Datenschutz:** Mit dem Upload an die ThingsBoard Cloud verlassen die Messwerte dein Heimnetz. Deine Zendure-Geräte und der Shelly brauchen dafür keinen Internetzugang, nur der Rechner, auf dem der Proxy läuft. Mit einem [eigenen Server](#eigener-thingsboard-server) bleibt alles bei dir. Mehr dazu unter [Betreiber und Datenschutz](#betreiber-und-datenschutz).

## Inhalt

- [Was du brauchst](#was-du-brauchst)
- [ThingsBoard vorbereiten](#thingsboard-vorbereiten)
- [Proxy einrichten](#proxy-einrichten)
- [So arbeitet der Upload](#so-arbeitet-der-upload)
- [Geräte und Werte](#geräte-und-werte)
- [Kontingent im Free-Tarif](#kontingent-im-free-tarif)
- [Eigener ThingsBoard-Server](#eigener-thingsboard-server)
- [Betreiber und Datenschutz](#betreiber-und-datenschutz)
- [Meldungen im Log](#meldungen-im-log)
- [Fehlersuche](#fehlersuche)

---

## Was du brauchst

- **zendash_watch ab 3.5.0** auf dem Dashboard-Shelly. Ältere Versionen funktionieren auch, liefern aber nur Ladestand, PV, Zellspannung und Netzsaldo. Die übrigen Leistungswerte fehlen dann.
- **Den Proxy** `zendure_proxy.py`, eingerichtet wie in der [Dashboard-Anleitung](dashboard.md) beschrieben.
- **`ts_bridge.py`** im selben Ordner wie der Proxy.
- **Einen ThingsBoard-Zugang:** entweder ein Konto bei der ThingsBoard Cloud (für Europa `https://eu.thingsboard.cloud`) – der kostenlose Tarif reicht für bis zu 3 Speicher, siehe [Kontingent](#kontingent-im-free-tarif) – oder einen [eigenen Server](#eigener-thingsboard-server).
- Der Proxy muss dauerhaft laufen, z. B. auf dem NAS oder als Home Assistant App. Läuft er nicht, wird nichts gesendet.

## ThingsBoard vorbereiten

Du brauchst **ein Gerät pro Speicher** und **ein Gerät für den Netzzähler**.

1. In ThingsBoard unter *Entities → Devices* mit **+** ein Gerät anlegen, z. B. mit dem Namen des Speichers.
2. Das Gerät öffnen und **„Copy access token“** anklicken. Das Token kommt gleich in den Proxy.
3. Für jeden weiteren Speicher wiederholen.
4. Ein weiteres Gerät für den Netzzähler anlegen, z. B. „Netz“, und auch dessen Token kopieren.

Der Netzsaldo ist bewusst ein eigenes Gerät: Er gehört zu keinem Speicher, sondern zum Zähler. So liegt er nur einmal in ThingsBoard statt in jedem Speicher doppelt.

## Proxy einrichten

1. `ts_bridge.py` neben `zendure_proxy.py` legen und den Proxy starten. In der Startmeldung steht dann:
   ```
   ThingsBoard: http://localhost:8000/thingsboard
   ```
   Steht dort `Cloud-Upload: nicht verfuegbar (ts_bridge.py fehlt)`, liegt die Datei nicht im richtigen Ordner.
2. `http://<proxy-host>:8000/thingsboard` im Browser öffnen.
3. **Server-Adresse** prüfen. Vorbelegt ist `https://eu.thingsboard.cloud`. Für einen eigenen Server z. B. `http://nas:8080` eintragen.
4. Auf **„Geräte vom Shelly laden“** tippen. Für jeden Speicher erscheint ein Eingabefeld, darunter eines für **„Netz (Netzsaldo)“**.
5. Die Access Tokens eintragen, **„Upload aktiv“** anhaken und **„Speichern & Tokens testen“**.

Beim Speichern prüft der Proxy jedes neue Token. Dazu schreibt er beim Gerät ein Attribut `zendashBridgeTest` mit der aktuellen Uhrzeit – du findest es in ThingsBoard beim Gerät unter *Attributes*. Das kostet keinen Datenpunkt. Ist ein Token falsch, siehst du das sofort. Änderst du die Server-Adresse, prüft der Proxy alle Tokens neu.

Die Einstellungen landen in `zendure_thingsboard_config.json` neben dem Proxy (in der Home Assistant App unter `/data`). Beim Umzug des Proxys, z. B. vom PC aufs NAS, kannst du die Datei einfach mitkopieren.

**Ändern und entfernen:** Ein leeres Feld behält das bisherige Token, ein `-` entfernt das Gerät aus dem Upload. Hinterlegte Tokens zeigt die Seite nur gekürzt an (`****AB12`).

**Sicherheit:** Die Seite hat kein Passwort, genau wie `/setup` und `/thingspeak`. Jeder in deinem Netz, der den Proxy erreicht, kann den Upload ein- oder ausschalten und Tokens ersetzen, aber keine hinterlegten Tokens auslesen.

## So arbeitet der Upload

ThingSpeak und ThingsBoard teilen sich das Einsammeln der Werte. Der Ablauf ist deshalb derselbe wie beim [ThingSpeak-Upload](thingspeak.md#so-arbeitet-der-upload):

**Fester Minutentakt.** Ist der Upload aktiv, geht zu jeder vollen Minute für jedes Gerät ein Eintrag an ThingsBoard. Der Zeitstempel ist genau die volle Minute, egal wann der Proxy gerade gesendet hat.

**Echte Werte, kein Mittelwert.** Gesendet werden die Werte der letzten frischen Antwort von `status_api` vor der vollen Minute, höchstens etwa 8 s alt.

**Keine Zusatzlast bei offenem Dashboard.** Solange ein Dashboard offen und sichtbar ist, liest der Proxy dessen Abfragen nur mit. Ohne Dashboard fragt er etwa 12 s vor der vollen Minute zweimal selbst ab – einmal zum Wecken, einmal für den frischen Stand. Das gilt für beide Ziele zusammen, nicht doppelt.

**Beide Ziele unabhängig.** ThingSpeak und ThingsBoard senden gleichzeitig. Ist eines der beiden nicht erreichbar, bremst das das andere nicht.

**Alles aus heißt keine Anfragen.** Erst wenn **weder** ThingSpeak **noch** ThingsBoard aktiv ist, stellt der Proxy keine einzige Anfrage an die zendash-API und liest auch nicht beim Dashboard mit. Solange eines der beiden läuft, wird abgefragt.

**Fehlende Werte werden weggelassen.** Liefert `status_api` einen Wert nicht, fehlt er im Eintrag, statt als 0 zu erscheinen.

| Situation | Was gesendet wird |
|---|---|
| Speicher online | Alle vorhandenen Werte |
| Gerät ohne PV-Eingang | Ohne `solarInputPower` |
| Keine Pack-Daten (`minVol` null oder 0) | Ohne `minVol` |
| Speicher offline | In dieser Minute nichts |
| Netzzähler offline | Für „Netz“ in dieser Minute nichts |
| Shelly nicht erreichbar | In dieser Minute nichts |

Anders als bei ThingSpeak schickt der Proxy bei fehlenden Daten keinen leeren Eintrag – das spart Datenpunkte. Im Diagramm entsteht eine Lücke.

Lehnt ThingsBoard eine Meldung ab oder ist das Internet weg, versucht der Proxy es nach 5 s noch einmal. Scheitert auch das, fehlt diese Minute. Nachgeliefert wird nichts.

## Geräte und Werte

**Speicher** – ein Gerät pro Speicher, Schlüssel wie im Zendure-Report:

| Schlüssel | Inhalt | Einheit | Quelle in `status_api` |
|---|---|---|---|
| `electricLevel` | Ladestand | % | `soc` |
| `solarInputPower` | PV-Eingang | W | `pv` |
| `outputHomePower` | Abgabe ans Haus | W | `home` |
| `gridInputPower` | Aufnahme aus dem Netz | W | `gridIn` |
| `packInputPower` | Entladen aus dem Akku | W | `packIn` |
| `outputPackPower` | Laden in den Akku | W | `packOut` |
| `minVol` | Niedrigste Zellspannung | V | `minVol` ÷ 100 |

**Netz** – ein Gerät für den Netzzähler:

| Schlüssel | Inhalt | Einheit | Quelle in `status_api` |
|---|---|---|---|
| `gridPower` | Netzsaldo, positiv = Bezug | W | `grid.power` |

ThingsBoard speichert keine Einheiten. Die trägst du im jeweiligen Dashboard-Widget ein.

**Tipp für Dashboards:** Ein Zeitreihen-Widget kann Werte mehrerer Geräte in einem Diagramm zeigen, z. B. `electricLevel` aller Speicher übereinander oder `gridPower` zusammen mit `outputHomePower`. Anders als bei ThingSpeak brauchst du dafür kein Script.

## Kontingent im Free-Tarif

Der kostenlose Tarif der ThingsBoard Cloud erlaubt **5 Geräte** und pro Monat **1 Million Datenpunkte** sowie 0,5 Millionen Nachrichten. Ein Datenpunkt ist ein einzelner Wert, eine Nachricht ein Eintrag pro Gerät und Minute.

Ein Speicher liefert bis zu 7 Datenpunkte pro Minute, das Netz-Gerät einen:

| Speicher | Geräte | Datenpunkte pro Minute | pro Monat (31 Tage) |
|---|---|---|---|
| 1 | 2 | 8 | ca. 357.000 |
| 2 | 3 | 15 | ca. 670.000 |
| 3 | 4 | 22 | ca. 982.000 |
| 4 | 5 | 29 | ca. 1.295.000 – zu viel |

Bis 3 Speicher passt es in den Free-Tarif, bei 3 Speichern allerdings knapp. Die Nachrichten sind mit höchstens rund 180.000 im Monat kein Engpass.

Wie lange ThingsBoard die Daten aufbewahrt, hängt vom Tarif ab (Aufbewahrungsdauer bzw. „Data point storage days“). Den aktuellen Stand siehst du in ThingsBoard unter *Plan and billing*. Die Angaben oben entsprechen dem Stand September 2026 – maßgeblich ist die [Tarifübersicht von ThingsBoard](https://thingsboard.io/docs/paas/eu/reference/subscriptions/).

## Eigener ThingsBoard-Server

ThingsBoard gibt es als **Community Edition** kostenlos und quelloffen zum Selbstbetrieb, ohne Grenzen bei Geräten und Datenpunkten. Läuft sie z. B. als Docker-Container auf deinem NAS, bleiben alle Daten in deinem Heimnetz.

Im Proxy trägst du dann nur die Adresse deines Servers ein, z. B. `http://nas:8080`. Alles andere ist gleich: Geräte anlegen, Tokens kopieren, eintragen.

Die Installation der Community Edition selbst beschreibt ThingsBoard in seiner [Installationsanleitung](https://thingsboard.io/docs/user-guide/install/installation-options/). Rechne mit etwas Arbeitsspeicher – ThingsBoard ist deutlich schwerer als der Proxy.

## Betreiber und Datenschutz

Dieser Abschnitt betrifft nur die ThingsBoard **Cloud**. Beim eigenen Server bleiben die Daten bei dir.

**Betreiber:** Vertragspartner der ThingsBoard Cloud ist ThingsBoard, Inc., ein Unternehmen mit Sitz in den USA.

**Speicherort:** Bei der Cloud-Region Europa (`eu.thingsboard.cloud`) werden die Daten im Rechenzentrum in Frankfurt gespeichert. Das ist ein Unterschied zu ThingSpeak, wo die Daten in den USA liegen können.

**Rechtlicher Rahmen:** Weil der Betreiber ein US-Unternehmen ist, kann er trotz EU-Speicherort US-Recht unterliegen, etwa dem CLOUD Act. Laut Nutzungsbedingungen bist du selbst dafür verantwortlich, dass deine Nutzung mit der DSGVO vereinbar ist. Details stehen in den [Nutzungsbedingungen der EU Cloud](https://thingsboard.io/products/paas/eu/terms-of-use/).

**Was übertragen wird:** Nur Leistungswerte, Ladestände, die Zellspannung und Zeitstempel – keine Namen, Adressen, Geräte-Seriennummern oder IP-Adressen deiner Geräte. Die Gerätenamen in ThingsBoard vergibst du selbst. Ganz belanglos sind solche Verläufe trotzdem nicht: Am Hausverbrauch über den Tag lässt sich zum Beispiel ablesen, wann jemand zu Hause ist.

**Empfehlung:** Dashboards nicht öffentlich freigeben. Wer seine Daten nicht außer Haus geben möchte, nimmt einen eigenen Server oder lässt den Upload einfach aus.

Stand dieser Angaben: September 2026. Maßgeblich sind die aktuellen Seiten von ThingsBoard.

## Meldungen im Log

Im Normalbetrieb schreibt der Proxy pro Minute und Gerät eine Zeile:

```
[thingsboard] Hub 0 2026-09-29T16:13:00Z gesendet (7 Werte)
[thingsboard] Netz 2026-09-29T16:13:00Z gesendet (1 Wert)
```

Ohne offenes Dashboard kommen davor zwei Zeilen dazu. Sie gelten für ThingSpeak und ThingsBoard gemeinsam:

```
[bridge] kein Dashboard offen - eigene Abfrage status_api (wecken)
[bridge] eigene Abfrage status_api (frischer Stand)
```

Ist ein Speicher offline, steht dort:

```
[thingsboard] Hub 1 2026-09-29T16:13:00Z: keine Daten (offline oder nicht geliefert)
```

Mit `-q` oder `-s` fallen diese Zeilen weg. Fehler erscheinen immer:

```
[thingsboard] Hub 0 2026-09-29T16:13:00Z: verworfen (HTTP 401)
[bridge] Shelly nicht erreichbar: ...
```

## Fehlersuche

**`/thingsboard` meldet 404 bzw. die Startmeldung sagt „nicht verfuegbar“.**
`ts_bridge.py` liegt nicht neben `zendure_proxy.py`. Bei der exe: Die Datei muss beim Bauen im selben Ordner liegen, sonst baut PyInstaller ohne Cloud-Upload.

**„ThingsBoard lehnt das Token ab (HTTP 401)“ beim Speichern.**
Das Token ist falsch oder gehört zu einem anderen Server. Beim Gerät erneut „Copy access token“ nutzen und prüfen, ob die Server-Adresse stimmt (EU-Cloud: `eu.thingsboard.cloud`, nicht `thingsboard.cloud`).

**Fehlermeldung mit `SSL` oder `WRONG_VERSION_NUMBER`.**
Die Adresse beginnt mit `https://`, der Server spricht aber nur `http://` – typisch bei einem eigenen Server. Adresse mit `http://` eintragen. Ohne Angabe ergänzt der Proxy automatisch `https://`.

**Regelmäßig „verworfen (HTTP 429)“ im Log.**
Das Monatskontingent oder eine Ratenbegrenzung ist erreicht. Unter *Plan and billing* nachsehen. Bei 3 Speichern im Free-Tarif ist der Spielraum knapp.

**`outputHomePower`, `gridInputPower`, `packInputPower` und `outputPackPower` fehlen.**
Auf dem Dashboard-Shelly läuft noch zendash_watch vor 3.5.0. Das Script aktualisieren, zum Beispiel mit dem [Configurator](../Multiconfigurator/readme.md).

**ThingSpeak ist aus, trotzdem fragt der Proxy den Shelly ab.**
Das ist richtig, solange ThingsBoard aktiv ist. Beide Ziele nutzen dieselben Abfragen. Erst wenn beide aus sind, fragt der Proxy nichts mehr ab.
