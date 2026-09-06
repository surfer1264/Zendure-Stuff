@echo off
setlocal

REM ====================================================================
REM  HIER ANPASSEN
REM ====================================================================
set SHELLY_IP=192.168.178.149
set SKRIPTNAME=zendash

REM Generische Version (frisch von GitHub geladen)
set QUELLE=zendash_api_src.js
REM Datei mit deinem CONFIG-Block
set MEINE_CONFIG=myconfig.js
REM Zwischendatei, die hochgeladen wird
set FERTIG=tmp.js
set MINI=zendash_api_mini.js
REM ====================================================================

cd /d "%~dp0"

echo.
echo === 1/3  CONFIG-Block einsetzen ===
python3 swap_config.py "%QUELLE%" --config-from "%MEINE_CONFIG%" -o "%FERTIG%"
if errorlevel 1 goto :fehler

echo === 2/3  MINIFY ===
python3 minify_keep_config.py "%FERTIG%" "%MINI%"
del "%FERTIG%"
if errorlevel 1 goto :fehler

echo.
echo === 3/3  Auf Shelly %SHELLY_IP% laden ===
python3 upload_shelly.py "%MINI%" --ip %SHELLY_IP% --name %SKRIPTNAME%
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


