# Giro de Supervisores - Nelson Casella
# v15: correccion definitiva de alta/baja de agentes sobre v14.
# No modifica generacion, equidad, turnos, zonas, Excel ni historial mensual.
#
# La nomina activa es GLOBAL a la aplicacion y se persiste separada de cada mes.
# Los cronogramas historicos conservan los nombres ya asignados, pero un agente dado
# de baja no vuelve a aparecer ni a participar al cambiar de mes o levantar historial.

import pickle
import tkinter as tk
from tkinter import messagebox

import giro_supervisores_launcher_v14 as v14
import giro_supervisores_launcher_v8 as v8
from giro_supervisores_launcher_v14 import GiroApp, BG


# -----------------------------------------------------------------------------
# NOMINA GLOBAL PERSISTENTE
# -----------------------------------------------------------------------------
def _roster_path():
    folder = v14._data_dir_v14().parent
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'agentes_global.pkl'


def _save_global_roster(self):
    data = {
        'sup': list(self.sup),
        'admin': self.admin,
        'active_agents': set(self.active_agents),
    }
    try:
        with open(_roster_path(), 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
        return True
    except Exception as exc:
        messagebox.showerror('Agentes', f'No se pudo guardar la nómina de agentes:\n{exc}', parent=self.root)
        return False


def _load_global_roster(self, create_if_missing=True):
    path = _roster_path()
    if not path.exists():
        if create_if_missing:
            _save_global_roster(self)
        return False
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
        self.sup = list(data.get('sup', self.sup))
        self.admin = data.get('admin', self.admin)
        allowed = set(self.sup)
        if self.admin:
            allowed.add(self.admin)
        saved_active = set(data.get('active_agents', allowed))
        self.active_agents = saved_active & allowed
        return True
    except Exception as exc:
        messagebox.showerror('Agentes', f'No se pudo recuperar la nómina de agentes:\n{exc}', parent=self.root)
        return False


def _all_agents_v15(self):
    agents = [a for a in self.sup if a in self.active_agents]
    if self.admin in self.active_agents and self.admin not in agents:
        agents.append(self.admin)
    return agents


def _refresh_agents_v15(self):
    """Refresco estricto: nunca reconstruye la lista desde agentes dados de baja."""
    active = _all_agents_v15(self)

    if hasattr(self, 'agent_tree'):
        for item in self.agent_tree.get_children():
            self.agent_tree.delete(item)
        for a in active:
            typ = 'ADMINISTRADOR FIJO' if a == self.admin else 'SUPERVISOR AEROPUERTO'
            self.agent_tree.insert('', 'end', values=(a, typ, 'ACTIVO'))

    if hasattr(self, 'cal_agent'):
        self.cal_agent['values'] = active
        if active and self.cal_agent.get() not in active:
            self.cal_agent.current(0)
        elif not active:
            self.cal_agent.set('')

    if hasattr(self, 'abs_agent'):
        self.abs_agent['values'] = active
        if active and self.abs_agent.get() not in active:
            self.abs_agent.current(0)
        elif not active:
            self.abs_agent.set('')


def _remove_agent_v15(self):
    """Baja real y persistente sin borrar antecedentes históricos."""
    sel = self.agent_tree.selection() if hasattr(self, 'agent_tree') else ()
    if not sel and hasattr(self, 'agent_tree'):
        focus = self.agent_tree.focus()
        if focus:
            sel = (focus,)
    if not sel:
        messagebox.showwarning('Baja', 'Seleccioná un agente de la lista.', parent=self.root)
        return

    values = self.agent_tree.item(sel[0], 'values')
    if not values:
        messagebox.showwarning('Baja', 'No se pudo identificar el agente seleccionado.', parent=self.root)
        return
    name = str(values[0]).strip()

    if name == self.admin:
        messagebox.showwarning('Baja', 'El administrador fijo debe reemplazarse antes de darlo de baja.', parent=self.root)
        return
    if name not in self.active_agents:
        _refresh_agents_v15(self)
        return
    if not messagebox.askyesno(
        'Confirmar baja',
        f'¿Dar de baja a {name}?\n\nSus cronogramas y antecedentes históricos NO se borrarán.',
        parent=self.root,
    ):
        return

    # La baja se aplica a la nómina operativa global, no a los resultados históricos.
    self.active_agents.discard(name)
    self.sup = [a for a in self.sup if a != name]

    _save_global_roster(self)
    _refresh_agents_v15(self)
    try:
        v8._save_month(self, silent=True)
    except Exception:
        pass
    self.status.set(f'Agente dado de baja: {name}')


def _add_agent_v15(self):
    name = self.new_agent.get().strip().upper()
    if not name:
        messagebox.showwarning('Alta', 'Ingresá el nombre del agente.', parent=self.root)
        return
    if name in self.active_agents:
        messagebox.showwarning('Alta', 'Ese agente ya está activo.', parent=self.root)
        return

    if self.agent_type.get() == 'ADMINISTRADOR FIJO':
        if self.admin in self.active_agents:
            messagebox.showwarning('Alta', 'Ya existe un administrador fijo activo.', parent=self.root)
            return
        self.admin = name
    else:
        if name not in self.sup:
            self.sup.append(name)

    self.active_agents.add(name)
    self.licenses.setdefault(name, set())
    self.unavailable.setdefault(name, set())
    if hasattr(self, 'primary_only'):
        self.primary_only.setdefault(name, set())
    if hasattr(self, 'secondary_only'):
        self.secondary_only.setdefault(name, set())

    self.new_agent.set('')
    _save_global_roster(self)
    _refresh_agents_v15(self)
    try:
        v8._save_month(self, silent=True)
    except Exception:
        pass
    self.status.set(f'Agente dado de alta: {name}')


# -----------------------------------------------------------------------------
# EVITAR QUE UN MES HISTORICO RESUCITE AGENTES DADOS DE BAJA
# -----------------------------------------------------------------------------
_original_v8_load_month = v8._load_month
_original_v14_load_history = v14._load_history_file


def _load_month_keep_global_roster(self, year, month):
    ok = _original_v8_load_month(self, year, month)
    if ok:
        _load_global_roster(self, create_if_missing=False)
        _refresh_agents_v15(self)
    return ok


def _load_history_keep_global_roster(self, path):
    ok = _original_v14_load_history(self, path)
    if ok:
        _load_global_roster(self, create_if_missing=False)
        _refresh_agents_v15(self)
        self.show_calendar()
        self.refresh_schedule()
    return ok


GiroApp.all_agents = _all_agents_v15
GiroApp.refresh_agents = _refresh_agents_v15
GiroApp.remove_agent = _remove_agent_v15
GiroApp.add_agent = _add_agent_v15
v8._load_month = _load_month_keep_global_roster
v14._load_history_file = _load_history_keep_global_roster


if __name__ == '__main__':
    v14._migrate_previous_history()
    root = tk.Tk()
    root.configure(bg=BG)
    root.option_add('*tearOff', False)
    v14._apply_window_icon(root)
    app = GiroApp(root)

    # Primero levanta el mes actual; luego impone la nómina global persistente.
    current = v8._month_path(app.year, app.month)
    if current.exists():
        _original_v14_load_history(app, current)

    if not _load_global_roster(app, create_if_missing=False):
        _save_global_roster(app)
    _refresh_agents_v15(app)
    app.show_calendar()
    app.refresh_schedule()

    root.mainloop()
