# Giro de Supervisores - Nelson Casella
# v17: prioridad estricta de equidad proporcional en AEROPUERTO.
# Se apoya en v16 y NO modifica alta/baja, historial, calendario, Excel ni reglas duras.

import tkinter as tk
from statistics import mean

from giro_supervisores_launcher_v16 import GiroApp, BG
import giro_supervisores_launcher_v16 as v16
import giro_supervisores_launcher_v15 as v15
import giro_supervisores_launcher_v14 as v14
import giro_supervisores_launcher_v12 as v12
import giro_supervisores_launcher_v11 as v11
import giro_supervisores_launcher_v10 as v10
import giro_supervisores_launcher_v8 as v8

AERO_KEYS = ('AERO_01_07', 'AERO_07_13', 'AERO_13_19', 'AERO_19_01')
_original_generate = GiroApp.generate


def _active_supervisors(self):
    return [a for a in self.sup if a in self.active_agents and a != self.admin]


def _airport_available_days(self, agent):
    if not self.result:
        return 0
    days = int(self.result.get('days', 0))
    blocks = self.result.get('blocks', {}).get(agent, {}).get('all', set())
    secondary_only = getattr(self, 'secondary_only', {}).get(agent, set())
    return sum(1 for d in range(1, days + 1) if d not in blocks and d not in secondary_only)


def _proportional_targets(weights, total):
    names = list(weights)
    targets = {a: 0 for a in names}
    capacities = {a: max(0, int(weights.get(a, 0))) for a in names}
    total = max(0, int(total))
    capacity_total = sum(capacities.values())
    if total <= 0 or capacity_total <= 0:
        return targets
    total = min(total, capacity_total)
    raw = {a: total * capacities[a] / capacity_total for a in names}
    for a in names:
        targets[a] = min(capacities[a], int(raw[a]))
    remaining = total - sum(targets.values())
    order = sorted(names, key=lambda a: (raw[a] - int(raw[a]), capacities[a], str(a)), reverse=True)
    while remaining > 0:
        progressed = False
        for a in order:
            if targets[a] < capacities[a]:
                targets[a] += 1
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break
        if not progressed:
            break
    return targets


def _airport_metrics(self):
    agents = _active_supervisors(self)
    m = {a: {'AERO': 0, 'P50': 0, 'P100': 0, 'H50': 0, 'H100': 0, 'VALOR': 0.0,
             **{k: 0 for k in AERO_KEYS}} for a in agents}
    cron = self.result.get('cron', {}) if self.result else {}
    for day, ass in cron.items():
        for key, agent in ass.items():
            if key not in AERO_KEYS or agent not in m:
                continue
            shift = self.turn_from_key(day, key)
            pay = self.pay_type(day, shift, True)
            m[agent]['AERO'] += 1
            m[agent][key] += 1
            if pay == '100%':
                m[agent]['P100'] += 1
                m[agent]['H100'] += 6
                m[agent]['VALOR'] += 6 * self.v100
            else:
                m[agent]['P50'] += 1
                m[agent]['H50'] += 6
                m[agent]['VALOR'] += 6 * self.v50
    return m


def _airport_total_slots(self):
    if not self.result:
        return 0
    return sum(1 for ass in self.result.get('cron', {}).values() for key, agent in ass.items()
               if key in AERO_KEYS and agent and agent != self.admin)


def _airport_targets(self):
    agents = _active_supervisors(self)
    weights = {a: _airport_available_days(self, a) for a in agents}
    return weights, _proportional_targets(weights, _airport_total_slots(self))


def _count_error(metrics, targets):
    return sum(abs(metrics[a]['AERO'] - targets.get(a, 0)) for a in metrics)


def _pay_error(metrics, pay100_targets):
    return sum(abs(metrics[a]['P100'] - pay100_targets.get(a, 0)) for a in metrics)


