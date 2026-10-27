# Giro de Supervisores - Nelson Casella
# v10: optimización final de equidad sobre la v9.
# Conserva toda la interfaz y reglas existentes. Después de generar, realiza
# únicamente intercambios locales seguros entre agentes del mismo día para mejorar:
# - distribución Aeropuerto / Zona Secundaria,
# - distribución de los cuatro turnos de Aeropuerto,
# - rotación por zonas secundarias sin repetir zona en días consecutivos,
# - equidad aproximada del importe final según días disponibles.
# CASTRO D. no se mueve.

import tkinter as tk
from statistics import mean

from giro_supervisores_launcher_v9 import GiroApp
import giro_supervisores_launcher_v8 as v8


_original_generate = GiroApp.generate


def _active_supervisors(self):
    return [a for a in self.sup if a in self.active_agents]


def _metrics(self):
    """Métricas finales por agente calculadas desde el cronograma real."""
    cron = self.result.get('cron', {}) if self.result else {}
    agents = _active_supervisors(self)
    m = {}
    for a in agents:
        m[a] = {
            'AERO': 0, 'SEC': 0,
            'AERO_01_07': 0, 'AERO_07_13': 0, 'AERO_13_19': 0, 'AERO_19_01': 0,
            'Z': {z: 0 for z in range(1, 7)},
            'H50': 0, 'H100': 0, 'VALOR': 0.0,
        }
    for d, ass in cron.items():
        for key, a in ass.items():
            if a not in m:
                continue
            aero = key.startswith('AERO_')
            sh = self.turn_from_key(d, key)
            p = self.pay_type(d, sh, aero)
            h = 6 if aero else 7
            if aero:
                m[a]['AERO'] += 1
                if key in m[a]:
                    m[a][key] += 1
            else:
                m[a]['SEC'] += 1
                try:
                    m[a]['Z'][int(key.split('_')[1])] += 1
                except Exception:
                    pass
            if p == '100%':
                m[a]['H100'] += h
            else:
                m[a]['H50'] += h
            m[a]['VALOR'] += h * (self.v100 if p == '100%' else self.v50)
    return m


def _variance(values):
    if len(values) < 2:
        return 0.0
    av = mean(values)
    return sum((x - av) ** 2 for x in values) / len(values)


def _objective(self):
    """Menor valor = mejor distribución. Normaliza por días disponibles."""
    if not self.result:
        return 0.0
    metrics = _metrics(self)
    agents = list(metrics)
    if not agents:
        return 0.0
    avail = self.result.get('avail', {})

    def ratio(a, value):
        return value / max(1, float(avail.get(a, 1)))

    # 1) Distribución de sector Aeropuerto / Secundaria.
    p_sector = 14.0 * (
        _variance([ratio(a, metrics[a]['AERO']) for a in agents]) +
        _variance([ratio(a, metrics[a]['SEC']) for a in agents])
    )

    # 2) Equidad de los cuatro turnos de aeropuerto.
    p_aero = 12.0 * sum(
        _variance([ratio(a, metrics[a][key]) for a in agents])
        for key in ('AERO_01_07', 'AERO_07_13', 'AERO_13_19', 'AERO_19_01')
    )

    # 3) Dispersión de zonas dentro de cada agente.
    p_zones = 0.0
    for a in agents:
        zvals = [metrics[a]['Z'][z] for z in range(1, 7)]
        p_zones += 6.0 * _variance(zvals)

    # 4) Equidad económica proporcional a la disponibilidad del mes.
    p_money = 10.0 * _variance([
        metrics[a]['VALOR'] / max(1.0, float(avail.get(a, 1))) for a in agents
    ]) / max(1.0, (self.v50 * 6.0) ** 2)

    return p_sector + p_aero + p_zones + p_money


