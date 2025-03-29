"""GUI Settings Window"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from common.utils import Folder, list_children
from common.log_helper import LOGGER
from common.settings import Settings
from common.lan_str import LAN_OPTIONS
from bot import MODEL_TYPE_STRINGS

class SettingsWindow(ctk.CTkToplevel):
    """Settings dialog window"""
    def __init__(self, parent: ctk.CTkFrame, setting: Settings):
        super().__init__(parent)
        self.settings = setting

        # Disable customtkinter default icon override
        self._iconify_enabled = False

        # Adjust window size to fit all settings
        self.geometry("880x830")
        self.minsize(880, 830)
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f"+{parent_x+10}+{parent_y+10}")
        self.bind("<<AppearanceModeChanged>>", self._on_appearance_change)

        # Flags
        self.exit_save: bool = False
        self.gui_need_reload: bool = False
        self.model_updated: bool = False
        self.mitm_proxinject_updated: bool = False

        # Initialize appearance
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.create_widgets()

    def create_widgets(self):
        """Create widgets for settings dialog"""
        self.title(self.settings.lan().SETTINGS)

        # Create main container frame
        main_frame = ctk.CTkFrame(self, corner_radius=10)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        pad_args = {"padx": 5, "pady": 5}
        std_wid = 15
        cur_row = 0

        #region Browser and Client Settings
        # Browser auto launch
        label_browser = ctk.CTkLabel(main_frame, text=self.settings.lan().BROWSER)
        label_browser.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.auto_launch_var = ctk.BooleanVar(value=self.settings.auto_launch_browser)
        auto_launch_checkbox = ctk.CTkCheckBox(
            main_frame,
            variable=self.auto_launch_var,
            text=self.settings.lan().AUTO_LAUNCH_BROWSER,
            width=std_wid * 10,
        )
        auto_launch_checkbox.grid(row=cur_row, column=1, sticky="w", **pad_args)

        label_client_size = ctk.CTkLabel(main_frame, text=self.settings.lan().CLIENT_SIZE)
        label_client_size.grid(row=cur_row, column=2, sticky="e", **pad_args)
        size_options = [
            "960 x 540",
            "1280 x 720",
            "1600 x 900",
            "1920 x 1080",
            "2560 x 1440",
            "3840 x 2160",
        ]
        setting_size = f"{self.settings.browser_width} x {self.settings.browser_height}"
        self.client_size_var = ctk.StringVar(value=setting_size)
        client_size_menu = ctk.CTkOptionMenu(
            main_frame, variable=self.client_size_var, values=size_options, width=std_wid * 15
        )
        client_size_menu.grid(row=cur_row, column=3, sticky="w", **pad_args)

        cur_row += 1

        # Majsoul URL and extensions
        label_ms_url = ctk.CTkLabel(main_frame, text=self.settings.lan().MAJSOUL_URL)
        label_ms_url.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.ms_url_var = ctk.StringVar(value=self.settings.ms_url)
        ms_url_entry = ctk.CTkEntry(main_frame, textvariable=self.ms_url_var, width=std_wid * 30)
        ms_url_entry.grid(row=cur_row, column=1, columnspan=2, sticky="w", **pad_args)

        self.enable_extension_var = ctk.BooleanVar(value=self.settings.enable_chrome_ext)
        enable_extension_checkbox = ctk.CTkCheckBox(
            main_frame,
            variable=self.enable_extension_var,
            text=self.settings.lan().ENABLE_CHROME_EXT,
            width=std_wid * 10,
        )
        enable_extension_checkbox.grid(row=cur_row, column=3, sticky="w", **pad_args)

        cur_row += 1

        #endregion

        #region Network Settings
        # MITM port and upstream proxy settings
        label_mitm_port = ctk.CTkLabel(main_frame, text=self.settings.lan().MITM_PORT)
        label_mitm_port.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mitm_port_var = ctk.StringVar(value=self.settings.mitm_port)
        mitm_port_entry = ctk.CTkEntry(main_frame, textvariable=self.mitm_port_var, width=std_wid * 15)
        mitm_port_entry.grid(row=cur_row, column=1, sticky="w", **pad_args)

        label_upstream_proxy = ctk.CTkLabel(main_frame, text=self.settings.lan().UPSTREAM_PROXY)
        label_upstream_proxy.grid(row=cur_row, column=2, sticky="e", **pad_args)
        self.upstream_proxy_var = ctk.StringVar(value=self.settings.upstream_proxy)
        upstream_proxy_entry = ctk.CTkEntry(
            main_frame, textvariable=self.upstream_proxy_var, width=std_wid * 15
        )
        upstream_proxy_entry.grid(row=cur_row, column=3, sticky="w", **pad_args)

        cur_row += 1

        # Language and proxy inject
        label_language = ctk.CTkLabel(main_frame, text=self.settings.lan().LANGUAGE)
        label_language.grid(row=cur_row, column=0, sticky="e", **pad_args)
        language_options = [v.LANGUAGE_NAME for v in LAN_OPTIONS.values()]
        self.language_var = ctk.StringVar(value=LAN_OPTIONS[self.settings.language].LANGUAGE_NAME)
        language_menu = ctk.CTkOptionMenu(
            main_frame, variable=self.language_var, values=language_options, width=std_wid * 10
        )
        language_menu.grid(row=cur_row, column=1, sticky="w", **pad_args)

        self.proxy_inject_var = ctk.BooleanVar(value=self.settings.enable_proxinject)
        proxy_inject_checkbox = ctk.CTkCheckBox(
            main_frame,
            variable=self.proxy_inject_var,
            text=self.settings.lan().CLIENT_INJECT_PROXY,
            width=std_wid * 20,
        )
        proxy_inject_checkbox.grid(row=cur_row, column=2, columnspan=2, sticky="w", **pad_args)

        cur_row += 1

        # Separator
        separator = ctk.CTkLabel(main_frame, text="")
        separator.grid(row=cur_row, column=0, columnspan=4, sticky="ew", pady=5)

        #endregion

        #region Model Settings
        # AI model configuration
        cur_row += 1
        label_model_type = ctk.CTkLabel(main_frame, text=self.settings.lan().MODEL_TYPE)
        label_model_type.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.model_type_var = ctk.StringVar(value=self.settings.model_type)
        model_type_menu = ctk.CTkOptionMenu(
            main_frame, variable=self.model_type_var, values=MODEL_TYPE_STRINGS, width=std_wid * 10
        )
        model_type_menu.grid(row=cur_row, column=1, sticky="w", **pad_args)

        cur_row += 1
        label_ai_model_file = ctk.CTkLabel(main_frame, text=self.settings.lan().AI_MODEL_FILE)
        label_ai_model_file.grid(row=cur_row, column=0, sticky="e", **pad_args)
        model_files = [""] + list_children(Folder.MODEL)
        self.model_file_var = ctk.StringVar(value=self.settings.model_file)
        model_file_menu = ctk.CTkOptionMenu(
            main_frame, variable=self.model_file_var, values=model_files, width=std_wid * 30
        )
        model_file_menu.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)

        cur_row += 1
        label_ai_model_file_3p = ctk.CTkLabel(main_frame, text=self.settings.lan().AI_MODEL_FILE_3P)
        label_ai_model_file_3p.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.model_file_3p_var = ctk.StringVar(value=self.settings.model_file_3p)
        model_file_3p_menu = ctk.CTkOptionMenu(
            main_frame, variable=self.model_file_3p_var, values=model_files, width=std_wid * 30
        )
        model_file_3p_menu.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)

        cur_row += 1
        label_akagi_ot_url = ctk.CTkLabel(main_frame, text=self.settings.lan().AKAGI_OT_URL)
        label_akagi_ot_url.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.akagiot_url_var = ctk.StringVar(value=self.settings.akagi_ot_url)
        akagi_ot_url_entry = ctk.CTkEntry(
            main_frame, textvariable=self.akagiot_url_var, width=std_wid * 41
        )
        akagi_ot_url_entry.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)

        cur_row += 1
        label_akagi_ot_apikey = ctk.CTkLabel(main_frame, text=self.settings.lan().AKAGI_OT_APIKEY)
        label_akagi_ot_apikey.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.akagiot_apikey_var = ctk.StringVar(value=self.settings.akagi_ot_apikey)
        akagi_ot_apikey_entry = ctk.CTkEntry(
            main_frame, textvariable=self.akagiot_apikey_var, width=std_wid * 41
        )
        akagi_ot_apikey_entry.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)

        cur_row += 1
        label_mjapi_url = ctk.CTkLabel(main_frame, text=self.settings.lan().MJAPI_URL)
        label_mjapi_url.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mjapi_url_var = ctk.StringVar(value=self.settings.mjapi_url)
        mjapi_url_entry = ctk.CTkEntry(main_frame, textvariable=self.mjapi_url_var, width=std_wid * 41)
        mjapi_url_entry.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)

        cur_row += 1
        label_mjapi_user = ctk.CTkLabel(main_frame, text=self.settings.lan().MJAPI_USER)  # 显示文本
        label_mjapi_user.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mjapi_user_var = ctk.StringVar(value=self.settings.mjapi_user)
        mjapi_user_entry = ctk.CTkEntry(main_frame, textvariable=self.mjapi_user_var, width=std_wid * 10)
        mjapi_user_entry.grid(row=cur_row, column=1, sticky="w", **pad_args)

        cur_row += 1
        label_mjapi_secret = ctk.CTkLabel(main_frame, text=self.settings.lan().MJAPI_SECRET)
        label_mjapi_secret.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mjapi_secret_var = ctk.StringVar(value=self.settings.mjapi_secret)
        mjapi_secret_entry = ctk.CTkEntry(
            main_frame, textvariable=self.mjapi_secret_var, width=std_wid * 41
        )
        mjapi_secret_entry.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)

        cur_row += 1
        label_mjapi_model_select = ctk.CTkLabel(
            main_frame, text=self.settings.lan().MJAPI_MODEL_SELECT
        )
        label_mjapi_model_select.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mjapi_model_select_var = ctk.StringVar(value=self.settings.mjapi_model_select)
        mjapi_models = self.settings.mjapi_models
        mjapi_model_select_menu = ctk.CTkOptionMenu(
            main_frame,
            variable=self.mjapi_model_select_var,
            values=mjapi_models,
            width=std_wid * 10,
        )
        mjapi_model_select_menu.grid(row=cur_row, column=1, sticky="w", **pad_args)

        label_login_to_refresh = ctk.CTkLabel(main_frame, text=self.settings.lan().LOGIN_TO_REFRESH)
        label_login_to_refresh.grid(row=cur_row, column=2, sticky="w", **pad_args)

        cur_row += 1
        separator = ctk.CTkLabel(main_frame, text="")
        separator.grid(row=cur_row, column=0, columnspan=4, sticky="ew", pady=5)

        #endregion

        #region Auto Play Settings  
        # Auto play behavior configuration
        cur_row += 1
        label_auto_play_settings = ctk.CTkLabel(
            main_frame, text=self.settings.lan().AUTO_PLAY_SETTINGS
        )
        label_auto_play_settings.grid(row=cur_row, column=0, sticky="e", **pad_args)

        self.random_move_var = ctk.BooleanVar(value=self.settings.auto_random_move)
        random_move_checkbox = ctk.CTkCheckBox(
            main_frame,
            variable=self.random_move_var,
            text=self.settings.lan().MOUSE_RANDOM_MOVE,
            width=std_wid * 10,
        )
        random_move_checkbox.grid(row=cur_row, column=1, sticky="w", **pad_args)

        self.auto_idle_move_var = ctk.BooleanVar(value=self.settings.auto_idle_move)
        auto_idle_move_checkbox = ctk.CTkCheckBox(
            main_frame,
            variable=self.auto_idle_move_var,
            text=self.settings.lan().AUTO_IDLE_MOVE,
            width=std_wid * 10,
        )
        auto_idle_move_checkbox.grid(row=cur_row, column=2, sticky="w", **pad_args)

        self.auto_drag_dahai_var = ctk.BooleanVar(value=self.settings.auto_dahai_drag)
        auto_drag_dahai_checkbox = ctk.CTkCheckBox(
            main_frame,
            variable=self.auto_drag_dahai_var,
            text=self.settings.lan().DRAG_DAHAI,
            width=std_wid * 10,
        )
        auto_drag_dahai_checkbox.grid(row=cur_row, column=3, sticky="w", **pad_args)

        cur_row += 1
        label_random_choice = ctk.CTkLabel(main_frame, text=self.settings.lan().RANDOM_CHOICE)
        label_random_choice.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.randomized_choice_var = ctk.StringVar(
            value=str(self.settings.ai_randomize_choice)
        )
        random_choice_options = ["0 (Off)", "1", "2", "3", "4", "5"]
        random_choice_menu = ctk.CTkOptionMenu(
            main_frame,
            variable=self.randomized_choice_var,
            values=random_choice_options,
            width=std_wid * 10,
        )
        random_choice_menu.grid(row=cur_row, column=1, sticky="w", **pad_args)

        label_reply_emoji_chance = ctk.CTkLabel(
            main_frame, text=self.settings.lan().REPLY_EMOJI_CHANCE
        )
        label_reply_emoji_chance.grid(row=cur_row, column=2, sticky="e", **pad_args)
        reply_emoji_options = [f"{i*10}%" for i in range(11)]
        reply_emoji_options[0] = "0% (off)"
        self.reply_emoji_var = ctk.StringVar(
            value=f"{int(self.settings.auto_reply_emoji_rate * 100)}%"
        )
        reply_emoji_menu = ctk.CTkOptionMenu(
            main_frame, variable=self.reply_emoji_var, values=reply_emoji_options, width=std_wid * 10
        )
        reply_emoji_menu.grid(row=cur_row, column=3, sticky="w", **pad_args)

        cur_row += 1
        label_random_delay_range = ctk.CTkLabel(
            main_frame, text=self.settings.lan().RANDOM_DELAY_RANGE
        )
        label_random_delay_range.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.delay_random_lower_var = ctk.DoubleVar(value=self.settings.delay_random_lower)
        delay_lower_entry = ctk.CTkEntry(
            main_frame, textvariable=self.delay_random_lower_var, width=std_wid * 10
        )
        delay_lower_entry.grid(row=cur_row, column=1, sticky="w", **pad_args)
        self.delay_random_upper_var = ctk.DoubleVar(value=self.settings.delay_random_upper)
        delay_upper_entry = ctk.CTkEntry(
            main_frame, textvariable=self.delay_random_upper_var, width=std_wid * 10
        )
        delay_upper_entry.grid(row=cur_row, column=2, sticky="w", **pad_args)

        cur_row += 1
        label_settings_tips = ctk.CTkLabel(
            main_frame, text=self.settings.lan().SETTINGS_TIPS, width=std_wid * 10
        )
        label_settings_tips.grid(row=cur_row, column=0, columnspan=4, sticky="w", **pad_args)

        #endregion

        #region Control Buttons
        # Save and cancel buttons
        button_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        button_frame.pack(side=ctk.BOTTOM, fill=ctk.X, pady=10)
        cancel_button = ctk.CTkButton(
            button_frame, text=self.settings.lan().CANCEL, command=self._on_cancel
        )
        cancel_button.pack(side=ctk.LEFT, padx=20)
        save_button = ctk.CTkButton(
            button_frame, text=self.settings.lan().SAVE, command=self._on_save
        )
        save_button.pack(side=ctk.RIGHT, padx=20)

        #endregion

    def _on_save(self):
        """Save settings and validate inputs"""
        # Get values from entry fields, validate, and save them
        size_list = self.client_size_var.get().split(" x ")
        width_new = int(size_list[0])
        height_new = int(size_list[1])
        ms_url_new = self.ms_url_var.get()

        mitm_port_new = int(self.mitm_port_var.get())
        if not self.settings.valid_mitm_port(mitm_port_new):
            messagebox.showerror("⚠", self.settings.lan().MITM_PORT_ERROR_PROMPT)
            return
        upstream_proxy_new = self.upstream_proxy_var.get()
        proxy_inject_new = self.proxy_inject_var.get()
        if (
            upstream_proxy_new != self.settings.upstream_proxy
            or mitm_port_new != self.settings.mitm_port
            or proxy_inject_new != self.settings.enable_proxinject
        ):

            self.mitm_proxinject_updated = True

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
            self.settings.model_type != model_type_new
            or self.settings.model_file != model_file_new
            or self.settings.model_file_3p != mode_file_3p_new
            or self.settings.akagi_ot_url != akagi_url_new
            or self.settings.akagi_ot_apikey != akagi_apikey_new
            or self.settings.mjapi_url != mjapi_url_new
            or self.settings.mjapi_user != mjapi_user_new
            or self.settings.mjapi_secret != mjapi_secret_new
            or self.settings.mjapi_model_select != mjapi_model_select_new
        ):
            self.model_updated = True

        randomized_choice_new: int = int(self.randomized_choice_var.get().split(" ")[0])
        reply_emoji_new: float = int(self.reply_emoji_var.get().split("%")[0]) / 100
        try:
            delay_lower_new = self.delay_random_lower_var.get()
            delay_upper_new = self.delay_random_upper_var.get()
        except Exception as _e:
            messagebox.showerror("⚠", self.settings.lan().RANDOM_DELAY_RANGE)
            return
        delay_lower_new = max(0, delay_lower_new)
        delay_upper_new = max(delay_lower_new, delay_upper_new)

        self.settings.auto_launch_browser = self.auto_launch_var.get()
        self.settings.browser_width = width_new
        self.settings.browser_height = height_new
        self.settings.ms_url = ms_url_new
        self.settings.enable_chrome_ext = self.enable_extension_var.get()
        self.settings.mitm_port = mitm_port_new
        self.settings.upstream_proxy = upstream_proxy_new
        self.settings.language = language_new
        self.settings.enable_proxinject = proxy_inject_new

        self.settings.model_type = model_type_new
        self.settings.model_file = model_file_new
        self.settings.model_file_3p = mode_file_3p_new
        self.settings.akagi_ot_url = akagi_url_new
        self.settings.akagi_ot_apikey = akagi_apikey_new
        self.settings.mjapi_url = mjapi_url_new
        self.settings.mjapi_user = mjapi_user_new
        self.settings.mjapi_secret = mjapi_secret_new
        self.settings.mjapi_model_select = mjapi_model_select_new

        self.settings.auto_idle_move = self.auto_idle_move_var.get()
        self.settings.auto_dahai_drag = self.auto_drag_dahai_var.get()
        self.settings.auto_random_move = self.random_move_var.get()
        self.settings.ai_randomize_choice = randomized_choice_new
        self.settings.auto_reply_emoji_rate = reply_emoji_new
        self.settings.delay_random_lower = delay_lower_new
        self.settings.delay_random_upper = delay_upper_new

        self.settings.save_json()
        self.exit_save = True
        if self.mitm_proxinject_updated:
            messagebox.showinfo(
                title=self.settings.lan().SETTINGS,
                message=self.settings.lan().SETTINGS_TIPS,
                parent=self,
                icon="info",
            )
        self.destroy()

    def _on_cancel(self):
        """Cancel and close the settings window"""
        LOGGER.info("Closing settings window without saving")
        self.exit_save = False
        self.destroy()

    def _on_appearance_change(self, event=None):
        """处理外观模式变化"""
        current_system_appearance = ctk.get_appearance_mode()
        self.configure(fg_color=("gray95", "gray10")[current_system_appearance == "Dark"])
