import calendar
import random
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import pandas as pd
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError as exc:
    raise SystemExit('Faltan dependencias. Instala: pip install pandas openpyxl') from exc

MESES_NOMBRES = {1:'ENERO',2:'FEBRERO',3:'MARZO',4:'ABRIL',5:'MAYO',6:'JUNIO',7:'JULIO',8:'AGOSTO',9:'SEPTIEMBRE',10:'OCTUBRE',11:'NOVIEMBRE',12:'DICIEMBRE'}
SUPERVISORES = ['ACCIETTO L.','ECHAVARRIA A.','AMAYA S.','MOCAYAR L.','MINGONE G.','GARAYZABAL D.','PEPA E.','DEVOTTO M.','RODRIGUEZ J.','MARTINEZ PAZ S.','DOMINGUEZ V.','BUSTOS FIERRO F.','JANISZEWSKI J.','MERLO C.','URZAGASTI F.']
ADMIN = 'CASTRO D.'
AGENTES = SUPERVISORES + [ADMIN]
DEFAULT_LICENCIAS = {'DOMINGUEZ V.':[2,3,4,5,6,7,8,9],'PEPA E.':[15,16,17,18,19,20,21,22,23],'RODRIGUEZ J.':list(range(1,15)),'URZAGASTI F.':[4,5],'GARAYZABAL D.':[13,14,15,16,17,18,19,20]}
DEFAULT_NO_TRAB = {'MERLO C.':[8,9,15,16,17,29,30],'DOMINGUEZ V.':[24,29],'JANISZEWSKI J.':[15,16,17],'URZAGASTI F.':[15,16,17]}

