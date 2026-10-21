import os
import pickle
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date
import pandas as pd

from giro_supervisores_final import GiroApp

APP_STATE_VERSION = 2
DEFAULT_STATE_FILE = 'GiroDeSupervisores_Trabajo.giro'

# Compatibilidad ANTES de instanciar la app.
if not hasattr(GiroApp, 'refresh_calendar') and hasattr(GiroApp, 'show_calendar'):
    GiroApp.refresh_calendar = GiroApp.show_calendar


def _active_names(app):
    return sorted(list(app.all_agents()), key=lambda x: str(x).upper())


def _extract_rows(app):
    """Convierte el cronograma real (result['cron']) en filas para la grilla."""
    result = getattr(app, 'result', None)
    if not result:
        return []
    # La aplicación base guarda el cronograma como {día: {puesto: agente}}.
    cron = result.get('cron') if isinstance(result, dict) else None
    if isinstance(cron, dict):
        rows = []
        for d in sorted(cron, key=lambda x: int(x)):
            for key, agent in sorted(cron[d].items()):
                aero = str(key).startswith('AERO_')
                section = 'AEROPUERTO' if aero else 'ZONA SECUNDARIA'
                zone = 'AEROPUERTO' if aero else str(key).replace('ZONA_', 'ZONA ')
                try:
                    shift = app.turn_from_key(int(d), key)
                    payment = app.pay_type(int(d), shift, aero)
                except Exception:
                    shift = str(key).replace('AERO_', '').replace('_', ' A ') if aero else ''
                    payment = ''
                rows.append({'DÍA': int(d), 'AGENTE': agent, 'SECCIÓN': section,
                             'ZONA': zone, 'TURNO': shift, 'PAGO': payment})
        return rows
    # Compatibilidad con posibles versiones futuras que entreguen DataFrame/lista.
    if isinstance(result, pd.DataFrame):
        df = result.copy()
    elif isinstance(result, list):
        df = pd.DataFrame(result)
    else:
        return []
    if df.empty:
        return []
    aliases = {'DIA':'DÍA','DÍA':'DÍA','AGENTE':'AGENTE','SECCION':'SECCIÓN',
               'SECCIÓN':'SECCIÓN','ZONA':'ZONA','TURNO':'TURNO','PAGO':'PAGO'}
    df.columns = [aliases.get(str(c).upper(), str(c).upper()) for c in df.columns]
    wanted = ['DÍA','AGENTE','SECCIÓN','ZONA','TURNO','PAGO']
    for c in wanted:
        if c not in df.columns: df[c] = ''
    return df[wanted].fillna('').to_dict('records')


def _build_schedule_tab(self):
    for w in self.tab_schedule.winfo_children(): w.destroy()
    toolbar = ttk.Frame(self.tab_schedule); toolbar.pack(fill='x', pady=(0,8))
    ttk.Button(toolbar,text='ACTUALIZAR VISTA',command=self.refresh_schedule).pack(side='left')
    ttk.Button(toolbar,text='GUARDAR TRABAJO',style='Accent.TButton',command=self.save_work).pack(side='left',padx=8)
    ttk.Button(toolbar,text='ABRIR TRABAJO',command=self.load_work).pack(side='left')
    ttk.Button(toolbar,text='EXPORTAR EXCEL',command=self.export_excel).pack(side='right')
    fb=ttk.LabelFrame(self.tab_schedule,text='Filtros por columna',padding=8); fb.pack(fill='x',pady=(0,8))
    self.schedule_filters={}; labels=['DÍA','AGENTE','SECCIÓN','ZONA','TURNO','PAGO']
    for i,col in enumerate(labels):
        ttk.Label(fb,text=col).grid(row=0,column=i,padx=4,sticky='w')
        cb=ttk.Combobox(fb,state='readonly',width=18); cb.grid(row=1,column=i,padx=4,sticky='ew')
        cb.bind('<<ComboboxSelected>>',lambda e:self.apply_schedule_filters()); self.schedule_filters[col]=cb; fb.columnconfigure(i,weight=1)
    ttk.Button(fb,text='LIMPIAR FILTROS',command=self.clear_schedule_filters).grid(row=1,column=6,padx=(8,0))
    self.schedule_count=tk.StringVar(value='0 registros'); ttk.Label(self.tab_schedule,textvariable=self.schedule_count).pack(anchor='w',pady=(0,4))
    cols=('DÍA','AGENTE','SECCIÓN','ZONA','TURNO','PAGO'); frame=ttk.Frame(self.tab_schedule); frame.pack(fill='both',expand=True)
    self.schedule_tree=ttk.Treeview(frame,columns=cols,show='headings')
    for c,w in zip(cols,[65,220,170,150,110,90]): self.schedule_tree.heading(c,text=c); self.schedule_tree.column(c,width=w,anchor='center')
    ys=ttk.Scrollbar(frame,orient='vertical',command=self.schedule_tree.yview); xs=ttk.Scrollbar(frame,orient='horizontal',command=self.schedule_tree.xview)
    self.schedule_tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set); self.schedule_tree.grid(row=0,column=0,sticky='nsew'); ys.grid(row=0,column=1,sticky='ns'); xs.grid(row=1,column=0,sticky='ew'); frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)
    self.refresh_schedule()


