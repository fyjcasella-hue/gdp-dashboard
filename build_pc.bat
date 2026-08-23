@echo off
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name GiroCustoms giro_customs_pc_v2.py
echo.
echo Ejecutable creado en dist\GiroCustoms.exe
pause
