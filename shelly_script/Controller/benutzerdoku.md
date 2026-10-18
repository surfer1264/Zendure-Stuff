# Controller im Alltag

> Diese Seite erklärt in einfachen Worten, was der Controller tut, woran du siehst, dass alles läuft, und wie du später etwas änderst. Eingerichtet wird er mit dem [Configurator](../Multiconfigurator/readme.md), siehe [Getting Started](readme.md). Alle technischen Details stehen in der [Gesamtdokumentation](gesamtdoku.md).

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

---

## 1) Was der Controller macht

Der Controller läuft auf einem Shelly und schaut alle 4 Sekunden, wie viel Strom dein Haus gerade aus dem Netz bezieht oder einspeist. Dann steuert er deine Zendure-Speicher:

- **Haus braucht Strom** → die Speicher geben ab.
- **Überschuss da** (z. B. von einer anderen Solaranlage) → die Speicher laden, wenn du das erlaubt hast.
- **Mehrere Speicher** → bei wenig Bedarf arbeitet nur einer, bei viel Bedarf alle gemeinsam.
- Alles läuft **lokal**, ohne Cloud und ohne App. Fällt das Internet aus, regelt er weiter.

**Was normal ist:**

- Der Netzwert steht nie exakt auf 0 W, sondern pendelt um wenige Watt. Die erlaubte Abweichung (Toleranz) zeigt das Dashboard unter dem Sollwert.
- Schaltet ein großer Verbraucher ein oder aus (Wasserkocher, Herd), gibt es für ein paar Sekunden Bezug oder Einspeisung, bis die Speicher nachgezogen haben.
- Ist der Netzbezug länger ruhig, meldet der Controller „Sparmodus“ und fragt die Speicher seltener ab.

⚠️ Betrieb auf eigene Gefahr und Verantwortung. Der Controller entbindet dich nicht davon, geltende Regeln (z. B. zum Netzexport) einzuhalten.

---

## 2) Läuft alles?

- **Im [Dashboard](../zendash_watch_API_ZenSDK/dashboard.md):** Alle Speicher haben einen grünen Statuspunkt, der Netzwert liegt nahe am Sollwert.
- **Im Log des Controller-Shelly** (Weboberfläche → Scripts → Log) erscheint alle paar Sekunden eine Zeile wie

    ```text
    Netzsaldo: 12 W | Ist-Summe: 340 W | Regelsignal: 352 W | Ladekorrektur: 0 W
    ```

    *Netzsaldo* ist dein Netzbezug (negativ = du speist ein).

**Einmal nach der Einrichtung prüfen:** Schalte einen großen Verbraucher ein. Der Netzwert muss kurz **steigen**. Sinkt er stattdessen, ist das Vorzeichen deines Messgeräts andersherum: im Configurator unter „Netzquelle“ das Häkchen „Vorzeichen ist invertiert“ setzen und neu hochladen.

---

## 3) Deine Einstellungen in einfachen Worten

Diese Fragen stellt dir der Configurator. Alles andere ist sinnvoll voreingestellt.

| Einstellung | Bedeutet |
|---|---|
| **Reserve** (min. SoC) | So leer darf der Akku höchstens werden. Der Rest bleibt für Notfälle. |
| **Ladeziel** (max. SoC) | So voll wird der Akku aus dem Netz geladen. |
| **Maximale Leistung** | So viel darf der Speicher höchstens abgeben bzw. aufnehmen. |
| **Laden vom Netz** | Darf der Speicher Überschuss aufnehmen, z. B. von einer anderen Solaranlage? Nein = er lädt nur mit seiner eigenen PV. |
| **Bei vollem Akku** | Darf ein voller Speicher ins Netz einspeisen? „Automatisch“ (empfohlen): erlaubt, solange ein anderer Speicher noch laden kann; sind alle voll, wird es gesperrt, bis wieder Platz ist. Alternativ „immer erlauben“ oder „immer sperren“. |
| **Netzquelle** | Woher der Controller den Netzwert bekommt, z. B. Shelly Pro 3EM oder Zendure Smart Meter. Für viele Messgeräte gibt es fertige Vorlagen. |
| **Benachrichtigungen** | Nachricht per Webhook, Signal oder WhatsApp, wenn etwas mehrmals hintereinander schiefgeht (z. B. ein Speicher nicht erreichbar ist), und noch einmal, sobald es wieder läuft. |
| **Live-Einstellungen (KVS)** | Erlaubt Änderungen im laufenden Betrieb, z. B. aus dem Dashboard. Ohne sie kann das Dashboard nur anzeigen. |

---

## 4) Etwas ändern

