""" GUI Settings Window """
import tkinter as tk
from tkinter import ttk, messagebox

import account_manager

from common.utils import MODEL_FOLDER, GAME_MODES
from common.utils import list_files
from common.log_helper import LOGGER
from common.settings import Settings
from common.lan_str import LAN_OPTIONS
from bot.bot import BotType
from .utils import set_style_normal

class SettingsWindow(tk.Toplevel):
    """ Settings dialog window"""
    def __init__(self, parent:tk.Frame, setting:Settings):
        super().__init__(parent)
        self.st = setting

        self.geometry('600x600')
        self.minsize(600,600)
        # self.resizable(False, False)
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f'+{parent_x+10}+{parent_y+10}')

        self.gui_need_reload:bool = False
        """ Whether a GUI refresh is needed to apply new settings"""

        self.model_updated:bool = False
        self.account_updated:bool = False
        # Call create_widgets after the window is fully initialized
        self.create_widgets()

    def create_widgets(self):
        """ Create widgets for settings dialog"""
        self.title(self.st.lan().SETTINGS)
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, minsize=150)
        main_frame.columnconfigure(1, minsize=100)
        main_frame.columnconfigure(2, minsize=100)
        main_frame.columnconfigure(3, minsize=100)

        # Styling
        style = ttk.Style(self)
        set_style_normal(style)
        
        pad_args = {"padx":(5, 4), "pady":(5, 4)}
        args_label = {"sticky":"e", **pad_args}
        args_entry = {"sticky":"w", **pad_args}
        # auto launch browser
        cur_row = 0
        _label = ttk.Label(main_frame, text=self.st.lan().AUTO_LAUNCH_BROWSER)
        _label.grid(row=cur_row, column=0, **args_label)
        self.auto_launch_var = tk.BooleanVar(value=self.st.auto_launch_browser)
        auto_launch_entry = ttk.Checkbutton(main_frame, variable=self.auto_launch_var, width=5)
        auto_launch_entry.grid(row=cur_row, column=1, columnspan=1, **args_entry)

        # Select client size
        _label = ttk.Label(main_frame, text=self.st.lan().CLIENT_SIZE)
        _label.grid(row=cur_row, column=2, **args_label)
        options = ["1920 x 1080", "1600 x 900", "1280 x 720"]
        setting_size = f"{self.st.browser_width} x {self.st.browser_height}"
        self.client_size_var = tk.StringVar(value=setting_size)
        select_menu = ttk.Combobox(main_frame, textvariable=self.client_size_var, values=options, state="readonly", width=12)
        select_menu.grid(row=cur_row, column=3, columnspan=1, **args_entry)
        
        # majsoul url
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MAJSOUL_URL)
        _label.grid(row=cur_row, column=0, **args_label)
        self.ms_url_var = tk.StringVar(value=self.st.ms_url)
        string_entry = ttk.Entry(main_frame, textvariable=self.ms_url_var, width=50)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        
        # mitm port
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MITM_PORT)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mitm_port_var = tk.StringVar(value=self.st.mitm_port)
        number_entry = ttk.Entry(main_frame, textvariable=self.mitm_port_var, width=12)
        number_entry.grid(row=cur_row, column=1,columnspan=1,  **args_entry)
        
        # Select language
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().LANGUAGE)
        _label.grid(row=cur_row, column=0, **args_label)
        options = [v.LANGUAGE_NAME for v in LAN_OPTIONS.values()]
        self.language_var = tk.StringVar(value=LAN_OPTIONS[self.st.language].LANGUAGE_NAME)
        select_menu = ttk.Combobox(main_frame, textvariable=self.language_var, values=options, state="readonly", width=12)
        select_menu.grid(row=cur_row, column=1,columnspan=1,  **args_entry)

        # Select Model Type
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MODEL_TYPE)
        _label.grid(row=cur_row, column=0, **args_label)
        options = [type.value for type in BotType]
        self.model_type_var = tk.StringVar(value=self.st.model_type)
        select_menu = ttk.Combobox(main_frame, textvariable=self.model_type_var, values=options, state="readonly", width=12)
        select_menu.grid(row=cur_row, column=1,columnspan=1,  **args_entry)
        
        # Select Model File
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().AI_MODEL_FILE)
        _label.grid(row=cur_row, column=0, **args_label)
        options = list_files(MODEL_FOLDER)
        self.model_file_var = tk.StringVar(value=self.st.model_file)
        select_menu = ttk.Combobox(main_frame, textvariable=self.model_file_var, values=options, state="readonly", width=30)
        select_menu.grid(row=cur_row, column=1, columnspan=3,  **args_entry)
        
        # Select Account
        # Inpute Account Name
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().ACCOUNT_SWITCH)
        _label.grid(row=cur_row, column=0, **args_label)
        options =account_manager.listUser()
        self.account_var = tk.StringVar(value=self.st.account)
        self.select_menu_account = ttk.Combobox(main_frame, textvariable=self.account_var, values=options, width=10)
        self.select_menu_account.grid(row=cur_row, column=1, columnspan=1,  **args_entry)
        
        # Save Account Name
        button_frame_2 = ttk.Frame(main_frame, relief="flat", borderwidth=2)
        button_frame_2.grid(row=cur_row, column=2)
        string_button =ttk.Button(button_frame_2, text=self.st.lan().ACCOUNT_SAVE, command=self.account_on_save)
        string_button.pack()

        
        # MJAPI url
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MJAPI_URL)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_url_var = tk.StringVar(value=self.st.mjapi_url)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_url_var, width=50)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        
        # MJAPI user
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MJAPI_USER)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_user_var = tk.StringVar(value=self.st.mjapi_user)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_user_var, width=12)
        string_entry.grid(row=cur_row, column=1,columnspan=1, **args_entry)
        # MJAPI usage
        _label = ttk.Label(main_frame, text=f"{self.st.lan().MJAPI_USAGE}: {self.st.mjapi_usage}")
        _label.grid(row=cur_row, column=2, **args_label)
        
        
        # MJAPI secret
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MJAPI_SECRET)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_secret_var = tk.StringVar(value=self.st.mjapi_secret)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_secret_var,width=50)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        
        # MJAPI model
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MJAPI_MODEL_SELECT)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_model_select_var = tk.StringVar(value=self.st.mjapi_model_select)
        options = self.st.mjapi_models
        sel_model = ttk.Combobox(main_frame, textvariable=self.mjapi_model_select_var, values=options, state="readonly", width=12)
        sel_model.grid(row=cur_row, column=1, columnspan=1,  **args_entry)
        
        _label = ttk.Label(main_frame, text=self.st.lan().LOGIN_TO_REFRESH)
        _label.grid(row=cur_row, column=2, **args_entry)
        
        # models_str = self.settings.lan().MODEL + ": " + ','.join(self.settings.mjapi_models)
        # text = tk.Text(main_frame, wrap=tk.NONE)
        # text.insert(tk.END, models_str)
        # text.configure(state=tk.DISABLED, height=1, width=30)
        # text.grid(row=cur_row, column=2, columnspan=2, **args_label)
        
        ### Auto play settings
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().AUTO_PLAY_SETTINGS)
        _label.grid(row=cur_row, column=0, **args_label)
        
        # auto play
        self.autoplay_var = tk.BooleanVar(value=self.st.enable_automation)
        autoplay_entry = ttk.Checkbutton(main_frame, variable=self.autoplay_var, text=self.st.lan().AUTOPLAY, width=12)
        autoplay_entry.grid(row=cur_row, column=1, columnspan=1, **args_entry)
        
        # random move        
        # _label = ttk.Label(main_frame, text=self.st.lan().MOUSE_RANDOM_MOVES)
        # _label.grid(row=cur_row, column=0, **args_label)
        self.random_move_var = tk.BooleanVar(value=self.st.auto_random_move)
        ran_moves_entry = ttk.Checkbutton(
            main_frame, variable=self.random_move_var, text=self.st.lan().MOUSE_RANDOM_MOVE, width=12)
        ran_moves_entry.grid(row=cur_row, column=2, columnspan=1, **args_entry)
        
        # idle move
        self.auto_idle_move_var = tk.BooleanVar(value=self.st.auto_idle_move)
        idle_move_entry = ttk.Checkbutton(main_frame, variable=self.auto_idle_move_var, text=self.st.lan().AUTO_IDLE_MOVE, width=12)
        idle_move_entry.grid(row=cur_row, column=3, columnspan=1, **args_entry)
        
        # randomize choice 
        cur_row += 1       
        _label = ttk.Label(main_frame, text=self.st.lan().RANDOM_CHOICE)
        _label.grid(row=cur_row, column=0, **args_label)
        self.randomized_choice_var = tk.StringVar(value=self.st.ai_randomize_choice)
        options = ['0 (Off)',1,2,3,4,5]
        random_choice_entry = ttk.Combobox(
            main_frame, textvariable=self.randomized_choice_var, values=options, state="readonly", width=12)
        random_choice_entry.grid(row=cur_row, column=1, columnspan=1, **args_entry)
        
        
        # random delay lower/upper
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().RANDOM_DELAY_RANGE)
        _label.grid(row=cur_row, column=0, **args_label)
        self.delay_random_lower_var = tk.DoubleVar(value=self.st.delay_random_lower)
        delay_lower_entry = tk.Entry(main_frame, textvariable= self.delay_random_lower_var,width=12)
        delay_lower_entry.grid(row=cur_row, column=1, **args_entry)
        self.delay_random_upper_var = tk.DoubleVar(value=self.st.delay_random_upper)
        delay_upper_entry = tk.Entry(main_frame, textvariable= self.delay_random_upper_var,width=12)
        delay_upper_entry.grid(row=cur_row, column=2, **args_entry)
        
        # auto join settings
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().AUTO_JOIN_GAME)
        _label.grid(row=cur_row, column=0, **args_label)
        self.auto_join_var = tk.BooleanVar(value=self.st.auto_join_game)
        auto_join_entry = ttk.Checkbutton(main_frame, variable=self.auto_join_var, text = self.st.lan().AUTO_JOIN_GAME, width=12)
        auto_join_entry.grid(row=cur_row, column=1,columnspan=1, **args_entry)
        
        self.auto_join_level_var = tk.StringVar(value=self.st.lan().GAME_LEVELS[self.st.auto_join_level])
        options = self.st.lan().GAME_LEVELS
        next_level = ttk.Combobox(main_frame, textvariable=self.auto_join_level_var, values=options, state="readonly", width=12)
        next_level.grid(row=cur_row, column=2,columnspan=1,  **args_entry)
        
        mode_idx = GAME_MODES.index(self.st.auto_join_mode)
        self.auto_join_mode_var = tk.StringVar(value=self.st.lan().GAME_MODES[mode_idx])
        options = self.st.lan().GAME_MODES
        next_mode = ttk.Combobox(main_frame, textvariable=self.auto_join_mode_var, values=options, state="readonly", width=12)
        next_mode.grid(row=cur_row, column=3,columnspan=1,  **args_entry)
        
        # tips :Settings
        cur_row += 1
        label_settings = ttk.Label(main_frame, text=self.st.lan().SETTINGS_TIPS, width=40)
        label_settings.grid(row=cur_row, column=1, columnspan=3, **args_entry)
        
        # Buttons frame
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", fill="x")
        cancel_button = ttk.Button(button_frame, text=self.st.lan().CANCEL, command=self._on_cancel)
        cancel_button.pack(side="left", padx=20, pady=10)
        save_button = ttk.Button(button_frame, text=self.st.lan().SAVE, command=self._on_save)
        save_button.pack(side="right", padx=20, pady=10)
    def account_on_save(self):        
        account_var_new = self.account_var.get()
        print(account_var_new)
        if account_var_new == "":
            return
        account_manager.saveUserAccount(account_var_new)
        LOGGER.info(str("Saving Account"+account_var_new+" to database"))

        self.account_var = tk.StringVar(value=account_var_new)
        self.select_menu_account['values']=account_manager.listUser()
        print("select_menu_values",self.select_menu_account['values'])
        # select_menu = ttk.Combobox(main_frame, textvariable=self.account_var, values=options, width=10)
        # select_menu.set(account_var_new)
        # print("select_menu.values=",select_menu['values'])
        # select_menu.set(select_menu.values[0])
        self.select_menu_account.set(account_var_new)
        self.select_menu_account.update()
        return
    def _on_save(self):
        # Get values from entry fields, validate, and save them
        
        # first get new values and validate
        auto_launch_new = self.auto_launch_var.get()
        
        size_list = self.client_size_var.get().split(' x ')
        width_new = int(size_list[0])
        height_new = int(size_list[1])
        
        mitm_port_new = int(self.mitm_port_var.get())
        if not self.st.valid_mitm_port(mitm_port_new):
            messagebox.showerror("⚠", self.st.lan().MITM_PORT_ERROR_PROMPT)
            return
        
        # language
        language_name = self.language_var.get()
        language_new = None
        for code, lan in LAN_OPTIONS.items():
            if language_name == lan.LANGUAGE_NAME:
                language_new = code
                break
        if self.st.language != language_new:
            self.gui_need_reload = True
        else:
            self.gui_need_reload = False
        
        account_var_new = self.account_var.get()
        # models
        model_type_new = self.model_type_var.get()
        model_file_new = self.model_file_var.get()
        mjapi_url_new = self.mjapi_url_var.get()
        mjapi_user_new = self.mjapi_user_var.get()
        mjapi_secret_new = self.mjapi_secret_var.get()
        mjapi_model_select_new = self.mjapi_model_select_var.get()
        
        if (
            self.st.model_type != model_type_new or
            self.st.model_file != model_file_new or
            self.st.mjapi_url != mjapi_url_new or
            self.st.mjapi_user != mjapi_user_new or
            self.st.mjapi_secret != mjapi_secret_new or 
            self.st.mjapi_model_select != mjapi_model_select_new
        ):
            self.model_updated = True
        
        if (
            self.st.account != account_var_new
        ):
            self.account_updated = True
        
        # auto play settings
        autoplay_new = self.autoplay_var.get()
        idle_move_new = self.auto_idle_move_var.get()
        randomized_choice_new:int = int(self.randomized_choice_var.get().split(' ')[0])
        auto_random_move_new = self.random_move_var.get()
        try:
            delay_lower_new = self.delay_random_lower_var.get()
            delay_upper_new = self.delay_random_upper_var.get()
        except Exception as _e:
            messagebox.showerror("⚠", self.st.lan().RANDOM_DELAY_RANGE)
            return
        delay_lower_new = max(0,delay_lower_new)
        delay_upper_new = max(delay_lower_new, delay_upper_new)
        auto_join_new = self.auto_join_var.get()
        auto_join_level_new = self.auto_join_level_var.get()    # convert to index
        auto_join_level_new = self.st.lan().GAME_LEVELS.index(auto_join_level_new)
        auto_join_mode_new = self.auto_join_mode_var.get()  # convert to string
        auto_join_mode_new = self.st.lan().GAME_MODES.index(auto_join_mode_new)
        auto_join_mode_new = GAME_MODES[auto_join_mode_new]
        
        
        # save settings        
        self.st.auto_launch_browser = auto_launch_new
        self.st.browser_width = width_new
        self.st.browser_height = height_new
        self.st.mitm_port = mitm_port_new
        self.st.language = language_new
        
        self.st.model_type = model_type_new
        self.st.model_file = model_file_new
        self.st.mjapi_url = mjapi_url_new
        self.st.mjapi_user = mjapi_user_new
        self.st.mjapi_secret = mjapi_secret_new
        self.st.mjapi_model_select = mjapi_model_select_new
        
        self.st.account = account_var_new
        self.st.enable_automation = autoplay_new
        self.st.auto_idle_move = idle_move_new
        self.st.ai_randomize_choice = randomized_choice_new
        self.st.auto_random_move = auto_random_move_new
        self.st.delay_random_lower = delay_lower_new
        self.st.delay_random_upper = delay_upper_new
        self.st.auto_join_game = auto_join_new
        self.st.auto_join_level = auto_join_level_new
        self.st.auto_join_mode = auto_join_mode_new
        
        LOGGER.info("Saving Settings to file")
        self.st.save_json()
        self.destroy()

    def _on_cancel(self):
        LOGGER.debug("Close settings window without saving")
        self.destroy()