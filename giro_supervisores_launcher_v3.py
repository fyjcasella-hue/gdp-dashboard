import os
import pickle
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd

from giro_supervisores_final import GiroApp

APP_STATE_VERSION = 1
DEFAULT_STATE_FILE = 'GiroDeSupervisores_Trabajo.giro'


def _active_names(app):
    return sorted(list(app.all_agents()), key=lambda x: str(x).upper())


def _extract_rows(app):
    result = getattr(app, 'result', None)
    if result is None:
        return []
    if isinstance(result, pd.DataFrame):
        df = result.copy()
    elif isinstance(result, list):
        df = pd.DataFrame(result)
    else:
        try:
            df = pd.DataFrame(result)
        except Exception:
            return []
    if df.empty:
        return []
    # Normalizar nombres posibles de columnas de la aplicación base.
    aliases = {
        'DIA':'DÍA', 'DÍA':'DÍA', 'AGENTE':'AGENTE', 'SECCION':'SECCIÓN',
        'SECCIÓN':'SECCIÓN', 'ZONA':'ZONA', 'TURNO':'TURNO', 'PAGO':'PAGO'
    }
    df.columns = [aliases.get(str(c).upper(), str(c).upper()) for c in df.columns]
    wanted = ['DÍA','AGENTE','SECCIÓN','ZONA','TURNO','PAGO']
    for c in wanted:
        if c not in df.columns:
            df[c] = ''
    return df[wanted].fillna('').to_dict('records')


def _build_schedule_tab(self):
    # Reemplaza la pestaña original por una vista filtrable, manteniendo el resto de la aplicación.
    for w in self.tab_schedule.winfo_children():
        w.destroy()

    toolbar = ttk.Frame(self.tab_schedule)
    toolbar.pack(fill='x', pady=(0, 8))
    ttk.Button(toolbar, text='ACTUALIZAR VISTA', command=self.refresh_schedule).pack(side='left')
    ttk.Button(toolbar, text='GUARDAR TRABAJO', style='Accent.TButton', command=self.save_work).pack(side='left', padx=8)
    ttk.Button(toolbar, text='ABRIR TRABAJO', command=self.load_work).pack(side='left')
    ttk.Button(toolbar, text='EXPORTAR EXCEL', command=self.export_excel).pack(side='right')

    filter_box = ttk.LabelFrame(self.tab_schedule, text='Filtros por columna', padding=8)
    filter_box.pack(fill='x', pady=(0, 8))
    self.schedule_filters = {}
    labels = ['DÍA','AGENTE','SECCIÓN','ZONA','TURNO','PAGO']
    for i, col in enumerate(labels):
        ttk.Label(filter_box, text=col).grid(row=0, column=i, padx=4, sticky='w')
        cb = ttk.Combobox(filter_box, state='readonly', width=18)
        cb.grid(row=1, column=i, padx=4, sticky='ew')
        cb.bind('<<ComboboxSelected>>', lambda e: self.apply_schedule_filters())
        self.schedule_filters[col] = cb
        filter_box.columnconfigure(i, weight=1)
    ttk.Button(filter_box, text='LIMPIAR FILTROS', command=self.clear_schedule_filters).grid(row=1, column=6, padx=(8,0))

    self.schedule_count = tk.StringVar(value='0 registros')
    ttk.Label(self.tab_schedule, textvariable=self.schedule_count).pack(anchor='w', pady=(0,4))

    cols=('DÍA','AGENTE','SECCIÓN','ZONA','TURNO','PAGO')
    frame = ttk.Frame(self.tab_schedule)
    frame.pack(fill='both', expand=True)
    self.schedule_tree = ttk.Treeview(frame, columns=cols, show='headings')
    widths=[65,220,170,150,110,90]
    for c,w in zip(cols,widths):
        self.schedule_tree.heading(c,text=c)
        self.schedule_tree.column(c,width=w,anchor='center')
    yscroll=ttk.Scrollbar(frame, orient='vertical', command=self.schedule_tree.yview)
    xscroll=ttk.Scrollbar(frame, orient='horizontal', command=self.schedule_tree.xview)
    self.schedule_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
    self.schedule_tree.grid(row=0,column=0,sticky='nsew')
    yscroll.grid(row=0,column=1,sticky='ns')
    xscroll.grid(row=1,column=0,sticky='ew')
    frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)
    self.refresh_schedule()


