"""Launcher de GIRO DE SUPERVISORES.

Incluye compatibilidad con refresh_calendar y garantiza una barra de acciones
visible para confirmar reemplazos después de buscar candidatos.
"""
import tkinter as tk
from tkinter import ttk
from giro_supervisores_final import GiroApp

if not hasattr(GiroApp, "refresh_calendar"):
    GiroApp.refresh_calendar = GiroApp.show_calendar


def _install_replacement_action_bar(app):
    """Reemplaza botones antiguos por una barra de confirmación siempre visible."""
    tab = app.tab_abs
    # Elimina cualquier botón de confirmación creado por versiones anteriores.
    for child in list(tab.winfo_children()):
        if isinstance(child, ttk.Button):
            try:
                if str(child.cget("text")).upper().startswith("CONFIRMAR REEMPLAZO"):
                    child.destroy()
            except tk.TclError:
                pass

    bar = ttk.Frame(tab)
    bar.pack(fill="x", side="bottom", pady=(4, 0))

    ttk.Label(
        bar,
        text="1) Seleccioná una fila PENDIENTE  →  2) Confirmá el reemplazo",
        font=("Segoe UI", 10, "bold")
    ).pack(side="left", padx=8)

    ttk.Button(
        bar,
        text="✓  CONFIRMAR REEMPLAZO",
        style="Accent.TButton",
        command=app.confirm_replacement
    ).pack(side="right", padx=8, pady=4)

    ttk.Button(
        bar,
        text="VER HISTORIAL",
        command=app.show_history
    ).pack(side="right", padx=8, pady=4)

    app.abs_confirm_bar = bar


def main():
    root = tk.Tk()
    app = GiroApp(root)
    _install_replacement_action_bar(app)
    app.status.set("Listo. La confirmación de reemplazos está disponible.")
    root.mainloop()


if __name__ == "__main__":
    main()
