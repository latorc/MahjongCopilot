""" GUI common/utility functions"""
import tkinter as tk
from tkinter import ttk, font
from PIL import Image, ImageDraw, ImageFont, ImageTk

from common.mj_helper import MJAI_TILE_2_UNICODE, ActionUnicode


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
        

def crop_image_from_top_left(image:Image, width, height):
    # Get the size of the original image
    original_width, original_height = image.size
    
    # Calculate the coordinates of the cropping box
    left = 0
    top = 0
    right = min(original_width, width)
    bottom = min(original_height, height)
    
    # Crop the image
    cropped_image = image.crop((left, top, right, bottom))    
    return cropped_image

def text_to_image(size:int, text:str, width:int=800, height:int=600):
    """ create image based on the text content"""
    
    # draw emojis and regular text in different fonts
    ft_emj = ImageFont.truetype(font="seguiemj.ttf", size=size)
    ft_txt = ImageFont.truetype(font="msyh.ttf", size=size)
    line_spacing = int(size/2)
    pad_x = int(size/2)
    pad_y = int(size/2)
    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)   

    cur_x = pad_x
    cur_y = pad_y + line_spacing
    
    # Create the image with calculated dimensions
    im = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(im)
    
    # draw text each line and each character, record line width and total height
    max_width = 1
    lines = text.split("\n")
    for l in lines:
        for c in l:
            if c in MJAI_TILE_2_UNICODE.values():
                ft = ft_emj
            else:
                ft = ft_txt
            bbox = dummy_draw.textbbox((0, 0), c, font=ft, embedded_color=True, spacing=line_spacing)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.text((cur_x,cur_y), c, font=ft, embedded_color=True, anchor="lm", fill="black", spacing=line_spacing)
            cur_x += text_w
        max_width = max(cur_x,max_width)
        cur_x = pad_x
        cur_y += size + line_spacing
        
    # crop image to fit the text
    max_width += pad_x
    max_height = cur_y - line_spacing   # mid > top    
    im = crop_image_from_top_left(im, max_width, max_height)

    return ImageTk.PhotoImage(im)


GUI_STYLE = GuiStyle()
