""" Help Window for tkinter GUI"""

from typing import Callable
import tkinter as tk
from tkinter import ttk, messagebox
from tkhtmlview import HTMLScrolledText

from common.log_helper import LOGGER
from common.settings import Settings
from updater import Updater, UpdateStatus
from .utils import GUI_STYLE


class HelpWindow(tk.Toplevel):
    """ dialog window for help information and update """
    def __init__(self, parent:tk.Frame, st:Settings, updater:Updater):
        super().__init__(parent)
        self.st = st            # Settings object
        self.updater = updater
        
        title_str = f"{st.lan().HELP} {st.lan().APP_TITLE} v{self.updater.local_version}"
        self.title(title_str)
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f'+{parent_x+10}+{parent_y+10}')
        self.win_size = (750, 700)
        self.geometry(f"{self.win_size[0]}x{self.win_size[1]}")  # Set the window size
        # self.resizable(False, False)

        self.html_text:str = None
        self.html_box = HTMLScrolledText(
            self, html=st.lan().HELP+st.lan().LOADING,
            wrap=tk.CHAR, font=GUI_STYLE.font_normal(), height=25,
            state=tk.DISABLED)
        self.html_box.pack(padx=10, pady=10, side=tk.TOP, fill=tk.BOTH, expand=True)        

        self.frame_bot = tk.Frame(self, height=30)
        self.frame_bot.pack(expand=True, fill=tk.X, padx=10, pady=10)
        col_widths = [int(w*self.win_size[0]) for w in (0.1, 0.4, 0.1)]
        for idx, width in enumerate(col_widths):
            self.frame_bot.grid_columnconfigure(idx, minsize=width, weight=1)
        
        # Updater button
        self.update_button = ttk.Button(self.frame_bot, text=st.lan().CHECK_FOR_UPDATE, state=tk.DISABLED, width=16)
        self.update_button.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)
        # label
        self.update_str_var = tk.StringVar(value="")
        self.update_label = ttk.Label(self.frame_bot, textvariable=self.update_str_var)
        self.update_label.grid(row=0, column=1, sticky=tk.NSEW, padx=10, pady=10)
        self.update_cmd:Callable = lambda: None
        # OK Button
        self.ok_button = ttk.Button(self.frame_bot, text="OK", command=self._on_close, width=8)
        self.ok_button.grid(row=0, column=2, sticky=tk.NSEW, padx=10, pady=10)
        
        self.after_idle(self._refresh_ui)
              
            
    def _check_for_update(self):
        LOGGER.info("Checking for update.")
        self.update_button.configure(state=tk.DISABLED)
        self.updater.check_update()
        
    
    def _download_update(self):
        LOGGER.info("Download and unzip update.")
        self.update_button.configure(state=tk.DISABLED)
        self.updater.prepare_update()
        
        
    def _start_update(self):
        LOGGER.info("Starting update process. will kill program and restart.")
        self.update_button.configure(state=tk.DISABLED)
        if messagebox.askokcancel(self.st.lan().START_UPDATE, self.st.lan().UPDATE_PREPARED):
            self.updater.start_update()
            
    
    def _refresh_ui(self):
        lan = self.st.lan()
        # Update html text if available
        if not self.html_text:  
            if self.updater.help_html:
                self.html_text = self.updater.help_html
                self.html_box.set_html(self.html_text)
        
        # update button and status
        match self.updater.update_status:
            case UpdateStatus.NONE:
                self.update_str_var.set("")
                self._check_for_update()
            case UpdateStatus.CHECKING:
                self.update_str_var.set(lan.CHECKING_UPDATE)
            case UpdateStatus.NO_UPDATE:
                self.update_str_var.set(lan.NO_UPDATE_FOUND + f" v{self.updater.web_version}")
                self.update_button.configure(
                    text = lan.CHECK_FOR_UPDATE,
                    state=tk.NORMAL,
                    command=self._check_for_update)
            case UpdateStatus.NEW_VERSION:
                self.update_str_var.set(lan.UPDATE_AVAILABLE + f" v{self.updater.web_version}")
                self.update_button.configure(
                    text=lan.DOWNLOAD_UPDATE,
                    state=tk.NORMAL,
                    command=self._download_update
                    )
                self.update_cmd = self.updater.prepare_update
            case UpdateStatus.DOWNLOADING:
                self.update_str_var.set(lan.DOWNLOADING + f"  {self.updater.dl_progress}")
            case UpdateStatus.UNZIPPING:
                self.update_str_var.set(lan.UNZIPPING)
            case UpdateStatus.PREPARED:
                self.update_str_var.set(lan.UPDATE_PREPARED)
                self.update_button.configure(
                    text=lan.START_UPDATE,
                    state=tk.NORMAL,
                    command = self.updater.start_update)
            case UpdateStatus.ERROR:
                self.update_str_var.set(str(self.updater.update_exception))
                self.update_button.configure(
                    text=lan.CHECK_FOR_UPDATE,
                    state=tk.NORMAL,
                    command=self._check_for_update)
            case _:
                pass
            
        self.after(100, self._refresh_ui)
        
    
    def _on_close(self):
        self.destroy()        
    
