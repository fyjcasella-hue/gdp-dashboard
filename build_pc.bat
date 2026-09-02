@echo off
setlocal
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m py_compile giro_supervisores_final.py
if errorlevel 1 (
  echo.
  echo ERROR: La aplicacion tiene errores de sintaxis.
  pause
  exit /b 1
)
pyinstaller --noconfirm --clean --onefile --windowed --name GiroDeSupervisores_NelsonCasella giro_supervisores_final.py
if errorlevel 1 (
  echo.
  echo ERROR: No se pudo compilar el ejecutable.
  pause
  exit /b 1
)
echo.
echo EJECUTABLE CREADO: dist\GiroDeSupervisores_NelsonCasella.exe
pause
