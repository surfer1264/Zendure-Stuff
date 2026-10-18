# Shelly Multi-Device Controller – Kurzanleitung für Nutzer

> Diese Anleitung ist die **schlanke, verständliche Kurzversion** der vollständigen technischen Dokumentation. Sie erklärt, was der Controller tut, wie du ihn einrichtest und wie du die wichtigsten Alltagsfragen selbst beantwortest – ohne Technik-Details, die du im Alltag nicht brauchst.
>

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

---

## 1) Wozu ist das Ganze gut?

Stell dir vor, du hast einen Stromzähler und einen oder mehrere Zendure-Speicher zuhause. Der Controller schaut sich **laufend an**, wie viel Strom dein Haus gerade vom Netz bezieht oder ins Netz einspeist – und steuert deine Zendure-Geräte automatisch so, dass **möglichst wenig Strom** teuer eingekauft oder ungenutzt ins Netz abgegeben wird.

- Er lädt deine Speicher, wenn Überschuss da ist (z. B. Solarstrom von der Dachanlage oder anderen Speichern, falls du das erlaubst).
- Er entlädt deine Speicher, wenn dein Haus gerade Strom braucht.
- Hast du **mehrere** Geräte, verteilt er die Arbeit automatisch fair unter ihnen – bei kleinem Bedarf nutzt er nur eins (schont die Akkus), bei großem Bedarf alle gemeinsam.
- Alles läuft **lokal auf einem kleinen Shelly-Gerät** – ohne Cloud, ohne Internet, ohne App. Funktioniert also auch, wenn dein Internet mal ausfällt.

⚠️ **Wichtig:** Betrieb auf eigene Gefahr und Verantwortung. Der Controller entbindet dich nicht davon, geltende regulatorische Regeln (z. B. zum Netzexport) einzuhalten.

---

## 2) Was du vorher brauchst

Kurz: ein Shelly (Gen2 oder neuer) mit genug Script-Speicher, ein Smartmeter und Zendure-Geräte mit **fester IP-Adresse** im selben Netz – und die Geräte **aus dem HEMS** in der Zendure-App entfernt. Welche Shellys und Smartmeter passen und wie du den Speicher prüfst: **[Kompatible Geräte](../kompatible_geraete.md)**.

---

## 3) Einrichtung und die wichtigsten Einstellungen

