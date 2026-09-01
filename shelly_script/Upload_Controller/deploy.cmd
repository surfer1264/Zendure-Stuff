@echo off
setlocal

REM ====================================================================
REM  HIER ANPASSEN
REM ====================================================================
set SHELLY_IP=192.168.178.117
set SKRIPTNAME=zerooutput

REM Generische Version (frisch von GitHub geladen)
set QUELLE=zerooutput_multi_kvs_mini.js
REM Datei mit deinem CONFIG-Block
set MEINE_CONFIG=myconfig.js
REM Zwischendatei, die hochgeladen wird
set FERTIG=fertig1.js
REM ====================================================================

cd /d "%~dp0"

echo.
echo === 1/2  CONFIG-Block einsetzen ===
python swap_config.py "%QUELLE%" --config-from "%MEINE_CONFIG%" -o "%FERTIG%"
if errorlevel 1 goto :fehler

echo.
echo === 2/2  Auf Shelly %SHELLY_IP% laden ===
python upload_shelly.py "%FERTIG%" --ip %SHELLY_IP% --name %SKRIPTNAME%
if errorlevel 1 goto :fehler

echo.
echo Alles erledigt.
pause
exit /b 0

:fehler
echo.
echo ABBRUCH - siehe Meldung oben. Auf dem Shelly wurde nichts veraendert,
echo falls der Fehler im Schritt 1 auftrat.
pause
exit /b 1