def _shift_error(metrics, targets):
    total = sum(targets.values())
    if total <= 0:
        return 0.0
    global_counts = {key: sum(metrics[a][key] for a in metrics) for key in AERO_KEYS}
    err = 0.0
    for a in metrics:
        target_total = targets.get(a, 0)
        if target_total <= 0:
            continue
        for key in AERO_KEYS:
            expected = target_total * global_counts[key] / total
            diff = metrics[a][key] - expected
            err += (diff * diff) / max(1.0, float(target_total))
    return err


def _airport_money_variance(self, metrics, airport_days):
    vals = []
    for a in metrics:
        d = max(1.0, float(airport_days.get(a, 0)))
        vals.append(metrics[a]['VALOR'] / d)
    if len(vals) < 2:
        return 0.0
    av = mean(vals)
    scale = max(1.0, 6.0 * float(self.v50))
    return sum(((x - av) / scale) ** 2 for x in vals) / len(vals)


def _profile_score(self, metrics, targets, airport_days, pay100_targets=None):
    if not metrics:
        return 0.0
    if pay100_targets is None:
        total100 = sum(x['P100'] for x in metrics.values())
        pay100_targets = _proportional_targets(targets, total100)
    pay_err = _pay_error(metrics, pay100_targets)
    shift_err = _shift_error(metrics, targets)
    money_var = _airport_money_variance(self, metrics, airport_days)
    return 12.0 * pay_err + 8.0 * money_var + 5.0 * shift_err


def _rebalance_airport_counts(self, targets, airport_days, max_passes=300):
    if not self.result:
        return 0
    cron = self.result.get('cron', {})
    changes = 0
    for _ in range(max_passes):
        metrics = _airport_metrics(self)
        over = [a for a in metrics if metrics[a]['AERO'] > targets.get(a, 0)]
        under = [a for a in metrics if metrics[a]['AERO'] < targets.get(a, 0)]
        if not over or not under:
            break
        hard0 = v10._hard_violations(self)
        best = None
        deficits = {a: targets[a] - metrics[a]['AERO'] for a in under}
        excess = {a: metrics[a]['AERO'] - targets[a] for a in over}

        for day in sorted(cron):
            today = cron[day]
            for key in AERO_KEYS:
                old = today.get(key)
                if old not in excess:
                    continue
                for new in sorted(under, key=lambda a: (-deficits[a], metrics[a][key], str(a))):
                    if not v11._eligible_for_slot(self, day, key, new, today):
                        continue
                    today[key] = new
                    hard = v10._hard_violations(self)
                    today[key] = old
                    if hard > hard0:
                        continue
                    score = (hard, -deficits[new], metrics[new][key] / max(1.0, float(targets.get(new, 1))),
                             -excess[old], day, key, str(new))
                    if best is None or score < best[0]:
                        best = (score, 'direct', day, key, old, new, None)

        if best is None:
            for day in sorted(cron):
                today = cron[day]
                zone_keys = [k for k in today if k.startswith('ZONA_')]
                for akey in AERO_KEYS:
                    old = today.get(akey)
                    if old not in excess or old == self.admin:
                        continue
                    for zkey in zone_keys:
                        new = today.get(zkey)
                        if new not in deficits or new == self.admin or new == old:
                            continue
                        today[akey], today[zkey] = new, old
                        hard = v10._hard_violations(self)
                        today[akey], today[zkey] = old, new
                        if hard > hard0:
                            continue
                        score = (hard, -deficits[new], metrics[new][akey] / max(1.0, float(targets.get(new, 1))),
                                 -excess[old], day, akey, zkey, str(new))
                        if best is None or score < best[0]:
                            best = (score, 'swap_sector', day, akey, old, new, zkey)

        if best is None:
            break
        _, mode, day, akey, old, new, zkey = best
        if mode == 'direct':
            cron[day][akey] = new
        else:
            cron[day][akey], cron[day][zkey] = new, old
        changes += 1

    if changes:
        self.recalculate_counts()
        self.refresh_schedule()
    return changes


