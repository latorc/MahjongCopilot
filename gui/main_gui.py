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
import  account_manager

from bot_manager import BotManager, mjai_reaction_2_guide
from common.utils import RES_FOLDER
from common.utils import UiState, MITMException, ModelFileException, sub_file
from common.log_helper import LOGGER, LogHelper
from common.settings import Settings
from common.mj_helper import GameInfo, MJAI_TILE_2_UNICODE
from updater import Updater
from .utils import set_style_normal
from .settings_window import SettingsWindow
from .help_window import HelpWindow


class MainGUI(tk.Tk):
    """ Main GUI Window"""
    def __init__(self, setting:Settings, bot_manager:BotManager):
        super().__init__()
        self.bot_manager = bot_manager
        self.st = setting
        self.updater = Updater(self.st.update_url)
        icon = tk.PhotoImage(file=sub_file(RES_FOLDER,'icon.png'))
        self.iconphoto(True, icon)
        self.protocol("WM_DELETE_WINDOW", self._on_exit)        # confirmation before close window        

        # icon resources:
        self.icon_green = sub_file(RES_FOLDER,'green.png')
        self.icon_red = sub_file(RES_FOLDER,'red.png')
        self.icon_yellow = sub_file(RES_FOLDER,'yellow.png')
        self.icon_gray =sub_file(RES_FOLDER,'gray.png')
        self.icon_ready = sub_file(RES_FOLDER,'ready.png')

        # create window widgets
        self._create_widgets()

        self.bot_manager.start()        # start the main program
        self.gui_update_delay = 50      # in ms
        self._update_gui_info()         # start updating gui info

    def _create_widgets(self):
        # Styling
        style = ttk.Style(self)
        set_style_normal(style)

        # Main window properties
        self.title(self.st.lan().APP_TITLE)
        self.geometry('750x500')
        self.minsize(750,500)

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
            self.st.lan().START_BROWSER, 'majsoul.png', self._on_btn_start_browser_clicked)
        self.toolbar.add_sep()
        self.switch_overlay = ToggleSwitch(
            self.toolbar, self.st.lan().WEB_OVERLAY, 75, command=self._on_switch_hud_clicked)
        self.switch_overlay.pack(side=tk.LEFT, padx=4, pady=4)
        self.switch_autoplay = ToggleSwitch(
            self.toolbar, self.st.lan().AUTOPLAY, 75, command=self._on_switch_autoplay_clicked)
        self.switch_autoplay.pack(side=tk.LEFT, padx=4, pady=4)
        self.switch_autojoin = ToggleSwitch(
            self.toolbar, self.st.lan().AUTO_JOIN_GAME, 75, command=self._on_switch_autojoin_clicked)
        self.switch_autojoin.pack(side=tk.LEFT, padx=4, pady=4)
        self.toolbar.add_sep()
        self.toolbar.add_button(self.st.lan().SETTINGS, 'settings.png', self._on_btn_settings_clicked)
        self.toolbar.add_button(self.st.lan().OPEN_LOG_FILE, 'log.png', self._on_btn_log_clicked)
        self.toolbar.add_button(self.st.lan().HELP, 'help.png', self._on_btn_help_clicked)
        self.toolbar.add_sep()
        self.toolbar.add_button(self.st.lan().EXIT, 'exit.png', self._on_exit)

        # AI guidance
        _label = ttk.Label(self.grid_frame, text=self.st.lan().AI_OUTPUT)
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
        _label = ttk.Label(self.grid_frame, text=self.st.lan().GAME_INFO)
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
        self.bot_manager.stop_browser()
        account_manager.switchAccountLogin(self.st.account)
        self.bot_manager.start_browser()

    def _on_switch_hud_clicked(self):
        self.switch_overlay.switch_mid()
        if not self.st.enable_overlay:
            self.bot_manager.enable_overlay()
        else:
            self.bot_manager.disable_overlay()
            
    def _on_switch_autoplay_clicked(self):
        self.switch_autoplay.switch_mid()
        if self.st.enable_automation:
            self.bot_manager.disable_automation()
        else:
            self.bot_manager.enable_automation()

    def _on_switch_autojoin_clicked(self):
        self.switch_autojoin.switch_mid()
        if self.st.auto_join_game:
            self.bot_manager.disable_autojoin()
        else:
            self.bot_manager.enable_autojoin()

    def _on_btn_log_clicked(self):
        # LOGGER.debug('Open log')
        os.startfile(LogHelper.log_file_name)

    def _on_btn_settings_clicked(self):
        # open settings dialog (modal/blocking)
        settings_window = SettingsWindow(self, self.st)
        settings_window.transient(self)
        settings_window.grab_set()
        self.wait_window(settings_window)
        
        if settings_window.gui_need_reload:     # reload UI if needed
            self.reload_gui()
        if settings_window.model_updated:       # re-create bot if needed
            if not self.bot_manager.is_in_game():
                self.bot_manager.create_bot()
        else:
            if not self.bot_manager.is_bot_created():
                self.bot_manager.create_bot()
        if settings_window.account_updated:
            LOGGER.debug("stop brower")
            self.bot_manager.stop_browser()
            account_manager.switchAccountLogin(self.st.account)

    def _on_btn_help_clicked(self):
        # open help dialog        
        help_win = HelpWindow(self, self.st, self.updater)
        help_win.transient(self)
        help_win.grab_set()
    
    def _on_exit(self):
        # Exit the app
        # pop up that confirm if the user really wants to quit
        if messagebox.askokcancel(self.st.lan().EXIT, self.st.lan().EIXT_CONFIRM):
            LOGGER.info("Exiting GUI and program. saving settings and stopping threads.")
            self.st.save_json()
            self.bot_manager.stop(False)
            self.quit()
            
    def reload_gui(self):
        """ Clear UI compontes and rebuid widgets"""       
        for widget in self.winfo_children():
            widget.destroy()
        self._create_widgets()
        

    def _update_gui_info(self):
        """ Update GUI widgets status with latest info from bot manager"""
        if not self.bot_manager.browser.is_running():
            self.btn_start_browser.config(state=tk.NORMAL)
        else:
            self.btn_start_browser.config(state=tk.DISABLED)
            
        # update switches' status
        sw_list = [
            (self.switch_overlay, lambda: self.st.enable_overlay),
            (self.switch_autoplay, lambda: self.st.enable_automation),
            (self.switch_autojoin, lambda: self.st.auto_join_game)
        ]
        for sw, func in sw_list:
            if func():
                sw.switch_on()
            else:
                sw.switch_off()

        # Update Reaction
        self.text_ai_guide.config(state=tk.NORMAL)
        self.text_ai_guide.delete('1.0', tk.END)
        pending_reaction = self.bot_manager.get_pending_reaction()
        # convert this reaction into string
        if pending_reaction:
            action_str, options = mjai_reaction_2_guide(pending_reaction, 3, self.st.lan())
            self.text_ai_guide.insert(tk.END, f'{action_str}\n')
            for tile_str, weight in options:
                self.text_ai_guide.insert(tk.END, f' {tile_str}  {weight*100:4.0f}%\n')
        self.text_ai_guide.config(state=tk.DISABLED)

        # update state: display tehai + tsumohai
        gi:GameInfo = self.bot_manager.get_game_info()
        self.text_state.config(state=tk.NORMAL)
        self.text_state.delete('1.0', tk.END)
        if gi and gi.my_tehai:
            tehai = gi.my_tehai
            tsumohai = gi.my_tsumohai
            hand_str = ''.join(MJAI_TILE_2_UNICODE[t] for t in tehai)
            if tsumohai:
                hand_str += f" + {MJAI_TILE_2_UNICODE[tsumohai]}"
            self.text_state.insert(tk.END, hand_str)
        self.text_state.config(state=tk.DISABLED)

        # Update status bar
        fps_disp = min([999, self.bot_manager.fps_counter.fps])
        fps_str = f"({fps_disp:3.0f})"
        if self.bot_manager.is_running():       # main thread
            self.status_bar.update_column(0, self.st.lan().MAIN_THREAD + fps_str, self.icon_green)
        else:
            self.status_bar.update_column(0, self.st.lan().MAIN_THREAD + fps_str, self.icon_red)

        if self.bot_manager.is_bot_created():
            text = self.st.lan().MODEL + ": " + self.bot_manager.bot.type.value
            self.status_bar.update_column(1, text, self.icon_green)
        else:
            text = self.st.lan().AWAIT_BOT
            self.status_bar.update_column(1, text, self.icon_red)

        
        fps_disp = min(999, self.bot_manager.browser.fps_counter.fps)
        fps_str = f"({fps_disp:3.0f})"
        if self.bot_manager.browser.is_running():
            self.status_bar.update_column(2, self.st.lan().BROWSER+fps_str, self.icon_green)
        else:
            self.status_bar.update_column(2, self.st.lan().BROWSER+fps_str, self.icon_gray)

        status_str, icon = self._get_status_text_icon(gi)
        self.status_bar.update_column(3, status_str, icon)
        
        self.bot_manager.update_overlay()

        self.after(self.gui_update_delay, self._update_gui_info)     # next update

    def _get_status_text_icon(self, gi:GameInfo) -> tuple[str, str]:
        # Get text and icon for status bar last column, based on bot running info
        
        bot_exception = self.bot_manager.main_thread_exception        
        if isinstance(bot_exception, MITMException):
            return self.st.lan().MITM_SERVER_ERROR, self.icon_red
        elif isinstance(bot_exception, Exception):
            return self.st.lan().MAIN_THREAD_ERROR + str(bot_exception), self.icon_red
        else:   # no exception in bot manager
            pass
        
        game_error:Exception = self.bot_manager.get_game_error()
        if isinstance(game_error, ModelFileException):
            return self.st.lan().MODEL_FILE_ERROR, self.icon_red
        elif isinstance(game_error, Exception):
            text = self.st.lan().GAME_ERROR + " " + str(game_error)
            return text, self.icon_red
        else:       # no game error
            pass
            
        if self.bot_manager.is_in_game():
            info_str = self.st.lan().GAME_RUNNING

            if self.bot_manager.is_game_syncing():
                info_str += " - " + self.st.lan().SYNCING
                return info_str, self.icon_green

            else:   # game in progress
                if gi and gi.bakaze:
                    info_str += f" - {self.st.lan().mjai2str(gi.bakaze)} {gi.kyoku} {self.st.lan().KYOKU} {gi.honba} {self.st.lan().HONBA}"
                else:
                    info_str += " - " + self.st.lan().GAME_STARTING
                return info_str, self.icon_green
        else:
            state_dict = {
                UiState.MAIN_MENU: self.st.lan().MAIN_MENU,
                UiState.GAME_ENDING: self.st.lan().GAME_ENDING,
                UiState.NOT_RUNNING: self.st.lan().GAME_NOT_RUNNING,
            }
            info_str = self.st.lan().READY_FOR_GAME + " - " + state_dict.get(self.bot_manager.automation.ui_state, "")
            return info_str, self.icon_ready


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
        img_on = tk.PhotoImage(file=sub_file(RES_FOLDER,'switch_on.png'))
        img_off = tk.PhotoImage(file=sub_file(RES_FOLDER,'switch_off.png'))
        img_mid = tk.PhotoImage(file=sub_file(RES_FOLDER,'switch_mid.png'))
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
        btn.original_bg = btn.cget("background")
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
        btn.configure(background=btn.original_bg)
        self._hover_text.destroy()
    

