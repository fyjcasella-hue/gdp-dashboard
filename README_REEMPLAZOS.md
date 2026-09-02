# Reemplazos automáticos de ausencias

GIRO CUSTOMS incorpora un motor de reparación local. El cronograma mensual ya generado se conserva y solo se cambia el puesto afectado por la ausencia.

## Comportamiento
- Ausencia por día completo o por puesto/turno.
- Busca candidatos compatibles sin regenerar el mes.
- Respeta licencias, días no trabajables, asignaciones del mismo día y descansos del día anterior.
- Para aeropuerto limita el reemplazo a supervisores de aeropuerto.
- Clasifica candidatos por carga del turno, turnos por día disponible, horas, ingresos y zona.
- Registra agente original, reemplazante, puesto, turno, pago y motivo.
- Si no hay candidato compatible, informa la incidencia en vez de forzar una asignación incorrecta.

## Principio
Una ausencia no altera otros turnos ya generados. La reparación es local.