def _refresh_schedule(self):
    if not hasattr(self, 'schedule_tree'):
        return
    for item in self.schedule_tree.get_children():
        self.schedule_tree.delete(item)
    rows = _extract_rows(self)
    # Actualizar listas de filtros con los valores que realmente existen.
    for col, cb in self.schedule_filters.items():
        vals = sorted({str(r.get(col,'')) for r in rows if str(r.get(col,'')) != ''}, key=lambda x: (float(x) if x.replace('.','',1).isdigit() else x.upper()))
        cb['values'] = ['TODOS'] + vals
        if not cb.get() or cb.get() not in cb['values']:
            cb.set('TODOS')
    self.apply_schedule_filters()


def _apply_schedule_filters(self):
    rows = _extract_rows(self)
    filters = {c: cb.get() for c,cb in self.schedule_filters.items()}
    visible=[]
    for r in rows:
        ok=True
        for c,v in filters.items():
            if v and v != 'TODOS' and str(r.get(c,'')) != v:
                ok=False; break
        if ok: visible.append(r)
    for r in visible:
        self.schedule_tree.insert('', 'end', values=tuple(r.get(c,'') for c in ['DÍA','AGENTE','SECCIÓN','ZONA','TURNO','PAGO']))
    self.schedule_count.set(f'{len(visible)} de {len(rows)} registros')


def _clear_schedule_filters(self):
    for cb in self.schedule_filters.values():
        cb.set('TODOS')
    self.apply_schedule_filters()


def _save_work(self, path=None, silent=False):
    if path is None:
        path = filedialog.asksaveasfilename(
            title='Guardar trabajo',
            defaultextension='.giro',
            filetypes=[('Trabajo Giro de Supervisores','*.giro'),('Todos los archivos','*.*')],
            initialfile=DEFAULT_STATE_FILE
        )
    if not path:
        return False
    state = {
        'version': APP_STATE_VERSION,
        'sup': list(self.sup),
        'admin': self.admin,
        'active_agents': set(self.active_agents),
        'licenses': {k:set(v) for k,v in self.licenses.items()},
        'unavailable': {k:set(v) for k,v in self.unavailable.items()},
        'holidays': set(self.holidays),
        'year': int(self.year),
        'month': int(self.month),
        'v50': float(self.v50),
        'v100': float(self.v100),
        'result': self.result,
        'pending': list(self.pending),
        'replacement_log': list(self.replacement_log),
    }
    try:
        with open(path, 'wb') as f:
            pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
        self.current_state_path = path
        self.status.set(f'Trabajo guardado: {os.path.basename(path)}')
        if not silent:
            messagebox.showinfo('Trabajo guardado', f'Se guardaron los antecedentes en:\n{path}')
        return True
    except Exception as exc:
        if not silent: messagebox.showerror('Guardar', f'No se pudo guardar el trabajo:\n{exc}')
        return False


def _load_work(self):
    path = filedialog.askopenfilename(
        title='Abrir trabajo guardado',
        filetypes=[('Trabajo Giro de Supervisores','*.giro'),('Todos los archivos','*.*')]
    )
    if not path:
        return
    try:
        with open(path, 'rb') as f:
            state = pickle.load(f)
        if state.get('version') != APP_STATE_VERSION:
            raise ValueError('La versión del archivo de trabajo no es compatible con esta versión del programa.')
        self.sup=list(state.get('sup', self.sup)); self.admin=state.get('admin', self.admin)
        self.active_agents=set(state.get('active_agents', self.sup+[self.admin]))
        self.licenses={k:set(v) for k,v in state.get('licenses',{}).items()}
        self.unavailable={k:set(v) for k,v in state.get('unavailable',{}).items()}
        self.holidays=set(state.get('holidays',set()))
        self.year=int(state.get('year',self.year)); self.month=int(state.get('month',self.month))
        self.v50=float(state.get('v50',self.v50)); self.v100=float(state.get('v100',self.v100))
        self.result=state.get('result'); self.pending=list(state.get('pending',[])); self.replacement_log=list(state.get('replacement_log',[]))
        if hasattr(self,'year_var'): self.year_var.set(self.year)
        if hasattr(self,'month_cb'): self.month_cb.current(self.month-1)
        if hasattr(self,'holiday_var'): self.holiday_var.set(','.join(str(x) for x in sorted(self.holidays)))
        if hasattr(self,'v50_var'): self.v50_var.set(str(self.v50))
        if hasattr(self,'v100_var'): self.v100_var.set(str(self.v100))
        self.current_state_path=path
        self.refresh_agents(); self.show_calendar(); self.refresh_schedule()
        self.status.set(f'Trabajo cargado: {os.path.basename(path)}')
    except Exception as exc:
        messagebox.showerror('Abrir trabajo', f'No se pudo abrir el archivo:\n{exc}')


