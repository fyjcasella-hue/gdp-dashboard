"""Launcher del ejecutable de GIRO DE SUPERVISORES.

La interfaz final usa show_calendar() como renderizador del almanaque. Algunas
acciones de configuración llaman al callback histórico refresh_calendar; aquí
se proporciona el alias antes de crear la ventana para mantener compatibilidad
sin alterar la lógica de generación.
"""
import tkinter as tk
from giro_supervisores_final import GiroApp

# Compatibilidad con callbacks creados antes de construir la pestaña Calendario.
if not hasattr(GiroApp, "refresh_calendar"):
    GiroApp.refresh_calendar = GiroApp.show_calendar


def main():
    root = tk.Tk()
    app = GiroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