class StatusBar(tk.Frame):
    """ Status bar with multiple columns"""
    def __init__(self, master, n_cols:int, font_size:int = 12):
        super().__init__(master, highlightbackground='gray', highlightthickness=0)
        self.n_cols = n_cols
        self.font_size = font_size
        self.columns:list[tk.Frame] = []

        # Style
        style = ttk.Style(self)
        set_style_normal(style, font_size)

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

        # Load icon
        # default_icon_file = str(sub_file(RES_FOLDER,'gray.png'))
        # icon = tk.PhotoImage(file=default_icon_file)  # Replace "icon.png" with your icon file
        # icon_ht = self.font_size * 2
        # icon = icon.subsample(int(icon.height()/icon_ht), int(icon.height()/icon_ht))
        # Label with icon and text
        label = ttk.Label(column_frame, text=f'Column {index+1}', compound='left')  # Background color for label
        # label.image = icon  # Retain a reference to the image to prevent garbage collection
        label.image_file = "placeholder"
        label.pack(side=tk.LEFT, anchor='w')
        column_frame.label = label

        return column_frame
    # def set_col_config(self, col:int, **kwargs):
    #     if col < self.n_cols:
    #         self.columns[col].configure()
    
    def update_column(self, index:int, text:str, icon_path:str=None):
        """ Update column's icon and text"""
        if not 0 <= index < len(self.columns):
            return
        
        label:ttk.Label = self.columns[index].label
        label.config(text=text)
        if icon_path is not None and label.image_file != icon_path:
            # Load new icon
            new_icon = tk.PhotoImage(file=icon_path)
            new_icon = new_icon.subsample(
                int(new_icon.height()/self.font_size/1.3333),
                int(new_icon.height() / self.font_size / 1.3333))
            label.config(image=new_icon)
            label.image = new_icon      # keep a reference to avoid garbage collection
            label.image_file = icon_path