def _autosave(self, path=None):
    p = path or getattr(self, 'current_state_path', None)
    if p and os.path.exists(p):
        _save_work(self, p, silent=True)


def _wrap(method_name):
    original = getattr(GiroApp, method_name)
    def wrapped(self, *args, **kwargs):
        out = original(self, *args, **kwargs)
        _autosave(self)
        return out
    return wrapped

# Correcciones/funciones nuevas aplicadas antes de crear la ventana.
GiroApp.schedule_tab = _build_schedule_tab
GiroApp.refresh_schedule = _refresh_schedule
GiroApp.apply_schedule_filters = _apply_schedule_filters
GiroApp.clear_schedule_filters = _clear_schedule_filters
GiroApp.save_work = _save_work
GiroApp.load_work = _load_work

# Orden alfabético en todos los desplegables.
_original_refresh_agents = GiroApp.refresh_agents
def _refresh_agents_sorted(self):
    _original_refresh_agents(self)
    vals = _active_names(self)
    self.cal_agent['values'] = vals
    self.abs_agent['values'] = vals
    if vals and self.cal_agent.get() not in vals: self.cal_agent.set(vals[0])
    if vals and self.abs_agent.get() not in vals: self.abs_agent.set(vals[0])
GiroApp.refresh_agents = _refresh_agents_sorted

# Guardado automático después de operaciones que cambian antecedentes.
for _name in ['add_agent','remove_agent','apply_holidays','clear_agent_month','generate','confirm_replacement']:
    if hasattr(GiroApp, _name):
        setattr(GiroApp, _name, _wrap(_name))

_original_init = GiroApp.__init__
def _init_with_state(self, root):
    self.current_state_path = None
    _original_init(self, root)
    # Si existe un trabajo guardado en la misma carpeta del ejecutable, cargarlo automáticamente.
    candidates = [
        os.path.join(os.getcwd(), DEFAULT_STATE_FILE),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), DEFAULT_STATE_FILE),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p,'rb') as f: state=pickle.load(f)
                if state.get('version') == APP_STATE_VERSION:
                    self.sup=list(state.get('sup',self.sup)); self.admin=state.get('admin',self.admin); self.active_agents=set(state.get('active_agents',self.active_agents))
                    self.licenses={k:set(v) for k,v in state.get('licenses',{}).items()}; self.unavailable={k:set(v) for k,v in state.get('unavailable',{}).items()}; self.holidays=set(state.get('holidays',self.holidays))
                    self.year=int(state.get('year',self.year)); self.month=int(state.get('month',self.month)); self.v50=float(state.get('v50',self.v50)); self.v100=float(state.get('v100',self.v100)); self.result=state.get('result'); self.pending=list(state.get('pending',[])); self.replacement_log=list(state.get('replacement_log',[])); self.current_state_path=p
                    self.year_var.set(self.year); self.month_cb.current(self.month-1); self.holiday_var.set(','.join(str(x) for x in sorted(self.holidays))); self.v50_var.set(str(self.v50)); self.v100_var.set(str(self.v100)); self.refresh_agents(); self.show_calendar(); self.refresh_schedule(); self.status.set('Trabajo guardado cargado automáticamente.')
            except Exception:
                pass
            break
GiroApp.__init__ = _init_with_state

if __name__ == '__main__':
    root = tk.Tk()
    app = GiroApp(root)
    root.mainloop()
