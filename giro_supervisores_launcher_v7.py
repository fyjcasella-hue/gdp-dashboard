# Giro de Supervisores - Nelson Casella
# v7: persistencia interna mes a mes.
# NO modifica la lógica de generación, reemplazos ni rotación de zonas de v6.

import os
import pickle
from pathlib import Path
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox

from giro_supervisores_launcher_v6 import GiroApp

APP_NAME = 'GiroDeSupervisores_NelsonCasella'
STATE_VERSION = 3


def _data_dir():
    """Carpeta privada de datos de la aplicación, fuera de la carpeta del EXE."""
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
        'saved_at': date.today().isoformat(),
    }


def _save_internal(self, silent=True):
    """Guarda automáticamente el mes actual sin abrir diálogos."""
    try:
        path = _month_path(self.year, self.month)
        with open(path, 'wb') as f:
            pickle.dump(_state_from_app(self), f, pickle.HIGHEST_PROTOCOL)
        self.current_internal_state_path = str(path)
        return True
    except Exception as exc:
        if not silent:
            messagebox.showerror('Guardar antecedentes', f'No se pudieron guardar los antecedentes:\n{exc}')
        return False


def _restore_state(self, state, source_name=''):
    if state.get('version') not in (1, 2, STATE_VERSION):
        raise ValueError('Versión de antecedentes incompatible.')

    self.sup = list(state.get('sup', self.sup))
    self.admin = state.get('admin', self.admin)
    self.active_agents = set(state.get('active_agents', self.sup + [self.admin]))
    self.licenses = {k: set(v) for k, v in state.get('licenses', {}).items()}
    self.unavailable = {k: set(v) for k, v in state.get('unavailable', {}).items()}
    self.holidays = set(state.get('holidays', set()))
    self.year = int(state.get('year', self.year))
    self.month = int(state.get('month', self.month))
    self.v50 = float(state.get('v50', self.v50))
    self.v100 = float(state.get('v100', self.v100))
    self.result = state.get('result')
    self.replacement_log = list(state.get('replacement_log', []))

    # Actualizar controles visuales si ya existen.
    if hasattr(self, 'year_var'):
        self.year_var.set(self.year)
    if hasattr(self, 'month_cb'):
        self.month_cb.current(self.month - 1)
    if hasattr(self, 'holiday_var'):
        self.holiday_var.set(','.join(str(x) for x in sorted(self.holidays)))
    if hasattr(self, 'v50_var'):
        self.v50_var.set(str(self.v50))
    if hasattr(self, 'v100_var'):
        self.v100_var.set(str(self.v100))

    self.refresh_agents()
    self.show_calendar()
    self.refresh_schedule()
    if source_name:
        self.status.set(f'Antecedentes recuperados: {source_name}')


def _restore_current_month(self):
    """Al abrir la aplicación, recupera automáticamente el mes que está configurado."""
    path = _month_path(self.year, self.month)
    if not path.exists():
        return False
    try:
        with open(path, 'rb') as f:
            state = pickle.load(f)
        _restore_state(self, state, path.name)
        self.current_internal_state_path = str(path)
        return True
    except Exception as exc:
        self.status.set(f'No se pudo recuperar automáticamente {path.name}: {exc}')
        return False


def _history(self):
    win = tk.Toplevel(self.root if hasattr(self, 'root') else self.master)
    win.title('Historial de meses - Giro de Supervisores')
    win.geometry('620x430')
    win.transient(self.root if hasattr(self, 'root') else self.master)
    win.grab_set()

    ttk.Label(win, text='ANTECEDENTES GUARDADOS MES A MES', font=('Segoe UI', 13, 'bold')).pack(pady=(15, 5))
    ttk.Label(win, text='El programa conserva automáticamente cada mes dentro de la misma aplicación.').pack(pady=(0, 10))

    frame = ttk.Frame(win, padding=10)
    frame.pack(fill='both', expand=True)
    tree = ttk.Treeview(frame, columns=('mes', 'modificado'), show='headings')
    tree.heading('mes', text='MES')
    tree.heading('modificado', text='ÚLTIMA MODIFICACIÓN')
    tree.column('mes', width=260, anchor='center')
    tree.column('modificado', width=220, anchor='center')
    ys = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=ys.set)
    tree.grid(row=0, column=0, sticky='nsew')
    ys.grid(row=0, column=1, sticky='ns')
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    files = sorted(_data_dir().glob('*.giro'), reverse=True)
    for p in files:
        stamp = date.fromtimestamp(p.stat().st_mtime).strftime('%d/%m/%Y')
        tree.insert('', 'end', iid=p.name, values=(p.stem, stamp))

    def load_selected():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Historial', 'Seleccioná un mes.', parent=win)
            return
        path = _data_dir() / sel[0]
        try:
            with open(path, 'rb') as f:
                state = pickle.load(f)
            _restore_state(self, state, path.name)
            self.current_internal_state_path = str(path)
            win.destroy()
        except Exception as exc:
            messagebox.showerror('Historial', f'No se pudo recuperar el mes:\n{exc}', parent=win)

    buttons = ttk.Frame(win)
    buttons.pack(fill='x', padx=10, pady=10)
    ttk.Button(buttons, text='ABRIR MES SELECCIONADO', command=load_selected).pack(side='left')
    ttk.Button(buttons, text='CERRAR', command=win.destroy).pack(side='right')


# Conservamos exactamente la lógica existente y agregamos persistencia alrededor.
_original_generate = GiroApp.generate
_original_confirm = GiroApp.confirm_replacement
_original_add = getattr(GiroApp, 'add_agent', None)
_original_remove = getattr(GiroApp, 'remove_agent', None)
_original_holidays = getattr(GiroApp, 'apply_holidays', None)
_original_clear_month = getattr(GiroApp, 'clear_agent_month', None)
_original_schedule_tab = GiroApp.schedule_tab


def _generate_and_persist(self, *args, **kwargs):
    out = _original_generate(self, *args, **kwargs)
    _save_internal(self)
    return out


def _confirm_and_persist(self, *args, **kwargs):
    before = len(getattr(self, 'replacement_log', []))
    out = _original_confirm(self, *args, **kwargs)
    after = len(getattr(self, 'replacement_log', []))
    if after != before:
        _save_internal(self)
    return out


def _wrap_and_persist(original):
    if original is None:
        return None
    def wrapped(self, *args, **kwargs):
        out = original(self, *args, **kwargs)
        _save_internal(self)
        return out
    return wrapped


def _schedule_with_history(self):
    _original_schedule_tab(self)
    # Agrega solamente el acceso al historial; no modifica los controles existentes.
    children = self.tab_schedule.winfo_children()
    if children:
        toolbar = children[0]
        ttk.Button(toolbar, text='HISTORIAL DE MESES', command=lambda: _history(self)).pack(side='left', padx=8)


GiroApp.generate = _generate_and_persist
GiroApp.confirm_replacement = _confirm_and_persist
GiroApp.add_agent = _wrap_and_persist(_original_add)
GiroApp.remove_agent = _wrap_and_persist(_original_remove)
GiroApp.apply_holidays = _wrap_and_persist(_original_holidays)
GiroApp.clear_agent_month = _wrap_and_persist(_original_clear_month)
GiroApp.schedule_tab = _schedule_with_history


if __name__ == '__main__':
    root = tk.Tk()
    app = GiroApp(root)
    # Recuperación automática: si ya trabajaste este año/mes, vuelve exactamente
    # al último estado guardado. Si no existe, inicia normalmente.
    _restore_current_month(app)
    root.mainloop()
