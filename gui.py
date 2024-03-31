"""
Main GUI implementation for Mahjong Copilot
The GUI is a desktop app based on tkinter library
GUI functions: controlling browser settings, displaying AI guidance info, game status
"""

import os
from pathlib import Path
from typing import Callable
import tkinter as tk
from tkinter import font
from tkinter import ttk, messagebox

from bot_manager import BotManager
import utils
import log_helper
from log_helper import LOGGER
from settings import Settings
import mj_helper
from lan_strings import LAN_OPTIONS, LanStrings

RES_FOLDER = 'resources'

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

class MainGUI(tk.Tk):
    """ Main GUI Window"""
    def __init__(self, setting:Settings, bot_manager:BotManager):
        super().__init__()
        self.bot_manager = bot_manager
        self.settings = setting
        self.lan_strings:LanStrings = self.settings.lan()

        icon = tk.PhotoImage(file=Path(RES_FOLDER)/'icon.png')
        self.iconphoto(True, icon)
        # create window widgets
        self._create_widgets()

        self.bot_manager.start()        # start the main program
        self.gui_update_delay = 100     # in ms
        self._update_gui_info()          # start updating gui info

    def _create_widgets(self):
        # Styling
        style = ttk.Style(self)
        set_style_normal(style)

        # Main window properties
        self.title(self.lan_strings.APP_TITLE)
        self.geometry('700x500')
        self.minsize(500,400)

        # container for grid control
        self.grid_frame = tk.Frame(self)
        self.grid_frame.pack(fill=tk.BOTH, expand=True)
        self.grid_frame.grid_columnconfigure(0, weight=1)
        cur_row = 0

        # toolbar frame (row 0)
        self.toolbar = ToolBar(self.grid_frame, 75)
        self.toolbar.grid(row=cur_row,column=0,sticky='ew',padx=5)
        self.grid_frame.grid_rowconfigure(cur_row, weight=0)
        cur_row += 1
        # Buttons in toolbar
        self.btn_start_browser = self.toolbar.add_button(
            self.lan_strings.START_BROWSER, 'majsoul.png', self._on_btn_start_browser_clicked)
        self.toolbar.add_sep()
        self.switch_overlay = ToggleSwitch(self.toolbar, self.lan_strings.WEB_OVERLAY, 75, command=self._on_switch_hud_clicked)
        self.switch_overlay.pack(side=tk.LEFT, padx=4, pady=4)
        self.switch_autoplay = ToggleSwitch(self.toolbar, self.lan_strings.AUTOPLAY, 75, command=self._on_switch_autoplay_clicked)
        self.switch_autoplay.pack(side=tk.LEFT, padx=4, pady=4)
        self.toolbar.add_sep()
        self.toolbar.add_button(self.lan_strings.SETTINGS, 'settings.png', self._on_btn_settings_clicked)
        self.toolbar.add_button(self.lan_strings.OPEN_LOG_FILE, 'log.png', self._on_btn_log_clicked)
        self.toolbar.add_button(self.lan_strings.HELP, 'help.png', self._on_btn_help_clicked)
        self.toolbar.add_sep()
        self.toolbar.add_button(self.lan_strings.EXIT, 'exit.png', self._on_btn_exit_clicked)

        # AI guidance
        _label = ttk.Label(self.grid_frame, text=self.lan_strings.AI_OUTPUT)
        _label.grid(row=cur_row, column=0, sticky='ew', padx=5, pady=2)
        self.grid_frame.grid_rowconfigure(cur_row, weight=0)
        cur_row += 1

        self.text_ai_guide = tk.Text(
            self.grid_frame,
            state=tk.DISABLED,
            font=font.Font(family="Segoe UI Emoji", size=25, weight="bold"),
            height=5,
            relief=tk.SUNKEN,
            padx=5,
            pady=5
            )
        self.text_ai_guide.grid(row=cur_row, column=0, sticky='ew', padx=5, pady=5)
        self.grid_frame.grid_rowconfigure(cur_row, weight=1)
        cur_row += 1

        # game info
        _label = ttk.Label(self.grid_frame, text=self.lan_strings.GAME_INFO)
        _label.grid(row=cur_row, column=0, sticky='ew', padx=5, pady=2)
        self.grid_frame.grid_rowconfigure(cur_row, weight=0)
        cur_row += 1

        self.text_state = tk.Text(
            self.grid_frame,
            state=tk.DISABLED,
            height=2,
            font=font.Font(family="Segoe UI Emoji", size=25, weight="bold")
            )
        self.text_state.grid(row=cur_row, column=0, sticky='ew', padx=5, pady=5)
        self.grid_frame.grid_rowconfigure(cur_row, weight=1)
        cur_row += 1

        # status bar
        self.status_bar = StatusBar(self.grid_frame, 4)
        self.status_bar.grid(row=cur_row, column=0, sticky='ew', padx=0, pady=0)
        self.grid_frame.grid_rowconfigure(cur_row, weight=0)
        cur_row += 1

    def _on_btn_start_browser_clicked(self):
        self.btn_start_browser.config(state=tk.DISABLED)
        self.bot_manager.start_browser()

    def _on_switch_hud_clicked(self):
        self.switch_overlay.switch_mid()
        if not self.bot_manager.is_overlay_enabled():
            self.bot_manager.enable_overlay()
        else:
            self.bot_manager.disable_overlay()
            
    def _on_switch_autoplay_clicked(self):
        self.switch_autoplay.switch_mid()
        if self.bot_manager.is_automation_enabled():
            self.bot_manager.disable_automation()
        else:
            self.bot_manager.enable_automation()
            

    def _on_btn_log_clicked(self):
        # LOGGER.debug('Open log')
        os.startfile(log_helper.log_file_name())

    def _on_btn_settings_clicked(self):
        # open settings dialog
        settings_window = SettingsWindow(self,self.settings)
        settings_window.transient(self)
        settings_window.grab_set()
        self.wait_window(settings_window)
        if settings_window.GUI_need_reload:
            self.reload_gui()

    def _on_btn_help_clicked(self):
        # open help dialog        
        messagebox.showinfo(self.lan_strings.HELP, self.lan_strings.HELP_STR)
    
    def _on_btn_exit_clicked(self):
        # Exit the app
        # pop up that confirm if the user really wants to quit
        if messagebox.askokcancel(self.lan_strings.EXIT, self.lan_strings.EIXT_CONFIRM):
            self.bot_manager.stop(True)
            self.quit()
            
    def reload_gui(self):
        """ Clear UI compontes and rebuid widgets"""
        lan_code = self.settings.language
        self.lan_strings = LAN_OPTIONS[lan_code]
        self.title(self.lan_strings.APP_TITLE)
        
        for widget in self.winfo_children():
            widget.destroy()
        self._create_widgets()
        

    def _update_gui_info(self):
        if not self.bot_manager.browser.is_running():
            self.btn_start_browser.config(state=tk.NORMAL)
        else:
            self.btn_start_browser.config(state=tk.DISABLED)
            
        # switch overlay
        if self.bot_manager.is_overlay_enabled():
            self.switch_overlay.switch_on()
        else:
            self.switch_overlay.switch_off()
            
        # switch autoplay 
        if self.bot_manager.is_automation_enabled():
            self.switch_autoplay.switch_on()
        else:
            self.switch_autoplay.switch_off()

        # Update Reaction
        self.text_ai_guide.config(state=tk.NORMAL)
        self.text_ai_guide.delete('1.0', tk.END)
        pending_reaction = self.bot_manager.get_pending_reaction()
        # convert this reaction into string
        if pending_reaction:
            action_str, options = mj_helper.mjai_reaction_2_guide(pending_reaction, 3, self.lan_strings)
            self.text_ai_guide.insert(tk.END, f'{action_str}\n')
            for tile_str, weight in options:
                self.text_ai_guide.insert(tk.END, f' {tile_str}  {weight*100:4.0f}%\n')
        self.text_ai_guide.config(state=tk.DISABLED)

        # update state
        gi:mj_helper.GameInfo = self.bot_manager.get_game_info()
        self.text_state.config(state=tk.NORMAL)
        self.text_state.delete('1.0', tk.END)
        if gi and gi.my_tehai:
            tehai = gi.my_tehai
            tsumohai = gi.my_tsumohai
            tehai_str = ''.join(mj_helper.MJAI_TILE_2_UNICODE[t] for t in tehai)
            tsumohai_str = f"{' + ' + mj_helper.MJAI_TILE_2_UNICODE[tsumohai] if tsumohai != '?' else ''}"
            info_str = f"{tehai_str}{tsumohai_str}"
            self.text_state.insert(tk.END, info_str)
        self.text_state.config(state=tk.DISABLED)

        # Update status bar
        if self.bot_manager.is_running():
            self.status_bar.update_column(0, self.lan_strings.MAIN_THREAD, Path(RES_FOLDER)/'green.png')
        else:
            self.status_bar.update_column(0, self.lan_strings.MAIN_THREAD, Path(RES_FOLDER)/'red.png')

        if self.bot_manager.mitm_server.is_running():
            self.status_bar.update_column(1, self.lan_strings.MITM_SERVICE, Path(RES_FOLDER)/'green.png')
        else:
            self.status_bar.update_column(1, self.lan_strings.MITM_SERVICE, Path(RES_FOLDER)/'red.png')

        if self.bot_manager.browser.is_running():
            self.status_bar.update_column(2, self.lan_strings.WEB_CLIENT, Path(RES_FOLDER)/'green.png')
        else:
            self.status_bar.update_column(2, self.lan_strings.WEB_CLIENT, Path(RES_FOLDER)/'gray.png')

        status_str, icon = self._get_status_text_icon(gi)
        self.status_bar.update_column(3, status_str, icon)

        self.after(self.gui_update_delay, self._update_gui_info)     # next update

    def _get_status_text_icon(self, gi:mj_helper.GameInfo) -> tuple[str, str]:
        icon_green = Path(RES_FOLDER)/'green.png'
        icon_red = Path(RES_FOLDER)/'red.png'
        icon_yellow = Path(RES_FOLDER)/'yellow.png'
        icon_gray = Path(RES_FOLDER)/'gray.png'
        icon_ready = Path(RES_FOLDER)/'ready.png'

        bot_exception = self.bot_manager.exception
        if isinstance(bot_exception, utils.ModelFileException):
            return self.lan_strings.MODEL_FILE_ERROR, icon_red
        elif isinstance(bot_exception, Exception):
            return self.lan_strings.MAIN_THREAD_ERROR + str(bot_exception), icon_red
        else:   # no exception in bot manager
            pass

        if self.bot_manager.is_in_game():
            info_str = self.lan_strings.GAME_RUNNING
            if self.bot_manager.is_mjai_error():
                info_str += " - " + self.lan_strings.AI_MODEL_ERROR
                return info_str, icon_yellow

            elif self.bot_manager.is_game_syncing():
                info_str += " - " + self.lan_strings.SYNCING
                return info_str, icon_green

            else:   # game in progress
                if gi and gi.bakaze:
                    info_str += f" - {self.lan_strings.mjai2str(gi.bakaze)} {gi.kyoku} {self.lan_strings.KYOKU} {gi.honba} {self.lan_strings.HONBA}"
                else:
                    info_str += " - " + self.lan_strings.PREPARATION
                return info_str, icon_green
        else:
            info_str = self.lan_strings.READY_FOR_GAME
            return info_str, icon_ready


