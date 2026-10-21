# Giro de Supervisores - Nelson Casella
# v16: baja de agentes endurecida sobre v15.
# No modifica generacion, equidad, turnos, zonas, Excel, calendario ni historial.
#
# Objetivo exclusivo:
# - la baja elimina al agente de la nomina operativa de forma inmediata y persistente;
# - un historial mensual viejo no puede volver a incorporarlo;
# - se conserva el nombre dentro de cronogramas historicos ya generados.

import pickle
import tkinter as tk
from tkinter import messagebox

import giro_supervisores_launcher_v15 as v15
import giro_supervisores_launcher_v14 as v14
import giro_supervisores_launcher_v8 as v8
from giro_supervisores_launcher_v15 import GiroApp, BG


def _norm(value):
    return ' '.join(str(value or '').strip().upper().split())


# -----------------------------------------------------------------------------
# NOMINA GLOBAL V2: agrega "tombstones" para impedir resurrecciones desde historiales
# -----------------------------------------------------------------------------
def _save_global_roster_v16(self):
    inactive = {_norm(a) for a in getattr(self, 'inactive_agents', set()) if _norm(a)}
    sup = []
    seen = set()
    for a in getattr(self, 'sup', []):
        n = _norm(a)
        if not n or n in inactive or n in seen:
            continue
        seen.add(n)
        sup.append(str(a).strip())

    active = {_norm(a) for a in getattr(self, 'active_agents', set()) if _norm(a)}
    allowed = {_norm(a) for a in sup}
    admin = str(getattr(self, 'admin', '') or '').strip()
    if admin:
        allowed.add(_norm(admin))

    data = {
        'version': 2,
        'sup': sup,
        'admin': admin,
        'active_agents': {a for a in active if a in allowed and a not in inactive},
        'inactive_agents': inactive,
    }

    try:
        path = v15._roster_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
        return True
    except Exception as exc:
        messagebox.showerror(
            'Agentes',
            f'No se pudo guardar la nómina de agentes:\n{exc}',
            parent=self.root,
        )
        return False


def _load_global_roster_v16(self, create_if_missing=True):
    path = v15._roster_path()
    if not path.exists():
        self.inactive_agents = set()
        if create_if_missing:
            _save_global_roster_v16(self)
        return False

    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)

        inactive = {_norm(a) for a in data.get('inactive_agents', set()) if _norm(a)}
        self.inactive_agents = inactive

        roster_sup = []
        seen = set()
        for a in data.get('sup', getattr(self, 'sup', [])):
            n = _norm(a)
            if not n or n in inactive or n in seen:
                continue
            seen.add(n)
            roster_sup.append(str(a).strip())
        self.sup = roster_sup

        self.admin = str(data.get('admin', getattr(self, 'admin', '')) or '').strip()

        allowed_by_norm = {_norm(a): a for a in self.sup}
        if self.admin:
            allowed_by_norm[_norm(self.admin)] = self.admin

        raw_active = data.get('active_agents', set(allowed_by_norm))
        active_norm = {_norm(a) for a in raw_active if _norm(a)}
        self.active_agents = {
            real for n, real in allowed_by_norm.items()
            if n in active_norm and n not in inactive
        }
        return True
    except Exception as exc:
        messagebox.showerror(
            'Agentes',
            f'No se pudo recuperar la nómina de agentes:\n{exc}',
            parent=self.root,
        )
        return False


def _all_agents_v16(self):
    inactive = {_norm(a) for a in getattr(self, 'inactive_agents', set())}
    active_norm = {_norm(a) for a in getattr(self, 'active_agents', set())}

    result = []
    seen = set()
    for a in getattr(self, 'sup', []):
        n = _norm(a)
        if n and n in active_norm and n not in inactive and n not in seen:
            result.append(a)
            seen.add(n)

    admin = str(getattr(self, 'admin', '') or '').strip()
    if admin:
        n = _norm(admin)
        if n in active_norm and n not in inactive and n not in seen:
            result.append(admin)
    return result


def _refresh_agents_v16(self):
    active = _all_agents_v16(self)

    if hasattr(self, 'agent_tree'):
        for item in self.agent_tree.get_children():
            self.agent_tree.delete(item)
        for a in active:
            typ = 'ADMINISTRADOR FIJO' if _norm(a) == _norm(self.admin) else 'SUPERVISOR AEROPUERTO'
            self.agent_tree.insert('', 'end', values=(a, typ, 'ACTIVO'))

    for attr in ('cal_agent', 'abs_agent'):
        combo = getattr(self, attr, None)
        if combo is None:
            continue
        combo['values'] = active
        if active:
            if combo.get() not in active:
                combo.set(active[0])
        else:
            combo.set('')


def _selected_agent_name(self):
    tree = getattr(self, 'agent_tree', None)
    if tree is None:
        return ''

    sel = tree.selection()
    if not sel:
        focus = tree.focus()
        if focus:
            sel = (focus,)
    if not sel:
        return ''

    values = tree.item(sel[0], 'values')
    if not values:
        return ''
    return str(values[0]).strip()


