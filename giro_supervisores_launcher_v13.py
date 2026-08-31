# Giro de Supervisores - Nelson Casella
# v13: modernizacion EXCLUSIVAMENTE VISUAL sobre v12.
# No modifica generacion, equidad, calendario funcional, reemplazos, historial,
# persistencia mensual ni exportacion Excel.

import tkinter as tk
from tkinter import ttk

from giro_supervisores_launcher_v12 import GiroApp


# Paleta visual alineada con Nelson Casella Software.
BG = '#F4F7F6'
SURFACE = '#FFFFFF'
SURFACE_ALT = '#F8FAF9'
TEXT = '#17211D'
MUTED = '#65736C'
BORDER = '#DDE5E1'
DARK = '#0E1713'
DARK_2 = '#15231D'
ACCENT = '#19B85A'
ACCENT_HOVER = '#139448'
ACCENT_SOFT = '#E8F8EF'
DANGER = '#C94141'
WARNING = '#C78A17'


_original_build_style = GiroApp.build_style
_original_build_ui = GiroApp.build_ui
_original_show_calendar = GiroApp.show_calendar


def _modern_build_style(self):
    """Capa ttk moderna sin alterar ningun widget funcional."""
    try:
        _original_build_style(self)
    except Exception:
        pass

    self.root.configure(bg=BG)
    style = ttk.Style(self.root)
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass

    # Base
    style.configure('.', font=('Segoe UI', 10), background=BG, foreground=TEXT)
    style.configure('TFrame', background=BG)
    style.configure('Card.TFrame', background=SURFACE)
    style.configure('TLabel', background=BG, foreground=TEXT, font=('Segoe UI', 10))
    style.configure('Muted.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 9))
    style.configure('Title.TLabel', background=BG, foreground=TEXT, font=('Segoe UI Semibold', 22))
    style.configure('Sub.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 10))

    # Tarjetas / grupos
    style.configure('TLabelframe', background=SURFACE, bordercolor=BORDER, relief='solid', borderwidth=1)
    style.configure('TLabelframe.Label', background=SURFACE, foreground=TEXT, font=('Segoe UI Semibold', 10))

    # Botones
    style.configure('TButton',
                    font=('Segoe UI Semibold', 9),
                    padding=(14, 9),
                    background=SURFACE,
                    foreground=TEXT,
                    bordercolor=BORDER,
                    relief='flat')
    style.map('TButton',
              background=[('active', '#EEF3F0'), ('pressed', '#E4EBE7')],
              bordercolor=[('focus', ACCENT), ('active', '#C9D6CF')])

    style.configure('Accent.TButton',
                    font=('Segoe UI Semibold', 9),
                    padding=(16, 10),
                    background=ACCENT,
                    foreground='white',
                    bordercolor=ACCENT,
                    relief='flat')
    style.map('Accent.TButton',
              background=[('active', ACCENT_HOVER), ('pressed', '#0F7D3D')],
              foreground=[('disabled', '#D5EEE0')])

    # Inputs
    style.configure('TEntry', padding=8, fieldbackground=SURFACE, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
    style.configure('TSpinbox', padding=7, fieldbackground=SURFACE, foreground=TEXT,
                    bordercolor=BORDER, arrowcolor=ACCENT)
    style.configure('TCombobox', padding=7, fieldbackground=SURFACE, foreground=TEXT,
                    background=SURFACE, bordercolor=BORDER, arrowcolor=ACCENT)
    style.map('TCombobox', fieldbackground=[('readonly', SURFACE)],
              selectbackground=[('readonly', SURFACE)],
              selectforeground=[('readonly', TEXT)])

    # Radio buttons
    style.configure('TRadiobutton', background=BG, foreground=TEXT, padding=(5, 4))
    style.map('TRadiobutton', foreground=[('active', ACCENT)])

    # Notebook moderno
    style.configure('TNotebook', background=BG, borderwidth=0, tabmargins=(0, 2, 0, 0))
    style.configure('TNotebook.Tab',
                    font=('Segoe UI Semibold', 9),
                    padding=(18, 11),
                    background='#E7ECE9',
                    foreground=MUTED,
                    borderwidth=0)
    style.map('TNotebook.Tab',
              background=[('selected', SURFACE), ('active', '#EEF3F0')],
              foreground=[('selected', ACCENT), ('active', TEXT)])

    # Tablas
    style.configure('Treeview',
                    background=SURFACE,
                    fieldbackground=SURFACE,
                    foreground=TEXT,
                    rowheight=32,
                    borderwidth=0,
                    font=('Segoe UI', 9))
    style.map('Treeview',
              background=[('selected', ACCENT_SOFT)],
              foreground=[('selected', TEXT)])
    style.configure('Treeview.Heading',
                    background=DARK_2,
                    foreground='white',
                    relief='flat',
                    borderwidth=0,
                    padding=(8, 9),
                    font=('Segoe UI Semibold', 9))
    style.map('Treeview.Heading', background=[('active', '#21352B')])

    style.configure('Horizontal.TScrollbar', background='#CBD6D0', troughcolor=BG, bordercolor=BG, arrowcolor=MUTED)
    style.configure('Vertical.TScrollbar', background='#CBD6D0', troughcolor=BG, bordercolor=BG, arrowcolor=MUTED)


def _recolor_classic_children(widget):
    """Moderniza los pocos tk.Frame/tk.Label clasicos creados por la UI base."""
    for child in widget.winfo_children():
        try:
            if isinstance(child, tk.Frame):
                current = child.cget('bg')
                if current == '#172B4D':
                    child.configure(bg=DARK, highlightthickness=0)
                elif current in ('SystemButtonFace', '#d9d9d9'):
                    child.configure(bg=BG)
            elif isinstance(child, tk.Label):
                bg = child.cget('bg')
                if bg == '#172B4D':
                    txt = child.cget('text')
                    if 'GIRO DE SUPERVISORES' in txt:
                        child.configure(bg=DARK, fg='white', font=('Segoe UI Semibold', 25))
                    else:
                        child.configure(bg=DARK, fg='#A9B9B0', font=('Segoe UI', 10))
        except Exception:
            pass
        _recolor_classic_children(child)


def _modern_build_ui(self):
    """Construye exactamente la UI existente y luego aplica presentacion moderna."""
    _original_build_ui(self)
    _recolor_classic_children(self.root)

    # Mejor respiracion visual general sin alterar jerarquia ni callbacks.
    try:
        self.nb.pack_configure(padx=20, pady=(18, 12))
    except Exception:
        pass

    # Zebra muy suave en las tablas existentes.
    for name in ('agent_tree', 'schedule_tree', 'abs_tree'):
        tree = getattr(self, name, None)
        if tree is not None:
            try:
                tree.tag_configure('odd', background=SURFACE)
                tree.tag_configure('even', background=SURFACE_ALT)
            except Exception:
                pass


def _modern_show_calendar(self):
    """Mantiene toda la logica v9/v12 y solo mejora la apariencia de las tarjetas-dia."""
    out = _original_show_calendar(self)
    frame = getattr(self, 'cal_frame', None)
    if frame is None:
        return out

    # Los dias son tk.Button en la implementacion existente. Solo se cambia su estilo.
    for child in frame.winfo_children():
        if not isinstance(child, tk.Button):
            continue
        try:
            bg = child.cget('bg')
            # Conservamos los colores semanticos existentes, con borde/relieve moderno.
            child.configure(
                relief='flat',
                bd=0,
                highlightthickness=1,
                highlightbackground=BORDER,
                highlightcolor=ACCENT,
                font=('Segoe UI Semibold', 10),
                cursor='hand2',
                padx=4,
                pady=4,
            )
            # Refinar neutro sin tocar estados de licencia/disponibilidad/feriado.
            if str(bg).lower() in ('#f3f5f7', 'systembuttonface'):
                child.configure(bg=SURFACE, activebackground=ACCENT_SOFT, fg=TEXT)
        except Exception:
            pass
    return out


GiroApp.build_style = _modern_build_style
GiroApp.build_ui = _modern_build_ui
GiroApp.show_calendar = _modern_show_calendar


if __name__ == '__main__':
    root = tk.Tk()
    root.configure(bg=BG)
    root.option_add('*tearOff', False)
    app = GiroApp(root)
    root.mainloop()