class ToggleSwitch(tk.Frame):
    """ Toggle button widget"""
    def __init__(self, master, text:str, height:int, font_size:int = 12, command:Callable=None):
        """ Create a toggle switch button
        Params:
            master: parent widget
            text: text on the button
            img_ht: height of the image
            command: callback function when button is clicked"""
        super().__init__(master, height=height,width=height)
        self.pack_propagate(False)
        
        # Load images for on and off states
        img_ht = height*0.4
        img_on = tk.PhotoImage(file=Path(RES_FOLDER)/'switch_on.png')
        img_off = tk.PhotoImage(file=Path(RES_FOLDER)/'switch_off.png')
        img_mid = tk.PhotoImage(file=Path(RES_FOLDER)/'switch_mid.png')
        self.img_on = img_on.subsample(int(img_on.height()/img_ht), int(img_on.height()/img_ht))
        self.img_off = img_off.subsample(int(img_off.height()/img_ht), int(img_off.height()/img_ht))
        self.img_mid = img_mid.subsample(int(img_mid.height()/img_ht), int(img_mid.height()/img_ht))
        
        # Set initial state
        self.is_on = False
        self.img_label = tk.Label(self, image=self.img_off)
        self.img_label.pack(side="top", pady=(0, 10))
        self.text_label = tk.Label(self, text=text, font=("Microsoft YaHei", font_size))
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
        if not self.is_on:
            # LOGGER.debug("Turning on switch %s",self.text_label.cget("text"))
            self.is_on = True
            self.img_label.config(image=self.img_on)
        
    def switch_off(self):
        if self.is_on:
            # LOGGER.debug("Turning off switch %s",self.text_label.cget("text"))
            self.is_on = False
            self.img_label.config(image=self.img_off)
            
    def switch_mid(self):
        self.img_label.config(image=self.img_mid)
        
    def _on_click(self, event=None):
        self.command()        
        
    def _on_enter(self, event=None):
        """Highlight the label when mouse enters."""
        self.img_label.config(background="light blue")

    def _on_leave(self, event=None):
        """Remove highlight from the label when mouse leaves."""
        self.img_label.config(background=self.default_background)  # Revert to original style