**Einrichten** geht am einfachsten mit dem [Configurator](../Multiconfigurator/readme.md) – er fragt alles Nötige ab und lädt das Script direkt hoch. Wer das Script von Hand anpassen und hochladen will, findet die Schritte unter [Getting Started → Ohne Configurator](readme.md#ohne-configurator-von-hand).

Egal wie du einrichtest: Für jedes Zendure-Gerät gibt es im CONFIG-Block einen Eintrag in `devices`. Hast du mehrere Geräte, kommt pro Gerät ein Eintrag dazu (siehe [Kapitel 5](#-ein-weiteres-gerät-hinzufügen)).

**Was die wichtigsten Werte bedeuten**, in einfachen Worten:

| Einstellung | Bedeutet für dich |
|---|---|
| `ip` | Wo im Netzwerk dein Gerät zu finden ist – muss immer gesetzt werden |
| `label` | Nur ein Name, taucht in Meldungen/Log auf |
| `minSoc` | "Nicht leerer als …%" – Schutzgrenze fürs Entladen |
| `maxSoc` | "Nicht voller als …%" – Grenze fürs Laden aus dem Netz |
| `maxOutput` | Wie viel Leistung das Gerät maximal abgeben (exportieren) darf |
| `maxInputPower` | Wie viel Leistung das Gerät maximal aus dem Netz laden darf |
| `dischargeAllowed` | Darf das Gerät überhaupt entladen? (`false` = Gerät wird nie zum Entladen benutzt, kann aber weiter laden) |
| `reverse` | Darf das Gerät aus dem Netz laden? (`false` = lädt nie vom Netz) |
| `dryRun` | Testmodus: Gerät wird ausgelesen und mitgerechnet, aber **nie** tatsächlich angesteuert |

**Stromzähler** – der Controller braucht einen laufenden Netz-Messwert. Dafür steht bei `gridSource` eine dieser drei Optionen:

| Wenn du … | dann setze `gridSource` auf … |
|---|---|
| den Controller **direkt auf deinem Shelly Pro 3EM** laufen lässt | `"local"` (schnellste, einfachste Option) |
| einen **separaten** Shelly Pro 3EM im Netzwerk als Zähler nutzt | `"remote"` (zusätzlich `gridSourceIp` eintragen) |
| einen anderen Zähler nutzt (z. B. Zendure Smart Meter, Tasmota, …) | `"http_json"` (zusätzlich `gridSourceUrl` und `gridSourceField` eintragen) |

Bei `"http_json"` rufst du die angegebene Adresse einmal im Browser auf, suchst dort das Feld mit der Gesamtleistung (z. B. `total_power`) und trägst dessen Namen bei `gridSourceField` ein. **Achtung:** bei geschachtelten JSON-Strukturen (mehrere öffnende geschweifte Klammern), siehe [Kapitel 5.1 der Gesamtdokumentation](gesamtdoku.md#51-eigeneweitere-smart-meter-einbinden-http_json) für ein konkretes Beispiel (Tasmota).

**Vorzeichen prüfen:** Schalte kurz einen größeren Verbraucher ein und schau im Log nach, ob der angezeigte Netzwert **positiver** wird (Bezug steigt). Wird er stattdessen negativer, setze `gridSourceInvert: true`.

⭐ **Das reicht für den Start.** Alle weiteren Einstellungen (siehe [Gesamtdokumentation](gesamtdoku.md#4-konfiguration)) sind sinnvoll voreingestellt und lassen sich später bei Bedarf feinjustieren.

---

## 4) Wichtige Begriffe – bitte nicht verwechseln!

Diese drei Dinge klingen ähnlich, bedeuten aber unterschiedliche Sachen:

| Begriff | Wo eingestellt | Bedeutung |
|---|---|---|
| **`reverse`** | Deine Konfiguration im Script | Darf dieses Gerät grundsätzlich aus dem Netz laden? `true` = Laden erlaubt, `false` = Laden nicht erlaubt |
| **`socLimit`** | Meldet das Zendure-Gerät selbst | Aktueller Betriebszustand des Geräts: `0` = normaler Betrieb, `1` = Ladesperre (Akku voll, Laden vom Netz gesperrt), `2` = Entladesperre |
| **`gridReverse`** | Eine Einstellung direkt am Zendure-Gerät | Legt fest, was das Gerät darf, **sobald es seine Ladesperre erreicht hat** – hat mit der Ladeeigenschaft (`reverse`) nichts zu tun! `1` = Netzexport erlaubt, `2` = Netzexport verboten |

Kurz gesagt: `reverse` ist *deine* Entscheidung, ob ein Gerät laden darf. `socLimit` ist die *Rückmeldung* des Geräts über seinen aktuellen Zustand. `gridReverse` ist ein *zusätzlicher Sicherheitsschalter* am Gerät, der unabhängig davon regelt, ob bei vollem Akku noch exportiert werden darf. Der Controller kann diesen dritten Schalter optional automatisch mitsteuern (`gridReverseMode: "dynamic"`, Standardeinstellung) – dazu musst du nichts weiter tun.

**Zwei weitere hilfreiche Begriffe:**

- **Konzentrationsmodus / Verteilmodus:** Bei kleinem Leistungsbedarf nutzt der Controller nur ein Gerät (schont die anderen Akkus). Wird mehr gebraucht, schaltet er automatisch auf alle passenden Geräte gleichzeitig um.
- **Testmodus (`dryRun`):** Ein Gerät mit `dryRun: true` wird ganz normal beobachtet und in die Berechnung einbezogen, aber es wird **nie** tatsächlich angesteuert. Ideal, um Neues gefahrlos auszuprobieren.

---

## 5) Häufige Aufgaben – "Ich möchte …"

### … ein weiteres Gerät hinzufügen

1. Kopiere im Script einen kompletten Geräteblock (`{ ... }`) und füge ihn mit Komma getrennt in `CONFIG.devices` ein.
2. Trage mindestens die `ip` des neuen Geräts ein, gib ihm einen eigenen `label`.
3. Passe `minSoc`, `maxOutput` etc. an das jeweilige Gerät an.
4. Starte das Script neu – der Rest passt sich automatisch an die neue Geräteanzahl an.

### … ein Gerät nur laden lassen, nie entladen

Setze bei diesem Gerät `dischargeAllowed: false` und `reverse: true`. So wird es nie zum Entladen herangezogen, kann aber weiterhin laden – praktisch, um ein Gerät gezielt für das Laden zu reservieren.

### … ein Gerät nie aus dem Netz laden lassen

Setze `reverse: false`. Das Gerät wird dann nie zum Laden benutzt (z. B. wenn es nur mit Solarstrom laden soll).

### … Neues testen, ohne dass etwas passiert

Setze bei dem betreffenden Geräteeintrag `dryRun: true`. Du siehst im Log, was der Controller *tun würde*, ohne dass real etwas geschrieben wird.

### … benachrichtigt werden, wenn etwas nicht funktioniert

Trage im Bereich `signal` deine Zugangsdaten ein und setze `enabled: true`:

```js
signal: {
  enabled: true,
  typ: "WEBHOOK",   // Alternativen: "SIGNAL" oder "WHATSAPP"
  webhookUrl: "http://<deine-Adresse>/api/webhook/<deine-Webhook-ID>"
}
```

Für Signal/WhatsApp brauchst du zusätzlich einen kostenlosen API-Key von [CallMeBot](https://www.callmebot.com). Du bekommst dann eine Meldung, wenn ein Fehler mehrfach hintereinander auftritt – und eine zweite, sobald er behoben ist.

### … Werte ändern, ohne den Controller neu zu starten

Dafür gibt es die **KVS-Live-Override-Funktion**: Damit kannst du z. B. per Kommandozeile oder aus Home Assistant heraus einzelne Werte (Sollwert, ob ein Gerät laden/entladen darf) live ändern, während der Controller läuft. Aktiviere dazu `kvsEnabled: true` im Script. Details und Beispiele (curl-Befehle, Home-Assistant-Einbindung) findest du in der ausführlichen Dokumentation, Kapitel 13.

⚠️ Diese Funktion schreibt in den internen Speicher des Shelly – nutze sie nur bei echter Bedienung durch dich, nicht automatisiert/zyklisch, damit der Speicher nicht unnötig verschleißt.

### … sicherstellen, dass mein Akku weder leer noch überlastet wird

Das steuerst du über `minSoc` (untere Grenze fürs Entladen) und `maxSoc` (obere Grenze fürs Laden) – für jedes Gerät einzeln einstellbar. Diese Werte werden beim Start automatisch an dein Zendure-Gerät übertragen.

### … prüfen, ob mein Smartmeter richtig eingebunden ist

Siehe "Vorzeichen prüfen" in Schritt 3 – lade kurz mehr Strom im Haus und beobachte, ob der Netzwert im Log wie erwartet ansteigt.

---

## 6) Was steht eigentlich im Log?

Du musst das Log nicht auswendig lernen – hier die wichtigsten Zeilen kurz erklärt:

**Zyklus-Kopfzeile** (einmal pro Regeltakt):

```
Netzsaldo: -4 W | Ist-Summe: 387 W | Regelsignal: 384 W | Ladekorrektur: 0 W
```

→ *Netzsaldo* ist dein aktueller Netzbezug (negativ = du speist ein). *Regelsignal* ist, was der Controller insgesamt gerade tun will.

**Pro-Geräte-Zeile:**

```
SF2400Pro: SOC 88% | socL 0 | gridR 1 | Ist 523 W | Soll 799 W | acMode 2 (Export)
```

→ Zeigt Ladestand (`SOC`), gemeldete Sperren (`socL`, `gridR`, siehe Kapitel 4), tatsächliche (`Ist`) und geplante (`Soll`) Leistung sowie die Richtung (`acMode`: 1 = Laden/Ruhe, 2 = Entladen/Export).

**Fehlermeldungen** sehen so aus:

```
FEHLER (<Gerät>/connect): Geraet nicht erreichbar - aufeinanderfolgende Fehler: 3
```

→ Taucht ein Gerät hier mehrfach auf, prüfe zuerst IP-Adresse und Netzwerkverbindung. Nach mehreren Fehlern in Folge (Standard: 5) bekommst du – falls aktiviert – automatisch eine Benachrichtigung.

---

## 7) Wenn etwas nicht funktioniert

| Symptom | Was du prüfen kannst |
|---|---|
| Gerät wird im Log dauerhaft als "nicht erreichbar" gemeldet | IP-Adresse korrekt? Gerät im selben Netzwerk? Firewall? |
| Script startet nicht / stürzt ab | Speicherplatz des Shelly prüfen (siehe Kapitel 2, `mem_free`) |
| Gerät reagiert nicht wie erwartet | Ist es evtl. noch im HEMS der Zendure-App? Dort entfernen |
| Ich sehe nicht, was der Controller genau tut | `debug: true` setzen und Log genauer beobachten (danach wieder auf `false` zurücksetzen) |

---

## 8) Weiterführende Links

- 📖 [Vollständige technische Dokumentation](gesamtdoku.md)
- 🧭 [Getting Started](readme.md)
- 🛠️ [Konfigurationsassistent](../Multiconfigurator/readme.md)
- 💬 Fragen & Austausch: [GitHub Discussions](https://github.com/surfer1264/Zendure-Stuff/discussions)
- 🐛 Probleme melden: [GitHub Issues](https://github.com/surfer1264/Zendure-Stuff/issues)
- [ab Version 4.x.x Script herunterladen](zerooutput_multi_kvs_mini.js) Minifyer eingesetzt

## 9) Live Erfahrungen

- https://github.com/surfer1264/Zendure-Stuff/wiki/Auswertung_3sun_20260811
- https://github.com/surfer1264/Zendure-Stuff/wiki/Auswertung_zenrix_20260808
- https://github.com/surfer1264/Zendure-Stuff/wiki/Auswertung_zenrix_20260810
- https://github.com/surfer1264/Zendure-Stuff/wiki/Auswertung_surfer1264_20260826
