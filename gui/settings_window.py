""" GUI Settings Window """
import tkinter as tk
from tkinter import ttk, messagebox

from common.utils import Folder
from common.utils import list_children
from common.log_helper import LOGGER
from common.settings import Settings
from common.lan_str import LAN_OPTIONS
from bot import MODEL_TYPE_STRINGS
from .utils import GUI_STYLE, add_hover_text

class SettingsWindow(tk.Toplevel):
    """ Settings dialog window"""
    def __init__(self, parent:tk.Frame, setting:Settings):
        super().__init__(parent)
        self.st = setting

        self.geometry('700x675')
        self.minsize(700,675)        
        # self.resizable(False, False)
        # set position: within main window
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f'+{parent_x+10}+{parent_y+10}')

        # flags
        self.exit_save:bool = False             # save btn clicked
        self.gui_need_reload:bool = False       #  
        self.model_updated:bool = False         # model settings updated
        self.mitm_proxinject_updated:bool = False          # mitm settings updated
        
        style = ttk.Style(self)
        GUI_STYLE.set_style_normal(style)
        self.create_widgets()
        

    def create_widgets(self):
        """ Create widgets for settings dialog"""
        self.title(self.st.lan().SETTINGS)
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")        
        
        pad_args = {"padx":(3, 3), "pady":(3, 2)}
        args_label = {"sticky":"e", **pad_args}
        args_entry = {"sticky":"w", **pad_args}
        std_wid = 15
        # auto launch browser
        cur_row = 0
        _label = ttk.Label(main_frame, text=self.st.lan().BROWSER)
        _label.grid(row=cur_row, column=0, **args_label)
        self.auto_launch_var = tk.BooleanVar(value=self.st.auto_launch_browser)
        auto_launch_entry = ttk.Checkbutton(
            main_frame, variable=self.auto_launch_var,
            text=self.st.lan().AUTO_LAUNCH_BROWSER, width=std_wid)
        auto_launch_entry.grid(row=cur_row, column=1, **args_entry)

        # Select client size
        _label = ttk.Label(main_frame, text=self.st.lan().CLIENT_SIZE)
        _label.grid(row=cur_row, column=2, **args_label)
        options = ["960 x 540", "1280 x 720", "1600 x 900", "1920 x 1080", "2560 x 1440", "3840 x 2160"]
        setting_size = f"{self.st.browser_width} x {self.st.browser_height}"
        self.client_size_var = tk.StringVar(value=setting_size)
        select_menu = ttk.Combobox(main_frame, textvariable=self.client_size_var, values=options, state="readonly", width=std_wid)
        select_menu.grid(row=cur_row, column=3, **args_entry)
        
        # majsoul url
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MAJSOUL_URL)
        _label.grid(row=cur_row, column=0, **args_label)
        self.ms_url_var = tk.StringVar(value=self.st.ms_url)
        string_entry = ttk.Entry(main_frame, textvariable=self.ms_url_var, width=std_wid*3)
        string_entry.grid(row=cur_row, column=1,columnspan=2,  **args_entry)
        # extensions
        self.enable_extension_var = tk.BooleanVar(value=self.st.enable_chrome_ext)
        auto_launch_entry = ttk.Checkbutton(
            main_frame, variable=self.enable_extension_var,
            text=self.st.lan().ENABLE_CHROME_EXT, width=std_wid+1)
        auto_launch_entry.grid(row=cur_row, column=3, **args_entry)
        
        # mitm port
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MITM_PORT)
        _label.grid(row=cur_row, column=0, **args_label)
        # add_hover_text(_label, "Need restart")
        self.mitm_port_var = tk.StringVar(value=self.st.mitm_port)
        number_entry = ttk.Entry(main_frame, textvariable=self.mitm_port_var, width=std_wid)
        number_entry.grid(row=cur_row, column=1, **args_entry)
        # upstream proxy
        _frame = tk.Frame(main_frame)
        _frame.grid(row=cur_row, column=2, columnspan=2)
        _label = ttk.Label(_frame, text=self.st.lan().UPSTREAM_PROXY)
        _label.pack(side=tk.LEFT, **pad_args)
        self.upstream_proxy_var = tk.StringVar(value=self.st.upstream_proxy)
        _entry = ttk.Entry(_frame, textvariable=self.upstream_proxy_var, width=std_wid*2)
        _entry.pack(side=tk.LEFT, **pad_args)   
        
        # Select language
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().LANGUAGE)
        _label.grid(row=cur_row, column=0, **args_label)
        options = [v.LANGUAGE_NAME for v in LAN_OPTIONS.values()]
        self.language_var = tk.StringVar(value=LAN_OPTIONS[self.st.language].LANGUAGE_NAME)
        select_menu = ttk.Combobox(main_frame, textvariable=self.language_var, values=options, state="readonly", width=std_wid)
        select_menu.grid(row=cur_row, column=1, **args_entry)
        
        # proxy inject
        self.proxy_inject_var = tk.BooleanVar(value=self.st.enable_proxinject)
        check_proxy_inject = ttk.Checkbutton(
            main_frame, variable=self.proxy_inject_var, text=self.st.lan().CLIENT_INJECT_PROXY, width=std_wid*2)
        check_proxy_inject.grid(row=cur_row, column=2, columnspan=2, **args_entry)  

        # sep
        cur_row += 1
        sep = ttk.Separator(main_frame, orient=tk.HORIZONTAL)
        sep.grid(row=cur_row, column=0, columnspan=4, sticky="ew", pady=5)
        # Select Model Type        
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MODEL_TYPE)
        _label.grid(row=cur_row, column=0, **args_label)
        self.model_type_var = tk.StringVar(value=self.st.model_type)
        select_menu = ttk.Combobox(main_frame, textvariable=self.model_type_var, values=MODEL_TYPE_STRINGS, state="readonly", width=std_wid)
        select_menu.grid(row=cur_row, column=1, **args_entry)
        
        # Select Model File
        model_files = [""] + list_children(Folder.MODEL)
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().AI_MODEL_FILE)
        _label.grid(row=cur_row, column=0, **args_label)        
        self.model_file_var = tk.StringVar(value=self.st.model_file)
        select_menu = ttk.Combobox(main_frame, textvariable=self.model_file_var, values=model_files, state="readonly", width=std_wid*3)
        select_menu.grid(row=cur_row, column=1, columnspan=3,  **args_entry)
        # model file 3p
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().AI_MODEL_FILE_3P)
        _label.grid(row=cur_row, column=0, **args_label)
        self.model_file_3p_var = tk.StringVar(value=self.st.model_file_3p)
        select_menu2 = ttk.Combobox(main_frame, textvariable=self.model_file_3p_var, values=model_files, state="readonly", width=std_wid*3)
        select_menu2.grid(row=cur_row, column=1, columnspan=3,  **args_entry)        
        # Akagi OT
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().AKAGI_OT_URL)
        _label.grid(row=cur_row, column=0, **args_label)
        self.akagiot_url_var = tk.StringVar(value=self.st.akagi_ot_url)
        string_entry = ttk.Entry(main_frame, textvariable=self.akagiot_url_var, width=std_wid*4)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        # Akagi OT API Key
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().AKAGI_OT_APIKEY)
        _label.grid(row=cur_row, column=0, **args_label)
        self.akagiot_apikey_var = tk.StringVar(value=self.st.akagi_ot_apikey)
        string_entry = ttk.Entry(main_frame, textvariable=self.akagiot_apikey_var, width=std_wid*4)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)        
        
        # MJAPI url
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MJAPI_URL)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_url_var = tk.StringVar(value=self.st.mjapi_url)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_url_var, width=std_wid*4)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        
        # MJAPI user
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MJAPI_USER)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_user_var = tk.StringVar(value=self.st.mjapi_user)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_user_var, width=std_wid)
        string_entry.grid(row=cur_row, column=1, **args_entry)   
        
        # MJAPI secret
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MJAPI_SECRET)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_secret_var = tk.StringVar(value=self.st.mjapi_secret)
        string_entry = ttk.Entry(main_frame, textvariable=self.mjapi_secret_var,width=std_wid*4)
        string_entry.grid(row=cur_row, column=1,columnspan=3,  **args_entry)
        
        # MJAPI model
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().MJAPI_MODEL_SELECT)
        _label.grid(row=cur_row, column=0, **args_label)
        self.mjapi_model_select_var = tk.StringVar(value=self.st.mjapi_model_select)
        options = self.st.mjapi_models
        sel_model = ttk.Combobox(main_frame, textvariable=self.mjapi_model_select_var, values=options, state="readonly", width=std_wid)
        sel_model.grid(row=cur_row, column=1, **args_entry)
        
        _label = ttk.Label(main_frame, text=self.st.lan().LOGIN_TO_REFRESH)
        _label.grid(row=cur_row, column=2, **args_entry)
        
        # sep
        cur_row += 1
        sep = ttk.Separator(main_frame, orient=tk.HORIZONTAL)
        sep.grid(row=cur_row, column=0, columnspan=4, sticky="ew", pady=5)
        ### Auto play settings
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().AUTO_PLAY_SETTINGS)
        _label.grid(row=cur_row, column=0, **args_label) 
        # random move        
        self.random_move_var = tk.BooleanVar(value=self.st.auto_random_move)
        ran_moves_entry = ttk.Checkbutton(
            main_frame, variable=self.random_move_var, text=self.st.lan().MOUSE_RANDOM_MOVE, width=std_wid)
        ran_moves_entry.grid(row=cur_row, column=1, **args_entry)        
        # idle move
        self.auto_idle_move_var = tk.BooleanVar(value=self.st.auto_idle_move)
        idle_move_entry = ttk.Checkbutton(main_frame, variable=self.auto_idle_move_var, text=self.st.lan().AUTO_IDLE_MOVE, width=std_wid)
        idle_move_entry.grid(row=cur_row, column=2, **args_entry)
        # drag dahai
        self.auto_drag_dahai_var = tk.BooleanVar(value=self.st.auto_dahai_drag)
        _entry = ttk.Checkbutton(main_frame, variable=self.auto_drag_dahai_var, text=self.st.lan().DRAG_DAHAI, width=std_wid)
        _entry.grid(row=cur_row, column=3, **args_entry)
        
        # randomize choice 
        cur_row += 1       
        _label = ttk.Label(main_frame, text=self.st.lan().RANDOM_CHOICE)
        _label.grid(row=cur_row, column=0, **args_label)
        self.randomized_choice_var = tk.StringVar(value=self.st.ai_randomize_choice)
        options = ['0 (Off)',1,2,3,4,5]
        random_choice_entry = ttk.Combobox(
            main_frame, textvariable=self.randomized_choice_var, values=options, state="readonly", width=std_wid)
        random_choice_entry.grid(row=cur_row, column=1, **args_entry)
        # reply emoji chance
        _label = ttk.Label(main_frame, text=self.st.lan().REPLY_EMOJI_CHANCE)
        _label.grid(row=cur_row, column=2, **args_label)
        options = [f"{i*10}%" for i in range(11)]
        options[0] = '0% (off)'
        self.reply_emoji_var = tk.StringVar(value=f"{int(self.st.auto_reply_emoji_rate*100)}%")
        _combo = ttk.Combobox(
            main_frame, textvariable=self.reply_emoji_var, values=options, state="readonly", width=std_wid)
        _combo.grid(row=cur_row, column=3, **args_entry)        
        
        # random delay lower/upper
        cur_row += 1
        _label = ttk.Label(main_frame, text=self.st.lan().RANDOM_DELAY_RANGE)
        _label.grid(row=cur_row, column=0, **args_label)
        self.delay_random_lower_var = tk.DoubleVar(value=self.st.delay_random_lower)
        delay_lower_entry = tk.Entry(main_frame, textvariable= self.delay_random_lower_var,width=std_wid)
        delay_lower_entry.grid(row=cur_row, column=1, **args_entry)
        self.delay_random_upper_var = tk.DoubleVar(value=self.st.delay_random_upper)
        delay_upper_entry = tk.Entry(main_frame, textvariable= self.delay_random_upper_var,width=std_wid)
        delay_upper_entry.grid(row=cur_row, column=2, **args_entry)
        
        # tips :Settings
        cur_row += 1
        label_settings = ttk.Label(main_frame, text=self.st.lan().SETTINGS_TIPS, width=std_wid*4)
        label_settings.grid(row=cur_row, column=0, columnspan=4, **args_entry)
        
        # Buttons frame
        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        cancel_button = ttk.Button(button_frame, text=self.st.lan().CANCEL, command=self._on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=20, pady=20)
        save_button = ttk.Button(button_frame, text=self.st.lan().SAVE, command=self._on_save)
        save_button.pack(side=tk.RIGHT, padx=20, pady=20)
        
        
    def _on_save(self):
        # Get values from entry fields, validate, and save them        
        # === Process and validate new values ===
        size_list = self.client_size_var.get().split(' x ')
        width_new = int(size_list[0])
        height_new = int(size_list[1])
        # url
        ms_url_new = self.ms_url_var.get()
        
        # mitm & proxy inject
        mitm_port_new = int(self.mitm_port_var.get())
        if not self.st.valid_mitm_port(mitm_port_new):
            messagebox.showerror("⚠", self.st.lan().MITM_PORT_ERROR_PROMPT)
            return
        upstream_proxy_new = self.upstream_proxy_var.get()
        proxy_inject_new = self.proxy_inject_var.get()
        if upstream_proxy_new != self.st.upstream_proxy or mitm_port_new != self.st.mitm_port or proxy_inject_new != self.st.enable_proxinject:
            self.mitm_proxinject_updated = True
        
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
        
        # models
        model_type_new = self.model_type_var.get()
        model_file_new = self.model_file_var.get()
        mode_file_3p_new = self.model_file_3p_var.get()
        akagi_url_new = self.akagiot_url_var.get()
        akagi_apikey_new = self.akagiot_apikey_var.get()
        mjapi_url_new = self.mjapi_url_var.get()
        mjapi_user_new = self.mjapi_user_var.get()
        mjapi_secret_new = self.mjapi_secret_var.get()
        mjapi_model_select_new = self.mjapi_model_select_var.get()        
        if (
            self.st.model_type != model_type_new or
            self.st.model_file != model_file_new or
            self.st.model_file_3p != mode_file_3p_new or
            self.st.akagi_ot_url != akagi_url_new or
            self.st.akagi_ot_apikey != akagi_apikey_new or
            self.st.mjapi_url != mjapi_url_new or
            self.st.mjapi_user != mjapi_user_new or
            self.st.mjapi_secret != mjapi_secret_new or 
            self.st.mjapi_model_select != mjapi_model_select_new
        ):
            self.model_updated = True
        
        # auto play settings
        randomized_choice_new:int = int(self.randomized_choice_var.get().split(' ')[0])
        reply_emoji_new:float = int(self.reply_emoji_var.get().split('%')[0])/100
        try:
            delay_lower_new = self.delay_random_lower_var.get()
            delay_upper_new = self.delay_random_upper_var.get()
        except Exception as _e:
            messagebox.showerror("⚠", self.st.lan().RANDOM_DELAY_RANGE)
            return
        delay_lower_new = max(0,delay_lower_new)
        delay_upper_new = max(delay_lower_new, delay_upper_new)
        
        # === save new values to setting ===        
        self.st.auto_launch_browser = self.auto_launch_var.get()
        self.st.browser_width = width_new
        self.st.browser_height = height_new
        self.st.ms_url = ms_url_new
        self.st.enable_chrome_ext = self.enable_extension_var.get()
        self.st.mitm_port = mitm_port_new
        self.st.upstream_proxy = upstream_proxy_new
        self.st.language = language_new
        self.st.enable_proxinject = proxy_inject_new
        
        self.st.model_type = model_type_new
        self.st.model_file = model_file_new
        self.st.model_file_3p = mode_file_3p_new
        self.st.akagi_ot_url = akagi_url_new
        self.st.akagi_ot_apikey = akagi_apikey_new
        self.st.mjapi_url = mjapi_url_new
        self.st.mjapi_user = mjapi_user_new
        self.st.mjapi_secret = mjapi_secret_new
        self.st.mjapi_model_select = mjapi_model_select_new
        
        self.st.auto_idle_move = self.auto_idle_move_var.get()
        self.st.auto_dahai_drag = self.auto_drag_dahai_var.get()
        self.st.auto_random_move = self.random_move_var.get()
        self.st.ai_randomize_choice = randomized_choice_new
        self.st.auto_reply_emoji_rate = reply_emoji_new        
        self.st.delay_random_lower = delay_lower_new
        self.st.delay_random_upper = delay_upper_new
        
        self.st.save_json()
        self.exit_save = True
        if self.mitm_proxinject_updated:
            messagebox.showinfo(self.st.lan().SETTINGS, self.st.lan().SETTINGS_TIPS, parent=self, icon='info', type='ok')
        self.destroy()
        

    def _on_cancel(self):
        LOGGER.info("Closing settings window without saving")
        self.exit_save = False
        self.destroy()
