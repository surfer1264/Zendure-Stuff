@echo off
rem Testmatrix: mehrere jumpFactor-Werte (schnelle Flanke) x mehrere Seeds, dampingFactor fest
rem Alle uebrigen Werte wie matrix_damping.cmd. Je Wert ein eigener Ergebnisordner.
rem Benoetigt im selben Ordner: matrix.js, run_test.js, mock_server.js,
rem shelly_shim.js, zdmc_test.js, szenario_werktag.json (generate_charts.js optional)

set START_MIN=360
set CYCLES=12600

set SPEED_FACTOR=100
rem Schritt = Regelintervall aus zdmc_test.js (interval: 4000 ms -> 4/60 min)
set STEP_MIN=0.0666667
set INTERVAL_MS=4000
set START_SOC=30
set LOAD_SCALE=0.4

set SCENARIO=szenario_werktag.json

rem Geraeteverzoegerung (leer bzw. 0 = Vorgabe wirkt sofort)
set WRITE_LAG_S=1.25
set DEVICE_RATE_WPS=350
set START_DELAY_S=3.25
set DEVICE_DELAY_S=
set REPORT_AGE_S=0

set DAMPINGS=0.65
set SEEDS=1,2,3
set PARALLEL=4

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format 'yyMMdd-HHmmss'"') do set TS=%%i
for %%J in (0.8 0.65 0.5) do call :lauf %%J

echo.
echo Ergebnisse in: Matrix-%TS%-jump...  (je Wert matrix_ergebnis.md, matrix_laeufe.csv, je Lauf ein Unterordner)
pause
goto :eof

:lauf
set JUMP=%1
set MATRIX_DIR=Matrix-%TS%-jump%1
node matrix.js
copy zdmc_test.js "%MATRIX_DIR%\" >nul
copy "%SCENARIO%" "%MATRIX_DIR%\" >nul
goto :eof
