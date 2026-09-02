# Giro de Supervisores - Nelson Casella
# v12: prioridad estricta AEROPUERTO.
# Mantiene todo lo anterior y corrige un problema de v11: la optimizacion local final
# de v10 podia volver a desarmar el equilibrio AEROPUERTO ya conseguido.
#
# Orden definitivo:
# 1) generar con todas las reglas existentes;
# 2) equilibrar CANTIDAD TOTAL de giros AEROPUERTO (objetivo diferencia <= 1);
# 3) equilibrar los cuatro TURNOS de AEROPUERTO sin cambiar el total AERO por agente;
# 4) compensar economicamente SOLO mediante movimientos dentro de ZONA SECUNDARIA;
# 5) auditar. Ninguna etapa posterior puede volver a cambiar el total AEROPUERTO.

import tkinter as tk
from statistics import mean

from giro_supervisores_launcher_v11 import GiroApp
import giro_supervisores_launcher_v11 as v11
import giro_supervisores_launcher_v10 as v10
import giro_supervisores_launcher_v8 as v8


_original_generate = GiroApp.generate


def _money_ratio(self, agent, metrics=None):
    if metrics is None:
        metrics = v10._metrics(self)
    if agent not in metrics:
        return 0.0
    avail = self.result.get('avail', {}).get(agent, 1) if self.result else 1
    return metrics[agent]['VALOR'] / max(1.0, float(avail))


def _money_variance(self):
    metrics = v10._metrics(self)
    agents = list(metrics)
    if len(agents) < 2:
        return 0.0
    vals = [_money_ratio(self, a, metrics) for a in agents]
    av = mean(vals)
    return sum((x - av) ** 2 for x in vals) / len(vals)


def _secondary_only_money_compensation(self, max_passes=250):
    """Mejora cobro final SIN tocar AEROPUERTO.

    Solo reasigna puestos ZONA_n entre supervisores. Cada prueba debe:
    - no aumentar infracciones duras;
    - respetar SOLO AEROPUERTO / SOLO ZONA SECUNDARIA;
    - no duplicar un agente el mismo dia;
    - no introducir repeticion de la misma zona en dias consecutivos;
    - reducir la varianza del valor cobrado por dia disponible.

    Como nunca toca una clave AERO_*, el total y los turnos de aeropuerto quedan congelados.
    """
    if not self.result:
        return 0

    cron = self.result.get('cron', {})
    changes = 0

    for _ in range(max_passes):
        metrics = v10._metrics(self)
        if not metrics:
            break
        ratios = {a: _money_ratio(self, a, metrics) for a in metrics}
        baseline_var = _money_variance(self)
        baseline_hard = v10._hard_violations(self)
        best = None

        # Priorizamos transferir un giro secundario desde quien esta mas alto
        # hacia quien esta mas bajo en valor/dia disponible.
        high_agents = sorted(ratios, key=lambda a: ratios[a], reverse=True)
        low_agents = sorted(ratios, key=lambda a: ratios[a])

        for day in sorted(cron):
            today = cron[day]
            for key, old_agent in list(today.items()):
                if not key.startswith('ZONA_'):
                    continue
                if not old_agent or old_agent == self.admin or old_agent not in high_agents:
                    continue

                for new_agent in low_agents:
                    if new_agent == old_agent:
                        continue
                    if ratios[new_agent] >= ratios[old_agent]:
                        continue
                    if not v11._eligible_for_slot(self, day, key, new_agent, today):
                        continue

                    today[key] = new_agent
                    hard = v10._hard_violations(self)
                    if hard <= baseline_hard:
                        new_var = _money_variance(self)
                        if new_var + 1e-9 < baseline_var:
                            # Favorece mayor mejora economica y menor uso historico de esa zona.
                            try:
                                zone = int(key.split('_')[1])
                                zcount = v11._zone_count(self, new_agent, zone)
                            except Exception:
                                zcount = 0
                            score = (hard, new_var, zcount, day, key, new_agent)
                            if best is None or score < best[0]:
                                best = (score, day, key, old_agent, new_agent)
                    today[key] = old_agent

        if best is None:
            break

        _, day, key, old_agent, new_agent = best
        cron[day][key] = new_agent
        changes += 1

    if changes:
        self.recalculate_counts()
        self.refresh_schedule()
    return changes


def _airport_summary(self):
    m = v10._metrics(self)
    if not m:
        return {}
    return {
        'aero_min': min(x['AERO'] for x in m.values()),
        'aero_max': max(x['AERO'] for x in m.values()),
        'sec_min': min(x['SEC'] for x in m.values()),
        'sec_max': max(x['SEC'] for x in m.values()),
        'turn_spread': {
            k.replace('AERO_', ''): max(x[k] for x in m.values()) - min(x[k] for x in m.values())
            for k in v11.AERO_KEYS
        },
        'money_min': round(min(_money_ratio(self, a, m) for a in m), 2),
        'money_max': round(max(_money_ratio(self, a, m) for a in m), 2),
    }


def _generate_v12(self, *args, **kwargs):
    # Ejecuta toda la cadena existente hasta v11.
    out = _original_generate(self, *args, **kwargs)
    if not self.result:
        return out

    # IMPORTANTE: v11 terminaba llamando una optimizacion generica de v10 que podia
    # volver a intercambiar AEROPUERTO <-> SECUNDARIA. Por eso aqui el ultimo bloque
    # vuelve a fijar AEROPUERTO y desde este punto ya no se permite tocarlo.
    aero_changes = v11._rebalance_sector_counts(self, 'AERO', max_passes=500)
    turn_changes = v11._rebalance_airport_turns(self, max_passes=300)

    # Desde aqui SOLO se toca Zona Secundaria para compensar el cobro final.
    money_changes = _secondary_only_money_compensation(self, max_passes=300)

    # Una segunda pasada de turnos AERO es inocua respecto del total y asegura que
    # ninguna condicion previa haya dejado margen de mejora entre horarios.
    turn_changes_2 = v11._rebalance_airport_turns(self, max_passes=200)

    audit = v10._distribution_audit(self)
    summary = _airport_summary(self)
    self.result['equity_summary_v12'] = summary

    try:
        v8._save_month(self, silent=True)
    except Exception:
        pass

    hard = audit.get('hard_violations', 0)
    if summary:
        self.status.set(
            'Cronograma final v12: '
            f'AEROPUERTO {summary["aero_min"]}-{summary["aero_max"]} giros/agente; '
            f'ZS {summary["sec_min"]}-{summary["sec_max"]}; '
            f'ajustes AERO={aero_changes}, turnos={turn_changes + turn_changes_2}, '
            f'compensacion ZS={money_changes}; infracciones={hard}.'
        )
    return out


GiroApp.generate = _generate_v12


if __name__ == '__main__':
    root = tk.Tk()
    app = GiroApp(root)
    root.mainloop()
