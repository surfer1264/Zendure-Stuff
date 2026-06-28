# Beschreibung meiner Anpassungen an Z-HA
## Motivation

- Z-HA Entwicklung stockt
- zum Zeitpunkt der Veröffentlichung von 1.2.5 wurden neue Gerätegenerationen nicht unterstützt
- mit 1.3.1 wurde eine umfangreiche Migration und Umbenennung der Entitäten gestartet, mehr oder weniger umfanggreiche Nacharbeiten (z.B. Node Red waren zu erwarten

## Repo 1.2.5_Hack

https://github.com/surfer1264/Zendure-Stuff/tree/main/zendure_ha_1-2-5-hack

Folgende Änderungen wurden an 1.2.5 (Feb. 2026) durchgeführt

## 1. Aufnahme SF2400Pro und SF2400AC+ in die Geräteprofile

**Problem:**
</br>
z-HA 1.2.5 unterstütze die neuen Geräteklassen nicht!

**Lösung**
</br>
Aufnahme der Hubs in die Gerätekonfiguration

## 2. Aufnahme des P1-Sensors in den ZendureManager als Select Feld und anpassbare Entität

**Problem:**
</br>
Nutzer wollen EInfluss auf Sollwert und Hysterese haben. Dies kann man über einen viruellen P1-Sensor lösen (als Ableitung des echten P!-Sensors (z.B: Shelly Pro3EM). Der P1 ist nur über den Konfigurationsdialog eingebbar. Danach muss die Integration neu geladen werden

**Lösung:**
</br>
Der P1-Sensor steht nun als Selct-Feld (editierbar) im Zendure-Manager zur Verfügung.
Das Select-Feld filtert dabei bereits auf die verfügbaren Power-Sensoren der HA-Instanz. Die Entität des P1 kann nun in HA_Automatisierungen (und NodeRed) verwendet werden.

- siehe: https://github.com/surfer1264/Zendure-Stuff/wiki/P1-Sensor-in-Z‐HA-konfigurierbar-machen
- siehe P1-Sensor bauen: https://github.com/surfer1264/Zendure-Stuff/wiki/Virtueller-P1‐Sensor


## 3. Anpassung der Schwellwerte für das Zusammenspiel mehrerer Hubs (Entladen)

**Ausgangspunkt:**
</br>
Das Zusammenspiel zweier Hubs wird über zwei Parameter orchestriert und erläutere ich an folgendem einfachen Beispiel exemplarisch:
</br>
Standard (für zwei 800W Hubs): 
- bis 400W läuft ein Hub allein
- ab 400W werden Hubs zusammengeschaltet, jeder Hub trägt die Last von 200W
- wenn ein Hub 120W unterschreitet, wird nach einer speziellen Logik ein Hub wieder abgeschaltet
- **Achtung**: die Schwellwerte werden abgeleitet aus einem Teiler/Faktor aus den jeweiligen HW-Grenzwerten, definiert in den Device-Profilen und werden erst zur Laufzeit ermittelt.

**Problem:**
- Die Parameter (Teiler/Faktor) sind im Code fest verdrahtet und nicht konfigurierbar.
- Das Zusammenschalten erfolgt recht früh. Die Hubs laufen (noch) nicht in einem effizienten Bereich.
- Das Abschalten erfolgt erst recht spät.

**Lösung**
</br>
Die Parameter (Teiler/Faktor) zur Ermittlung der Schwellwerte wurden in der `const.py` aufgenommen. Durch die Externalisierung, kann eine Individualisierung vorgenommen werden  
Die Parameter (Teiler/Faktor) wurden nun so gesetzt, dass beispielhaft für einen 800W-Hub folgende Grenzen gelten:
- gemeinsamer Start erst bei 533W
- Stopp bei Unterschreiten von 160W
- Achtung: Vorsicht beim Spielen mit den Parametern, man muss die FUnktionsweise verstanden haben...das unkontrollierte Setzen irgendwelcher Werte, führt auch zu unvorhergeshenem Regelverhalten.

- siehe: https://github.com/surfer1264/Zendure-Stuff/wiki/Z‐HA-Entlade-Effizienz-steigern


## 4. Übernahme des SOCFULL Fixes aus dem zHA gitHub Repo

**Problem:**
</br>
Wenn der Hub die obere Ladegrenze 100% erreicht hat, geht der Hub in den Standby, die Anforderungen des Haushalts werden nicht mehr bedient. PV Leistung/Akku-Leistung wird nicht abgerufen.

**Achtung:** Es gibt Stimmen, die sagen: "Funktioniert einwandfrei". Es gibt aber auch gegenteilige Stimmen: "Funktioniert trotzdem nicht".

**Lösung**
</br>
Übernahme eines Fixes aus dem Z-HA-Github-Repo:

- siehe: https://github.com/Zendure/Zendure-HA/pull/1296
- siehe: https://github.com/Zendure/Zendure-HA/commit/b221cd086c1030561ac758f8ae0326c7c18a30da



## 5. Berücksichtigung der Fusegroup Einstellungen bei der Ermittlung der Schwellwerte für das Entladeverhalten

**Ausgangspunkt:**
</br>
Die Schwellwerte zum Laden/Entladen richten sich an den HW-Grenzen aus (Geräteprpfile in zHA). Üblicherweise werden auch passende FuseGroups gewählt.

**Problem:**
</br>
Betreibt man einen SF2400 als klassisches BKW mit 800W Begrenzung würde man auch die passende 800W FuseGroup auswählen.
In der Ableitung der Schwellwerte für den gemeinsamen Betrieb von Hubs gelten aber weiterhin die HW-Grenzen. Das Zuschalten eines Hubs würde standardmäsig erst bei 1200W erfolgen, das Abschalten eines Hubs erst bei 480W. Insbesondere letzteres kann in bestimmten Lastbereichen zu einem EIN/AUS-Schalten eines Hubs führen, wenn dieser Hub der Hub mit dem schwächeren SoC ist. Die gewählte FuseGroup hat überhaupt keinen Einfluss auf die Parametrisierung.

**Lösung**
</br>
Bei der Ableitung der Schwellwerte wird die gewählte FuseGroup nun berücksichtigt:

`pwr_max = min(Fuse-Group, Hardware-Limit)`

Folge: ein SF2400 verhält sich mit einer gewählten FuseGroup "800W" auch wie ein 800W-Hub. Die Einstellungen der FiseGroup wird damit führend, ohne die HW-Grenzen zu missachten.

- siehe: https://github.com/surfer1264/Zendure-Stuff/wiki/Regelung-SF1200-und-SF2400Pro-konkret-mit-zwei-FuseGroups










