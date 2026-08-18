del tageslauf.log
del closed_loop_result.csv
set START_MIN=480
set CYCLES=2400

set SPEED_FACTOR=150
set STEP_MIN=0.05
set INTERVAL_MS=3000
set START_SOC=50
set LOAD_SCALE=1

echo Werte fuer diesen Lauf:
echo   SPEED_FACTOR=%SPEED_FACTOR%
echo   STEP_MIN=%STEP_MIN%
echo   CYCLES=%CYCLES%
echo   INTERVAL_MS=%INTERVAL_MS%
echo   START_SOC=%START_SOC%
echo   LOAD_SCALE=%LOAD_SCALE%

node run_test.js > tageslauf.log 2>&1

echo Fertig - erste Log-Zeile zur Kontrolle:
findstr /N "^" tageslauf.log | findstr "^1:"
