@echo off
rem pushd statt cd: funktioniert auch auf Netzlaufwerken (\\Server\Freigabe\...),
rem dafuer wird voruebergehend ein freier Laufwerksbuchstabe verbunden
pushd "%~dp0"
python3 analyse.py %*
popd
