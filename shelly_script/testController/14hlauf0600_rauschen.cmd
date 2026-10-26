set LOGFILE=14tageslauf.log
set RELEASE=533

del %LOGFILE%
del closed_loop_result.csv
del report.html

set START_MIN=360
set CYCLES=12600

set SPEED_FACTOR=120
set STEP_MIN=0.0666667
set INTERVAL_MS=4000
set START_SOC=30
set LOAD_SCALE=0.5

rem --- Rauschmodell (leer lassen = Mock ohne Rauschen wie bisher) ---
set SCENARIO=szenario_werktag.json
set NOISE_SEED=42

rem Geraeteverzoegerung (leer bzw. 0 = Vorgabe wirkt sofort)
set WRITE_LAG_S=1.25
set DEVICE_RATE_WPS=350
set START_DELAY_S=3.25
set DEVICE_DELAY_S=
set REPORT_AGE_S=0

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format 'yyMMdd-HHmmss'"') do set TS=%%i
set OUTDIR=Test14h-%RELEASE%-seed%NOISE_SEED%-%TS%
mkdir "%OUTDIR%"

echo Werte fuer diesen Lauf (Ordner: %OUTDIR%):
echo   SPEED_FACTOR=%SPEED_FACTOR%
echo   STEP_MIN=%STEP_MIN%
echo   CYCLES=%CYCLES%
echo   INTERVAL_MS=%INTERVAL_MS%
echo   START_SOC=%START_SOC%
echo   LOAD_SCALE=%LOAD_SCALE%
echo   SCENARIO=%SCENARIO%
echo   NOISE_SEED=%NOISE_SEED%
echo   WRITE_LAG_S=%WRITE_LAG_S%
echo   DEVICE_RATE_WPS=%DEVICE_RATE_WPS%
echo   START_DELAY_S=%START_DELAY_S%
echo   DEVICE_DELAY_S=%DEVICE_DELAY_S%
echo   REPORT_AGE_S=%REPORT_AGE_S%

node run_test.js > %LOGFILE% 2>&1

echo Fertig - erste Log-Zeile zur Kontrolle:
findstr /N "^" %LOGFILE% | findstr "^1:"

node generate_charts.js closed_loop_result.csv report.html

move %LOGFILE% "%OUTDIR%\" >nul
move closed_loop_result.csv "%OUTDIR%\" >nul
move report.html "%OUTDIR%\" >nul
copy zdmc_test.js "%OUTDIR%\" >nul
if not "%SCENARIO%"=="" copy "%SCENARIO%" "%OUTDIR%\" >nul

echo.
echo Ergebnisse gespeichert in: %OUTDIR%
pause
