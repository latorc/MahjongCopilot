""" GUI common/utility functions"""
from tkinter import ttk, font

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
