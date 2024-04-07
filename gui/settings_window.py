""" GUI Settings Window """
import tkinter as tk
from tkinter import ttk, messagebox


from common.utils import MODEL_FOLDER, GAME_MODES
from common.utils import list_files
from common.log_helper import LOGGER
from common.settings import Settings
from common.lan_str import LAN_OPTIONS
from bot.bot import BOT_TYPE
from .utils import set_style_normal

class SettingsWindow(tk.Toplevel):
    """ Settings dialog window"""
    def __init__(self, parent:tk.Frame, setting:Settings):
        super().__init__(parent)
        self.settings = setting

        self.geometry('600x550')
        self.minsize(600,550)
        # self.resizable(False, False)
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f'+{parent_x+10}+{parent_y+10}')

        self.gui_need_reload:bool = False
        """ Whether a GUI refresh is needed to apply new settings"""

        self.model_updated:bool = False
        # Call create_widgets after the window is fully initialized
        self.create_widgets()

    def create_widgets(self):
        """ Create widgets for settings dialog"""
        self.title(self.settings.lan().SETTINGS)
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
        
        pad_args = {"padx":(5, 5), "pady":(5, 5)}
        args_label = {"sticky":"e", **pad_args}
        args_entry = {"sticky":"w", **pad_args}
        # auto launch browser
        cur_row = 0
        _label = ttk.Label(main_frame, text=self.settings.lan().AUTO_LAUNCH_BROWSER)
        _label.grid(row=cur_row, column=0, **args_label)
        self.auto_launch_var = tk.BooleanVar(value=self.settings.auto_launch_browser)
        auto_launch_entry = ttk.Checkbutton(main_frame, variable=self.auto_launch_var, width=5)
        auto_launch_entry.grid(row=cur_row, column=1, columnspan=1, **args_entry)

        # Select client size
        _label = ttk.Label(main_frame, text=self.settings.lan().CLIENT_SIZE)
        _label.grid(row=cur_row, column=2, **args_label)
        options = ["1920 x 1080", "1600 x 900", "1280 x 720"]
        setting_size = f"{self.settings.browser_width} x {self.settings.browser_height}"
        self.client_size_var = tk.StringVar(value=setting_size)
        select_menu = ttk.Combobox(main_frame, textvariable=self.client_size_var, values=options, state="readonly", width=12)
        select_menu.grid(row=cur_row, column=3, columnspan=1, **args_entry)
        
        # majsoul url
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().MAJSOUL_URL)
        _label.grid(row=cur_row, column=0, **args_label)
        self.ms_url_var = tk.StringVar(value=self.settings.ms_url)
        string_entry = ttk.Entry(main_frame, textvariable=self.ms_url_var, width=50)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        
        # mitm port
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().MITM_PORT)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mitm_port_var = tk.StringVar(value=self.settings.mitm_port)
        number_entry = ttk.Entry(main_frame, textvariable=self.mitm_port_var, width=12)
        number_entry.grid(row=cur_row, column=1,columnspan=1,  **args_entry)
        
        # Select language
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().LANGUAGE)
        _label.grid(row=cur_row, column=0, **args_label)
        options = [v.LANGUAGE_NAME for v in LAN_OPTIONS.values()]
        self.language_var = tk.StringVar(value=LAN_OPTIONS[self.settings.language].LANGUAGE_NAME)
        select_menu = ttk.Combobox(main_frame, textvariable=self.language_var, values=options, state="readonly", width=12)
        select_menu.grid(row=cur_row, column=1,columnspan=1,  **args_entry)

        # Select Model Type
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().MODEL_TYPE)
        _label.grid(row=cur_row, column=0, **args_label)
        options = [type.value for type in BOT_TYPE]
        self.model_type_var = tk.StringVar(value=self.settings.model_type)
        select_menu = ttk.Combobox(main_frame, textvariable=self.model_type_var, values=options, state="readonly", width=12)
        select_menu.grid(row=cur_row, column=1,columnspan=1,  **args_entry)
        
        # Select Model File
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().AI_MODEL_FILE)
        _label.grid(row=cur_row, column=0, **args_label)
        options = list_files(MODEL_FOLDER)
        self.model_file_var = tk.StringVar(value=self.settings.model_file)
        select_menu = ttk.Combobox(main_frame, textvariable=self.model_file_var, values=options, state="readonly", width=30)
        select_menu.grid(row=cur_row, column=1, columnspan=3,  **args_entry)
        
        # MJAPI url
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().MJAPI_URL)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_url_var = tk.StringVar(value=self.settings.mjapi_url)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_url_var, width=50)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        
        # MJAPI user
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().MJAPI_USER)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_user_var = tk.StringVar(value=self.settings.mjapi_user)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_user_var, width=12)
        string_entry.grid(row=cur_row, column=1,columnspan=1, **args_entry)
        
        # MJAPI secret
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().MJAPI_SECRET)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_secret_var = tk.StringVar(value=self.settings.mjapi_secret)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_secret_var,width=50)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        
        # MJAPI model
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().MJAPI_MODEL_SELECT)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_model_select_var = tk.StringVar(value=self.settings.mjapi_model_select)
        options = self.settings.mjapi_models
        sel_model = ttk.Combobox(main_frame, textvariable=self.mjapi_model_select_var, values=options, state="readonly", width=12)
        sel_model.grid(row=cur_row, column=1, columnspan=1,  **args_entry)
        
        _label = ttk.Label(main_frame, text=self.settings.lan().LOGIN_TO_REFRESH)
        _label.grid(row=cur_row, column=2, **args_entry)
        
        # models_str = self.settings.lan().MODEL + ": " + ','.join(self.settings.mjapi_models)
        # text = tk.Text(main_frame, wrap=tk.NONE)
        # text.insert(tk.END, models_str)
        # text.configure(state=tk.DISABLED, height=1, width=30)
        # text.grid(row=cur_row, column=2, columnspan=2, **args_label)
        
        ### Auto play settings
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.settings.lan().AUTO_PLAY_SETTINGS)
        _label.grid(row=cur_row, column=0, **args_label)
        
        # auto play
        self.autoplay_var = tk.BooleanVar(value=self.settings.enable_automation)
        autoplay_entry = ttk.Checkbutton(main_frame, variable=self.autoplay_var, text=self.settings.lan().AUTOPLAY, width=12)
        autoplay_entry.grid(row=cur_row, column=1, columnspan=1, **args_entry)
        
        # random move
        self.random_move_var = tk.BooleanVar(value=self.settings.auto_random_move)
        ran_move_entry = ttk.Checkbutton(main_frame, variable=self.random_move_var, text=self.settings.lan().MOUSE_RANDOM_MOVES, width=12)
        ran_move_entry.grid(row=cur_row, column=2, columnspan=1, **args_entry)
        
        # auto join settings
        cur_row += 1
        self.auto_join_var = tk.BooleanVar(value=self.settings.auto_join_game)
        auto_join_entry = ttk.Checkbutton(main_frame, variable=self.auto_join_var, text = self.settings.lan().AUTO_JOIN_GAME, width=12)
        auto_join_entry.grid(row=cur_row, column=1,columnspan=1, **args_entry)
        
        self.auto_join_level_var = tk.StringVar(value=self.settings.lan().GAME_LEVELS[self.settings.auto_join_level])
        options = self.settings.lan().GAME_LEVELS
        next_level = ttk.Combobox(main_frame, textvariable=self.auto_join_level_var, values=options, state="readonly", width=12)
        next_level.grid(row=cur_row, column=2,columnspan=1,  **args_entry)
        
        mode_idx = GAME_MODES.index(self.settings.auto_join_mode)
        self.auto_join_mode_var = tk.StringVar(value=self.settings.lan().GAME_MODES[mode_idx])
        options = self.settings.lan().GAME_MODES
        next_mode = ttk.Combobox(main_frame, textvariable=self.auto_join_mode_var, values=options, state="readonly", width=12)
        next_mode.grid(row=cur_row, column=3,columnspan=1,  **args_entry)
        
        # tips :Settings
        cur_row += 1
        label_settings = ttk.Label(main_frame, text=self.settings.lan().SETTINGS_TIPS, width=40)
        label_settings.grid(row=cur_row, column=1, columnspan=3, **args_entry)
        
        # Buttons frame
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", fill="x")
        cancel_button = ttk.Button(button_frame, text=self.settings.lan().CANCEL, command=self._on_cancel)
        cancel_button.pack(side="left", padx=20, pady=10)
        save_button = ttk.Button(button_frame, text=self.settings.lan().SAVE, command=self._on_save)
        save_button.pack(side="right", padx=20, pady=10)
        
    def _on_save(self):
        # Get values from entry fields, validate, and save them
        
        # first get new values and validate
        auto_launch_new = self.auto_launch_var.get()
        
        size_list = self.client_size_var.get().split(' x ')
        width_new = int(size_list[0])
        height_new = int(size_list[1])
        
        mitm_port_new = int(self.mitm_port_var.get())
        if not self.settings.valid_mitm_port(mitm_port_new):
            messagebox.showerror("⚠", self.settings.lan().MITM_PORT_ERROR_PROMPT)
            return
        
        # language
        language_name = self.language_var.get()
        language_new = None
        for code, lan in LAN_OPTIONS.items():
            if language_name == lan.LANGUAGE_NAME:
                language_new = code
                break
        if self.settings.language != language_new:
            self.gui_need_reload = True
        else:
            self.gui_need_reload = False
        
        # models
        model_type_new = self.model_type_var.get()
        model_file_new = self.model_file_var.get()
        mjapi_url_new = self.mjapi_url_var.get()
        mjapi_user_new = self.mjapi_user_var.get()
        mjapi_secret_new = self.mjapi_secret_var.get()
        mjapi_model_select_new = self.mjapi_model_select_var.get()
        
        if (
            self.settings.model_type != model_type_new or
            self.settings.model_file != model_file_new or
            self.settings.mjapi_url != mjapi_url_new or
            self.settings.mjapi_user != mjapi_user_new or
            self.settings.mjapi_secret != mjapi_secret_new or 
            self.settings.mjapi_model_select != mjapi_model_select_new
        ):
            self.model_updated = True
        
        # auto play settings
        autoplay_new = self.autoplay_var.get()
        auto_random_moves_new = self.random_move_var.get()
        auto_join_new = self.auto_join_var.get()
        auto_join_level_new = self.auto_join_level_var.get()    # convert to index
        auto_join_level_new = self.settings.lan().GAME_LEVELS.index(auto_join_level_new)
        auto_join_mode_new = self.auto_join_mode_var.get()  # convert to string
        auto_join_mode_new = self.settings.lan().GAME_MODES.index(auto_join_mode_new)
        auto_join_mode_new = GAME_MODES[auto_join_mode_new]
        
        
        # save settings        
        self.settings.auto_launch_browser = auto_launch_new
        self.settings.browser_width = width_new
        self.settings.browser_height = height_new
        self.settings.mitm_port = mitm_port_new
        self.settings.language = language_new
        
        self.settings.model_type = model_type_new
        self.settings.model_file = model_file_new
        self.settings.mjapi_url = mjapi_url_new
        self.settings.mjapi_user = mjapi_user_new
        self.settings.mjapi_secret = mjapi_secret_new
        self.settings.mjapi_model_select = mjapi_model_select_new
        
        self.settings.enable_automation = autoplay_new
        self.settings.auto_random_move = auto_random_moves_new
        self.settings.auto_join_game = auto_join_new
        self.settings.auto_join_level = auto_join_level_new
        self.settings.auto_join_mode = auto_join_mode_new
        
        self.settings.save_json()
        self.destroy()

    def _on_cancel(self):
        LOGGER.debug("Close settings window without saving")
        self.destroy()