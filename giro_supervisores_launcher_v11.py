# Giro de Supervisores - Nelson Casella
# v11: equilibrio fuerte de cantidad de giros por sector.
# Parte de v10 y NO modifica interfaz, calendario, historial, Excel ni reemplazos.
# Agrega una etapa final que intenta dejar, cuando las restricciones lo permiten,
# la cantidad de giros de AEROPUERTO y de ZONA SECUNDARIA con diferencia maxima 1
# entre agentes comparables, preservando las reglas duras y la equidad de turnos/zonas.

import tkinter as tk

from giro_supervisores_launcher_v10 import GiroApp
import giro_supervisores_launcher_v10 as v10
import giro_supervisores_launcher_v8 as v8


_original_generate = GiroApp.generate

AERO_KEYS = ('AERO_01_07', 'AERO_07_13', 'AERO_13_19', 'AERO_19_01')


def _eligible_for_slot(self, day, key, agent, today):
    """Valida restricciones basicas antes de probar una reasignacion."""
    if not agent or agent not in self.active_agents:
        return False
    if agent == self.admin:
        return False
    if agent in today.values():
        return False

    blocks = self.result.get('blocks', {}) if self.result else {}
    if day in blocks.get(agent, {}).get('all', set()):
        return False

    if key.startswith('AERO_'):
        if agent not in self.sup:
            return False
        if day in getattr(self, 'secondary_only', {}).get(agent, set()):
            return False
    else:
        if day in getattr(self, 'primary_only', {}).get(agent, set()):
            return False
    return True


def _count_map(self, sector):
    m = v10._metrics(self)
    return {a: m[a][sector] for a in m}


def _turn_count(self, agent, key):
    return v10._metrics(self).get(agent, {}).get(key, 0)


def _zone_count(self, agent, zone):
    return v10._metrics(self).get(agent, {}).get('Z', {}).get(zone, 0)


def _try_reassign(self, day, key, new_agent, baseline_hard, baseline_obj):
    cron = self.result['cron']
    today = cron[day]
    old_agent = today.get(key)
    if not old_agent or old_agent == self.admin or old_agent == new_agent:
        return None
    if not _eligible_for_slot(self, day, key, new_agent, today):
        return None

    today[key] = new_agent
    hard = v10._hard_violations(self)
    if hard > baseline_hard:
        today[key] = old_agent
        return None

    obj = v10._objective(self)
    return old_agent, hard, obj


def _rebalance_sector_counts(self, sector, max_passes=200):
    """Reduce diferencias de cantidad de giros de un sector mediante reemplazos seguros.

    Objetivo principal: max(count)-min(count) <= 1 cuando la disponibilidad y las
    restricciones duras lo permiten. Entre varias opciones, elige la que mejora tambien
    turno de aeropuerto / zona secundaria y el objetivo global de equidad.
    """
    if not self.result:
        return 0

    cron = self.result.get('cron', {})
    changes = 0

    for _ in range(max_passes):
        counts = _count_map(self, sector)
        if not counts:
            break

        min_count = min(counts.values())
        max_count = max(counts.values())
        if max_count - min_count <= 1:
            break

        under = sorted([a for a, c in counts.items() if c == min_count])
        over = sorted([a for a, c in counts.items() if c == max_count])

        baseline_hard = v10._hard_violations(self)
        baseline_obj = v10._objective(self)
        best = None

        for day in sorted(cron):
            today = cron[day]
            for key, old_agent in list(today.items()):
                is_aero = key.startswith('AERO_')
                if (sector == 'AERO') != is_aero:
                    continue
                if old_agent not in over or old_agent == self.admin:
                    continue

                for new_agent in under:
                    if not _eligible_for_slot(self, day, key, new_agent, today):
                        continue

                    # Preferencias secundarias sin perder el objetivo principal de conteo.
                    if sector == 'AERO':
                        slot_specific = _turn_count(self, new_agent, key)
                    else:
                        try:
                            zone = int(key.split('_')[1])
                            slot_specific = _zone_count(self, new_agent, zone)
                        except Exception:
                            slot_specific = 0

                    trial = _try_reassign(self, day, key, new_agent, baseline_hard, baseline_obj)
                    if trial is None:
                        continue
                    old, hard, obj = trial

                    # Guardamos candidato y deshacemos; se aplica solo el mejor.
                    today[key] = old
                    score = (
                        hard,
                        slot_specific,
                        obj,
                        day,
                        str(key),
                        str(new_agent),
                    )
                    if best is None or score < best[0]:
                        best = (score, day, key, old_agent, new_agent)

        if best is None:
            break

        _, day, key, old_agent, new_agent = best
        self.result['cron'][day][key] = new_agent
        changes += 1

    if changes:
        self.recalculate_counts()
        self.refresh_schedule()
    return changes


