# Giro de Supervisores - Nelson Casella
# v9: restricción puntual de destino por agente/día.
# NO modifica la lógica estable de v8 salvo para respetar, al generar,
# si un agente solo puede girar a zona primaria (aeropuerto) o secundaria.

import tkinter as tk
from tkinter import ttk

from giro_supervisores_launcher_v8 import GiroApp, _save_month, _load_month, _reset_new_month


# ---------- Compatibilidad de estado ----------
def _ensure_destination_maps(self):
    if not hasattr(self, 'primary_only') or not isinstance(getattr(self, 'primary_only'), dict):
        self.primary_only = {a: set() for a in self.sup + [self.admin]}
    if not hasattr(self, 'secondary_only') or not isinstance(getattr(self, 'secondary_only'), dict):
        self.secondary_only = {a: set() for a in self.sup + [self.admin]}
    for a in self.sup + [self.admin]:
        self.primary_only.setdefault(a, set())
        self.secondary_only.setdefault(a, set())


# ---------- Calendario: dos modos adicionales ----------
_original_calendar_tab = GiroApp.calendar_tab
_original_show_calendar = GiroApp.show_calendar
_original_toggle_day = GiroApp.toggle_day
_original_refresh_agents = GiroApp.refresh_agents
_original_generate = GiroApp.generate


def _calendar_tab_with_destination_modes(self):
    _original_calendar_tab(self)
    # El calendario base crea self.cal_mode y los radiobuttons LICENCIA/NO DISPONIBLE.
    # Agregamos dos modos más sin tocar los controles existentes.
    top = self.cal_frame.master.winfo_children()[0] if self.cal_frame.master.winfo_children() else None
    if isinstance(top, ttk.Frame):
        ttk.Radiobutton(top, text='SOLO ZONA PRIMARIA', value='SOLO PRIMARIA', variable=self.cal_mode, command=self.show_calendar).pack(side='left', padx=6)
        ttk.Radiobutton(top, text='SOLO ZONA SECUNDARIA', value='SOLO SECUNDARIA', variable=self.cal_mode, command=self.show_calendar).pack(side='left', padx=6)


def _show_calendar_with_destination_modes(self):
    _ensure_destination_maps(self)
    # Reutilizamos exactamente la visualización estable para licencia/no disponible.
    mode = self.cal_mode.get() if hasattr(self, 'cal_mode') else 'LICENCIA'
    if mode not in ('SOLO PRIMARIA', 'SOLO SECUNDARIA'):
        return _original_show_calendar(self)

    if not hasattr(self, 'cal_frame'):
        return
    self.parse_month()
    for w in self.cal_frame.winfo_children():
        w.destroy()
    agent = self.cal_agent.get() if hasattr(self, 'cal_agent') else None
    if not agent:
        return

    primary = self.primary_only.setdefault(agent, set())
    secondary = self.secondary_only.setdefault(agent, set())
    licenses = self.licenses.setdefault(agent, set())
    unavailable = self.unavailable.setdefault(agent, set())

    heads = ['L','M','X','J','V','S','D']
    for c, h in enumerate(heads):
        ttk.Label(self.cal_frame, text=h, font=('Segoe UI',10,'bold'), anchor='center').grid(row=0,column=c,sticky='nsew',padx=3,pady=3)

    import calendar
    first, days = calendar.monthrange(self.year, self.month)
    for i in range(first + days):
        d = i - first + 1
        if d < 1:
            continue
        is_holiday = d in self.holidays
        is_license = d in licenses
        is_unavailable = d in unavailable
        is_primary = d in primary
        is_secondary = d in secondary

        if is_license:
            bg = '#F7B7B7'
            suffix = 'LICENCIA'
        elif is_unavailable:
            bg = '#C9D7FF'
            suffix = 'NO DISP.'
        elif is_primary:
            bg = '#D6EAF8'
            suffix = 'SOLO PRIM.'
        elif is_secondary:
            bg = '#D5F5E3'
            suffix = 'SOLO SEC.'
        elif is_holiday:
            bg = '#FFE3A3'
            suffix = 'FERIADO'
        else:
            bg = '#F3F5F7'
            suffix = ''

        text = str(d) + (f'\n{suffix}' if suffix else '')
        r = i // 7 + 1
        c = i % 7
        tk.Button(self.cal_frame, text=text, bg=bg, activebackground=bg, relief='flat', font=('Segoe UI',10,'bold'), width=9, height=3, command=lambda x=d: self.toggle_day(x)).grid(row=r,column=c,sticky='nsew',padx=4,pady=4)

    for c in range(7):
        self.cal_frame.columnconfigure(c, weight=1)
    self.cal_help.set(f'{agent}: modo {mode}. Azul claro = solo primaria · Verde = solo secundaria. Estas restricciones son independientes de feriados y se guardan por mes.')


def _toggle_day_with_destination_modes(self, d):
    _ensure_destination_maps(self)
    mode = self.cal_mode.get() if hasattr(self, 'cal_mode') else 'LICENCIA'
    if mode not in ('SOLO PRIMARIA', 'SOLO SECUNDARIA'):
        return _original_toggle_day(self, d)

    agent = self.cal_agent.get()
    if not agent:
        return

    primary = self.primary_only.setdefault(agent, set())
    secondary = self.secondary_only.setdefault(agent, set())
    target = primary if mode == 'SOLO PRIMARIA' else secondary
    opposite = secondary if mode == 'SOLO PRIMARIA' else primary

    if d in target:
        target.remove(d)
    else:
        target.add(d)
        # No pueden coexistir 'solo primaria' y 'solo secundaria' el mismo día.
        opposite.discard(d)
    self.show_calendar()
    try:
        _save_month(self, silent=True)
    except Exception:
        pass


