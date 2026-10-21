"""Motor de reemplazos locales para GIRO CUSTOMS.

No regenera el mes: reemplaza únicamente el puesto afectado y conserva el resto
 del cronograma. La función replace_absence recibe el cronograma ya generado,
las restricciones y contadores actuales, y devuelve el cambio y sus candidatos.
"""
from copy import deepcopy
from datetime import date

AERO_KEYS = ['AERO_01_07','AERO_07_13','AERO_13_19','AERO_19_01']


def payment_type(year, month, holidays, day, shift, airport=True):
    wd = date(year, month, day).weekday()
    if day in holidays or wd == 6:
        return '100%'
    if wd == 5:
        if airport and shift in ('13 A 19', '19 A 01'):
            return '100%'
        if not airport and shift == '15 A 22':
            return '100%'
        if airport and shift in ('01 A 07', '07 A 13'):
            return '50%'
    return '50%'


def _shift_info(day, key, weekend_or_holiday):
    if key.startswith('AERO_'):
        shift = key.replace('AERO_', '').replace('_', ' A ')
        return 'AEROPUERTO', shift, 'AEROPUERTO', True
    shift = '15 A 22' if weekend_or_holiday else '19 A 02'
    return 'ZONA SECUNDARIA', shift, key.replace('ZONA_', 'ZONA '), False


def replace_absence(*, cronograma, year, month, holidays, absences, blocked, counters,
                    available_days, zone_history, agents, supervisors, admin_name):
    """Repara ausencias de forma local.

    absences: lista de dicts {'day': int, 'agent': str, 'key': opcional str}.
    Si key no se informa, se reemplazan todos los puestos del agente ese día.

    Devuelve un NUEVO cronograma, lista de cambios y candidatos evaluados.
    El cronograma original nunca se modifica in-place.
    """
    new_cron = deepcopy(cronograma)
    changes, audits = [], []

    def blocked(agent, day):
        return day in blocked.get(agent, {}).get('todos', set())

    def previous_day_conflict(agent, day, key):
        if day <= 1:
            return False
        previous = new_cron.get(day - 1, {})
        if key == 'AERO_01_07':
            # No madrugada después de noche/zona del día anterior.
            if previous.get('AERO_19_01') == agent:
                return True
            if any(a == agent for k, a in previous.items() if k.startswith('ZONA_')):
                return True
        if key.startswith('AERO_') and any(previous.get(k) == agent for k in AERO_KEYS):
            return True
        if key.startswith('ZONA_') and any(previous.get(k) == agent for k in previous if k.startswith('ZONA_')):
            return True
        return False

    def day_conflict(agent, day, key):
        return any(a == agent and k != key for k, a in new_cron.get(day, {}).items())

    def score(agent, day, key, payment):
        c = counters[agent]
        total = max(1, available_days.get(agent, 1))
        specific = c.get(key, 0) if key.startswith('AERO_') else c.get(payment == '100%' and 'SEC_100' or 'SEC_50', 0)
        hours = c.get('HORAS_50', 0) + c.get('HORAS_100', 0)
        income = c.get('INGRESOS_ESTIMADOS', 0)
        zone = 0
        if key.startswith('ZONA_'):
            try: zone = zone_history.get(agent, {}).get(int(key.split('_')[1]), 0)
            except (ValueError, IndexError): pass
        # Menor score = menor distorsión. Pesos deliberadamente lexicográficos.
        return (specific, round(c.get('TOTAL_TURNOS', 0) / total, 4),
                round(hours / total, 4), round(income / total, 2), zone)

    for absence in absences:
        day = int(absence['day']); absent = absence['agent']; requested_key = absence.get('key')
        if day not in new_cron:
            audits.append({'day': day, 'agent': absent, 'status': 'ERROR', 'reason': 'Día inexistente'})
            continue
        targets = [requested_key] if requested_key else [k for k, a in new_cron[day].items() if a == absent]
        for key in targets:
            if not key or new_cron[day].get(key) != absent:
                audits.append({'day': day, 'agent': absent, 'key': key, 'status': 'ERROR', 'reason': 'El agente no ocupa ese puesto'})
                continue
            weekend_or_holiday = date(year, month, day).weekday() >= 5 or day in holidays
            section, shift, zone, airport = _shift_info(day, key, weekend_or_holiday)
            pay = payment_type(year, month, holidays, day, shift, airport)
            pool = supervisors if airport else agents
            candidates = []
            for candidate in pool:
                if candidate == absent or blocked(candidate, day):
                    continue
                if day_conflict(candidate, day, key):
                    continue
                if previous_day_conflict(candidate, day, key):
                    continue
                candidates.append(candidate)
            if not candidates:
                audits.append({'day': day, 'agent': absent, 'key': key, 'status': 'SIN REEMPLAZO', 'reason': 'No existe candidato compatible'})
                continue
            ranked = sorted(candidates, key=lambda a: score(a, day, key, pay))
            chosen = ranked[0]
            old = new_cron[day][key]
            new_cron[day][key] = chosen
            changes.append({'day': day, 'key': key, 'section': section, 'zone': zone,
                            'shift': shift, 'payment': pay, 'original': old,
                            'replacement': chosen, 'reason': 'Ausencia'})
            audits.append({'day': day, 'agent': absent, 'key': key, 'status': 'REEMPLAZADO',
                           'replacement': chosen, 'candidates': ranked[:5]})

    return new_cron, changes, audits