class ToolBar(tk.Frame):
    """ Tool bar on top for buttons"""
    def __init__(self, master, height:int=60):
        super().__init__(master)
        self.height = height
        self._hover_text:tk.Label = None
    
    
    def add_button(self, text:str, img_file:str, command) -> tk.Button:
        """ Add a button on toolbar"""
        
        img = tk.PhotoImage(file = Path(RES_FOLDER) / img_file)
        img = img.subsample(int(img.width()/self.height), int(img.height()/self.height))
        btn = tk.Button(
            self,
            text=text,
            image=img,
            width=self.height, height=self.height,
            command=command
        )
        btn.image = img  # Keep a reference to prevent image from being garbage collected
        btn.pack(side=tk.LEFT, padx=4, pady=4)

        btn.bind("<Enter>", lambda event, btn=btn: self._on_button_hover(btn))
        btn.bind("<Leave>", lambda event, btn=btn: self._on_button_leave(btn))
        return btn
    
    def add_sep(self):
        """ add a vertical separator bar """
        separator = ttk.Separator(self, orient=tk.VERTICAL)
        separator.pack(side=tk.LEFT, fill='y', expand=False,padx=5)

    def _on_button_hover(self, btn:tk.Button):
        # change bg color; display a hover text label
        self.original_bg = btn.cget("background")
        btn.configure(background="light blue")
        self._hover_text = tk.Label(self, text=btn.cget("text"),
            bg="lightyellow",highlightbackground="black", highlightthickness=1)
        x = btn.winfo_x() + self.winfo_x() + btn.winfo_width()
        y = btn.winfo_y() + self.winfo_y() + btn.winfo_height() //2
        self._hover_text.place(
            x=x,
            y=y,
            anchor=tk.SW
        )

    def _on_button_leave(self, btn:tk.Button):
        btn.configure(background=self.original_bg)
        self._hover_text.destroy()
    

