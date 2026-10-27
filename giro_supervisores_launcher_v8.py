# Giro de Supervisores - Nelson Casella
# v8: correcciones puntuales sobre v7.
# NO modifica la lógica de generación, reemplazos ni rotación de zonas.
# 1) Baja de agentes robusta.
# 2) Historial independiente por mes: al cambiar de mes se guarda el anterior
#    y se recupera el nuevo; si es un mes nuevo, calendario/restricciones comienzan limpios.
# Build trigger: v8 workflow active.

import os
import pickle
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from giro_supervisores_launcher_v7 import GiroApp

APP_NAME = 'GiroDeSupervisores_NelsonCasella'
STATE_VERSION = 4


def _data_dir():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    path = Path(base) / APP_NAME / 'meses'
    path.mkdir(parents=True, exist_ok=True)
    return path


def _month_path(year, month):
    return _data_dir() / f'{int(year):04d}-{int(month):02d}.giro'


def _state_from_app(self):
    return {
        'version': STATE_VERSION,
        'sup': list(self.sup),
        'admin': self.admin,
        'active_agents': set(self.active_agents),
        'licenses': {k: set(v) for k, v in self.licenses.items()},
        'unavailable': {k: set(v) for k, v in self.unavailable.items()},
        'holidays': set(self.holidays),
        'year': int(self.year),
        'month': int(self.month),
        'v50': float(self.v50),
        'v100': float(self.v100),
        'result': self.result,
        'replacement_log': list(self.replacement_log),
    }


def _save_month(self, year=None, month=None, silent=True):
    y = int(self.year if year is None else year)
    m = int(self.month if month is None else month)
    old_y, old_m = self.year, self.month
    self.year, self.month = y, m
    try:
        path = _month_path(y, m)
        with open(path, 'wb') as f:
            pickle.dump(_state_from_app(self), f, pickle.HIGHEST_PROTOCOL)
        self.current_internal_state_path = str(path)
        return True
    except Exception as exc:
        if not silent:
            messagebox.showerror('Guardar antecedentes', f'No se pudieron guardar los antecedentes:\n{exc}')
        return False
    finally:
        self.year, self.month = old_y, old_m


def _load_month(self, year, month):
    path = _month_path(year, month)
    if not path.exists():
        return False
    with open(path, 'rb') as f:
        state = pickle.load(f)
    if state.get('version') not in (1, 2, 3, STATE_VERSION):
        raise ValueError('Versión de antecedentes incompatible.')
    self.sup = list(state.get('sup', self.sup))
    self.admin = state.get('admin', self.admin)
    self.active_agents = set(state.get('active_agents', self.sup + [self.admin]))
    self.licenses = {k: set(v) for k, v in state.get('licenses', {}).items()}
    self.unavailable = {k: set(v) for k, v in state.get('unavailable', {}).items()}
    self.holidays = set(state.get('holidays', set()))
    self.year = int(state.get('year', year))
    self.month = int(state.get('month', month))
    self.v50 = float(state.get('v50', self.v50))
    self.v100 = float(state.get('v100', self.v100))
    self.result = state.get('result')
    self.replacement_log = list(state.get('replacement_log', []))
    self.current_internal_state_path = str(path)
    return True


def _reset_new_month(self, year, month):
    # Los agentes son globales; las restricciones y el cronograma son propios del mes.
    self.year = int(year)
    self.month = int(month)
    self.licenses = {a: set() for a in self.sup + [self.admin]}
    self.unavailable = {a: set() for a in self.sup + [self.admin]}
    self.holidays = set()
    self.result = None
    self.pending = []
    self.replacement_log = []
    self.current_internal_state_path = str(_month_path(year, month))