def _refresh_schedule(self):
    if not hasattr(self,'schedule_tree'): return
    rows=_extract_rows(self)
    for item in self.schedule_tree.get_children(): self.schedule_tree.delete(item)
    for col,cb in self.schedule_filters.items():
        vals=sorted({str(r.get(col,'')) for r in rows if str(r.get(col,''))!=''},key=lambda x: (int(x) if x.isdigit() else x.upper()))
        cb['values']=['TODOS']+vals
        if cb.get() not in cb['values']: cb.set('TODOS')
    self.apply_schedule_filters()


def _apply_schedule_filters(self):
    rows=_extract_rows(self); filters={c:cb.get() for c,cb in self.schedule_filters.items()}; visible=[]
    for r in rows:
        if all(not v or v=='TODOS' or str(r.get(c,''))==v for c,v in filters.items()): visible.append(r)
    for r in visible: self.schedule_tree.insert('', 'end', values=tuple(r.get(c,'') for c in ['DÍA','AGENTE','SECCIÓN','ZONA','TURNO','PAGO']))
    self.schedule_count.set(f'{len(visible)} de {len(rows)} registros')


def _clear_schedule_filters(self):
    for cb in self.schedule_filters.values(): cb.set('TODOS')
    self.apply_schedule_filters()


def _build_absence_tab(self):
    for w in self.tab_abs.winfo_children(): w.destroy()
    box=ttk.LabelFrame(self.tab_abs,text='Ausencia puntual — reparación local',padding=14); box.pack(fill='x')
    ttk.Label(box,text='El cronograma existente NO se regenera. Solo se reemplaza el puesto afectado.').pack(anchor='w')
    row=ttk.Frame(box); row.pack(fill='x',pady=12)
    ttk.Label(row,text='Día').pack(side='left'); self.abs_day=tk.IntVar(value=1); ttk.Spinbox(row,from_=1,to=31,textvariable=self.abs_day,width=6).pack(side='left',padx=6)
    ttk.Label(row,text='Agente ausente').pack(side='left',padx=(18,5)); self.abs_agent=ttk.Combobox(row,state='readonly',width=25); self.abs_agent.pack(side='left')
    ttk.Label(row,text='Puesto').pack(side='left',padx=(18,5)); self.abs_key=ttk.Combobox(row,state='readonly',width=23,values=['TODOS LOS TURNOS','AERO_01_07','AERO_07_13','AERO_13_19','AERO_19_01',*[f'ZONA_{i}' for i in range(1,7)] ]); self.abs_key.current(0); self.abs_key.pack(side='left')
    ttk.Button(row,text='BUSCAR REEMPLAZO',style='Accent.TButton',command=self.search_replacement).pack(side='left',padx=12)
    self.abs_msg=tk.StringVar(value='Generá primero el cronograma.'); ttk.Label(box,textvariable=self.abs_msg).pack(anchor='w')

    # Barra de acción ARRIBA de la grilla: nunca queda fuera de pantalla.
    actions=ttk.Frame(self.tab_abs); actions.pack(fill='x',pady=(10,6))
    ttk.Button(actions,text='✓  CONFIRMAR REEMPLAZO',style='Accent.TButton',command=self.confirm_replacement).pack(side='left')
    ttk.Button(actions,text='VER HISTORIAL',command=self.show_history).pack(side='left',padx=8)
    ttk.Label(actions,text='Seleccione cualquier fila recomendada o alternativa y luego confirme.').pack(side='left',padx=12)

    cols=('Día','Puesto','Turno','Original','Mejor candidato','Carga','Estado'); frame=ttk.Frame(self.tab_abs); frame.pack(fill='both',expand=True,pady=4)
    self.abs_tree=ttk.Treeview(frame,columns=cols,show='headings',height=16)
    for c,w in zip(cols,[55,150,105,175,190,260,120]): self.abs_tree.heading(c,text=c); self.abs_tree.column(c,width=w,anchor='center')
    ys=ttk.Scrollbar(frame,orient='vertical',command=self.abs_tree.yview); xs=ttk.Scrollbar(frame,orient='horizontal',command=self.abs_tree.xview)
    self.abs_tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set); self.abs_tree.grid(row=0,column=0,sticky='nsew'); ys.grid(row=0,column=1,sticky='ns'); xs.grid(row=1,column=0,sticky='ew'); frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)


