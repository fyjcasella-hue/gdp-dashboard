# GIRO CUSTOMS — Aplicación para PC

Aplicación Windows con interfaz gráfica para generar el cronograma de asignaciones a partir de la lógica suministrada.

## Funciones
- Selección de año y mes.
- Feriados configurables.
- Valores de hora al 50% y 100% editables.
- Licencias y días no trabajables editables desde la interfaz.
- Generación automática del cronograma.
- Vista previa de cronograma, control de equidad y licencias.
- Exportación a Excel con cuatro hojas.
- Generación de ejecutable `.exe` mediante PyInstaller.

## Ejecutar desde Python
```bash
pip install -r requirements.txt
python giro_customs_pc.py
```

## Crear ejecutable para Windows
Ejecutar `build_pc.bat`. El archivo final aparecerá como:
`dist\GiroCustoms.exe`

## Nota
La interfaz conserva la lógica de asignación del código proporcionado, pero la separa de la configuración para que el usuario pueda cambiar el período, feriados, valores y restricciones sin editar el programa.
