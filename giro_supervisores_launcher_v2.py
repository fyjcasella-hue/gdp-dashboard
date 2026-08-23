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


GiroApp.show_calendar = calendar_view
GiroApp.refresh_calendar = calendar_view
GiroApp.toggle_calendar_day = toggle_calendar_day


def main():
    root = tk.Tk()
    app = GiroApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
