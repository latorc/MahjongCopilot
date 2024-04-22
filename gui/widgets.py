""" Custom widgets for GUI"""
from pathlib import Path
from typing import Callable
import tkinter as tk
from tkinter import ttk
import time

from common.log_helper import LOGGER
from common.utils import sub_file, Folder
from .utils import GUI_STYLE, add_hover_text

class ToggleSwitch(tk.Frame):
    """ Toggle button widget"""
    def __init__(self, master, text:str, height:int, font_size:int = 12, command:Callable=None):
        """ Create a toggle switch button
        Params:
            master: parent widget
            text: text on the button
            height: widget height
            font_size: font size
            command: callback function when button is clicked"""
        super().__init__(master, height=height,width=height)
        self.pack_propagate(False)
        
        # Load images for on and off states
        img_ht = height*0.4
        img_on = tk.PhotoImage(file=sub_file(Folder.RES,'switch_on.png'))
        img_off = tk.PhotoImage(file=sub_file(Folder.RES,'switch_off.png'))
        img_mid = tk.PhotoImage(file=sub_file(Folder.RES,'switch_mid.png'))
        self.img_on = img_on.subsample(int(img_on.height()/img_ht), int(img_on.height()/img_ht))
        self.img_off = img_off.subsample(int(img_off.height()/img_ht), int(img_off.height()/img_ht))
        self.img_mid = img_mid.subsample(int(img_mid.height()/img_ht), int(img_mid.height()/img_ht))
        
        # Set initial state
        self.is_on = False
        self.img_label = tk.Label(self, image=self.img_off)
        self.img_label.pack(side="top", pady=(0, 10))
        font = GUI_STYLE.font_normal(size=font_size)
        self.text_label = tk.Label(self, text=text, font=font)
        self.text_label.pack(side="top")
        if command:
            self.command = command
            self.img_label.bind("<Button-1>", self._on_click)
        else:
            self.command = None

        # Bind enter and leave events for highlighting
        self.default_background = self.img_label.cget("background")
        self.img_label.bind("<Enter>", self._on_enter)
        self.img_label.bind("<Leave>", self._on_leave)
        

    def switch_on(self):
        """ switch on the button"""
        if not self.is_on:
            # LOGGER.debug("Turning on switch %s",self.text_label.cget("text"))
            self.is_on = True
            self.img_label.config(image=self.img_on)
            

    def switch_off(self):
        """ Switch off the button"""
        if self.is_on:
            # LOGGER.debug("Turning off switch %s",self.text_label.cget("text"))
            self.is_on = False
            self.img_label.config(image=self.img_off)
            

    def switch_mid(self):
        """ Switch to middle state"""
        self.img_label.config(image=self.img_mid)
        
        
    def _on_click(self, _event=None):
        self.command()
        
        
    def _on_enter(self, _event=None):
        """Highlight the label when mouse enters."""
        self.img_label.config(background="light blue")
        

    def _on_leave(self, _event=None):
        """Remove highlight from the label when mouse leaves."""
        self.img_label.config(background=self.default_background)  # Revert to original style


class Timer(tk.Frame):
    """ A timer widget in which user can input hh:mm:ss, and start timing """
    START="⏱"
    STOP="■"
    def __init__(self, master: tk.Frame, height: int, font_size:int=10, hover_text:str=None):
        super().__init__(master, height=height)
        self.configure(height=height)
        self.pack_propagate(False)

        # Time setup
        self.font_size:int = font_size
        self.hover_text:str = hover_text
        self.callback:Callable = None
        self.timer_running:bool = False
        self.timer_id = None
        self.stop_time:float = None

        # Variables for time
        self.hour_var = tk.StringVar(value="01")
        self.minute_var = tk.StringVar(value="00")
        self.second_var = tk.StringVar(value="00")

        # Frame for entries and labels
        self.frame_top = tk.Frame(self)
        self.frame_top.grid(row=0, column=0, sticky=tk.N, padx=(0, 0), pady=(0, 0))
        self.pack_args = {'side': tk.LEFT, 'padx': (0, 0), 'pady': (1, 1)}    # pack args
        # Setup each entry
        self.entries:list[tk.Entry] = []
        self._setup_entry(self.hour_var, 23)
        tk.Label(self.frame_top, text=":", font=GUI_STYLE.font_normal(size=self.font_size), width=1).pack(**self.pack_args)
        self._setup_entry(self.minute_var, 59)
        tk.Label(self.frame_top, text=":", font=GUI_STYLE.font_normal(size=self.font_size), width=1).pack(**self.pack_args)
        self._setup_entry(self.second_var, 59)

        # Start/Stop button
        self.the_btn = tk.Button(
            self, text=Timer.START, font=GUI_STYLE.font_normal("Segoe UI Emoji",size=self.font_size),
            command=self._toggle_timer, width=6, padx=1, pady=1)
        self.the_btn.grid(row=1, column=0, sticky=tk.N, padx=(1, 1),pady=(1, 1))
        if self.hover_text:
            add_hover_text(self.the_btn, self.hover_text)
            

    def set_callback(self, callback:Callable):
        """ Set callback function to be called when timer is stopped"""
        self.callback = callback
        
    
    def _setup_entry(self, var:tk.StringVar, max_val: int):
        """ Helper function to setup each time entry field. """
        def validate_time(value):
            """ Validate time input; reset to '00' if invalid. """
            try:
                val = int(value)
                if 0 <= val <= max_val:
                    self.after_idle(lambda: var.set(f"{val:02}"))
                    return True
                else:
                    new_val = min(max(max_val, 0), val)
                    self.after_idle(lambda: var.set(f"{new_val:02}"))
                    return False
            except:     # pylint: disable=bare-except
                self.after_idle(lambda: var.set("00"))
                return False
        
        entry = tk.Entry(
            self.frame_top, textvariable=var, 
            validatecommand=(self.register(validate_time), '%P'), validate='focusout',
            font=GUI_STYLE.font_normal(size=self.font_size), width=2, justify=tk.CENTER, 
        )
        entry.pack(**self.pack_args)
        self.entries.append(entry)


    def _toggle_timer(self):
        if self.timer_running:
            self._stop_timer()
        else:
            self._start_timer()
            

    def _start_timer(self):
        self.timer_running = True
        self.the_btn.config(text=Timer.STOP)
        hours = int(self.hour_var.get())
        minutes = int(self.minute_var.get())
        seconds = int(self.second_var.get())
        LOGGER.info("Timer set %d:%d:%d", hours, minutes, seconds)
        self.stop_time = time.time() + hours * 3600 + minutes * 60 + seconds
        for e in self.entries:
            e.configure(state=tk.DISABLED)
        add_hover_text(self.the_btn, Timer.STOP)
        self._run_timer()
        

    def _run_timer(self):
        """ run timer and update the time display"""
        if self.timer_running and self.stop_time is not None:
            remaining_time = int(self.stop_time - time.time())
            if remaining_time > 0:
                hours = remaining_time // 3600
                minutes = (remaining_time % 3600) // 60
                seconds = remaining_time % 60
                self.hour_var.set(f"{hours:02}")
                self.minute_var.set(f"{minutes:02}")
                self.second_var.set(f"{seconds:02}")
                self.timer_id = self.after(100, self._run_timer)
            else:   # time is up
                self._clear_time()
                if self.callback:   
                    self.callback()                
                self._stop_timer()
                

    def _clear_time(self):
        self.hour_var.set("01")
        self.minute_var.set("00")
        self.second_var.set("00")
        
    
    def _stop_timer(self):
        if self.timer_id is not None:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self.timer_running = False
        self.the_btn.config(text=Timer.START)
        for e in self.entries:
            e.configure(state=tk.NORMAL)
        self.stop_time = None
        if self.hover_text:
            add_hover_text(self.the_btn, self.hover_text)
        LOGGER.info("Timer stopped.")
        