def _confirm_replacement(self):
    sel=self.abs_tree.selection()
    if not sel:
        messagebox.showwarning('Reemplazo','Seleccioná una fila de reemplazo y luego presioná CONFIRMAR REEMPLAZO.'); return
    vals=self.abs_tree.item(sel[0],'values')
    if not vals or len(vals)<7:
        messagebox.showwarning('Reemplazo','No se pudo leer la fila seleccionada.'); return
    try: d=int(vals[0])
    except Exception: messagebox.showerror('Reemplazo','El día seleccionado no es válido.'); return
    key=str(vals[1]); old=str(vals[3]); new=str(vals[4]); state=str(vals[6])
    if state not in ('PENDIENTE','ALTERNATIVA'):
        messagebox.showwarning('Reemplazo','Seleccioná una recomendación o alternativa.'); return
    if not self.result or d not in self.result.get('cron',{}) or self.result['cron'][d].get(key)!=old:
        messagebox.showwarning('Reemplazo','Ese puesto ya cambió o ya fue reemplazado. Volvé a buscar reemplazo.'); return
    if new not in self.active_agents or d in self.result['blocks'].get(new,{}).get('all',set()) or new in self.result['cron'][d].values():
        messagebox.showwarning('Reemplazo','El candidato ya no está disponible para ese turno. Volvé a buscar reemplazo.'); return
    if not messagebox.askyesno('Confirmar reemplazo',f'{old} será reemplazado por {new} en {key} del día {d}.\n\nSe modificará únicamente este puesto.\n¿Confirmar?'):
        return
    self.result['cron'][d][key]=new
    self.replacement_log.append({'Día':d,'Puesto':key,'Turno':self.turn_from_key(d,key),'Original':old,'Reemplazante':new,'Motivo':'Ausencia','Fecha de registro':date.today().isoformat()})
    self.recalculate_counts(); self.refresh_schedule(); self.search_replacement(); self.status.set(f'Reemplazo confirmado: {old} → {new}.')


def _save_work(self,path=None,silent=False):
    if path is None:
        path=filedialog.asksaveasfilename(title='Guardar trabajo',defaultextension='.giro',filetypes=[('Trabajo Giro de Supervisores','*.giro'),('Todos los archivos','*.*')],initialfile=DEFAULT_STATE_FILE)
    if not path:return False
    state={'version':APP_STATE_VERSION,'sup':list(self.sup),'admin':self.admin,'active_agents':set(self.active_agents),'licenses':{k:set(v) for k,v in self.licenses.items()},'unavailable':{k:set(v) for k,v in self.unavailable.items()},'holidays':set(self.holidays),'year':int(self.year),'month':int(self.month),'v50':float(self.v50),'v100':float(self.v100),'result':self.result,'replacement_log':list(self.replacement_log)}
    try:
        with open(path,'wb') as f: pickle.dump(state,f,pickle.HIGHEST_PROTOCOL)
        self.current_state_path=path; self.status.set(f'Trabajo guardado: {os.path.basename(path)}')
        if not silent: messagebox.showinfo('Trabajo guardado',f'Se guardaron los antecedentes en:\n{path}')
        return True
    except Exception as exc:
        if not silent: messagebox.showerror('Guardar',f'No se pudo guardar el trabajo:\n{exc}')
        return False