class StatusBar(tk.Frame):
    """ Status bar with multiple columns"""
    def __init__(self, master, n_cols:int, font_size:int = 12):
        super().__init__(master, highlightbackground='gray', highlightthickness=0)
        self.n_cols = n_cols
        self.font_size = font_size
        self.columns = []

        # Style
        style = ttk.Style(self)
        set_style_normal(style, font_size)

        for i in range(n_cols):
            column = self._create_column(i)
            self.columns.append(column)


    def _create_column(self, index:int):
         # Background color for the column
        if index < self.n_cols - 1:
            column_frame = tk.Frame(self, highlightbackground='gray', highlightthickness=1)
            column_frame.pack(side=tk.LEFT, padx=1, pady=1, expand=False)
        else:
            column_frame = tk.Frame(self, highlightbackground='gray', highlightthickness=1)
            column_frame.pack(side=tk.LEFT, padx=1, pady=1, expand=True, fill=tk.X)

        # Load icon
        default_icon_file = str(Path(RES_FOLDER)/'gray.png')
        icon = tk.PhotoImage(file=default_icon_file)  # Replace "icon.png" with your icon file
        icon_ht = self.font_size * 2
        icon = icon.subsample(int(icon.height()/icon_ht), int(icon.height()/icon_ht))
        # Label with icon and text
        label = ttk.Label(column_frame, image=icon, text=f'Column {index+1}', compound='left')  # Background color for label
        label.image = icon  # Retain a reference to the image to prevent garbage collection
        label.image_file = default_icon_file
        label.pack(side=tk.LEFT, anchor='w')
        column_frame.label = label

        return column_frame

    def update_column(self, index:int, text:str, icon_path:str=None):
        """ Update column's icon and text"""
        if not 0 <= index < len(self.columns):
            return
        
        label:ttk.Label = self.columns[index].label
        label.config(text=text)
        if icon_path is not None and label.image_file != icon_path:
            # Load new icon
            new_icon = tk.PhotoImage(file=icon_path)
            new_icon = new_icon.subsample(int(new_icon.height()/self.font_size/1.3333), int(new_icon.height() / self.font_size / 1.3333))
            label.config(image=new_icon)
            label.image = new_icon      # keep a reference to avoid garbage collection
            label.image_file = icon_path

