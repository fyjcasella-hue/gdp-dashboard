import calendar
import tkinter as tk
from tkinter import ttk

# Importa la versión estable v4, que contiene filtros, guardado,
# reemplazos y demás funcionalidades ya probadas.
from giro_supervisores_launcher_v4 import GiroApp


def _show_calendar_holiday_selectable(self):
    if not hasattr(self, 'cal_frame'):
        return
    nd = self.parse_month()
    for w in self.cal_frame.winfo_children():
        w.destroy()

    agent = self.cal_agent.get() if hasattr(self, 'cal_agent') else None
    if not agent:
        return

    mode = self.cal_mode.get()
    licenses = self.licenses.setdefault(agent, set())
    unavailable = self.unavailable.setdefault(agent, set())
    self.calendar_agent = agent

    heads = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
    for c, h in enumerate(heads):
        ttk.Label(self.cal_frame, text=h, font=('Segoe UI', 10, 'bold'), anchor='center').grid(
            row=0, column=c, sticky='nsew', padx=3, pady=3
        )

    first, days = calendar.monthrange(self.year, self.month)
    for i in range(first + days):
        d = i - first + 1
        if d < 1:
            continue

        is_holiday = d in self.holidays
        is_license = d in licenses
        is_unavailable = d in unavailable

        # El feriado NO bloquea la selección. Puede coexistir con licencia
        # o no disponible para ese agente.
        if is_license:
            bg = '#F7B7B7'
            state_text = 'FERIADO + LICENCIA' if is_holiday else 'LICENCIA'
        elif is_unavailable:
            bg = '#C9D7FF'
            state_text = 'FERIADO + NO DISP.' if is_holiday else 'NO DISPONIBLE'
        elif is_holiday:
            bg = '#FFE3A3'
            state_text = 'FERIADO'
        else:
            bg = '#F3F5F7'
            state_text = 'DISPONIBLE'

        text = str(d)
        if is_holiday and (is_license or is_unavailable):
            text += '\nFERIADO'

        r = i // 7 + 1
        c = i % 7
        b = tk.Button(
            self.cal_frame,
            text=text,
            bg=bg,
            activebackground=bg,
            relief='flat',
            font=('Segoe UI', 11, 'bold'),
            width=8,
            height=3,
            command=lambda x=d: self.toggle_day(x)
        )
        b.grid(row=r, column=c, sticky='nsew', padx=4, pady=4)

    for c in range(7):
        self.cal_frame.columnconfigure(c, weight=1)

    self.cal_help.set(
        f'{agent}: modo {mode}. Rojo = licencia · Azul = no disponible · '
        'Amarillo = feriado. Un feriado también puede marcarse como licencia o no disponible.'
    )


def _toggle_day_holiday_selectable(self, d):
    agent = self.cal_agent.get()
    mode = self.cal_mode.get()
    if not agent:
        return

    if mode == 'LICENCIA':
        target = self.licenses.setdefault(agent, set())
    else:
        target = self.unavailable.setdefault(agent, set())

    # IMPORTANTE: NO rechazar d in self.holidays.
    # El feriado es una condición general del día, mientras que licencia /
    # no disponible es una restricción individual del agente.
    if d in target:
        target.remove(d)
    else:
        target.add(d)

    self.show_calendar()


GiroApp.show_calendar = _show_calendar_holiday_selectable
GiroApp.refresh_calendar = _show_calendar_holiday_selectable
GiroApp.toggle_day = _toggle_day_holiday_selectable


if __name__ == '__main__':
    root = tk.Tk()
    GiroApp(root)
    root.mainloop()
