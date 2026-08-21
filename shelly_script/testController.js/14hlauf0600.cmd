set LOGFILE=14tageslauf.log

del %LOGFILE%
del closed_loop_result.csv
del report.html

set START_MIN=360
set CYCLES=16800

set SPEED_FACTOR=150
set STEP_MIN=0.05
set INTERVAL_MS=3000
set START_SOC=30
set LOAD_SCALE=1

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format 'yyMMdd-HHmmss'"') do set TS=%%i
set OUTDIR=Testlauf-%TS%
mkdir "%OUTDIR%"

echo Werte fuer diesen Lauf (Ordner: %OUTDIR%):
echo   SPEED_FACTOR=%SPEED_FACTOR%
echo   STEP_MIN=%STEP_MIN%
echo   CYCLES=%CYCLES%
echo   INTERVAL_MS=%INTERVAL_MS%
echo   START_SOC=%START_SOC%
echo   LOAD_SCALE=%LOAD_SCALE%

node run_test.js > %LOGFILE% 2>&1

echo Fertig - erste Log-Zeile zur Kontrolle:
findstr /N "^" %LOGFILE% | findstr "^1:"

node generate_charts.js closed_loop_result.csv report.html

move %LOGFILE% "%OUTDIR%\" >nul
move closed_loop_result.csv "%OUTDIR%\" >nul
move report.html "%OUTDIR%\" >nul
copy zdmc_test.js "%OUTDIR%\" >nul

echo.
echo Ergebnisse gespeichert in: %OUTDIR%
pause
