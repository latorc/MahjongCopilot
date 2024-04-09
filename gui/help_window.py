""" Help Window"""

from typing import Callable
import webbrowser
import tkinter as tk
from tkinter import font
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from common.log_helper import LOGGER
from common.settings import Settings
from common.utils import WEBSITE
from updater import Updater, UpdateStatus
from .utils import font_normal


class HelpWindow(tk.Toplevel):
    """ dialog window for help information and update """
    def __init__(self, parent:tk.Frame, st:Settings, updater:Updater):
        super().__init__(parent)
        self.st = st            # Settings object
        self.updater = updater
        
        self.title(st.lan().HELP)
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f'+{parent_x+10}+{parent_y+10}')
        self.geometry("600x500")  # Set the window size
        self.resizable(False, False)

        # Scrollable Text Widget for help info
        self.textbox = ScrolledText(self, wrap=tk.WORD, font=font_normal(12), height=15)
        self.textbox.pack(padx=10, pady=10, side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.textbox.tag_configure("title", font=font.Font(family="Microsoft YaHei", size=20, weight="bold"))
        firstline = st.lan().APP_TITLE + f" v{self.updater.local_version}" + "\n"
        self.textbox.insert(tk.END, firstline, "title")
        self.textbox.insert(tk.END, st.lan().HELP_STR)
        self.textbox.configure(state='disabled')  # Make the text read-only

        self.box = tk.Frame(self, height=40)
        self.box.pack(expand=True, fill=tk.X)
        col_widths = [100,300,100]
        for idx, width in enumerate(col_widths):
            self.box.grid_columnconfigure(idx, minsize=width)
        
        # Updater
        self.update_button = ttk.Button(self.box, text=st.lan().CHECK_FOR_UPDATE, state=tk.DISABLED, width=16)
        self.update_button.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)

        self.update_str_var = tk.StringVar(value="")
        self.update_label = ttk.Label(self.box, textvariable=self.update_str_var,width=20)
        self.update_label.grid(row=0, column=1, sticky=tk.NSEW, padx=10, pady=10)
        self.update_cmd:Callable = lambda: None
        
        # OK Button
        self.ok_button = ttk.Button(self.box, text="OK", command=self._on_close, width=10)
        self.ok_button.grid(row=0, column=2, sticky=tk.NSEW, padx=10, pady=10)
        
        # Link
        def open_link():
            webbrowser.open(WEBSITE + r'/?tab=readme-ov-file#%E9%BA%BB%E5%B0%86-copilot--mahjong-copilot')
        label = tk.Label(self, text=WEBSITE, fg="blue", cursor="hand2")
        label.pack(padx=5, pady=5, side=tk.LEFT)
        label.bind("<Button-1>", lambda event: open_link())
        
        self._refresh_ui()
    
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
        match self.updater.update_status:
            case UpdateStatus.NONE:
                self.update_str_var.set("")
                self._check_for_update()
            case UpdateStatus.CHECKING:
                self.update_str_var.set(lan.CHECKING_UPDATE)
            case UpdateStatus.NO_UPDATE:
                self.update_str_var.set(lan.NO_UPDATE_FOUND)
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
            case UpdateStatus.OK:
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
