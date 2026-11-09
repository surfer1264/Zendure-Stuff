<a href="https://ko-fi.com/surfer1264"><img width="143" alt="Buy me a coffee at ko-fi.com" src="../../../shelly_script/img/kofi2.png" /></a>

# Upload Controller to Shelly

> ⚠️ **Veraltet – wird nicht mehr weiterentwickelt.** Ersetzt durch den [Configurator](../../../shelly_script/Multiconfigurator/readme.md) mit Helfer (Direkt-Upload und Update). Für eigene Deploy-Pipelines gibt es die Werkzeuge jetzt in den Ordnern [Controller/Deploy](../../../shelly_script/Controller/Deploy) und [zendash_watch_API_ZenSDK/Deploy](../../../shelly_script/zendash_watch_API_ZenSDK/Deploy). Diese Seite bleibt nur zum Nachschlagen.

Das `deploy Script` ersetzt die generische Konfig mit deiner konkreten Config `myconfig.js`, lädt den Controller auf den Shelly und startet den Controller. Update erfolgt nach gleichem Muster.

* Voraussetzung ist eine Python Umgebung
   	* gibt es für jede Umgebung, einfach nach installieren

**Nur geeignet für den Upload auf ein Shelly-Device**

* Lade die Dateien in ein Verzeichnis
* Lade den Shelly Multi-Device-Controller `zerooutput_multi_kvs_src.js` in das gleiche Verzeichnis
* Bennene den Controller `zerooutput_multi_kvs_src.js`
* Stelle sicher, dass Deine `myconfig.js` im gleichen Verzeichnis liegt
    * die `myconfig.js` erzeuge Dir zuvor aus dem Webkonfigurator oder hast Du Dir selber angelegt
* Editiere die `deploy.cmd`
    * Trage die IP-Adresse des Shelly-Devices ein, auf den der Controller geladen werden soll
* Fertig
* `deploy.cmd` starten
    * der Controller übernimmt jetzt Deine `myconfig.js`
    * Der Controller-Code wird minimiert
    * Der Controller wird auf den Shelly geladen und gestartet
* Updateprozess erfolgt analog, keine Änderungen nötig, denn
    * deploy stoppt das Script, aktualisiert und startet erneut