### Dauerhaft, z. B. einen Speicher hinzufügen oder die Leistung ändern

1. [Helfer](../Multiconfigurator/readme.md#empfohlen-der-lokale-helfer-exe-installer) starten, **„Neu konfigurieren oder manuell updaten“** wählen.
2. Unter „Funktionen“ **„📡 Vom Controller-Shelly lesen“** – deine aktuelle Konfiguration wird übernommen.
3. Ändern, z. B. unter „Geräte“ einen Speicher hinzufügen.
4. Im Ergebnis **„⚡ Direkt hochladen“**. Der Controller startet neu, fertig.

Hast du Speicher hinzugefügt oder ihre Leistung geändert: Die Regelparameter passt der Configurator nicht von selbst an. Prüfe im Schritt „Regelparameter“ die Schwellen fürs Verteilen der Leistung, siehe [Empfehlung für die Ersteinstellung](gesamtdoku.md#7b-empfehlung-für-ersteinstellung).

### Sofort, ohne Neustart – im Dashboard

Nach dem Entsperren (Schloss oben rechts) kannst du im [Dashboard](../zendash_watch_API_ZenSDK/dashboard.md#was-du-einstellen-kannst) live ändern:

- **Sollwert** – etwas mehr Bezug oder Einspeisung als 0 W
- **Fix-Entladung** – feste Leistung statt Regelung
- je Speicher: **Entladen erlaubt**, **Laden vom Netz erlaubt**, **Reserve**
- **Manuelles Laden** aus dem Netz mit fester Leistung

Das geht nur mit eingeschalteten Live-Einstellungen (KVS). Ändere solche Werte von Hand, nicht automatisch alle paar Minuten (z. B. aus Home Assistant) – jede Änderung wird im Speicher des Shelly abgelegt, und der verschleißt dabei. Mehr dazu: [Gesamtdokumentation, Kapitel 13](gesamtdoku.md#13-live-override-der-regelparameter-per-kvs-z-b-home-assistant).

### Update auf eine neue Version

Helfer starten → **„Updaten“**. Deine Einstellungen bleiben erhalten. Ablauf: [Update](../Multiconfigurator/readme.md#4-update).

---

## 5) Wenn etwas nicht klappt

| Was passiert | Was du tun kannst |
|---|---|
| Ein Speicher ist dauerhaft „nicht erreichbar“ | IP-Adresse noch richtig? Am besten im Router eine feste IP vergeben. Speicher im selben Netz (nicht im Gast-WLAN)? |
| Ein Speicher macht nicht, was er soll | Ist er in der Zendure-App noch im **HEMS**? Dort entfernen, sonst steuert die Cloud dazwischen. |
| Der Controller startet nicht oder stürzt ab | Auf dem Controller-Shelly darf nur dieses eine Script liegen. Mit [Speicher prüfen](../Multiconfigurator/readme.md#speicher-eines-shelly-prüfen) nachsehen, wie viel frei ist. |
| Netzwert läuft falsch herum | siehe [Läuft alles?](#2-läuft-alles) – Vorzeichen umdrehen |
| Ein Speicher tut gerade nichts | Im Dashboard steht der Grund in Klartext, z. B. „voll, Laden gesperrt“ oder „leer, Entladen gesperrt“. Meist ist das gewollt. |
| Du brauchst Hilfe | Mit dem Helfer ein [Log aufzeichnen](../Multiconfigurator/readme.md#log-aufzeichnen) und in den [Discussions](https://github.com/surfer1264/Zendure-Stuff/discussions) fragen. Für mehr Details vorher die Debug-Ausgaben einschalten (Häkchen im Ergebnis-Schritt), danach wieder aus. |

---

## 6) Weiter lesen

- 🧭 [Getting Started](readme.md) – Einrichtung, auch von Hand
- 🛠️ [Configurator](../Multiconfigurator/readme.md) – Einrichten, Update, Fehlermeldungen
- 📊 [Dashboard](../zendash_watch_API_ZenSDK/dashboard.md) – Bedienung und Anzeige
- 📖 [Gesamtdokumentation](gesamtdoku.md) – alle Einstellungen, Log-Zeilen ([Kapitel 12](gesamtdoku.md#12-logging)), Fachbegriffe wie `socLimit` und `gridReverse` ([Kapitel 12.8](gesamtdoku.md#128-wertetabellen-kurzreferenz)), Testmodus ([Kapitel 4c](gesamtdoku.md#4c-testmodus-dryrun))
- 🐛 Probleme melden: [GitHub Issues](https://github.com/surfer1264/Zendure-Stuff/issues)
