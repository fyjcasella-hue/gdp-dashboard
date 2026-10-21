import calendar
import tkinter as tk
from tkinter import ttk
from giro_supervisores_final import GiroApp


def calendar_view(self):
    if not hasattr(self, 'cal_frame'):
        return
    self.parse_month()
    for w in self.cal_frame.winfo_children():
        w.destroy()
    agent = self.cal_agent.get() if hasattr(self, 'cal_agent') else None
    if not agent:
        return
    mode = self.cal_mode.get()
    selected = self.licenses.setdefault(agent, set()) if mode == 'LICENCIA' else self.unavailable.setdefault(agent, set())
    self.calendar_agent = agent
    heads = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
    for c, h in enumerate(heads):
        ttk.Label(self.cal_frame, text=h, font=('Segoe UI', 10, 'bold'), anchor='center').grid(row=0, column=c, sticky='nsew', padx=3, pady=3)
        self.cal_frame.columnconfigure(c, weight=1)
    first, days = calendar.monthrange(self.year, self.month)
    for i in range(first + days):
        d = i - first + 1
        if d < 1:
            continue
        row, col = i // 7 + 1, i % 7
        holiday = d in self.holidays
        chosen = d in selected
        weekend = calendar.weekday(self.year, self.month, d) >= 5
        if chosen:
            bg = '#C62828' if mode == 'LICENCIA' else '#1565C0'
            fg = 'white'
            label = f'{d}\n{("LIC" if mode == "LICENCIA" else "NO DISP")}'
        elif holiday:
            bg, fg, label = '#F9A825', '#172B4D', f'{d}\nFERIADO'
        elif weekend:
            bg, fg, label = '#FFF4D6', '#172B4D', str(d)
        else:
            bg, fg, label = '#F4F6F8', '#172B4D', str(d)
        btn = tk.Button(self.cal_frame, text=label, bg=bg, fg=fg, activebackground='#90CAF9', activeforeground='#172B4D', relief='solid', bd=1, font=('Segoe UI', 10, 'bold' if (chosen or holiday) else 'normal'), cursor='hand2', command=lambda day=d: self.toggle_calendar_day(day))
        btn.grid(row=row, column=col, sticky='nsew', padx=3, pady=3, ipady=10)
    self.cal_help.set(f'{mode}: hacé clic en cualquier día. Los feriados se muestran en amarillo, pero siguen siendo seleccionables.')


def toggle_calendar_day(self, day):
    agent = self.cal_agent.get()
    if not agent:
        return
    mode = self.cal_mode.get()
    selected = self.licenses.setdefault(agent, set()) if mode == 'LICENCIA' else self.unavailable.setdefault(agent, set())
    if day in selected:
        selected.remove(day)
    else:
        selected.add(day)
    self.show_calendar()


def replacement_view(self):
    """Reemplazo local con barra de acciones fija y siempre visible."""
    box = ttk.LabelFrame(self.tab_abs, text='Ausencia puntual — reparación local', padding=14)
    box.pack(fill='x')
    ttk.Label(box, text='El cronograma existente NO se regenera. Solo se reemplaza el puesto afectado.').pack(anchor='w')

    row = ttk.Frame(box)
    row.pack(fill='x', pady=12)
    ttk.Label(row, text='Día').pack(side='left')
    self.abs_day = tk.IntVar(value=1)
    ttk.Spinbox(row, from_=1, to=31, textvariable=self.abs_day, width=6).pack(side='left', padx=6)
    ttk.Label(row, text='Agente ausente').pack(side='left', padx=(18, 5))
    self.abs_agent = ttk.Combobox(row, state='readonly', width=25)
    self.abs_agent.pack(side='left')
    ttk.Label(row, text='Puesto').pack(side='left', padx=(18, 5))
    self.abs_key = ttk.Combobox(row, state='readonly', width=23,
                                values=['TODOS LOS TURNOS', *AERO, *[f'ZONA_{i}' for i in range(1, 7)]])
    self.abs_key.current(0)
    self.abs_key.pack(side='left')
    ttk.Button(row, text='BUSCAR REEMPLAZO', style='Accent.TButton',
               command=self.search_replacement).pack(side='left', padx=12)

    self.abs_msg = tk.StringVar(value='Generá primero el cronograma.')
    ttk.Label(box, textvariable=self.abs_msg).pack(anchor='w')

    cols = ('Día', 'Puesto', 'Turno', 'Original', 'Mejor candidato', 'Carga', 'Estado')
    self.abs_tree = ttk.Treeview(self.tab_abs, columns=cols, show='headings', height=16)
    for c, w in zip(cols, [55, 150, 105, 175, 190, 260, 120]):
        self.abs_tree.heading(c, text=c)
        self.abs_tree.column(c, width=w, anchor='center')
    self.abs_tree.pack(fill='both', expand=True, pady=(12, 6))

    # Barra de acciones FIJA: se reserva primero en la parte inferior para que
    # nunca quede oculta por el Treeview, incluso con ventanas pequeñas.
    actions = ttk.Frame(self.tab_abs)
    actions.pack(side='bottom', fill='x', pady=(4, 0))
    ttk.Label(actions, text='Seleccione una fila PENDIENTE para confirmar:',
              font=('Segoe UI', 10, 'bold')).pack(side='left', padx=4)
    ttk.Button(actions, text='VER HISTORIAL', command=self.show_history).pack(side='right', padx=(8, 0))
    ttk.Button(actions, text='✓  CONFIRMAR REEMPLAZO', style='Accent.TButton',
               command=self.confirm_replacement).pack(side='right')


GiroApp.show_calendar = calendar_view
GiroApp.refresh_calendar = calendar_view
GiroApp.toggle_calendar_day = toggle_calendar_day
GiroApp.absence_tab = replacement_view


def main():
    root = tk.Tk()
    app = GiroApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
