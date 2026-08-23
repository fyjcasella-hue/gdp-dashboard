import calendar
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox

from giro_customs_pc import GiroCustomsApp as BaseApp, SUPERVISORES, AGENTES, ADMIN, MESES_NOMBRES

class GiroCustomsFinalApp(BaseApp):
    """GIRO CUSTOMS with local absence repair: only the affected assignment changes."""
    def build_ui(self):
        super().build_ui()
        # Dedicated absence workflow below the existing controls.
        box = ttk.LabelFrame(self.root, text='Ausencias y reemplazos locales', padding=10)
        box.pack(fill='x', padx=22, pady=(0,12))
        ttk.Label(box, text='Día').grid(row=0,column=0,padx=5)
        self.abs_day = ttk.Spinbox(box, from_=1, to=31, width=6); self.abs_day.set('1'); self.abs_day.grid(row=0,column=1,padx=5)
        ttk.Label(box, text='Agente ausente').grid(row=0,column=2,padx=5)
        self.abs_agent = ttk.Combobox(box, values=AGENTES, state='readonly', width=24); self.abs_agent.current(0); self.abs_agent.grid(row=0,column=3,padx=5)
        ttk.Label(box, text='Turno / puesto').grid(row=0,column=4,padx=5)
        self.abs_shift = ttk.Combobox(box, values=['TODOS LOS TURNOS','01 A 07','07 A 13','13 A 19','19 A 01','15 A 22','19 A 02','ZONA 1','ZONA 2','ZONA 3','ZONA 4','ZONA 5','ZONA 6'], state='readonly', width=20)
        self.abs_shift.current(0); self.abs_shift.grid(row=0,column=5,padx=5)
        ttk.Button(box,text='BUSCAR REEMPLAZO',command=self.search_replacement).grid(row=0,column=6,padx=8)
        ttk.Button(box,text='HISTORIAL',command=self.show_replacement_history).grid(row=0,column=7,padx=4)
        self.abs_status = tk.StringVar(value='El cronograma generado permanece sin cambios hasta confirmar un reemplazo.')
        ttk.Label(box,textvariable=self.abs_status).grid(row=1,column=0,columnspan=8,sticky='w',padx=5,pady=(8,0))
        self.replacement_log=[]

    def _config_restrictions(self):
        year, month, holidays, v50, v100, licenses, nonwork = self.config()
        days = calendar.monthrange(year, month)[1]
        def weekend_or_holiday(d): return date(year,month,d).weekday() >= 5 or d in holidays
        blocked={}
        for ag in AGENTES:
            lic=set(licenses.get(ag,[])); no=set(nonwork.get(ag,[])); ext=set()
            for d in lic:
                nxt=d+1
                if nxt <= days and weekend_or_holiday(nxt) and nxt not in lic: ext.add(nxt)
            blocked[ag]=lic|ext|no
        return year,month,holidays,blocked,licenses,nonwork

    def _target_keys(self, day, agent, selected):
        cron=self.result['cron']
        if selected == 'TODOS LOS TURNOS':
            return [k for k,v in cron.get(day,{}).items() if v == agent]
        mapping={'01 A 07':'AERO_01_07','07 A 13':'AERO_07_13','13 A 19':'AERO_13_19','19 A 01':'AERO_19_01',
                 '15 A 22':None,'19 A 02':None,'ZONA 1':'ZONA_1','ZONA 2':'ZONA_2','ZONA 3':'ZONA_3','ZONA 4':'ZONA_4','ZONA 5':'ZONA_5','ZONA 6':'ZONA_6'}
        key=mapping.get(selected)
        if key: return [key] if cron.get(day,{}).get(key)==agent else []
        return [k for k,v in cron.get(day,{}).items() if v==agent and k.startswith('ZONA_')]

    def _score_candidates(self, candidates, day, key, payment):
        cron=self.result['cron']
        counts={a:{'total':0,'aero':0,'shift':0,'sec50':0,'sec100':0,'zone':0} for a in AGENTES}
        for d, assignments in cron.items():
            for k,a in assignments.items():
                if a not in counts: continue
                counts[a]['total'] += 1
                if k.startswith('AERO_'):
                    counts[a]['aero'] += 1
                    if k == key: counts[a]['shift'] += 1
                else:
                    if k == key: counts[a]['zone'] += 1
                    # secondary payment is determined by the date, not stored in cron
                    wd=date(self.result['year'],self.result['month'],d).weekday()
                    is100=d in self.result['holidays'] or wd==6 or (wd==5)
                    counts[a]['sec100' if is100 else 'sec50'] += 1
        available={a:max(1,self.result['days']-len(self._blocked.get(a,set()))) for a in AGENTS}
        # Lexicographic score: exact assignment frequency, normalized workload, then total workload.
        def score(a):
            c=counts[a]; avail=available[a]
            exact=c['shift'] if key.startswith('AERO_') else c['zone']
            return (exact, round(c['total']/avail,5), round(c['aero']/avail,5), round((c['sec100']+c['sec50'])/avail,5))
        return sorted(candidates,key=score), counts

    def _candidate_pool(self, day, key):
        cron=self.result['cron']; blocked=self._blocked
        pool=SUPERVISORES if key.startswith('AERO_') else AGENTES
        candidates=[]
        previous=cron.get(day-1,{}) if day>1 else {}
        for a in pool:
            if day in blocked.get(a,set()): continue
            if a in cron.get(day,{}).values(): continue
            # Preserve the rest rules used by the generator.
            if key.startswith('AERO_'):
                if any(previous.get(k)==a for k in ('AERO_01_07','AERO_07_13','AERO_13_19','AERO_19_01')): continue
                if key=='AERO_01_07' and (previous.get('AERO_19_01')==a or any(v==a for k,v in previous.items() if k.startswith('ZONA_'))): continue
            else:
                if any(v==a for k,v in previous.items() if k.startswith('ZONA_')): continue
            candidates.append(a)
        return candidates

    def search_replacement(self):
        if not self.result:
            messagebox.showwarning('GIRO CUSTOMS','Primero genera el cronograma del mes.')
            return
        try:
            day=int(self.abs_day.get()); agent=self.abs_agent.get(); selected=self.abs_shift.get()
            if day<1 or day>self.result['days']: raise ValueError(f'El día debe estar entre 1 y {self.result["days"]}.')
            self._year,self._month,self._holidays,self._blocked,_,_=self._config_restrictions()
            targets=self._target_keys(day,agent,selected)
            if not targets:
                messagebox.showinfo('Ausencia','El agente seleccionado no tiene ese puesto/turno en el día indicado.')
                return
            if len(targets)>1:
                self._choose_target_window(day,agent,targets)
            else:
                self._show_replacement_candidates(day,agent,targets[0])
        except Exception as e:
            messagebox.showerror('Error',str(e))

    def _choose_target_window(self,day,agent,targets):
        win=tk.Toplevel(self.root); win.title('Seleccionar turno afectado'); win.geometry('500x300')
        ttk.Label(win,text=f'{agent} tiene {len(targets)} asignaciones el día {day}.').pack(pady=12)
        for key in targets:
            label=key.replace('AERO_','AEROPUERTO ').replace('_',' A ') if key.startswith('AERO_') else key.replace('_',' ')
            ttk.Button(win,text=label,command=lambda k=key:(win.destroy(),self._show_replacement_candidates(day,agent,k))).pack(fill='x',padx=40,pady=5)

    def _show_replacement_candidates(self,day,absent,key):
        cron=self.result['cron']; weekend=date(self.result['year'],self.result['month'],day).weekday()>=5 or day in self.result['holidays']
        if key.startswith('AERO_'):
            shift=key.replace('AERO_','').replace('_',' A '); payment=self._payment(day,shift,True); section='AEROPUERTO'; zone='AEROPUERTO'
        else:
            shift='15 A 22' if weekend else '19 A 02'; payment=self._payment(day,shift,False); section='ZONA SECUNDARIA'; zone=key.replace('_',' ')
        candidates=self._candidate_pool(day,key)
        ranked,_=self._score_candidates(candidates,day,key,payment)
        win=tk.Toplevel(self.root); win.title('Mejor reemplazo'); win.geometry('760x470')
        ttk.Label(win,text='REEMPLAZO LOCAL — NO SE REGENERA EL MES',font=('Segoe UI',13,'bold')).pack(pady=12)
        info=f'Día {day} | {section} | {zone} | Turno {shift} | Pago {payment}\nAusente: {absent}'
        ttk.Label(win,text=info,justify='left').pack(anchor='w',padx=20,pady=5)
        tree=ttk.Treeview(win,columns=('agente','puesto','criterio'),show='headings',height=9)
        for col,title,width in [('agente','Candidato',190),('puesto','Puesto',180),('criterio','Prioridad de equidad',300)]: tree.heading(col,text=title);tree.column(col,width=width)
        for i,a in enumerate(ranked[:8]): tree.insert('', 'end', iid=str(i), values=(a,zone, 'MEJOR OPCIÓN' if i==0 else f'Alternativa #{i+1}'))
        tree.pack(fill='both',expand=True,padx=20,pady=10)
        if not ranked:
            ttk.Label(win,text='NO EXISTE un reemplazante compatible con todas las restricciones.',foreground='red').pack(pady=8)
            ttk.Button(win,text='Cerrar',command=win.destroy).pack(pady=8); return
        tree.selection_set('0')
        def confirm():
            sel=tree.selection()
            if not sel:return
            chosen=tree.item(sel[0],'values')[0]
            if not messagebox.askyesno('Confirmar reemplazo',f'Reemplazar a {absent} por {chosen}?\n\nSolo se modificará este puesto.',parent=win): return
            self._apply_replacement(day,key,absent,chosen,section,zone,shift,payment)
            win.destroy()
        ttk.Button(win,text='CONFIRMAR REEMPLAZO',command=confirm).pack(side='left',padx=20,pady=10)
        ttk.Button(win,text='Cancelar',command=win.destroy).pack(side='right',padx=20,pady=10)

    def _payment(self,day,shift,airport):
        wd=date(self.result['year'],self.result['month'],day).weekday()
        if day in self.result['holidays'] or wd==6:return '100%'
        if wd==5:
            if airport and shift in ('13 A 19','19 A 01'):return '100%'
            if not airport and shift=='15 A 22':return '100%'
            if airport and shift in ('01 A 07','07 A 13'):return '50%'
        return '50%'

    def _apply_replacement(self,day,key,absent,chosen,section,zone,shift,payment):
        # Local mutation only: no regeneration.
        self.result['cron'][day][key]=chosen
        self.result['df_cron'].loc[(self.result['df_cron']['DÍA']==day)&(self.result['df_cron']['AGENTE']==absent)&(self.result['df_cron']['ZONA']==zone)&(self.result['df_cron']['TURNO']==shift),'AGENTE']=chosen
        entry={'DÍA':day,'SECCIÓN':section,'ZONA':zone,'TURNO':shift,'PAGO':payment,'AGENTE ORIGINAL':absent,'REEMPLAZANTE':chosen}
        self.replacement_log.append(entry)
        self.abs_status.set(f'Reemplazo confirmado: {absent} → {chosen} | día {day} | {zone} | {shift}. El resto del cronograma permanece intacto.')
        messagebox.showinfo('Reemplazo confirmado',f'{absent} fue reemplazado por {chosen}.\n\nNo se regeneró ningún otro turno.')

    def show_replacement_history(self):
        win=tk.Toplevel(self.root);win.title('Historial de reemplazos');win.geometry('900x420')
        cols=['DÍA','SECCIÓN','ZONA','TURNO','PAGO','AGENTE ORIGINAL','REEMPLAZANTE']
        tree=ttk.Treeview(win,columns=cols,show='headings')
        for c in cols:tree.heading(c,text=c);tree.column(c,width=125,anchor='center')
        for row in self.replacement_log:tree.insert('', 'end',values=[row.get(c,'') for c in cols])
        tree.pack(fill='both',expand=True,padx=12,pady=12)

# Base generator uses these attributes only after a result exists; replacement screen populates them from config.
if __name__=='__main__':
    root=tk.Tk(); app=GiroCustomsFinalApp(root); root.mainloop()