def _remove_agent_v16(self):
    name = _selected_agent_name(self)
    if not name:
        messagebox.showwarning('Baja', 'Seleccioná un agente de la lista.', parent=self.root)
        return

    if _norm(name) == _norm(self.admin):
        messagebox.showwarning(
            'Baja',
            'El administrador fijo debe reemplazarse antes de darlo de baja.',
            parent=self.root,
        )
        return

    if not messagebox.askyesno(
        'Confirmar baja',
        f'¿Dar de baja a {name}?\n\n'
        'Se quitará de la nómina operativa. Sus cronogramas históricos se conservarán.',
        parent=self.root,
    ):
        return

    target = _norm(name)
    self.inactive_agents = {_norm(a) for a in getattr(self, 'inactive_agents', set()) if _norm(a)}
    self.inactive_agents.add(target)

    # Tres capas de protección: activo, nómina base y listas de selección.
    self.active_agents = {
        a for a in getattr(self, 'active_agents', set())
        if _norm(a) != target
    }
    self.sup = [
        a for a in getattr(self, 'sup', [])
        if _norm(a) != target
    ]

    # Persistir primero la nómina global; el mes se guarda después como fotografía.
    if not _save_global_roster_v16(self):
        return

    _refresh_agents_v16(self)

    # Verificación defensiva: el nombre no debe permanecer visualmente.
    tree = getattr(self, 'agent_tree', None)
    if tree is not None:
        for item in list(tree.get_children()):
            values = tree.item(item, 'values')
            if values and _norm(values[0]) == target:
                tree.delete(item)

    try:
        v8._save_month(self, silent=True)
    except Exception:
        pass

    self.status.set(f'Agente dado de baja: {name}')


def _add_agent_v16(self):
    name = str(self.new_agent.get() or '').strip().upper()
    if not name:
        messagebox.showwarning('Alta', 'Ingresá el nombre del agente.', parent=self.root)
        return

    target = _norm(name)
    active_norm = {_norm(a) for a in getattr(self, 'active_agents', set())}
    if target in active_norm:
        messagebox.showwarning('Alta', 'Ese agente ya está activo.', parent=self.root)
        return

    if self.agent_type.get() == 'ADMINISTRADOR FIJO':
        if self.admin and _norm(self.admin) in active_norm:
            messagebox.showwarning('Alta', 'Ya existe un administrador fijo activo.', parent=self.root)
            return
        self.admin = name
    else:
        if target not in {_norm(a) for a in self.sup}:
            self.sup.append(name)

    self.inactive_agents = {_norm(a) for a in getattr(self, 'inactive_agents', set()) if _norm(a)}
    self.inactive_agents.discard(target)

    # Quitar cualquier variante anterior del set y agregar el nombre canonico.
    self.active_agents = {
        a for a in getattr(self, 'active_agents', set())
        if _norm(a) != target
    }
    self.active_agents.add(name)

    self.licenses.setdefault(name, set())
    self.unavailable.setdefault(name, set())
    if hasattr(self, 'primary_only'):
        self.primary_only.setdefault(name, set())
    if hasattr(self, 'secondary_only'):
        self.secondary_only.setdefault(name, set())

    self.new_agent.set('')
    _save_global_roster_v16(self)
    _refresh_agents_v16(self)
    try:
        v8._save_month(self, silent=True)
    except Exception:
        pass
    self.status.set(f'Agente dado de alta: {name}')


# -----------------------------------------------------------------------------
# REBIND EXPLICITO DEL BOTON "DAR DE BAJA"
# Evita cualquier callback antiguo capturado por capas visuales previas.
# -----------------------------------------------------------------------------
_original_build_ui = GiroApp.build_ui


def _walk_widgets(widget):
    for child in widget.winfo_children():
        yield child
        yield from _walk_widgets(child)


def _build_ui_v16(self):
    _original_build_ui(self)
    for widget in _walk_widgets(self.root):
        try:
            if isinstance(widget, ttk.Button) and _norm(widget.cget('text')) == 'DAR DE BAJA':
                widget.configure(command=self.remove_agent)
        except Exception:
            pass

    if hasattr(self, 'agent_tree'):
        self.agent_tree.bind('<Delete>', lambda event: self.remove_agent())


# Publicar las funciones v16 también en el módulo v15 porque sus wrappers de carga
# resuelven estos nombres globalmente al cambiar de mes o levantar historial.
v15._save_global_roster = _save_global_roster_v16
v15._load_global_roster = _load_global_roster_v16

GiroApp.all_agents = _all_agents_v16
GiroApp.refresh_agents = _refresh_agents_v16
GiroApp.remove_agent = _remove_agent_v16
GiroApp.add_agent = _add_agent_v16
GiroApp.build_ui = _build_ui_v16


if __name__ == '__main__':
    v14._migrate_previous_history()

    root = tk.Tk()
    root.configure(bg=BG)
    root.option_add('*tearOff', False)
    v14._apply_window_icon(root)
    app = GiroApp(root)

    # Cargar el mes actual sin permitir que su fotografia historica gobierne la nomina.
    current = v8._month_path(app.year, app.month)
    if current.exists():
        try:
            v15._original_v14_load_history(app, current)
        except Exception:
            pass

    if not _load_global_roster_v16(app, create_if_missing=False):
        _save_global_roster_v16(app)

    _refresh_agents_v16(app)
    app.show_calendar()
    app.refresh_schedule()

    root.mainloop()
