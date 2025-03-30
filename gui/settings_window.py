"""GUI Settings Window"""
import os # <-- Import os for path checking
import tkinter as tk # <-- Import tk for TclError
import customtkinter as ctk
from tkinter import messagebox
from PIL import ImageTk # <-- Import ImageTk for type checking PhotoImage
from common.utils import Folder, list_children
from common.log_helper import LOGGER
from common.settings import Settings
from common.lan_str import LAN_OPTIONS
from bot import MODEL_TYPE_STRINGS

class SettingsWindow(ctk.CTkToplevel):
    """Settings dialog window"""
    def __init__(self, parent: ctk.CTk, setting: Settings): # Type hint parent as ctk.CTk
        super().__init__(parent)
        self.settings = setting
        self._parent = parent # Store the parent reference

        # Keep this line? It might be relevant for CTk's own handling. Let's keep it for now.
        # self._iconify_enabled = False # Comment says: Disable customtkinter default icon override

        # --- Window geometry and setup ---
        self.geometry("880x830")
        self.minsize(880, 830)
        try: # Add try-except for robustness during positioning
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            self.geometry(f"+{parent_x+10}+{parent_y+10}")
        except Exception as e_pos:
            LOGGER.warning(f"无法获取父窗口位置来定位设置窗口: {e_pos}")
            # Fallback position if needed, e.g., self.geometry("+100+100")

        # --- Icon Setup ---
        self._setup_icon() # <-- Call the new method to set the icon

        self.bind("<<AppearanceModeChanged>>", self._on_appearance_change)

        # Flags
        self.exit_save: bool = False
        self.gui_need_reload: bool = False
        self.model_updated: bool = False
        self.mitm_proxinject_updated: bool = False

        # Initialize appearance (already done by CTkToplevel?)
        # ctk.set_appearance_mode("System") # Usually inherits from parent
        # ctk.set_default_color_theme("blue") # Usually inherits from parent

        # Create widgets after setting up window properties
        self.create_widgets()

    def _setup_icon(self):
        """Set the window icon using the parent's icon data."""
        LOGGER.debug("开始设置 SettingsWindow 图标...")
        # 从父窗口 (_parent) 获取图标数据
        parent_icon_path_ico = getattr(self._parent, 'app_icon_path_ico', None)
        parent_icon_photo = getattr(self._parent, 'app_icon_photo', None)

        # 1. 【立即尝试】设置 .ico (使用 wm_iconbitmap) - 主要影响任务栏等
        if parent_icon_path_ico and os.path.exists(parent_icon_path_ico):
            try:
                self.wm_iconbitmap(parent_icon_path_ico)
                LOGGER.debug(f"SettingsWindow 尝试设置 wm_iconbitmap: {parent_icon_path_ico}")
            except tk.TclError as e_wm_ico:
                 LOGGER.warning(f"SettingsWindow 设置 wm_iconbitmap 时发生 TclError: {e_wm_ico}")
            except Exception as e_wm_ico_gen:
                 LOGGER.warning(f"SettingsWindow 设置 wm_iconbitmap 失败: {e_wm_ico_gen}", exc_info=True)
        else:
             LOGGER.debug("SettingsWindow: 未从父窗口获取到有效的 .ico 路径用于 wm_iconbitmap。")

        # 2. 【延迟执行】使用 after 设置 PhotoImage (关键步骤，用于窗口左上角)
        if parent_icon_photo and isinstance(parent_icon_photo, ImageTk.PhotoImage):
            try:
                # 使用与 ConfirmExitDialog 相同的延迟
                self.after(210, lambda: self.iconphoto(False, parent_icon_photo))
                LOGGER.debug("SettingsWindow: 已安排 iconphoto 设置。")
            except Exception as e_schedule:
                LOGGER.error(f"SettingsWindow 安排 iconphoto 设置失败: {e_schedule}", exc_info=True)
        else:
             LOGGER.debug("SettingsWindow: 未从父窗口获取到有效的 PhotoImage 对象用于 iconphoto。")
        LOGGER.debug("SettingsWindow 图标设置结束。")


    def create_widgets(self):
        """Create widgets for settings dialog"""
        self.title(self.settings.lan().SETTINGS)

        # Create main container frame
        main_frame = ctk.CTkFrame(self, corner_radius=10)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        pad_args = {"padx": 5, "pady": 5}
        std_wid = 15 # Standard width unit? Assume it's defined elsewhere or use a fixed value
        cur_row = 0

        # --- Widgets creation logic (保持不变) ---
        #region Browser and Client Settings
        # ... (保持不变) ...
        label_browser = ctk.CTkLabel(main_frame, text=self.settings.lan().BROWSER)
        label_browser.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.auto_launch_var = ctk.BooleanVar(value=self.settings.auto_launch_browser)
        auto_launch_checkbox = ctk.CTkCheckBox(main_frame, variable=self.auto_launch_var, text=self.settings.lan().AUTO_LAUNCH_BROWSER, width=std_wid * 10)
        auto_launch_checkbox.grid(row=cur_row, column=1, sticky="w", **pad_args)
        label_client_size = ctk.CTkLabel(main_frame, text=self.settings.lan().CLIENT_SIZE)
        label_client_size.grid(row=cur_row, column=2, sticky="e", **pad_args)
        size_options = ["960 x 540", "1280 x 720", "1600 x 900", "1920 x 1080", "2560 x 1440", "3840 x 2160"]
        setting_size = f"{self.settings.browser_width} x {self.settings.browser_height}"
        self.client_size_var = ctk.StringVar(value=setting_size)
        client_size_menu = ctk.CTkOptionMenu(main_frame, variable=self.client_size_var, values=size_options, width=std_wid * 15)
        client_size_menu.grid(row=cur_row, column=3, sticky="w", **pad_args)
        cur_row += 1
        label_ms_url = ctk.CTkLabel(main_frame, text=self.settings.lan().MAJSOUL_URL)
        label_ms_url.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.ms_url_var = ctk.StringVar(value=self.settings.ms_url)
        ms_url_entry = ctk.CTkEntry(main_frame, textvariable=self.ms_url_var, width=std_wid * 30)
        ms_url_entry.grid(row=cur_row, column=1, columnspan=2, sticky="w", **pad_args)
        self.enable_extension_var = ctk.BooleanVar(value=self.settings.enable_chrome_ext)
        enable_extension_checkbox = ctk.CTkCheckBox(main_frame, variable=self.enable_extension_var, text=self.settings.lan().ENABLE_CHROME_EXT, width=std_wid * 10)
        enable_extension_checkbox.grid(row=cur_row, column=3, sticky="w", **pad_args)
        cur_row += 1
        #endregion

        #region Network Settings
        # ... (保持不变) ...
        label_mitm_port = ctk.CTkLabel(main_frame, text=self.settings.lan().MITM_PORT)
        label_mitm_port.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mitm_port_var = ctk.StringVar(value=self.settings.mitm_port)
        mitm_port_entry = ctk.CTkEntry(main_frame, textvariable=self.mitm_port_var, width=std_wid * 15)
        mitm_port_entry.grid(row=cur_row, column=1, sticky="w", **pad_args)
        label_upstream_proxy = ctk.CTkLabel(main_frame, text=self.settings.lan().UPSTREAM_PROXY)
        label_upstream_proxy.grid(row=cur_row, column=2, sticky="e", **pad_args)
        self.upstream_proxy_var = ctk.StringVar(value=self.settings.upstream_proxy)
        upstream_proxy_entry = ctk.CTkEntry(main_frame, textvariable=self.upstream_proxy_var, width=std_wid * 15)
        upstream_proxy_entry.grid(row=cur_row, column=3, sticky="w", **pad_args)
        cur_row += 1
        label_language = ctk.CTkLabel(main_frame, text=self.settings.lan().LANGUAGE)
        label_language.grid(row=cur_row, column=0, sticky="e", **pad_args)
        language_options = [v.LANGUAGE_NAME for v in LAN_OPTIONS.values()]
        self.language_var = ctk.StringVar(value=LAN_OPTIONS[self.settings.language].LANGUAGE_NAME)
        language_menu = ctk.CTkOptionMenu(main_frame, variable=self.language_var, values=language_options, width=std_wid * 10)
        language_menu.grid(row=cur_row, column=1, sticky="w", **pad_args)
        self.proxy_inject_var = ctk.BooleanVar(value=self.settings.enable_proxinject)
        proxy_inject_checkbox = ctk.CTkCheckBox(main_frame, variable=self.proxy_inject_var, text=self.settings.lan().CLIENT_INJECT_PROXY, width=std_wid * 20)
        proxy_inject_checkbox.grid(row=cur_row, column=2, columnspan=2, sticky="w", **pad_args)
        cur_row += 1
        separator1 = ctk.CTkFrame(main_frame, height=1, fg_color=("gray70", "gray30")) # Use a Frame for separator
        separator1.grid(row=cur_row, column=0, columnspan=4, sticky="ew", pady=10)
        #endregion

        #region Model Settings
        # ... (保持不变) ...
        cur_row += 1
        label_model_type = ctk.CTkLabel(main_frame, text=self.settings.lan().MODEL_TYPE)
        label_model_type.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.model_type_var = ctk.StringVar(value=self.settings.model_type)
        model_type_menu = ctk.CTkOptionMenu(main_frame, variable=self.model_type_var, values=MODEL_TYPE_STRINGS, width=std_wid * 10)
        model_type_menu.grid(row=cur_row, column=1, sticky="w", **pad_args)
        cur_row += 1
        label_ai_model_file = ctk.CTkLabel(main_frame, text=self.settings.lan().AI_MODEL_FILE)
        label_ai_model_file.grid(row=cur_row, column=0, sticky="e", **pad_args)
        model_files = [""] + list_children(Folder.MODEL)
        self.model_file_var = ctk.StringVar(value=self.settings.model_file)
        model_file_menu = ctk.CTkOptionMenu(main_frame, variable=self.model_file_var, values=model_files, width=std_wid * 30)
        model_file_menu.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)
        cur_row += 1
        label_ai_model_file_3p = ctk.CTkLabel(main_frame, text=self.settings.lan().AI_MODEL_FILE_3P)
        label_ai_model_file_3p.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.model_file_3p_var = ctk.StringVar(value=self.settings.model_file_3p)
        model_file_3p_menu = ctk.CTkOptionMenu(main_frame, variable=self.model_file_3p_var, values=model_files, width=std_wid * 30)
        model_file_3p_menu.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)
        cur_row += 1
        label_akagi_ot_url = ctk.CTkLabel(main_frame, text=self.settings.lan().AKAGI_OT_URL)
        label_akagi_ot_url.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.akagiot_url_var = ctk.StringVar(value=self.settings.akagi_ot_url)
        akagi_ot_url_entry = ctk.CTkEntry(main_frame, textvariable=self.akagiot_url_var, width=std_wid * 41)
        akagi_ot_url_entry.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)
        cur_row += 1
        label_akagi_ot_apikey = ctk.CTkLabel(main_frame, text=self.settings.lan().AKAGI_OT_APIKEY)
        label_akagi_ot_apikey.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.akagiot_apikey_var = ctk.StringVar(value=self.settings.akagi_ot_apikey)
        akagi_ot_apikey_entry = ctk.CTkEntry(main_frame, textvariable=self.akagiot_apikey_var, width=std_wid * 41)
        akagi_ot_apikey_entry.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)
        cur_row += 1
        label_mjapi_url = ctk.CTkLabel(main_frame, text=self.settings.lan().MJAPI_URL)
        label_mjapi_url.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mjapi_url_var = ctk.StringVar(value=self.settings.mjapi_url)
        mjapi_url_entry = ctk.CTkEntry(main_frame, textvariable=self.mjapi_url_var, width=std_wid * 41)
        mjapi_url_entry.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)
        cur_row += 1
        label_mjapi_user = ctk.CTkLabel(main_frame, text=self.settings.lan().MJAPI_USER)
        label_mjapi_user.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mjapi_user_var = ctk.StringVar(value=self.settings.mjapi_user)
        mjapi_user_entry = ctk.CTkEntry(main_frame, textvariable=self.mjapi_user_var, width=std_wid * 10)
        mjapi_user_entry.grid(row=cur_row, column=1, sticky="w", **pad_args)
        cur_row += 1 # MJAPI Secret should be on a new row
        label_mjapi_secret = ctk.CTkLabel(main_frame, text=self.settings.lan().MJAPI_SECRET)
        label_mjapi_secret.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mjapi_secret_var = ctk.StringVar(value=self.settings.mjapi_secret)
        mjapi_secret_entry = ctk.CTkEntry(main_frame, textvariable=self.mjapi_secret_var, width=std_wid * 41)
        mjapi_secret_entry.grid(row=cur_row, column=1, columnspan=3, sticky="w", **pad_args)
        cur_row += 1
        label_mjapi_model_select = ctk.CTkLabel(main_frame, text=self.settings.lan().MJAPI_MODEL_SELECT)
        label_mjapi_model_select.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.mjapi_model_select_var = ctk.StringVar(value=self.settings.mjapi_model_select)
        mjapi_models = self.settings.mjapi_models
        mjapi_model_select_menu = ctk.CTkOptionMenu(main_frame, variable=self.mjapi_model_select_var, values=mjapi_models, width=std_wid * 10)
        mjapi_model_select_menu.grid(row=cur_row, column=1, sticky="w", **pad_args)
        label_login_to_refresh = ctk.CTkLabel(main_frame, text=self.settings.lan().LOGIN_TO_REFRESH)
        label_login_to_refresh.grid(row=cur_row, column=2, sticky="w", **pad_args)
        cur_row += 1
        separator2 = ctk.CTkFrame(main_frame, height=1, fg_color=("gray70", "gray30"))
        separator2.grid(row=cur_row, column=0, columnspan=4, sticky="ew", pady=10)
        #endregion

        #region Auto Play Settings
        # ... (保持不变) ...
        cur_row += 1
        label_auto_play_settings = ctk.CTkLabel(main_frame, text=self.settings.lan().AUTO_PLAY_SETTINGS)
        label_auto_play_settings.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.random_move_var = ctk.BooleanVar(value=self.settings.auto_random_move)
        random_move_checkbox = ctk.CTkCheckBox(main_frame, variable=self.random_move_var, text=self.settings.lan().MOUSE_RANDOM_MOVE, width=std_wid * 10)
        random_move_checkbox.grid(row=cur_row, column=1, sticky="w", **pad_args)
        self.auto_idle_move_var = ctk.BooleanVar(value=self.settings.auto_idle_move)
        auto_idle_move_checkbox = ctk.CTkCheckBox(main_frame, variable=self.auto_idle_move_var, text=self.settings.lan().AUTO_IDLE_MOVE, width=std_wid * 10)
        auto_idle_move_checkbox.grid(row=cur_row, column=2, sticky="w", **pad_args)
        self.auto_drag_dahai_var = ctk.BooleanVar(value=self.settings.auto_dahai_drag)
        auto_drag_dahai_checkbox = ctk.CTkCheckBox(main_frame, variable=self.auto_drag_dahai_var, text=self.settings.lan().DRAG_DAHAI, width=std_wid * 10)
        auto_drag_dahai_checkbox.grid(row=cur_row, column=3, sticky="w", **pad_args)
        cur_row += 1
        label_random_choice = ctk.CTkLabel(main_frame, text=self.settings.lan().RANDOM_CHOICE)
        label_random_choice.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.randomized_choice_var = ctk.StringVar(value=str(self.settings.ai_randomize_choice))
        random_choice_options = ["0 (Off)", "1", "2", "3", "4", "5"]
        random_choice_menu = ctk.CTkOptionMenu(main_frame, variable=self.randomized_choice_var, values=random_choice_options, width=std_wid * 10)
        random_choice_menu.grid(row=cur_row, column=1, sticky="w", **pad_args)
        label_reply_emoji_chance = ctk.CTkLabel(main_frame, text=self.settings.lan().REPLY_EMOJI_CHANCE)
        label_reply_emoji_chance.grid(row=cur_row, column=2, sticky="e", **pad_args)
        reply_emoji_options = [f"{i*10}%" for i in range(11)]
        reply_emoji_options[0] = "0% (off)"
        self.reply_emoji_var = ctk.StringVar(value=f"{int(self.settings.auto_reply_emoji_rate * 100)}%")
        reply_emoji_menu = ctk.CTkOptionMenu(main_frame, variable=self.reply_emoji_var, values=reply_emoji_options, width=std_wid * 10)
        reply_emoji_menu.grid(row=cur_row, column=3, sticky="w", **pad_args)
        cur_row += 1
        label_random_delay_range = ctk.CTkLabel(main_frame, text=self.settings.lan().RANDOM_DELAY_RANGE)
        label_random_delay_range.grid(row=cur_row, column=0, sticky="e", **pad_args)
        self.delay_random_lower_var = ctk.DoubleVar(value=self.settings.delay_random_lower)
        delay_lower_entry = ctk.CTkEntry(main_frame, textvariable=self.delay_random_lower_var, width=std_wid * 10)
        delay_lower_entry.grid(row=cur_row, column=1, sticky="w", **pad_args)
        self.delay_random_upper_var = ctk.DoubleVar(value=self.settings.delay_random_upper)
        delay_upper_entry = ctk.CTkEntry(main_frame, textvariable=self.delay_random_upper_var, width=std_wid * 10)
        delay_upper_entry.grid(row=cur_row, column=2, sticky="w", **pad_args)
        cur_row += 1
        label_settings_tips = ctk.CTkLabel(main_frame, text=self.settings.lan().SETTINGS_TIPS, justify="center" )
        label_settings_tips.grid(row=cur_row, column=0, columnspan=4, sticky="w", **pad_args)
        #endregion

        # --- Control Buttons (保持不变) ---
        #region Control Buttons
        button_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        # Pack to bottom of the window, not inside main_frame
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(10, 20)) # Adjusted padding
        # Center buttons within the frame
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        cancel_button = ctk.CTkButton(button_frame, text=self.settings.lan().CANCEL, command=self._on_cancel)
        # Use grid for better control within button_frame
        cancel_button.grid(row=0, column=0, padx=(0, 10), sticky="e")
        save_button = ctk.CTkButton(button_frame, text=self.settings.lan().SAVE, command=self._on_save)
        save_button.grid(row=0, column=1, padx=(10, 0), sticky="w")
        #endregion

    def _on_save(self):
        """Save settings and validate inputs"""
        # --- 保存逻辑 (保持不变) ---
        try: # Add try-except around parsing/validation
            size_list = self.client_size_var.get().split(" x ")
            width_new = int(size_list[0])
            height_new = int(size_list[1])
            ms_url_new = self.ms_url_var.get()

            mitm_port_new = int(self.mitm_port_var.get())
            if not self.settings.valid_mitm_port(mitm_port_new):
                messagebox.showerror("⚠", self.settings.lan().MITM_PORT_ERROR_PROMPT, parent=self) # Specify parent
                return
            upstream_proxy_new = self.upstream_proxy_var.get()
            proxy_inject_new = self.proxy_inject_var.get()
            if (upstream_proxy_new != self.settings.upstream_proxy or
                mitm_port_new != self.settings.mitm_port or
                proxy_inject_new != self.settings.enable_proxinject):
                self.mitm_proxinject_updated = True

            language_name = self.language_var.get()
            language_new = None
            for code, lan in LAN_OPTIONS.items():
                if language_name == lan.LANGUAGE_NAME: language_new = code; break
            if self.settings.language != language_new: self.gui_need_reload = True
            else: self.gui_need_reload = False # Ensure flag is reset if language didn't change

            model_type_new = self.model_type_var.get()
            model_file_new = self.model_file_var.get()
            mode_file_3p_new = self.model_file_3p_var.get()
            akagi_url_new = self.akagiot_url_var.get()
            akagi_apikey_new = self.akagiot_apikey_var.get()
            mjapi_url_new = self.mjapi_url_var.get()
            mjapi_user_new = self.mjapi_user_var.get()
            mjapi_secret_new = self.mjapi_secret_var.get()
            mjapi_model_select_new = self.mjapi_model_select_var.get()
            if (self.settings.model_type != model_type_new or self.settings.model_file != model_file_new or
                self.settings.model_file_3p != mode_file_3p_new or self.settings.akagi_ot_url != akagi_url_new or
                self.settings.akagi_ot_apikey != akagi_apikey_new or self.settings.mjapi_url != mjapi_url_new or
                self.settings.mjapi_user != mjapi_user_new or self.settings.mjapi_secret != mjapi_secret_new or
                self.settings.mjapi_model_select != mjapi_model_select_new):
                self.model_updated = True

            randomized_choice_new: int = int(self.randomized_choice_var.get().split(" ")[0])
            reply_emoji_new: float = int(self.reply_emoji_var.get().split("%")[0]) / 100
            try:
                delay_lower_new = self.delay_random_lower_var.get()
                delay_upper_new = self.delay_random_upper_var.get()
            except tk.TclError: # Catch specific error for double var
                messagebox.showerror("⚠", self.settings.lan().RANDOM_DELAY_RANGE + " (输入无效)", parent=self)
                return
            delay_lower_new = max(0.0, delay_lower_new) # Ensure float comparison
            delay_upper_new = max(delay_lower_new, delay_upper_new) # Ensure upper >= lower

            # --- Update settings object (Assign validated values) ---
            self.settings.auto_launch_browser = self.auto_launch_var.get()
            self.settings.browser_width = width_new; self.settings.browser_height = height_new
            self.settings.ms_url = ms_url_new; self.settings.enable_chrome_ext = self.enable_extension_var.get()
            self.settings.mitm_port = mitm_port_new; self.settings.upstream_proxy = upstream_proxy_new
            self.settings.language = language_new; self.settings.enable_proxinject = proxy_inject_new
            self.settings.model_type = model_type_new; self.settings.model_file = model_file_new
            self.settings.model_file_3p = mode_file_3p_new; self.settings.akagi_ot_url = akagi_url_new
            self.settings.akagi_ot_apikey = akagi_apikey_new; self.settings.mjapi_url = mjapi_url_new
            self.settings.mjapi_user = mjapi_user_new; self.settings.mjapi_secret = mjapi_secret_new
            self.settings.mjapi_model_select = mjapi_model_select_new
            self.settings.auto_idle_move = self.auto_idle_move_var.get(); self.settings.auto_dahai_drag = self.auto_drag_dahai_var.get()
            self.settings.auto_random_move = self.random_move_var.get(); self.settings.ai_randomize_choice = randomized_choice_new
            self.settings.auto_reply_emoji_rate = reply_emoji_new; self.settings.delay_random_lower = delay_lower_new
            self.settings.delay_random_upper = delay_upper_new

            self.settings.save_json()
            self.exit_save = True
            if self.mitm_proxinject_updated:
                messagebox.showinfo(title=self.settings.lan().SETTINGS, message=self.settings.lan().SETTINGS_TIPS, parent=self, icon="info")
            self.destroy()

        except ValueError as ve: # Catch potential int/float conversion errors
             messagebox.showerror("⚠", f"输入错误: {ve}", parent=self)
        except Exception as e_save: # Catch other unexpected errors
             LOGGER.error(f"保存设置时发生错误: {e_save}", exc_info=True)
             messagebox.showerror("错误", f"保存设置时出错:\n{e_save}", parent=self)


    def _on_cancel(self):
        """Cancel and close the settings window"""
        LOGGER.info("关闭设置窗口，未保存。")
        self.exit_save = False
        self.destroy()

    def _on_appearance_change(self, event=None):
        """处理外观模式变化"""
        # This might not be necessary if CTkToplevel handles it, but can be kept as a fallback
        LOGGER.debug("SettingsWindow 检测到外观模式变化。")
        # current_system_appearance = ctk.get_appearance_mode()
        # self.configure(fg_color=("gray95", "gray10")[current_system_appearance == "Dark"])