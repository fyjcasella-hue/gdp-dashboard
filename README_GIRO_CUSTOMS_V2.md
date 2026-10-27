# GIRO CUSTOMS v2 — Reemplazos automáticos

La versión 2 agrega un tercer panel de **AUSENCIAS EXTRAORDINARIAS**. Se cargan como:

`AGENTE: 3,10,18`

Al generar el cronograma, esos días se consideran indisponibles para ese agente y el motor asigna automáticamente otro agente elegible.

## Parámetros respetados durante el reemplazo
- Licencias oficiales.
- Extensiones de licencia por fin de semana/feriado.
- Días no trabajables.
- Ausencias extraordinarias.
- No duplicar un agente en dos puestos del mismo día.
- Restricción de descanso respecto del día anterior.
- Restricción especial del turno 01 A 07 cuando el agente salió tarde.
- Equilibrio de turnos específicos de aeropuerto.
- Equilibrio de horas, turnos e ingresos proporcionales a la disponibilidad.
- Distribución de zonas secundarias.

El sistema además ejecuta una auditoría: si una ausencia continúa asignada al agente ausente, detiene la generación y avisa al usuario en lugar de producir un cronograma incorrecto.

## Uso
1. Cargar el mes y los valores.
2. Cargar licencias y días no trabajables.
3. Si aparece una ausencia, agregarla en **AUSENCIAS EXTRAORDINARIAS**.
4. Pulsar **GENERAR / REEMPLAZAR AUSENCIAS**.
5. Revisar la vista previa y exportar Excel.

La ausencia no se resuelve manualmente: el algoritmo selecciona el reemplazo automáticamente entre los agentes elegibles.