def _hard_violations(self):
    """Cuenta infracciones que nunca deben introducirse por la optimización."""
    if not self.result:
        return 0
    cron = self.result.get('cron', {})
    blocks = self.result.get('blocks', {})
    violations = 0
    for d in sorted(cron):
        ass = cron[d]
        seen = set()
        for key, a in ass.items():
            if a in seen:
                violations += 1
            seen.add(a)
            if d in blocks.get(a, {}).get('all', set()):
                violations += 1
            if key.startswith('AERO_'):
                if a not in self.sup or a not in self.active_agents:
                    violations += 1
                if d in getattr(self, 'secondary_only', {}).get(a, set()):
                    violations += 1
            elif key.startswith('ZONA_'):
                if a != self.admin and d in getattr(self, 'primary_only', {}).get(a, set()):
                    violations += 1

        if d > 1:
            prev = cron.get(d - 1, {})
            prev_aero = {prev.get(k) for k in ('AERO_01_07','AERO_07_13','AERO_13_19','AERO_19_01')}
            for key, a in ass.items():
                if key.startswith('AERO_') and a in prev_aero:
                    violations += 1
                if key == 'AERO_01_07':
                    if prev.get('AERO_19_01') == a or any(v == a for k, v in prev.items() if k.startswith('ZONA_')):
                        violations += 1

        # Repetición de la MISMA zona secundaria en días consecutivos.
        if d > 1:
            prev = cron.get(d - 1, {})
            for z in range(1, 7):
                key = f'ZONA_{z}'
                a = ass.get(key)
                if a and a != self.admin and prev.get(key) == a:
                    violations += 1
    return violations


def _try_swap(self, day, key1, key2, baseline_hard, baseline_obj):
    cron = self.result['cron']
    today = cron[day]
    a = today.get(key1)
    b = today.get(key2)
    if not a or not b or a == b:
        return None
    if a == self.admin or b == self.admin:
        return None

    today[key1], today[key2] = b, a
    hard = _hard_violations(self)
    if hard > baseline_hard:
        today[key1], today[key2] = a, b
        return None

    obj = _objective(self)
    if hard < baseline_hard or obj + 1e-9 < baseline_obj:
        return hard, obj

    today[key1], today[key2] = a, b
    return None


def _optimize_balanced_distribution(self):
    """Hill-climbing mediante swaps del mismo día: no crea ni elimina puestos."""
    if not self.result:
        return 0
    cron = self.result.get('cron', {})
    swaps = 0
    hard = _hard_violations(self)
    obj = _objective(self)

    # Varias pasadas, siempre aceptando únicamente mejoras y sin empeorar reglas duras.
    for _ in range(8):
        improved = False
        for day in sorted(cron):
            keys = [k for k, a in cron[day].items() if a and a != self.admin]
            # Considera intercambios entre turnos de aeropuerto, entre zonas y entre sectores.
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    result = _try_swap(self, day, keys[i], keys[j], hard, obj)
                    if result is not None:
                        hard, obj = result
                        swaps += 1
                        improved = True
        if not improved:
            break

    if swaps:
        self.recalculate_counts()
        self.refresh_schedule()
    return swaps


def _distribution_audit(self):
    """Resumen de control guardado dentro de self.result para diagnóstico."""
    if not self.result:
        return {}
    m = _metrics(self)
    audit = {
        'hard_violations': _hard_violations(self),
        'objective': round(_objective(self), 6),
        'agents': {},
    }
    for a, x in m.items():
        audit['agents'][a] = {
            'aeropuerto': x['AERO'],
            'secundaria': x['SEC'],
            'aero_turnos': {k.replace('AERO_', ''): x[k] for k in ('AERO_01_07','AERO_07_13','AERO_13_19','AERO_19_01')},
            'zonas': dict(x['Z']),
            'horas_50': x['H50'],
            'horas_100': x['H100'],
            'valor_total': round(x['VALOR'], 2),
            'dias_disponibles': self.result.get('avail', {}).get(a, 0),
        }
    self.result['distribution_audit'] = audit
    return audit


def _generate_v10(self, *args, **kwargs):
    out = _original_generate(self, *args, **kwargs)
    if not self.result:
        return out

    swaps = _optimize_balanced_distribution(self)
    audit = _distribution_audit(self)

    # Guardado mensual con toda la información final.
    try:
        v8._save_month(self, silent=True)
    except Exception:
        pass

    hard = audit.get('hard_violations', 0)
    if hard == 0:
        self.status.set(
            f'Cronograma generado y auditado: distribución equilibrada optimizada ({swaps} ajuste(s) local(es)); sin infracciones detectadas.'
        )
    else:
        self.status.set(
            f'Cronograma generado y auditado: {swaps} ajuste(s) local(es). Quedaron {hard} condición(es) no resolubles automáticamente.'
        )
    return out


GiroApp.generate = _generate_v10


if __name__ == '__main__':
    root = tk.Tk()
    app = GiroApp(root)
    root.mainloop()