class SettingsWindow(tk.Toplevel):
    """ Settings dialog window"""
    def __init__(self, parent:tk.Frame, setting:Settings):
        super().__init__(parent)
        self.settings = setting
        self.lan_strings:LanStrings = LAN_OPTIONS[self.settings.language]
        self.title(self.lan_strings.SETTINGS)
        self.geometry('600x400')
        self.resizable(False, False)
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f'+{parent_x+10}+{parent_y+10}')
        
        self.GUI_need_reload:bool = False
        """ Whether a GUI refresh is needed to apply new settings"""

        # Call create_widgets after the window is fully initialized
        self.create_widgets()

    def create_widgets(self):
        """ Create widgets for settings dialog"""
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, minsize=150)
        main_frame.columnconfigure(1, minsize=300)

        # Styling
        style = ttk.Style(self)
        set_style_normal(style)
        cur_row = 0

        # Title:Settings
        label_settings = ttk.Label(main_frame, text=self.lan_strings.SETTINGS_TIPS)
        label_settings.grid(row=cur_row, column=1, sticky="w", padx=(0, 10), pady=(5, 0))

        # auto launch browser
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.lan_strings.AUTO_LAUNCH_BROWSER)
        _label.grid(row=cur_row, column=0, sticky="e", padx=(0, 10), pady=(5, 0))
        self.auto_launch_var = tk.BooleanVar(value=self.settings.auto_launch_browser)
        auto_launch_entry = ttk.Checkbutton(main_frame, variable=self.auto_launch_var)
        auto_launch_entry.grid(row=cur_row, column=1, sticky="w", pady=(5, 0))

        # Select client size
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.lan_strings.CLIENT_SIZE)
        _label.grid(row=cur_row, column=0, sticky="e", padx=(0, 10), pady=(5, 0))
        options = ["1920 x 1080", "1600 x 900", "1280 x 720"]
        setting_size = f"{self.settings.browser_width} x {self.settings.browser_height}"
        self.client_size_var = tk.StringVar(value=setting_size)
        select_menu = ttk.Combobox(main_frame, textvariable=self.client_size_var, values=options, state="readonly")
        select_menu.grid(row=cur_row, column=1, sticky="w", pady=(5, 0))
        
        # majsoul url
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.lan_strings.MAJSOUL_URL)
        _label.grid(row=cur_row, column=0, sticky="e", padx=(0, 10), pady=(5, 0))
        self.ms_url_var = tk.StringVar(value=self.settings.ms_url)
        string_entry = ttk.Entry(main_frame, textvariable=self.ms_url_var)
        string_entry.grid(row=cur_row, column=1, sticky="ew", pady=(5, 0))
        
        # mitm port
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.lan_strings.MITM_PORT)
        _label.grid(row=cur_row, column=0, sticky="e", padx=(0, 10), pady=(5, 0))
        self.mitm_port_var = tk.StringVar(value=self.settings.mitm_port)
        number_entry = ttk.Entry(main_frame, textvariable=self.mitm_port_var, width=10)
        number_entry.grid(row=cur_row, column=1, sticky="w", pady=(5, 0))
        
        # Select language
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.lan_strings.LANGUAGE)
        _label.grid(row=cur_row, column=0, sticky="e", padx=(0, 10), pady=(5, 0))
        options = [v.LANGUAGE_NAME for v in LAN_OPTIONS.values()]
        self.language_var = tk.StringVar(value=LAN_OPTIONS[self.settings.language].LANGUAGE_NAME)
        select_menu = ttk.Combobox(main_frame, textvariable=self.language_var, values=options, state="readonly")
        select_menu.grid(row=cur_row, column=1, sticky="w", pady=(5, 0))

        # Select Model
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.lan_strings.AI_MODEL_FILE)
        _label.grid(row=cur_row, column=0, sticky="e", padx=(0, 10), pady=(5, 0))
        options = utils.list_files(utils.MODEL_FOLDER)
        self.model_var = tk.StringVar(value=self.settings.model_file)
        select_menu = ttk.Combobox(main_frame, textvariable=self.model_var, values=options, state="readonly")
        select_menu.grid(row=cur_row, column=1, sticky="w", pady=(5, 0))

        # Buttons frame
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", fill="x")
        cancel_button = ttk.Button(button_frame, text=self.lan_strings.CANCEL, command=self._on_cancel)
        cancel_button.pack(side="left", padx=20, pady=10)
        save_button = ttk.Button(button_frame, text=self.lan_strings.SAVE, command=self._on_save)
        save_button.pack(side="right", padx=20, pady=10)

    def _on_save(self):
        # Get values from entry fields, validate, and save them
        auto_launch_new = self.auto_launch_var.get()
        size_list = self.client_size_var.get().split(' x ')
        width_new = int(size_list[0])
        height_new = int(size_list[1])
        mitm_port_new = int(self.mitm_port_var.get())
        language_name = self.language_var.get()
        language_new = None
        for code, lan in LAN_OPTIONS.items():
            if language_name == lan.LANGUAGE_NAME:
                language_new = code
                break
        model_new = self.model_var.get()

        if not Settings.valid_mitm_port(mitm_port_new):
            messagebox.showerror("Error", self.lan_strings.MITM_PORT_ERROR_PROMPT)
            return

        if self.settings.language != language_new:
            self.GUI_need_reload = True
        else:
            self.GUI_need_reload = False
        
        # All validated, save settings
        self.settings.auto_launch_browser = auto_launch_new
        self.settings.browser_width = width_new
        self.settings.browser_height = height_new
        self.settings.mitm_port = mitm_port_new
        self.settings.language = language_new
        self.settings.model_file = model_new
        self.settings.save_json()
        LOGGER.info("Settings saved successfully")
        self.destroy()

    def _on_cancel(self):
        LOGGER.debug("Close settings window without saving")
        self.destroy()


def main():
    """ Main entry point """
    log_helper.config_logging()
    setting = Settings()
    bot_manager = BotManager(setting)
    gui = MainGUI(setting, bot_manager)
    gui.mainloop()

if __name__ == "__main__":
    main()