def _load_work(self):
    path=filedialog.askopenfilename(title='Abrir trabajo guardado',filetypes=[('Trabajo Giro de Supervisores','*.giro'),('Todos los archivos','*.*')])
    if not path:return
    try:
        with open(path,'rb') as f: state=pickle.load(f)
        if state.get('version') not in (1,APP_STATE_VERSION): raise ValueError('Versión de archivo incompatible.')
        self.sup=list(state.get('sup',self.sup)); self.admin=state.get('admin',self.admin); self.active_agents=set(state.get('active_agents',self.sup+[self.admin])); self.licenses={k:set(v) for k,v in state.get('licenses',{}).items()}; self.unavailable={k:set(v) for k,v in state.get('unavailable',{}).items()}; self.holidays=set(state.get('holidays',set())); self.year=int(state.get('year',self.year)); self.month=int(state.get('month',self.month)); self.v50=float(state.get('v50',self.v50)); self.v100=float(state.get('v100',self.v100)); self.result=state.get('result'); self.replacement_log=list(state.get('replacement_log',[])); self.current_state_path=path
        self.year_var.set(self.year); self.month_cb.current(self.month-1); self.holiday_var.set(','.join(str(x) for x in sorted(self.holidays))); self.v50_var.set(str(self.v50)); self.v100_var.set(str(self.v100)); self.refresh_agents(); self.show_calendar(); self.refresh_schedule(); self.status.set(f'Trabajo cargado: {os.path.basename(path)}')
    except Exception as exc: messagebox.showerror('Abrir trabajo',f'No se pudo abrir el archivo:\n{exc}')


def _autosave(self):
    p=getattr(self,'current_state_path',None)
    if p and os.path.exists(p): _save_work(self,p,silent=True)


def _wrap(name):
    original=getattr(GiroApp,name)
    def wrapped(self,*args,**kwargs):
        out=original(self,*args,**kwargs); _autosave(self); return out
    return wrapped

# Overrides definitivos.
GiroApp.schedule_tab=_build_schedule_tab
GiroApp.refresh_schedule=_refresh_schedule
GiroApp.apply_schedule_filters=_apply_schedule_filters
GiroApp.clear_schedule_filters=_clear_schedule_filters
GiroApp.absence_tab=_build_absence_tab
GiroApp.confirm_replacement=_confirm_replacement
GiroApp.save_work=_save_work
GiroApp.load_work=_load_work

_original_refresh_agents=GiroApp.refresh_agents
def _refresh_agents_sorted(self):
    _original_refresh_agents(self)
    vals=_active_names(self)
    self.cal_agent['values']=vals; self.abs_agent['values']=vals
    if vals and self.cal_agent.get() not in vals:self.cal_agent.set(vals[0])
    if vals and self.abs_agent.get() not in vals:self.abs_agent.set(vals[0])
GiroApp.refresh_agents=_refresh_agents_sorted

for _name in ['add_agent','remove_agent','apply_holidays','clear_agent_month','generate']:
    if hasattr(GiroApp,_name): setattr(GiroApp,_name,_wrap(_name))

_original_init=GiroApp.__init__
def _init_with_state(self,root):
    self.current_state_path=None
    _original_init(self,root)
    candidates=[os.path.join(os.getcwd(),DEFAULT_STATE_FILE),os.path.join(os.path.dirname(os.path.abspath(__file__)),DEFAULT_STATE_FILE)]
    for p in candidates:
        if not os.path.exists(p):continue
        try:
            with open(p,'rb') as f: state=pickle.load(f)
            if state.get('version') not in (1,APP_STATE_VERSION): continue
            self.sup=list(state.get('sup',self.sup)); self.admin=state.get('admin',self.admin); self.active_agents=set(state.get('active_agents',self.active_agents)); self.licenses={k:set(v) for k,v in state.get('licenses',{}).items()}; self.unavailable={k:set(v) for k,v in state.get('unavailable',self.unavailable).items()}; self.holidays=set(state.get('holidays',self.holidays)); self.year=int(state.get('year',self.year)); self.month=int(state.get('month',self.month)); self.v50=float(state.get('v50',self.v50)); self.v100=float(state.get('v100',self.v100)); self.result=state.get('result'); self.replacement_log=list(state.get('replacement_log',[])); self.current_state_path=p
            self.year_var.set(self.year); self.month_cb.current(self.month-1); self.holiday_var.set(','.join(str(x) for x in sorted(self.holidays))); self.v50_var.set(str(self.v50)); self.v100_var.set(str(self.v100)); self.refresh_agents(); self.show_calendar(); self.refresh_schedule(); self.status.set('Trabajo guardado cargado automáticamente.')
        except Exception: pass
        break
GiroApp.__init__=_init_with_state

if __name__=='__main__':
    root=tk.Tk(); GiroApp(root); root.mainloop()