def _refresh_calendar_month_aware(self):
    """Cambio de mes: guarda el mes saliente y carga/crea el nuevo mes."""
    if getattr(self, '_switching_month', False):
        self.show_calendar()
        return
    self._switching_month = True
    try:
        old_year, old_month = int(self.year), int(self.month)
        try:
            new_year = int(self.year_var.get())
        except Exception:
            new_year = old_year
        try:
            new_month = int(self.month_cb.current()) + 1
        except Exception:
            new_month = old_month

        if (new_year, new_month) != (old_year, old_month):
            _save_month(self, old_year, old_month, silent=True)
            if not _load_month(self, new_year, new_month):
                _reset_new_month(self, new_year, new_month)
            self.year_var.set(self.year)
            self.month_cb.current(self.month - 1)
            self.holiday_var.set(','.join(str(x) for x in sorted(self.holidays)))
            self.v50_var.set(str(self.v50))
            self.v100_var.set(str(self.v100))
            self.refresh_agents()
            self.show_calendar()
            self.refresh_schedule()
            if self.result:
                self.status.set(f'Antecedentes recuperados: {self.month:02d}/{self.year}.')
            else:
                self.status.set(f'Nuevo mes: {self.month:02d}/{self.year}. Calendario limpio.')
        else:
            self.show_calendar()
    finally:
        self._switching_month = False


def _remove_agent_robust(self):
    sel = self.agent_tree.selection()
    if not sel:
        focused = self.agent_tree.focus()
        if focused:
            sel = (focused,)
    if not sel:
        messagebox.showwarning('Baja', 'Seleccioná un agente de la lista de agentes activos.')
        return
    values = self.agent_tree.item(sel[0], 'values')
    if not values:
        messagebox.showwarning('Baja', 'No se pudo identificar el agente seleccionado.')
        return
    name = str(values[0]).strip()
    if not name:
        return
    if name == self.admin:
        messagebox.showwarning('Baja', 'El administrador fijo debe reemplazarse antes de darlo de baja.')
        return
    if name not in self.active_agents:
        messagebox.showinfo('Baja', f'{name} ya no está activo.')
        return
    if not messagebox.askyesno('Confirmar baja', f'¿Dar de baja a {name}?\n\nNo se borrará su historial ni sus antecedentes mensuales.'):
        return
    self.active_agents.discard(name)
    self.refresh_agents()
    self.status.set(f'Agente dado de baja: {name}')
    _save_month(self, silent=True)


_original_generate = GiroApp.generate
_original_confirm = GiroApp.confirm_replacement
_original_add = getattr(GiroApp, 'add_agent', None)
_original_holidays = getattr(GiroApp, 'apply_holidays', None)
_original_clear_month = getattr(GiroApp, 'clear_agent_month', None)


def _generate_and_persist(self, *args, **kwargs):
    out = _original_generate(self, *args, **kwargs)
    _save_month(self, silent=True)
    return out


def _confirm_and_persist(self, *args, **kwargs):
    before = len(getattr(self, 'replacement_log', []))
    out = _original_confirm(self, *args, **kwargs)
    if len(getattr(self, 'replacement_log', [])) != before:
        _save_month(self, silent=True)
    return out


def _wrap_persist(original):
    if original is None:
        return None
    def wrapped(self, *args, **kwargs):
        out = original(self, *args, **kwargs)
        _save_month(self, silent=True)
        return out
    return wrapped


GiroApp.refresh_calendar = _refresh_calendar_month_aware
GiroApp.remove_agent = _remove_agent_robust
GiroApp.generate = _generate_and_persist
GiroApp.confirm_replacement = _confirm_and_persist
GiroApp.add_agent = _wrap_persist(_original_add)
GiroApp.apply_holidays = _wrap_persist(_original_holidays)
GiroApp.clear_agent_month = _wrap_persist(_original_clear_month)


if __name__ == '__main__':
    root = tk.Tk()
    app = GiroApp(root)
    if not _load_month(app, app.year, app.month):
        _reset_new_month(app, app.year, app.month)
    app.year_var.set(app.year)
    app.month_cb.current(app.month - 1)
    app.holiday_var.set(','.join(str(x) for x in sorted(app.holidays)))
    app.v50_var.set(str(app.v50))
    app.v100_var.set(str(app.v100))
    app.refresh_agents()
    app.show_calendar()
    app.refresh_schedule()
    root.mainloop()
