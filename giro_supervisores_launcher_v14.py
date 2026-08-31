# Giro de Supervisores - Nelson Casella
# v14: historial mensual recuperable + almacenamiento persistente junto al programa.
# Mantiene INTACTAS la lógica de generación/equidad de v12 y la interfaz moderna de v13.
#
# Cambios exclusivos:
# 1) Historial: seleccionar o hacer doble clic sobre un mes lo recupera correctamente.
# 2) Los antecedentes se guardan en una carpeta de datos junto al EXE cuando es posible.
#    Si Windows no permite escribir allí, usa APPDATA como respaldo seguro.
# 3) Migra automáticamente antecedentes previos desde APPDATA al nuevo almacenamiento.
# 4) Aplica el icono Nelson Casella también a la ventana del programa.

import os
import pickle
import shutil
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from giro_supervisores_launcher_v13 import GiroApp, BG
import giro_supervisores_launcher_v7 as v7
import giro_supervisores_launcher_v8 as v8
import giro_supervisores_launcher_v9 as v9


# -----------------------------------------------------------------------------
# ALMACENAMIENTO MENSUAL
# -----------------------------------------------------------------------------
_original_v8_data_dir = v8._data_dir


def _exe_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _preferred_data_dir():
    return _exe_dir() / 'GiroDeSupervisores_Datos' / 'meses'


def _fallback_data_dir():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return Path(base) / 'GiroDeSupervisores_NelsonCasella' / 'meses'


