@echo off
setlocal
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name GiroCustoms giro_customs_final.py
if errorlevel 1 (
  echo.
  echo ERROR: No se pudo compilar GiroCustoms.exe
  pause
  exit /b 1
)
echo.
echo Ejecutable creado en dist\GiroCustoms.exe
pause