def _airport_slots(self):
    slots = []
    if not self.result:
        return slots
    for day in sorted(self.result.get('cron', {})):
        ass = self.result['cron'][day]
        for key in AERO_KEYS:
            agent = ass.get(key)
            if not agent or agent == self.admin:
                continue
            pay = self.pay_type(day, self.turn_from_key(day, key), True)
            slots.append((day, key, agent, pay))
    return slots


def _can_cross_day_swap(self, day1, agent1, day2, agent2):
    if day1 == day2:
        return True
    cron = self.result['cron']
    if agent2 in cron[day1].values():
        return False
    if agent1 in cron[day2].values():
        return False
    return True


def _rebalance_airport_pay(self, targets, airport_days, max_passes=180):
    if not self.result:
        return 0
    changes = 0
    for _ in range(max_passes):
        metrics = _airport_metrics(self)
        total100 = sum(x['P100'] for x in metrics.values())
        pay100_targets = _proportional_targets(targets, total100)
        over = [a for a in metrics if metrics[a]['P100'] > pay100_targets.get(a, 0)]
        under = [a for a in metrics if metrics[a]['P100'] < pay100_targets.get(a, 0)]
        if not over or not under:
            break
        hard0 = v10._hard_violations(self)
        slots = _airport_slots(self)
        best = None
        for d1, k1, a, p1 in slots:
            if p1 != '100%' or a not in over:
                continue
            for d2, k2, b, p2 in slots:
                if p2 != '50%' or b not in under or a == b:
                    continue
                if not _can_cross_day_swap(self, d1, a, d2, b):
                    continue
                cron = self.result['cron']
                cron[d1][k1], cron[d2][k2] = b, a
                hard = v10._hard_violations(self)
                if hard <= hard0:
                    mm = _airport_metrics(self)
                    payerr = _pay_error(mm, pay100_targets)
                    score_profile = _profile_score(self, mm, targets, airport_days, pay100_targets)
                    score = (hard, payerr, score_profile, d1, k1, d2, k2, str(a), str(b))
                    if best is None or score < best[0]:
                        best = (score, d1, k1, a, d2, k2, b)
                cron[d1][k1], cron[d2][k2] = a, b
        if best is None:
            break
        _, d1, k1, a, d2, k2, b = best
        self.result['cron'][d1][k1], self.result['cron'][d2][k2] = b, a
        changes += 1
    if changes:
        self.recalculate_counts()
        self.refresh_schedule()
    return changes


def _rebalance_airport_shifts(self, targets, airport_days, max_passes=220):
    if not self.result:
        return 0
    changes = 0
    for _ in range(max_passes):
        metrics = _airport_metrics(self)
        before = _shift_error(metrics, targets)
        if before <= 0.05:
            break
        hard0 = v10._hard_violations(self)
        slots = _airport_slots(self)
        candidates = []
        total = max(1, sum(targets.values()))
        global_counts = {k: sum(metrics[a][k] for a in metrics) for k in AERO_KEYS}

        def local_err(agent, key, value):
            expected = targets.get(agent, 0) * global_counts[key] / total
            return ((value - expected) ** 2) / max(1.0, float(targets.get(agent, 0)))

        for i in range(len(slots)):
            d1, k1, a, p1 = slots[i]
            for j in range(i + 1, len(slots)):
                d2, k2, b, p2 = slots[j]
                if a == b or k1 == k2 or p1 != p2:
                    continue
                if not _can_cross_day_swap(self, d1, a, d2, b):
                    continue
                before_local = (local_err(a, k1, metrics[a][k1]) + local_err(a, k2, metrics[a][k2]) +
                                local_err(b, k1, metrics[b][k1]) + local_err(b, k2, metrics[b][k2]))
                after_local = (local_err(a, k1, metrics[a][k1] - 1) + local_err(a, k2, metrics[a][k2] + 1) +
                               local_err(b, k1, metrics[b][k1] + 1) + local_err(b, k2, metrics[b][k2] - 1))
                delta = after_local - before_local
                if delta < -1e-9:
                    candidates.append((delta, d1, k1, a, d2, k2, b))

        candidates.sort(key=lambda x: (x[0], x[1], x[2], x[4], x[5]))
        applied = False
        for _, d1, k1, a, d2, k2, b in candidates[:120]:
            cron = self.result['cron']
            cron[d1][k1], cron[d2][k2] = b, a
            hard = v10._hard_violations(self)
            if hard <= hard0:
                mm = _airport_metrics(self)
                after = _shift_error(mm, targets)
                if after + 1e-9 < before:
                    changes += 1
                    applied = True
                    break
            cron[d1][k1], cron[d2][k2] = a, b
        if not applied:
            break
    if changes:
        self.recalculate_counts()
        self.refresh_schedule()
    return changes