def _rebalance_airport_turns(self, max_passes=120):
    """Dentro del total AEROPUERTO ya equilibrado, mejora los cuatro horarios."""
    if not self.result:
        return 0
    cron = self.result.get('cron', {})
    changes = 0

    # Solo swaps entre dos puestos de aeropuerto del mismo dia: no altera AERO_TOTAL.
    for _ in range(max_passes):
        metrics = v10._metrics(self)
        before = sum(
            max(x[k] for x in metrics.values()) - min(x[k] for x in metrics.values())
            for k in AERO_KEYS
        ) if metrics else 0
        if before <= 4:  # ideal: diferencia <=1 en cada uno de los 4 turnos
            break

        hard0 = v10._hard_violations(self)
        obj0 = v10._objective(self)
        best = None

        for day in sorted(cron):
            keys = [k for k in AERO_KEYS if cron[day].get(k) and cron[day].get(k) != self.admin]
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    k1, k2 = keys[i], keys[j]
                    a, b = cron[day][k1], cron[day][k2]
                    if a == b:
                        continue
                    cron[day][k1], cron[day][k2] = b, a
                    hard = v10._hard_violations(self)
                    if hard <= hard0:
                        mm = v10._metrics(self)
                        spread = sum(
                            max(x[k] for x in mm.values()) - min(x[k] for x in mm.values())
                            for k in AERO_KEYS
                        ) if mm else 0
                        obj = v10._objective(self)
                        if spread < before or (spread == before and obj < obj0):
                            score = (hard, spread, obj, day, k1, k2)
                            if best is None or score < best[0]:
                                best = (score, day, k1, k2, a, b)
                    cron[day][k1], cron[day][k2] = a, b

        if best is None:
            break
        _, day, k1, k2, a, b = best
        cron[day][k1], cron[day][k2] = b, a
        changes += 1

    if changes:
        self.recalculate_counts()
        self.refresh_schedule()
    return changes


def _equity_summary(self):
    m = v10._metrics(self)
    if not m:
        return {}
    return {
        'aero_min': min(x['AERO'] for x in m.values()),
        'aero_max': max(x['AERO'] for x in m.values()),
        'sec_min': min(x['SEC'] for x in m.values()),
        'sec_max': max(x['SEC'] for x in m.values()),
        'aero_turnos_spread': {
            k.replace('AERO_', ''): max(x[k] for x in m.values()) - min(x[k] for x in m.values())
            for k in AERO_KEYS
        },
    }


def _generate_v11(self, *args, **kwargs):
    # Primero corre toda la v10, incluyendo restricciones de v9 y rotacion secundaria de v6.
    out = _original_generate(self, *args, **kwargs)
    if not self.result:
        return out

    # Prioridad solicitada: cantidad de giros pareja por sector.
    aero_changes = _rebalance_sector_counts(self, 'AERO')
    sec_changes = _rebalance_sector_counts(self, 'SEC')

    # Luego mejora reparto de horarios de aeropuerto sin tocar el total AERO de cada agente.
    turn_changes = _rebalance_airport_turns(self)

    # Una ultima optimizacion local de v10 para importe/zonas, sin aceptar infracciones.
    local_changes = v10._optimize_balanced_distribution(self)
    audit = v10._distribution_audit(self)
    summary = _equity_summary(self)
    self.result['equity_summary_v11'] = summary

    try:
        v8._save_month(self, silent=True)
    except Exception:
        pass

    hard = audit.get('hard_violations', 0)
    if summary:
        self.status.set(
            'Cronograma equilibrado: '
            f'Aeropuerto {summary["aero_min"]}-{summary["aero_max"]} giros por agente; '
            f'Zona Secundaria {summary["sec_min"]}-{summary["sec_max"]}; '
            f'ajustes AERO={aero_changes}, SEC={sec_changes}, turnos={turn_changes}, locales={local_changes}; '
            f'infracciones={hard}.'
        )
    return out


GiroApp.generate = _generate_v11


if __name__ == '__main__':
    root = tk.Tk()
    app = GiroApp(root)
    root.mainloop()
