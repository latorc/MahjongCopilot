""" GUI common/utility functions"""
from tkinter import ttk, font
import tkinter as tk

class GuiStyle:
    """ GUI Style Class"""
    def __init__(self, std_font_size:int=12):
        self.std_font_size = std_font_size
        self.font_size = std_font_size
        self.dpi_scale:float = 1.0
        

    def set_style_normal(self, style:ttk.Style):
        """ Set style for ttk widgets"""
        style.configure("TLabel", font=("Microsoft YaHei", self.font_size))
        style.configure(
            "TButton",
            background="#4CAF50", foreground="black",
            font=("Microsoft YaHei", self.font_size),
            relief="raised",
            borderwidth=2,
            )
        
    
    def font_normal(self, family:str=None, size:int=None):
        """ return normal font for gui/widgets"""
        if not family:
            family = "Microsoft YaHei"
        if not size:
            size = self.font_size
        else:
            size = int(size / self.dpi_scale)        
        return (family, size)
    

    def set_dpi_scaling(self, scale:float=1.0):
        """ set dpi scaling, change font size accordingly"""
        self.dpi_scale = scale
        self.font_size = int(self.std_font_size / scale)


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
        

GUI_STYLE = GuiStyle()
