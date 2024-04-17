""" GUI common/utility functions"""
from tkinter import ttk, font
import tkinter as tk

def set_style_normal(style:ttk.Style, font_size:int=12):
    """ Set style for ttk widgets"""
    style.configure("TLabel", font=("Microsoft YaHei", font_size))
    style.configure(
        "TButton",
        background="#4CAF50", foreground="black",
        font=("Microsoft YaHei", font_size),
        relief="raised",
        borderwidth=2
        )

def font_normal(size:int=12):
    """ return normal font size"""
    return font.Font(family="Microsoft YaHei", size=size)


def add_hover_text(widget:tk.Widget, text:str):
    """ Add a hover string label when mouse is over the widget"""
    widget.bind("<Enter>", lambda event: _on_hover(widget, text))
    widget.bind("<Leave>", lambda event: _on_leave_hover(widget))
    
def _on_hover(wdg:tk.Widget, text:str):
    # display a hover label with text
    toplvl = wdg.winfo_toplevel()
    wdg.original_bg = wdg.cget("background")
    wdg.configure(background="light blue")
    wdg.hover_text = tk.Label(toplvl, text=text, bg="lightyellow", highlightbackground="black", highlightthickness=1)
    x = wdg.winfo_rootx() - toplvl.winfo_rootx() + wdg.winfo_width()
    y = wdg.winfo_rooty() - toplvl.winfo_rooty() + wdg.winfo_height() //2
    wdg.hover_text.place(x=x, y=y, anchor=tk.W)

def _on_leave_hover(wdg:tk.Widget):
    # destroy the hover label
    if hasattr(wdg, "hover_text"):
        wdg.hover_text.destroy()
    if hasattr(wdg, "original_bg"):
        wdg.configure(background=wdg.original_bg)