class GiroCustomsApp:
    def __init__(self, root):
        self.root = root
        self.root.title('GIRO CUSTOMS — Generador de Cronogramas')
        self.root.geometry('1050x700')
        self.root.minsize(900,620)
        self.result = None
        self.build_ui()

    def build_ui(self):
        style = ttk.Style()
        try: style.theme_use('clam')
        except tk.TclError: pass
        header = tk.Frame(self.root, bg='#1F4E79', height=82)
        header.pack(fill='x')
        tk.Label(header, text='GIRO CUSTOMS', bg='#1F4E79', fg='white', font=('Segoe UI',22,'bold')).pack(anchor='w', padx=28, pady=(13,0))
        tk.Label(header, text='Generador automático de cronogramas y control de equidad', bg='#1F4E79', fg='#D9EAF7', font=('Segoe UI',10)).pack(anchor='w', padx=30)
        body = ttk.Frame(self.root, padding=22); body.pack(fill='both', expand=True)
        config = ttk.LabelFrame(body, text='Configuración del período y valores', padding=16); config.pack(fill='x')
        ttk.Label(config,text='Año').grid(row=0,column=0,sticky='w',padx=6,pady=6)
        self.year = ttk.Spinbox(config, from_=2020,to=2100,width=10); self.year.set('2026'); self.year.grid(row=0,column=1,padx=6)
        ttk.Label(config,text='Mes').grid(row=0,column=2,sticky='w',padx=6)
        self.month = ttk.Combobox(config, values=[f'{i:02d} - {MESES_NOMBRES[i]}' for i in range(1,13)], state='readonly', width=18); self.month.current(7); self.month.grid(row=0,column=3,padx=6)
        ttk.Label(config,text='Feriados (días)').grid(row=0,column=4,sticky='w',padx=6)
        self.holidays = ttk.Entry(config,width=18); self.holidays.insert(0,'17'); self.holidays.grid(row=0,column=5,padx=6)
        ttk.Label(config,text='Hora 50%').grid(row=1,column=0,sticky='w',padx=6,pady=8)
        self.v50 = ttk.Entry(config,width=12); self.v50.insert(0,'17731.5'); self.v50.grid(row=1,column=1,padx=6)
        ttk.Label(config,text='Hora 100%').grid(row=1,column=2,sticky='w',padx=6)
        self.v100 = ttk.Entry(config,width=12); self.v100.insert(0,'23642'); self.v100.grid(row=1,column=3,padx=6)
        ttk.Label(config,text='Semilla aleatoria (opcional)').grid(row=1,column=4,sticky='w',padx=6)
        self.seed = ttk.Entry(config,width=18); self.seed.grid(row=1,column=5,padx=6)

        people = ttk.LabelFrame(body,text='Personal y restricciones',padding=16); people.pack(fill='both',expand=True,pady=16)
        left = ttk.Frame(people); left.pack(side='left',fill='both',expand=True,padx=(0,10))
        ttk.Label(left,text='Licencias por agente — formato: NOMBRE: días separados por coma').pack(anchor='w')
        self.lic_text = tk.Text(left,height=12,width=55,font=('Consolas',9)); self.lic_text.pack(fill='both',expand=True,pady=6)
        self.lic_text.insert('1.0', '\n'.join(f'{a}: {",".join(map(str,days))}' for a,days in DEFAULT_LICENCIAS.items()))
        right = ttk.Frame(people); right.pack(side='left',fill='both',expand=True,padx=(10,0))
        ttk.Label(right,text='Días no trabajables — mismo formato').pack(anchor='w')
        self.no_text = tk.Text(right,height=12,width=55,font=('Consolas',9)); self.no_text.pack(fill='both',expand=True,pady=6)
        self.no_text.insert('1.0', '\n'.join(f'{a}: {",".join(map(str,days))}' for a,days in DEFAULT_NO_TRAB.items()))

        actions = ttk.Frame(body); actions.pack(fill='x')
        self.status = tk.StringVar(value='Listo para generar.')
        ttk.Label(actions,textvariable=self.status).pack(side='left')
        ttk.Button(actions,text='GENERAR CRONOGRAMA',command=self.generate).pack(side='right',padx=5)
        ttk.Button(actions,text='EXPORTAR EXCEL',command=self.export_excel).pack(side='right',padx=5)
        ttk.Button(actions,text='VISTA PREVIA',command=self.preview).pack(side='right',padx=5)

    def parse_days(self, text):
        out={}
        for line in text.splitlines():
            if ':' not in line: continue
            name, values = line.split(':',1); name=name.strip()
            try: days=sorted({int(x.strip()) for x in values.split(',') if x.strip()})
            except ValueError: raise ValueError(f'Días inválidos en {name}.')
            if name: out[name]=days
        return out

    def config(self):
        year=int(self.year.get()); month=self.month.current()+1
        holidays={int(x.strip()) for x in self.holidays.get().split(',') if x.strip()}
        v50=float(self.v50.get().replace(',','.')); v100=float(self.v100.get().replace(',','.'))
        seed=self.seed.get().strip(); random.seed(int(seed) if seed else None)
        return year,month,holidays,v50,v100,self.parse_days(self.lic_text.get('1.0','end')),self.parse_days(self.no_text.get('1.0','end'))

    @staticmethod
    def ranges(days):
        if not days:return 'Ninguno'
        d=sorted(set(days)); parts=[]; start=prev=d[0]
        for x in d[1:]:
            if x==prev+1: prev=x
            else: parts.append(str(start) if start==prev else f'{start} al {prev}'); start=prev=x
        parts.append(str(start) if start==prev else f'{start} al {prev}')
        return ', '.join(parts)

    def generate(self):
        try:
            AÑO,MES,FERIADOS,V50,V100,licencias,no_trab=self.config()
            dias=calendar.monthrange(AÑO,MES)[1]
            def weekend_or_holiday(d): return date(AÑO,MES,d).weekday()>=5 or d in FERIADOS
            bloqueos={}
            for ag in AGENTES:
                lic=set(licencias.get(ag,[])); no=set(no_trab.get(ag,[])); ext=set()
                for d in lic:
                    nxt=d+1
                    if nxt<=dias and weekend_or_holiday(nxt) and nxt not in lic: ext.add(nxt)
                bloqueos[ag]={'licencias':lic,'extensiones_licencia':ext,'no_trabajables':no,'todos':lic|ext|no}
            disponibles={a:max(1,dias-len(bloqueos[a]['todos'])) for a in AGENTES}
            keys=['AERO_01_07','AERO_07_13','AERO_13_19','AERO_19_01']
            cont={a:{k:0 for k in keys} | {'AERO_TOTAL':0,'SEC_50':0,'SEC_100':0,'TOTAL_TURNOS':0,'HORAS_50':0,'HORAS_100':0,'AERO_FIN_DE_SEMANA':0,'INGRESOS_ESTIMADOS':0.0} for a in AGENTES}
            zonas={a:{z:0 for z in range(1,7)} for a in AGENTES}; cron={d:{} for d in range(1,dias+1)}; zona_castro=1
            def pay(d,t,aero=True):
                wd=date(AÑO,MES,d).weekday()
                if d in FERIADOS or wd==6:return '100%'
                if wd==5:
                    if aero and t in ['13 A 19','19 A 01']:return '100%'
                    if not aero and t=='15 A 22':return '100%'
                    if aero and t in ['01 A 07','07 A 13']:return '50%'
                return '50%'
            def income(a):cont[a]['INGRESOS_ESTIMADOS']=cont[a]['HORAS_50']*V50+cont[a]['HORAS_100']*V100
            for d in range(1,dias+1):
                weekend=weekend_or_holiday(d); late=set()
                if d>1:
                    n=cron[d-1].get('AERO_19_01')
                    if n:late.add(n)
                    late.update(a for k,a in cron[d-1].items() if k.startswith('ZONA_'))
                active=['01 A 07','07 A 13','13 A 19','19 A 01'] if weekend else ['01 A 07','19 A 01']
                for t in active:
                    lbl='AERO_'+t.replace(' A ','_'); typ=pay(d,t,True)
                    cand=[a for a in SUPERVISORES if a not in cron[d].values() and d not in bloqueos[a]['todos'] and a not in cron[d-1].values() if d>1 else True]
                    # apply previous-day rest restrictions for airport shifts
                    cand=[a for a in cand if not (d>1 and a in [cron[d-1].get(k) for k in keys])]
                    if t=='01 A 07' and any(x not in late for x in cand):cand=[x for x in cand if x not in late]
                    if not cand:cand=[a for a in SUPERVISORES if a not in cron[d].values() and d not in bloqueos[a]['todos']]
                    random.shuffle(cand); cand.sort(key=lambda x:(cont[x][lbl],round(cont[x]['AERO_TOTAL']/disponibles[x],3),round(cont[x]['INGRESOS_ESTIMADOS']/disponibles[x],3)))
                    if cand:
                        a=cand[0]; cron[d][lbl]=a; cont[a][lbl]+=1;cont[a]['AERO_TOTAL']+=1;cont[a]['TOTAL_TURNOS']+=1;cont[a]['HORAS_100' if typ=='100%' else 'HORAS_50']+=6;cont[a]['AERO_FIN_DE_SEMANA']+=int(weekend);income(a)
                if d not in bloqueos[ADMIN]['todos']:
                    turno='15 A 22' if weekend else '19 A 02'; typ=pay(d,turno,False); cron[d][f'ZONA_{zona_castro}']=ADMIN; cont[ADMIN]['SEC_100' if typ=='100%' else 'SEC_50']+=1;cont[ADMIN]['TOTAL_TURNOS']+=1;cont[ADMIN]['HORAS_100' if typ=='100%' else 'HORAS_50']+=7;zonas[ADMIN][zona_castro]+=1;income(ADMIN);zona_castro=zona_castro+1 if zona_castro<6 else 1
                occupied=zona_castro-1 if zona_castro>1 else 6
                remaining=[1,2,3,4,5,6] if d in bloqueos[ADMIN]['todos'] else [z for z in range(1,7) if z!=occupied]
                random.shuffle(remaining)
                for z in remaining:
                    turno='15 A 22' if weekend else '19 A 02';typ=pay(d,turno,False);lbl='SEC_100' if typ=='100%' else 'SEC_50';cand=[a for a in AGENTES if a not in cron[d].values() and d not in bloqueos[a]['todos']]
                    if cand:
                        random.shuffle(cand);cand.sort(key=lambda x:(cont[x]['INGRESOS_ESTIMADOS']/disponibles[x],cont[x]['TOTAL_TURNOS']/disponibles[x],zonas[x][z]));a=cand[0];cron[d][f'ZONA_{z}']=a;cont[a][lbl]+=1;cont[a]['TOTAL_TURNOS']+=1;cont[a]['HORAS_100' if typ=='100%' else 'HORAS_50']+=7;zonas[a][z]+=1;income(a)
            final=[]
            for d,assign in cron.items():
                for k,a in assign.items():
                    if k.startswith('AERO_'):sec='AEROPUERTO';turno=k.replace('AERO_','').replace('_',' A ');zone='AEROPUERTO';p=pay(d,turno,True)
                    else:sec='ZONA SECUNDARIA';turno='15 A 22' if weekend_or_holiday(d) else '19 A 02';zone=k.replace('ZONA_','ZONA ');p=pay(d,turno,False)
                    final.append({'DÍA':d,'AGENTE':a,'SECCIÓN':sec,'ZONA':zone,'TURNO':turno,'PAGO':p})
            df_cron=pd.DataFrame(final).sort_values(['DÍA','SECCIÓN','TURNO'])
            rows=[]
            for a,c in cont.items():
                rows.append({'Agente':a,'Dias_Disponibles':disponibles[a],**{k:c[k] for k in keys},'SEC_50':c['SEC_50'],'SEC_100':c['SEC_100'],'TOTAL_TURNOS':c['TOTAL_TURNOS'],'CANT_HORAS_50':c['HORAS_50'],'CANT_HORAS_100':c['HORAS_100'],'CANT_HORAS_TOTALES':c['HORAS_50']+c['HORAS_100'],'VALOR_TOTAL_50':c['HORAS_50']*V50,'VALOR_TOTAL_100':c['HORAS_100']*V100,'VALOR_TOTAL_AGENTE':c['INGRESOS_ESTIMADOS'],'Sueldo_Proporcional_Por_Dia':round(c['INGRESOS_ESTIMADOS']/disponibles[a],2)})
            df_control=pd.DataFrame(rows)
            licrows=[]
            for a in AGENTES:
                b=bloqueos[a];licrows.append({'Agente':a,'Días Licencia':len(b['licencias']),'Fechas Licencia':self.ranges(b['licencias']),'Días Extensión (Finde/Feriado)':len(b['extensiones_licencia']),'Fechas Extensión Finde/Feriado':self.ranges(b['extensiones_licencia']),'Días No Trabajables':len(b['no_trabajables']),'Fechas Días No Trabajables':self.ranges(b['no_trabajables']),'Total Días No Disponibles':len(b['todos'])})
            self.result={'year':AÑO,'month':MES,'holidays':FERIADOS,'v50':V50,'v100':V100,'cron':cron,'df_cron':df_cron,'df_control':df_control,'df_licencias':pd.DataFrame(licrows),'days':dias}
            self.status.set(f'Cronograma generado: {MESES_NOMBRES[MES]} {AÑO} — {dias} días.')
            messagebox.showinfo('GIRO CUSTOMS','Cronograma generado correctamente.')
        except Exception as e:
            messagebox.showerror('Error',str(e))

    def preview(self):
        if not self.result:self.generate()
        if not self.result:return
        r=self.result; win=tk.Toplevel(self.root);win.title('Vista previa');win.geometry('1050x650')
        nb=ttk.Notebook(win);nb.pack(fill='both',expand=True)
        for name,df in [('Cronograma',r['df_cron']),('Control de Equidad',r['df_control']),('Licencias',r['df_licencias'])]:
            frame=ttk.Frame(nb);nb.add(frame,text=name);tree=ttk.Treeview(frame,columns=list(df.columns),show='headings')
            for col in df.columns:tree.heading(col,text=col);tree.column(col,width=max(90,min(220,len(str(col))*9+20)),anchor='center')
            for row in df.itertuples(index=False):tree.insert('', 'end', values=list(row))
            ys=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);xs=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set);tree.pack(side='top',fill='both',expand=True);ys.pack(side='right',fill='y');xs.pack(side='bottom',fill='x')

    def export_excel(self):
        if not self.result:self.generate()
        if not self.result:return
        r=self.result; mes=r['month'];year=r['year'];path=filedialog.asksaveasfilename(title='Guardar Excel',initialfile=f'Giro_Customs_Equidad_Total_{mes}_{year}.xlsx',defaultextension='.xlsx',filetypes=[('Excel','*.xlsx')])
        if not path:return
        try:
            wb=openpyxl.Workbook(); header=PatternFill('solid',fgColor='1F4E79');dayfill=PatternFill('solid',fgColor='D9E1F2');aero=PatternFill('solid',fgColor='EBF5FB');week=PatternFill('solid',fgColor='FEF2CB');zebra=PatternFill('solid',fgColor='F9FAFB');white=PatternFill('solid',fgColor='FFFFFF');accent=PatternFill('solid',fgColor='ECF0F1');border=Border(*(Side(style='thin',color='BDC3C7') for _ in range(4)))
            title=Font(name='Segoe UI',size=14,bold=True,color='1F4E79');fh=Font(name='Segoe UI',size=10,bold=True,color='FFFFFF');fd=Font(name='Segoe UI',size=9)
            ws=wb.active;ws.title='Cronograma Día a Día';ws['A1']=f"CRONOGRAMA DE ASIGNACIONES - {MESES_NOMBRES[mes]} {year}";ws['A1'].font=title
            for ci,t in enumerate(r['df_cron'].columns,1):c=ws.cell(3,ci,t);c.fill=header;c.font=fh;c.alignment=Alignment(horizontal='center')
            for ri,row in enumerate(r['df_cron'].itertuples(False),4):
                fill=aero if row[2]=='AEROPUERTO' else (zebra if ri%2==0 else white)
                for ci,v in enumerate(row,1):c=ws.cell(ri,ci,v);c.font=fd;c.border=border;c.fill=fill;c.alignment=Alignment(horizontal='center')
            ws.column_dimensions['F'].hidden=True
            mat=wb.create_sheet('Cronograma Consolidado',1);mat.merge_cells('B3:C3');mat.merge_cells('D3:G3');mat.merge_cells('H3:M3');mat['B3']='DIA - HORARIO A CUBRIR';mat['D3']='SECCIÓN AEROPUERTO';mat['H3']='ZONA SECUNDARIA'
            for pos,t in [(4,'01 A 07'),(5,'07 A 13'),(6,'13 A 19'),(7,'19 A 01'),(8,'ZONA 1'),(9,'ZONA 2'),(10,'ZONA 3'),(11,'ZONA 4'),(12,'ZONA 5'),(13,'ZONA 6')]:mat.cell(4,pos,t)
            for row in [mat['B3'],mat['D3'],mat['H3']]:row.fill=header;row.font=fh;row.alignment=Alignment(horizontal='center')
            for c in range(4,14):mat.cell(4,c).fill=header;mat.cell(4,c).font=fh;mat.cell(4,c).alignment=Alignment(horizontal='center')
            days=['LUNES','MARTES','MIÉRCOLES','JUEVES','VIERNES','SÁBADO','DOMINGO']
            mapping=[(4,'AERO_01_07'),(5,'AERO_07_13'),(6,'AERO_13_19'),(7,'AERO_19_01'),(8,'ZONA_1'),(9,'ZONA_2'),(10,'ZONA_3'),(11,'ZONA_4'),(12,'ZONA_5'),(13,'ZONA_6')]
            for d in range(1,r['days']+1):
                rr=d+4;dt=date(year,mes,d);mat.cell(rr,2,days[dt.weekday()]);mat.cell(rr,3,d);mat.cell(rr,2).fill=dayfill;mat.cell(rr,3).fill=dayfill
                isweek=dt.weekday()>=5 or d in r['holidays']
                for ci,k in mapping:mat.cell(rr,ci,r['cron'][d].get(k,''));mat.cell(rr,ci).fill=week if isweek else (PatternFill('solid',fgColor='E2EFDA') if ci in (4,7) else (white if rr%2==0 else zebra));mat.cell(rr,ci).border=border;mat.cell(rr,ci).alignment=Alignment(horizontal='center')
            for c,w in {'A':3,'B':14,'C':6,'D':20,'E':20,'F':20,'G':20,'H':20,'I':20,'J':20,'K':20,'L':20,'M':20}.items():mat.column_dimensions[c].width=w
            ctrl=wb.create_sheet('Control de Equidad');ctrl['A1']=f"MÉTRICAS Y CONTROL DE EQUIDAD FINANCIERA - {MESES_NOMBRES[mes]} {year}";ctrl['A1'].font=title
            self.write_df_sheet(ctrl,r['df_control'],header,fh,fd,border,accent,zebra,white,currency_from=13)
            lic=wb.create_sheet('Consolidado de Licencias');lic['A1']=f"CONSOLIDADO DE LICENCIAS Y DÍAS NO TRABAJABLES - {MESES_NOMBRES[mes]} {year}";lic['A1'].font=title
            self.write_df_sheet(lic,r['df_licencias'],header,fh,fd,border,accent,zebra,white)
            for sheet in wb.worksheets:
                for col in sheet.columns:
                    letter=get_column_letter(col[0].column); maxlen=max((len(str(c.value or '')) for c in col if c.row>1),default=10);sheet.column_dimensions[letter].width=max(12,min(42,maxlen+4))
            wb.save(path);self.status.set(f'Excel guardado: {path}');messagebox.showinfo('Excel','Archivo guardado correctamente.')
        except Exception as e:messagebox.showerror('Error al exportar',str(e))

    @staticmethod
    def write_df_sheet(ws,df,header,fh,fd,border,accent,zebra,white,currency_from=None):
        for ci,t in enumerate(df.columns,1):c=ws.cell(3,ci,t);c.fill=header;c.font=fh;c.alignment=Alignment(horizontal='center')
        for ri,row in enumerate(df.itertuples(False),4):
            for ci,v in enumerate(row,1):c=ws.cell(ri,ci,v);c.font=fd;c.border=border;c.fill=zebra if ri%2==0 else white;c.alignment=Alignment(horizontal='left' if ci==1 else 'center');
        if currency_from:
            for row in ws.iter_rows(min_row=4):
                for c in row[currency_from-1:]:c.number_format='$#,##0.00'
        total=4+len(df);ws.cell(total,1,'TOTALES / PROMEDIOS').font=Font(name='Segoe UI',size=9,bold=True)
        for ci in range(2,len(df.columns)+1):
            c=ws.cell(total,ci);c.font=Font(name='Segoe UI',size=9,bold=True);c.fill=accent;c.border=border;letter=get_column_letter(ci)
            c.value=f'=SUM({letter}4:{letter}{total-1})' if ci<13 else f'=SUM({letter}4:{letter}{total-1})';c.number_format='$#,##0.00' if ci>=13 else '#,##0'

if __name__ == '__main__':
    root=tk.Tk();app=GiroCustomsApp(root);root.mainloop()