def _is_writable_folder(path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / '.write_test'
        with open(probe, 'w', encoding='utf-8') as f:
            f.write('ok')
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _data_dir_v14():
    """Carpeta efectiva de antecedentes.

    Prioridad: junto al ejecutable. Si no es escribible (por ejemplo Program Files),
    usa APPDATA. Así los datos nunca dependen del directorio temporal de PyInstaller.
    """
    preferred = _preferred_data_dir()
    if _is_writable_folder(preferred):
        return preferred
    fallback = _fallback_data_dir()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _migrate_previous_history():
    """Copia meses previos de APPDATA al almacenamiento actual, sin sobrescribir."""
    target = _data_dir_v14()
    sources = []
    try:
        sources.append(Path(_original_v8_data_dir()))
    except Exception:
        pass
    sources.append(_fallback_data_dir())

    for source in sources:
        try:
            if source.resolve() == target.resolve() or not source.exists():
                continue
            for p in source.glob('*.giro'):
                dst = target / p.name
                if not dst.exists():
                    shutil.copy2(p, dst)
        except Exception:
            # La migración no debe impedir que el programa abra.
            pass


# Todas las funciones mensuales heredadas de v8/v9 pasan a usar esta carpeta.
v8._data_dir = _data_dir_v14
v7._data_dir = _data_dir_v14


# -----------------------------------------------------------------------------
# RECUPERACIÓN DE UN MES
# -----------------------------------------------------------------------------
def _refresh_ui_after_load(self, source_name=''):
    self.year_var.set(self.year)
    self.month_cb.current(self.month - 1)
    self.holiday_var.set(','.join(str(x) for x in sorted(self.holidays)))
    self.v50_var.set(str(self.v50))
    self.v100_var.set(str(self.v100))
    self.refresh_agents()
    self.show_calendar()
    self.refresh_schedule()
    if source_name:
        self.status.set(f'Antecedentes recuperados: {source_name}')


def _load_history_file(self, path):
    """Carga un .giro v1-v4 incluyendo restricciones SOLO AERO/SOLO SECUNDARIA."""
    path = Path(path)
    try:
        with open(path, 'rb') as f:
            state = pickle.load(f)

        version = state.get('version')
        if version not in (1, 2, 3, 4):
            raise ValueError(f'Versión de antecedentes incompatible: {version}')

        # Restauración completa compatible con v9+.
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
        self.pending = []

        self.primary_only = {k: set(v) for k, v in state.get('primary_only', {}).items()}
        self.secondary_only = {k: set(v) for k, v in state.get('secondary_only', {}).items()}
        v9._ensure_destination_maps(self)

        self.current_internal_state_path = str(path)
        _refresh_ui_after_load(self, path.stem)
        return True
    except Exception as exc:
        messagebox.showerror('Historial', f'No se pudo recuperar el mes:\n{exc}', parent=self.root)
        return False


def _history_v14(self):
    """Historial mensual seleccionable y recuperable por botón o doble clic."""
    _migrate_previous_history()

    win = tk.Toplevel(self.root)
    win.title('Historial mensual - Giro de Supervisores')
    win.geometry('760x500')
    win.minsize(680, 430)
    win.transient(self.root)
    win.grab_set()

    try:
        win.configure(bg=BG)
    except Exception:
        pass

    head = ttk.Frame(win, padding=(22, 18, 22, 8))
    head.pack(fill='x')
    ttk.Label(head, text='HISTORIAL DE MESES', font=('Segoe UI Semibold', 17)).pack(anchor='w')
    ttk.Label(
        head,
        text='Seleccioná un mes y presioná LEVANTAR MES. También podés abrirlo con doble clic.',
        style='Muted.TLabel'
    ).pack(anchor='w', pady=(4, 0))

    frame = ttk.Frame(win, padding=(22, 10, 22, 8))
    frame.pack(fill='both', expand=True)

    tree = ttk.Treeview(frame, columns=('periodo', 'guardado', 'archivo'), show='headings', selectmode='browse')
    tree.heading('periodo', text='PERÍODO')
    tree.heading('guardado', text='ÚLTIMA MODIFICACIÓN')
    tree.heading('archivo', text='ARCHIVO INTERNO')
    tree.column('periodo', width=180, anchor='center')
    tree.column('guardado', width=190, anchor='center')
    tree.column('archivo', width=260, anchor='w')

    ys = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=ys.set)
    tree.grid(row=0, column=0, sticky='nsew')
    ys.grid(row=0, column=1, sticky='ns')
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    months_es = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE']
    files = sorted(_data_dir_v14().glob('*.giro'), key=lambda p: p.stem, reverse=True)

    for p in files:
        try:
            y, m = [int(x) for x in p.stem.split('-', 1)]
            period = f'{months_es[m-1]} {y}' if 1 <= m <= 12 else p.stem
        except Exception:
            period = p.stem
        stamp = datetime.fromtimestamp(p.stat().st_mtime).strftime('%d/%m/%Y %H:%M')
        tree.insert('', 'end', iid=p.name, values=(period, stamp, p.name))

    if files:
        first = tree.get_children()[0]
        tree.selection_set(first)
        tree.focus(first)
    else:
        ttk.Label(frame, text='Todavía no hay meses guardados.', style='Muted.TLabel').grid(row=1, column=0, sticky='w', pady=8)

    def load_selected(event=None):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Historial', 'Seleccioná un mes para levantarlo.', parent=win)
            return
        path = _data_dir_v14() / sel[0]
        if _load_history_file(self, path):
            win.destroy()

    tree.bind('<Double-1>', load_selected)
    tree.bind('<Return>', load_selected)

    buttons = ttk.Frame(win, padding=(22, 8, 22, 18))
    buttons.pack(fill='x')
    ttk.Button(buttons, text='LEVANTAR MES', style='Accent.TButton', command=load_selected).pack(side='left')
    ttk.Button(buttons, text='ABRIR CARPETA DE DATOS', command=lambda: os.startfile(str(_data_dir_v14())) if os.name == 'nt' else None).pack(side='left', padx=8)
    ttk.Button(buttons, text='CERRAR', command=win.destroy).pack(side='right')


# El botón creado originalmente por v7 resuelve v7._history al ejecutarse,
# por eso reemplazar esa función corrige el historial sin reconstruir la interfaz.
v7._history = _history_v14
GiroApp.show_month_history = _history_v14


# -----------------------------------------------------------------------------
# ICONO DE VENTANA
# -----------------------------------------------------------------------------
def _resource_path(relative):
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return base / relative


def _apply_window_icon(root):
    try:
        ico = _resource_path(Path('assets') / 'nelson_casella.ico')
        if ico.exists():
            root.iconbitmap(default=str(ico))
    except Exception:
        pass


if __name__ == '__main__':
    _migrate_previous_history()
    root = tk.Tk()
    root.configure(bg=BG)
    root.option_add('*tearOff', False)
    _apply_window_icon(root)
    app = GiroApp(root)

    # Recupera el mes configurado al iniciar, si ya existe.
    current = v8._month_path(app.year, app.month)
    if current.exists():
        _load_history_file(app, current)

    root.mainloop()