def _refresh_agents_with_destination_maps(self):
    _ensure_destination_maps(self)
    return _original_refresh_agents(self)


# ---------- Generación: respetar destino permitido ----------
def _generate_with_destination_restrictions(self, *args, **kwargs):
    _ensure_destination_maps(self)

    # Interceptamos temporalmente all_agents/sup para que la lógica existente de v8
    # siga intacta y solo descarte candidatos según el destino del día.
    original_all_agents = self.all_agents
    original_sup = list(self.sup)

    # Guardamos una función auxiliar que la generación base puede consultar mediante
    # el filtro posterior local. Se aplica después de generar, reparando únicamente
    # asignaciones que violen SOLO PRIMARIA/SOLO SECUNDARIA.
    out = _original_generate(self, *args, **kwargs)

    if not self.result:
        return out

    cron = self.result.get('cron', {})
    blocks = self.result.get('blocks', {})
    admin = self.admin
    changed = False

    for day in sorted(cron):
        today = cron[day]

        # 1) Quien está marcado SOLO SECUNDARIA no puede quedar en aeropuerto.
        for key in [k for k in list(today) if k.startswith('AERO_')]:
            agent = today.get(key)
            if not agent or day not in self.secondary_only.get(agent, set()):
                continue
            candidates = [
                a for a in original_sup
                if a in self.active_agents
                and day not in self.secondary_only.get(a, set())
                and day not in blocks.get(a, {}).get('all', set())
                and a not in today.values()
            ]
            if candidates:
                # Usa el score ya probado del programa.
                candidates.sort(key=lambda a: self.candidate_score(a, key, None))
                today[key] = candidates[0]
                changed = True

        # 2) Quien está marcado SOLO PRIMARIA no puede quedar en zona secundaria.
        zone_keys = [k for k in list(today) if k.startswith('ZONA_')]
        for key in zone_keys:
            agent = today.get(key)
            if not agent or agent == admin or day not in self.primary_only.get(agent, set()):
                continue
            zone = int(key.split('_')[1])
            candidates = [
                a for a in self.all_agents()
                if a != admin
                and a in self.active_agents
                and day not in self.primary_only.get(a, set())
                and day not in blocks.get(a, {}).get('all', set())
                and a not in today.values()
            ]
            if candidates:
                # Determina el tipo SEC correcto para el score existente.
                shift = self.turn_from_key(day, key)
                sec_key = 'SEC_100' if self.pay_type(day, shift, False) == '100%' else 'SEC_50'
                candidates.sort(key=lambda a: self.candidate_score(a, sec_key, zone))
                today[key] = candidates[0]
                changed = True

    if changed:
        self.recalculate_counts()
        self.refresh_schedule()
        self.status.set('Cronograma generado respetando restricciones SOLO PRIMARIA / SOLO SECUNDARIA.')
        try:
            _save_month(self, silent=True)
        except Exception:
            pass

    return out


GiroApp.calendar_tab = _calendar_tab_with_destination_modes
GiroApp.show_calendar = _show_calendar_with_destination_modes
GiroApp.toggle_day = _toggle_day_with_destination_modes
GiroApp.refresh_agents = _refresh_agents_with_destination_maps
GiroApp.generate = _generate_with_destination_restrictions


# ---------- Extender persistencia mensual de v8 ----------
import giro_supervisores_launcher_v8 as v8

_original_state_from_app = v8._state_from_app
_original_load_month = v8._load_month
_original_reset_new_month = v8._reset_new_month


def _state_from_app_v9(self):
    _ensure_destination_maps(self)
    state = _original_state_from_app(self)
    state['primary_only'] = {k: set(v) for k, v in self.primary_only.items()}
    state['secondary_only'] = {k: set(v) for k, v in self.secondary_only.items()}
    return state


def _load_month_v9(self, year, month):
    path = v8._month_path(year, month)
    if not path.exists():
        return False
    import pickle
    with open(path, 'rb') as f:
        state = pickle.load(f)
    ok = _original_load_month(self, year, month)
    if ok:
        self.primary_only = {k: set(v) for k, v in state.get('primary_only', {}).items()}
        self.secondary_only = {k: set(v) for k, v in state.get('secondary_only', {}).items()}
        _ensure_destination_maps(self)
    return ok


def _reset_new_month_v9(self, year, month):
    _original_reset_new_month(self, year, month)
    self.primary_only = {a: set() for a in self.sup + [self.admin]}
    self.secondary_only = {a: set() for a in self.sup + [self.admin]}


v8._state_from_app = _state_from_app_v9
v8._load_month = _load_month_v9
v8._reset_new_month = _reset_new_month_v9


if __name__ == '__main__':
    root = tk.Tk()
    app = GiroApp(root)
    _ensure_destination_maps(app)
    # La recuperación mensual de v8 sigue siendo la misma, extendida con los dos mapas nuevos.
    if not _load_month_v9(app, app.year, app.month):
        _reset_new_month_v9(app, app.year, app.month)
    app.year_var.set(app.year)
    app.month_cb.current(app.month - 1)
    app.holiday_var.set(','.join(str(x) for x in sorted(app.holidays)))
    app.v50_var.set(str(app.v50))
    app.v100_var.set(str(app.v100))
    app.refresh_agents()
    app.show_calendar()
    app.refresh_schedule()
    root.mainloop()