class ToolBar(tk.Frame):
    """ Tool bar for buttons"""
    def __init__(self, master, height:int=60):
        super().__init__(master)
        self.height = height
        self._hover_text:tk.Label = None
    
    
    def add_button(self, text:str, img_file:str, command) -> tk.Button:
        """ Add a button on toolbar"""        
        img = tk.PhotoImage(file = Path(Folder.RES) / img_file)
        img = img.subsample(int(img.width()/self.height), int(img.height()/self.height))
        btn = tk.Button(self, image=img, width=self.height, height=self.height, command=command)
        btn.image = img  # Keep a reference to prevent image from being garbage collected
        btn.img_file = img_file
        btn.pack(side=tk.LEFT, padx=4, pady=4)

        add_hover_text(btn, text)
        return btn
    
    
    def set_img(self, btn:tk.Button, img_file:str):
        """ Replace button image"""
        if btn.img_file == img_file:
            return
        img = tk.PhotoImage(file = Path(Folder.RES) / img_file)
        img = img.subsample(int(img.width()/self.height), int(img.height()/self.height))
        btn.config(image=img)
        btn.image = img  # Keep a reference
        btn.img_file = img_file
        
    
    def add_sep(self):
        """ add a vertical separator bar """
        separator = ttk.Separator(self, orient=tk.VERTICAL)
        separator.pack(side=tk.LEFT, fill='y', expand=False,padx=5)
    

class StatusBar(tk.Frame):
    """ Status bar with multiple columns"""
    def __init__(self, master, n_cols:int):
        super().__init__(master, highlightbackground='gray', highlightthickness=0)
        self.n_cols = n_cols
        self.columns:list[tk.Frame] = []
        # Style
        style = ttk.Style(self)
        GUI_STYLE.set_style_normal(style)

        for i in range(n_cols):
            column = self._create_column(i)
            self.columns.append(column)


    def _create_column(self, index:int) -> tk.Frame:
         # Background color for the column
        if index < self.n_cols - 1:
            column_frame = tk.Frame(self, highlightbackground='gray', highlightthickness=1)
            column_frame.pack(side=tk.LEFT, padx=1, pady=1, expand=False)
        else:
            column_frame = tk.Frame(self, highlightbackground='gray', highlightthickness=1)
            column_frame.pack(side=tk.LEFT, padx=1, pady=1, expand=True, fill=tk.X)

        # Label with icon and text
        label = ttk.Label(column_frame, text=f'Column {index+1}', compound='left')  # Background color for label
        # label.image = icon  # Retain a reference to the image to prevent garbage collection
        label.image_file = "placeholder"
        label.pack(side=tk.LEFT, anchor='w')
        column_frame.label = label

        return column_frame

    
    def update_column(self, index:int, text:str, icon_path:str=None):
        """ Update column's text and icon """
        if not 0 <= index < len(self.columns):
            return
        
        label:ttk.Label = self.columns[index].label
        label.config(text=text)
        if icon_path is not None and label.image_file != icon_path:
            # Load new icon
            new_icon = tk.PhotoImage(file=icon_path)
            new_icon = new_icon.subsample(
                int(new_icon.height() / GUI_STYLE.std_font_size / 1.3333),
                int(new_icon.height() / GUI_STYLE.std_font_size / 1.3333))
            label.config(image=new_icon)
            label.image = new_icon      # keep a reference to avoid garbage collection
            label.image_file = icon_path