def _v17_audit(self, airport_days, targets):
    metrics = _airport_metrics(self)
    total100 = sum(x['P100'] for x in metrics.values())
    p100_targets = _proportional_targets(targets, total100)
    audit = {
        'airport_available_days': dict(airport_days),
        'airport_targets': dict(targets),
        'count_error': _count_error(metrics, targets),
        'shift_error': round(_shift_error(metrics, targets), 6),
        'p100_targets': dict(p100_targets),
        'p100_error': _pay_error(metrics, p100_targets),
        'hard_violations': v10._hard_violations(self),
        'agents': {},
    }
    for a, x in metrics.items():
        audit['agents'][a] = {
            'dias_aeropuerto_disponibles': airport_days.get(a, 0),
            'aeropuerto_objetivo': targets.get(a, 0),
            'aeropuerto_real': x['AERO'],
            '01_07': x['AERO_01_07'],
            '07_13': x['AERO_07_13'],
            '13_19': x['AERO_13_19'],
            '19_01': x['AERO_19_01'],
            'horas_50_aeropuerto': x['H50'],
            'horas_100_aeropuerto': x['H100'],
            'valor_aeropuerto': round(x['VALOR'], 2),
        }
    self.result['equity_summary_v17'] = audit
    return audit


def _generate_v17(self, *args, **kwargs):
    out = _original_generate(self, *args, **kwargs)
    if not self.result:
        return out
    airport_days, targets = _airport_targets(self)
    count_changes = _rebalance_airport_counts(self, targets, airport_days, max_passes=350)
    pay_changes = _rebalance_airport_pay(self, targets, airport_days, max_passes=220)
    shift_changes = _rebalance_airport_shifts(self, targets, airport_days, max_passes=260)
    secondary_changes = v12._secondary_only_money_compensation(self, max_passes=350)
    audit = _v17_audit(self, airport_days, targets)
    try:
        v8._save_month(self, silent=True)
    except Exception:
        pass
    self.status.set(
        'Cronograma v17: AEROPUERTO proporcional por días disponibles; '
        f'desvío cantidad={audit["count_error"]}, desvío 100%={audit["p100_error"]}, '
        f'ajustes cantidad={count_changes}, 50/100={pay_changes}, horarios={shift_changes}, '
        f'compensación ZS={secondary_changes}, infracciones={audit["hard_violations"]}.'
    )
    return out


GiroApp.generate = _generate_v17


if __name__ == '__main__':
    v14._migrate_previous_history()
    root = tk.Tk()
    root.configure(bg=BG)
    root.option_add('*tearOff', False)
    v14._apply_window_icon(root)
    app = GiroApp(root)
    current = v8._month_path(app.year, app.month)
    if current.exists():
        try:
            v15._original_v14_load_history(app, current)
        except Exception:
            pass
    if not v16._load_global_roster_v16(app, create_if_missing=False):
        v16._save_global_roster_v16(app)
    v16._refresh_agents_v16(app)
    app.show_calendar()
    app.refresh_schedule()
    root.mainloop()
