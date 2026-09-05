@echo off
setlocal

REM ====================================================================
REM  HIER ANPASSEN
REM ====================================================================
set SHELLY_IP=192.168.178.149
set SKRIPTNAME=zendash

REM Generische Version (frisch von GitHub geladen)
set QUELLE=zendure_dashboard_api.js
REM Datei mit deinem CONFIG-Block
set MEINE_CONFIG=myconfig.js
REM Zwischendatei, die hochgeladen wird
set FERTIG=zendash_api_upload.js
set MINI=zendash_api_upload_mini.js
REM ====================================================================

cd /d "%~dp0"

echo.
echo === 1/2  CONFIG-Block einsetzen ===
python swap_config.py "%QUELLE%" --config-from "%MEINE_CONFIG%" -o "%FERTIG%"
if errorlevel 1 goto :fehler

python3 minify_keep_config.py "%FERTIG%" "%MINI%"
if errorlevel 1 goto :fehler

echo.
echo === 2/2  Auf Shelly %SHELLY_IP% laden ===
python upload_shelly.py "%MINI%" --ip %SHELLY_IP% --name %SKRIPTNAME%
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


