"""
Main GUI implementation for Mahjong Copilot (CustomTkinter Version) - Optimized
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from typing import Tuple, Any, Dict, Optional
import customtkinter as ctk
from PIL import Image, ImageTk

# Assume these imports are adjusted if necessary
from bot_manager import BotManager, mjai_reaction_2_guide
from common.utils import Folder, GameMode, GAME_MODES, GameClientType
from common.utils import UiState, sub_file, error_to_str
from common.log_helper import LOGGER, LogHelper
from common.settings import Settings
from common.mj_helper import GameInfo, MJAI_TILE_2_UNICODE
from updater import Updater, UpdateStatus
from .settings_window import SettingsWindow
from .dialogs import ConfirmExitDialog
from .help_window import HelpWindow
# Import the CORRECTLY REFACTORED widgets
from .widgets import ToolBar, StatusBar, Timer

# ================= Constants =================
PADX = 10
PADY_OUTER = (10, 5)
PADY_INNER = 5
TOOLBAR_HEIGHT = 40
TB2_HEIGHT = 70
AI_GUIDE_HEIGHT = 120
STATUS_BAR_HEIGHT = 26
DEFAULT_WINDOW_SIZE = (720, 580)
GUI_UPDATE_INTERVAL_MS = 50 # Update frequency in milliseconds

# ================= MainGUI Class =================
class MainGUI(ctk.CTk):
    """ Main GUI Window (CustomTkinter Version) - Optimized"""
    def __init__(self, setting: Settings, bot_manager: BotManager):
        super().__init__() # *** 调用父类 CTk 的初始化是第一步 ***
        self.bot_manager = bot_manager
        self.st = setting
        self.updater = Updater(self.st.update_url)
        self._cached_widget_states: Dict[str, Any] = {} # Cache for GUI states

        # --- 【修改】初始化图标属性 (在调用任何可能使用它们的方法之前) ---
        self.app_icon_path_ico = None # 用于 iconbitmap 的 .ico 路径
        self.app_icon_photo = None    # 用于 iconphoto 的 PhotoImage 对象

        # --- 按顺序执行初始化步骤 ---
        self._setup_ctk()
        self._load_fonts()
        self._setup_window() # <-- 这里会设置上面的图标属性
        self._load_icons()   # 加载状态栏等其他小图标 (确保在 setup_window 之后)
        self._create_widgets()
        self._init_gui_state() # Set initial states based on settings

        # --- Start Background Tasks ---
        self.after(100, self.updater.load_help)
        self.after(500, self.updater.check_update)
        self.bot_manager.start()
        self._schedule_gui_update() # Start the optimized GUI update loop

    def _setup_ctk(self):
        """Configure CustomTkinter appearance."""
        ctk.set_appearance_mode("System") # Follow system
        ctk.set_default_color_theme("blue")

    def _load_fonts(self):
        """Load fonts used in the GUI."""
        self.header_font = ctk.CTkFont(size=14, weight="bold")
        self.content_font = ctk.CTkFont(size=12)
        self.emoji_font = ctk.CTkFont(family="Segoe UI Emoji", size=18)
        self.ai_guide_font = ctk.CTkFont(family="Segoe UI Emoji", size=16)

    def _setup_window(self):
        """Set up main window properties (icon, title, size, protocols).【核心修改处】"""
        # 再次确认属性已初始化 (在 __init__ 中已做)
        self.app_icon_path_ico = None
        self.app_icon_photo = None
        LOGGER.debug("开始 _setup_window...")

        try:
            res_folder = getattr(Folder, 'RES', None)
            LOGGER.debug(f"资源文件夹 (Folder.RES): {res_folder}")
            if res_folder and os.path.isdir(res_folder):

                # --- 1. 处理 .ico 文件，用于 iconbitmap (任务栏等) ---
                icon_filename_ico = 'icon.ico'
                icon_path_ico = sub_file(res_folder, icon_filename_ico)
                LOGGER.debug(f"尝试 .ico 路径: {icon_path_ico}")
                if os.path.exists(icon_path_ico):
                    try:
                        self.iconbitmap(icon_path_ico)
                        self.app_icon_path_ico = icon_path_ico # 保存路径供对话框使用
                        LOGGER.info(f"主窗口 iconbitmap 已从设置: {icon_path_ico}")
                    except tk.TclError as e_ico:
                        LOGGER.error(f"设置 iconbitmap 时发生 TclError (文件 '{icon_path_ico}' 是有效的 .ico 吗?): {e_ico}", exc_info=False)
                    except Exception as e_ico_gen:
                        LOGGER.error(f"从 '{icon_path_ico}' 设置 iconbitmap 失败: {e_ico_gen}", exc_info=True)
                else:
                    LOGGER.warning(f"窗口图标 (.ico) 未找到: {icon_path_ico}")

                # --- 2. 处理图像文件 (优先 .png)，用于 iconphoto (窗口左上角) ---
                icon_filename_photo = 'icon.png' # 优先使用 png
                icon_path_photo = sub_file(res_folder, icon_filename_photo)
                LOGGER.debug(f"尝试 .png 路径: {icon_path_photo}")
                photo_source_path = None # 记录实际使用的源文件

                if os.path.exists(icon_path_photo):
                     photo_source_path = icon_path_photo
                elif self.app_icon_path_ico: # .png 未找到，尝试用 .ico 作为备选
                     LOGGER.info(f"图标 '{icon_filename_photo}' 未找到，尝试使用 '{icon_filename_ico}' 作为 iconphoto 源。")
                     photo_source_path = self.app_icon_path_ico
                # else: # 两者都找不到

                if photo_source_path: # 如果找到了源文件
                    try:
                        LOGGER.debug(f"尝试从 {photo_source_path} 加载 iconphoto")
                        image = Image.open(photo_source_path)
                        # 可选：调整大小
                        # image = image.resize((16, 16), Image.Resampling.LANCZOS)
                        # 【关键】创建 PhotoImage 并保存在实例变量中
                        self.app_icon_photo = ImageTk.PhotoImage(image)
                        # 【关键】将 PhotoImage 应用到主窗口自身
                        self.iconphoto(False, self.app_icon_photo)
                        LOGGER.info(f"主窗口 iconphoto 已从设置: {photo_source_path}")
                    except Exception as e_photo:
                        # 捕获 PIL 打开、创建 PhotoImage 或 tk 设置 iconphoto 的错误
                        LOGGER.error(f"从 '{photo_source_path}' 加载或设置 iconphoto 失败: {e_photo}", exc_info=True)
                else:
                     LOGGER.warning(f"未能找到适用于 iconphoto 的图标文件 (已检查 '{icon_filename_photo}' 和备选)。")

            else:
                LOGGER.error("在加载图标时，Folder.RES 未定义或不是一个目录。")
        except AttributeError as e_attr:
             LOGGER.error(f"设置图标时发生 AttributeError (请检查 Folder/sub_file 是否正确?): {e_attr}", exc_info=True)
        except Exception as e_gen:
            # 捕获其他意外错误
            LOGGER.error(f"设置窗口图标时发生一般错误: {e_gen}", exc_info=True)

        # --- 窗口设置的其余部分 ---
        self.protocol("WM_DELETE_WINDOW", self._on_exit)
        self.geometry(f"{DEFAULT_WINDOW_SIZE[0]}x{DEFAULT_WINDOW_SIZE[1]}")
        self.minsize(*DEFAULT_WINDOW_SIZE)
        try:
            self.title(self.st.lan().APP_TITLE)
        except AttributeError:
            self.title("Mahjong Copilot")
            LOGGER.error("无法从语言设置加载 APP_TITLE。")
        LOGGER.debug("_setup_window 完成。")


    def _load_icons(self):
        """Load paths to status icons (for status bar etc.)."""
        LOGGER.debug("开始 _load_icons...") # 添加日志，确认它在 _setup_window 之后被调用
        self.icons = {}
        res_folder = getattr(Folder, 'RES', None)
        if res_folder and os.path.isdir(res_folder):
            icon_files = {
                'green': 'green.png', 'red': 'red.png', 'yellow': 'yellow.png',
                'gray': 'gray.png', 'ready': 'ready.png', 'help': 'help.png',
                'help_update': 'help_update.png', 'majsoul': 'majsoul.png',
                'settings': 'settings.png', 'log': 'log.png', 'exit': 'exit.png'
                # 注意：主窗口的大图标 icon.ico/icon.png 在 _setup_window 中处理
            }
            for name, filename in icon_files.items():
                path = sub_file(res_folder, filename)
                if os.path.exists(path):
                    self.icons[name] = path
                    #LOGGER.debug(f"图标已加载: {name} -> {path}")
                else:
                    self.icons[name] = None
                    LOGGER.warning(f"图标文件未找到: {path}")
            LOGGER.info("状态图标加载完成。")
        else:
             LOGGER.error("Folder.RES 未定义或不是目录，无法加载状态图标。")
             # 确保即使加载失败，icons 字典的键也存在，避免后续 KeyError
             for name in ['green', 'red', 'yellow', 'gray', 'ready', 'help', 'help_update', 'majsoul', 'settings', 'log', 'exit']:
                 self.icons.setdefault(name, None)
        LOGGER.debug("_load_icons 完成。")


    def _create_widgets(self):
        """Create all widgets in the main window."""
        LOGGER.debug("开始 _create_widgets...")
        # Main grid frame setup
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=0, pady=0)
        self.grid_frame.grid_columnconfigure(0, weight=1)
        row_weights = {0: 0, 1: 0, 2: 1, 3: 0, 4: 0, 5: 0}
        for i, weight in row_weights.items():
            self.grid_frame.grid_rowconfigure(i, weight=weight)

        cur_row = 0
        self._create_toolbar1(self.grid_frame, cur_row)
        cur_row += 1
        self._create_toolbar2(self.grid_frame, cur_row)
        cur_row += 1
        self._create_ai_section(self.grid_frame, cur_row)
        cur_row += 1
        self._create_game_info_section(self.grid_frame, cur_row)
        cur_row += 1
        self._create_status_bars(self.grid_frame, cur_row) # 注意这里是 cur_row，不是固定的 4
        LOGGER.debug("_create_widgets 完成。")

    def _create_toolbar1(self, parent, row):
        """Create the main toolbar (row 0)."""
        self.toolbar = ToolBar(parent, height=TOOLBAR_HEIGHT)
        self.toolbar.grid(row=row, column=0, sticky="ew", padx=PADX, pady=(PADY_OUTER[0], PADY_INNER))

        self.toolbar.add_sep()
        self.btn_start_browser = self.toolbar.add_button(
            self.st.lan().START_BROWSER, self.icons.get('majsoul'), self._on_btn_start_browser_clicked
        )
        self.toolbar.add_sep()
        self.toolbar.add_button(self.st.lan().SETTINGS, self.icons.get('settings'), self._on_btn_settings_clicked)
        self.toolbar.add_button(self.st.lan().OPEN_LOG_FILE, self.icons.get('log'), self._on_btn_log_clicked)
        self.btn_help = self.toolbar.add_button(self.st.lan().HELP, self.icons.get('help'), self._on_btn_help_clicked)
        self.toolbar.add_sep()
        self.toolbar.add_button(self.st.lan().EXIT, self.icons.get('exit'), self._on_exit)

    def _create_toolbar2(self, parent, row):
        """Create the second toolbar with switches and combos (row 1)."""
        self.tb2 = ToolBar(parent, height=TB2_HEIGHT)
        self.tb2.grid(row=row, column=0, sticky="ew", padx=PADX, pady=(PADY_INNER, PADY_INNER))

        self.tb2.add_sep()
        self.switch_overlay = self._create_switch_group(self.tb2, self.st.lan().WEB_OVERLAY, self._on_switch_hud_toggled)
        self.tb2.add_sep()
        self.switch_autoplay = self._create_switch_group(self.tb2, self.st.lan().AUTOPLAY, self._on_switch_autoplay_toggled)
        self.tb2.add_sep()
        self.switch_autojoin = self._create_switch_group(self.tb2, self.st.lan().AUTO_JOIN_GAME, self._on_switch_autojoin_toggled)

        combo_frame = ctk.CTkFrame(self.tb2, fg_color="transparent")
        combo_frame.pack(side="left", padx=4, pady=5, fill="y", expand=False)
        self.auto_join_level_var, level_options = self._setup_combobox_data(
            get_options=lambda: self.st.lan().GAME_LEVELS,
            get_initial_index=lambda opts: self.st.auto_join_level,
            log_prefix="Level"
        )
        self.combo_autojoin_level = ctk.CTkComboBox(
            combo_frame, variable=self.auto_join_level_var, values=level_options,
            state="readonly", command=self._on_autojoin_level_selected
        )
        self.combo_autojoin_level.grid(row=0, column=0, padx=3, pady=(5,3))
        self.auto_join_mode_var, mode_options = self._setup_combobox_data(
            get_options=lambda: self.st.lan().GAME_MODES,
            get_initial_index=lambda opts: self._get_mode_display_index(opts),
            log_prefix="Mode"
        )
        self.combo_autojoin_mode = ctk.CTkComboBox(
            combo_frame, variable=self.auto_join_mode_var, values=mode_options,
            state="readonly", command=self._on_autojoin_mode_selected
        )
        self.combo_autojoin_mode.grid(row=1, column=0, padx=3, pady=3)

        self.tb2.add_sep()
        self.timer = Timer(master=self.tb2, label_text=self.st.lan().AUTO_JOIN_TIMER, height=TB2_HEIGHT-10)
        self.timer.set_callback(self.bot_manager.disable_autojoin)
        self.timer.pack(side="left", padx=4, pady=5, fill="y", expand=False)

    def _create_switch_group(self, parent, switch_text: str, command) -> ctk.CTkSwitch:
        """Helper to create a label and switch group."""
        group_frame = ctk.CTkFrame(parent, fg_color="transparent")
        label = ctk.CTkLabel(group_frame, text=switch_text, font=ctk.CTkFont(size=11))
        switch = ctk.CTkSwitch(group_frame, text="", command=command, width=0)
        label.pack(side="top", anchor="w", pady=(2, 0))
        switch.pack(side="top", anchor="w", pady=(0, 2))
        group_frame.pack(side="left", padx=6, pady=5, fill="y", expand=False)
        return switch

    def _setup_combobox_data(self, get_options, get_initial_index, log_prefix) -> Tuple[tk.StringVar, list]:
        """Helper to safely get options and initial value for a ComboBox."""
        options = ["Error"]
        initial_index = 0
        try:
            options = get_options()
            if not isinstance(options, list) or not options:
                options = ["Error"]; LOGGER.error(f"{log_prefix} options are not a valid list.")
            else:
                 try:
                     idx = get_initial_index(options)
                     if isinstance(idx, int) and 0 <= idx < len(options): initial_index = idx
                     else: LOGGER.warning(f"Invalid initial {log_prefix} index ({idx}), defaulting to 0."); initial_index = 0
                 except Exception as e_idx:
                     LOGGER.error(f"Error getting initial {log_prefix} index: {e_idx}", exc_info=True); initial_index = 0
        except Exception as e:
            LOGGER.error(f"Unexpected error initializing {log_prefix} combobox data: {e}", exc_info=True)
            options = ["Error"]; initial_index = 0

        if initial_index >= len(options): initial_index = 0
        var = tk.StringVar(value=options[initial_index])
        return var, options

    def _get_mode_display_index(self, display_options: list) -> int:
        """Helper to find the index corresponding to st.auto_join_mode."""
        # Ensure GAME_MODES is imported and valid
        if 'GAME_MODES' not in globals() or not isinstance(GAME_MODES, list):
            LOGGER.error("Internal GAME_MODES definition invalid or not imported.")
            return 0 # Default index on error
        internal_modes = GAME_MODES

        initial_mode_value = self.st.auto_join_mode
        if initial_mode_value not in internal_modes:
             LOGGER.error(f"Initial mode '{initial_mode_value}' not in internal GAME_MODES list: {internal_modes}. Defaulting index.")
             return 0 # Default index on error

        try:
            mode_idx_internal = internal_modes.index(initial_mode_value)
            # Now check if this index is valid for the *display* options
            if 0 <= mode_idx_internal < len(display_options):
                 return mode_idx_internal
            else:
                 LOGGER.error(f"Internal mode index {mode_idx_internal} for '{initial_mode_value}' is out of bounds for display options (len {len(display_options)}). Defaulting index.")
                 return 0 # Default index on error
        except ValueError: # Should not happen if initial_mode_value is in internal_modes
            LOGGER.error(f"Cannot find mode '{initial_mode_value}' in internal GAME_MODES list (this should not happen). Defaulting index.")
            return 0 # Default index on error
        except Exception as e:
             LOGGER.error(f"Unexpected error getting mode display index: {e}", exc_info=True)
             return 0


    def _create_ai_section(self, parent, row):
        """Create the AI Guidance section (row 2)."""
        ai_frame = ctk.CTkFrame(parent, fg_color=("gray90", "gray15"))
        ai_frame.grid(row=row, column=0, sticky="nsew", padx=PADX, pady=(PADY_INNER, PADY_INNER))
        ai_frame.grid_columnconfigure(0, weight=1)
        ai_frame.grid_rowconfigure(1, weight=1)

        label_ai = ctk.CTkLabel(ai_frame, text=self.st.lan().AI_OUTPUT, anchor="w", font=self.header_font)
        label_ai.grid(row=0, column=0, sticky="ew", padx=PADY_INNER, pady=(PADY_INNER, 2))

        self.text_ai_guide = ctk.CTkTextbox(
            ai_frame, font=self.ai_guide_font, wrap="word", border_width=1, state="disabled",
            height=AI_GUIDE_HEIGHT
        )
        self.text_ai_guide.grid(row=1, column=0, sticky="nsew", padx=PADY_INNER, pady=(0, PADY_INNER))

    def _create_game_info_section(self, parent, row):
        """Create the Game Info section (row 3)."""
        game_info_frame = ctk.CTkFrame(parent, fg_color=("gray90", "gray15"))
        game_info_frame.grid(row=row, column=0, sticky="ew", padx=PADX, pady=(PADY_INNER, PADY_INNER))
        game_info_frame.grid_columnconfigure(0, weight=1)

        label_gi = ctk.CTkLabel(game_info_frame, text=self.st.lan().GAME_INFO, anchor="w", font=self.header_font)
        label_gi.grid(row=0, column=0, sticky="ew", padx=PADY_INNER, pady=(PADY_INNER, 2))

        self.gameinfo_var = tk.StringVar()
        self.text_gameinfo = ctk.CTkLabel(
            game_info_frame, textvariable=self.gameinfo_var,
            font=self.emoji_font, anchor="w", justify="left",
        )
        self.text_gameinfo.grid(row=1, column=0, sticky="ew", padx=PADY_INNER, pady=(0, PADY_INNER))

    def _create_status_bars(self, parent, start_row):
        """Create the Model and Status bars (rows start_row, start_row + 1)."""
        self.model_bar = StatusBar(parent, num_columns=2, height=STATUS_BAR_HEIGHT)
        self.model_bar.grid(row=start_row, column=0, sticky='ew', padx=PADX, pady=(PADY_INNER, 0))

        self.status_bar = StatusBar(parent, num_columns=3, height=STATUS_BAR_HEIGHT)
        # Use start_row + 1 for the second status bar
        self.status_bar.grid(row=start_row + 1, column=0, sticky='ew', padx=PADX, pady=(1, PADY_OUTER[1]))

    def _init_gui_state(self):
        """Set initial states of widgets based on settings."""
        LOGGER.debug("开始 _init_gui_state...")
        if hasattr(self, 'switch_overlay'):
            if self.st.enable_overlay: self.switch_overlay.select()
            else: self.switch_overlay.deselect()
            self._cached_widget_states['overlay_switch'] = self.st.enable_overlay

        if hasattr(self, 'switch_autoplay'):
            if self.st.enable_automation: self.switch_autoplay.select()
            else: self.switch_autoplay.deselect()
            self._cached_widget_states['autoplay_switch'] = self.st.enable_automation

        if hasattr(self, 'switch_autojoin'):
            if self.st.auto_join_game: self.switch_autojoin.select()
            else: self.switch_autojoin.deselect()
            self._cached_widget_states['autojoin_switch'] = self.st.auto_join_game
        LOGGER.debug("_init_gui_state 完成。")

    # --- Event Handlers (No changes needed here usually) ---
    def report_callback_exception(self, exc, val, tb):
        """Log uncaught Tkinter exceptions."""
        LOGGER.error("GUI 未捕获异常: %s", exc, exc_info=(exc, val, tb))

    def _on_autojoin_level_selected(self, choice: str):
        try:
            game_levels = self.st.lan().GAME_LEVELS
            if isinstance(game_levels, list):
                try:
                    self.st.auto_join_level = game_levels.index(choice)
                    LOGGER.debug(f"自动加入等级设置为索引: {self.st.auto_join_level} ('{choice}')")
                except ValueError: LOGGER.error(f"选择的等级 '{choice}' 未在 GAME_LEVELS 列表中找到。")
            else: LOGGER.error("语言设置中的 GAME_LEVELS 不是列表。")
        except Exception as e: LOGGER.error(f"从选择 '{choice}' 设置自动加入等级时出错: {e}", exc_info=True)

    def _on_autojoin_mode_selected(self, choice: str):
        try:
            game_modes_display = self.st.lan().GAME_MODES
            if not isinstance(game_modes_display, list): raise ValueError("显示模式 (GAME_MODES) 不是列表。")
            if 'GAME_MODES' not in globals() or not isinstance(GAME_MODES, list): raise ValueError("内部 GAME_MODES 定义无效。")
            internal_modes = GAME_MODES

            try:
                mode_idx = game_modes_display.index(choice)
                if 0 <= mode_idx < len(internal_modes):
                    self.st.auto_join_mode = internal_modes[mode_idx]
                    LOGGER.debug(f"自动加入模式设置为: {self.st.auto_join_mode} ('{choice}')")
                else: LOGGER.error(f"从 '{choice}' 得到的模式索引 {mode_idx} 对内部 GAME_MODES (长度 {len(internal_modes)}) 无效。")
            except ValueError: LOGGER.error(f"选择的模式 '{choice}' 未在显示的 GAME_MODES 列表中找到。")
        except Exception as e: LOGGER.error(f"从选择 '{choice}' 设置自动加入模式时出错: {e}", exc_info=True)

    def _on_btn_start_browser_clicked(self):
        if hasattr(self, 'btn_start_browser') and self.btn_start_browser.winfo_exists():
            self.btn_start_browser.configure(state="disabled")
            self._cached_widget_states['start_browser_state'] = "disabled"
        self.bot_manager.start_browser()

    def _on_switch_toggled(self, switch_attr: str, enable_func, disable_func, setting_attr: str):
        """Generic handler for toggle switches."""
        if not hasattr(self, switch_attr): return
        switch_widget = getattr(self, switch_attr)
        if not switch_widget.winfo_exists(): return

        try:
            is_enabled = bool(switch_widget.get())
            if is_enabled: enable_func()
            else: disable_func()
            setattr(self.st, setting_attr, is_enabled)
            self._cached_widget_states[f'{switch_attr}_state'] = is_enabled
            LOGGER.debug(f"{setting_attr} 设置为 {is_enabled}")
        except Exception as e: LOGGER.error(f"切换开关 {switch_attr} 时出错: {e}", exc_info=True)

    def _on_switch_hud_toggled(self):
        self._on_switch_toggled('switch_overlay', self.bot_manager.enable_overlay, self.bot_manager.disable_overlay, 'enable_overlay')

    def _on_switch_autoplay_toggled(self):
        self._on_switch_toggled('switch_autoplay', self.bot_manager.enable_automation, self.bot_manager.disable_automation, 'enable_automation')

    def _on_switch_autojoin_toggled(self):
        self._on_switch_toggled('switch_autojoin', self.bot_manager.enable_autojoin, self.bot_manager.disable_autojoin, 'auto_join_game')

    def _on_btn_log_clicked(self):
        log_file = LogHelper.log_file_name
        if not log_file: LOGGER.error("日志文件路径未设置。"); messagebox.showerror("错误", "日志文件路径未配置。"); return
        if not os.path.exists(log_file): LOGGER.error(f"日志文件未找到: '{log_file}'"); messagebox.showerror("错误", f"日志文件未找到:\n{log_file}"); return
        try:
            if sys.platform == 'win32': os.startfile(log_file)
            elif sys.platform == 'darwin': subprocess.call(['open', log_file])
            else: subprocess.call(['xdg-open', log_file])
        except Exception as e: LOGGER.error(f"打开日志文件 '{log_file}' 失败: {e}", exc_info=True); messagebox.showerror("错误", f"无法打开日志文件:\n{e}")

    def _on_btn_settings_clicked(self):
        try:
            settings_window = SettingsWindow(self, self.st)
            settings_window.grab_set()
            self.wait_window(settings_window)
            if getattr(settings_window, 'exit_save', False):
                LOGGER.info("设置已保存。")
                if getattr(settings_window, 'model_updated', False): self.bot_manager.set_bot_update()
                if getattr(settings_window, 'gui_need_reload', False): self.reload_gui()
            else: LOGGER.info("设置已取消或未保存关闭。")
        except Exception as e: LOGGER.error(f"打开或处理设置窗口时出错: {e}", exc_info=True); messagebox.showerror("错误", f"无法打开设置窗口:\n{e}")

    def _on_btn_help_clicked(self):
        try:
            help_win = HelpWindow(self, self.st, self.updater)
            help_win.grab_set()
            self.wait_window(help_win)

        except Exception as e: LOGGER.error(f"打开帮助窗口时出错: {e}", exc_info=True); messagebox.showerror("错误", f"无法打开帮助窗口:\n{e}")

    def _on_exit(self):
        """处理窗口关闭事件 (X button or Exit menu) using custom dialog."""
        # --- 【修改】使用 ConfirmExitDialog ---
        title = getattr(self.st.lan(), 'EXIT', "退出确认")
        message = getattr(self.st.lan(), 'EIXT_CONFIRM', "您确定要退出程序吗？")

        if ConfirmExitDialog.ask(master=self, title=title, message=message): # 调用修改后的对话框
            # --- 退出清理逻辑不变 ---
            try:
                LOGGER.info("正在退出 GUI 和程序...")
                if hasattr(self, 'status_bar') and self.status_bar.winfo_exists() and self.icons.get('yellow'):
                    try:
                        exit_text = getattr(self.st.lan(), 'EXITING', "正在退出...")
                        self.status_bar.update_column(2, exit_text, self.icons['yellow'])
                        self.update_idletasks()
                    except Exception as e_status: LOGGER.warning(f"退出时无法更新状态栏: {e_status}")

                if hasattr(self.st, 'save_json') and callable(self.st.save_json):
                    self.st.save_json(); LOGGER.info("设置已保存。")
                else: LOGGER.warning("Settings 对象缺少 save_json 方法。")

                if hasattr(self.bot_manager, 'stop') and callable(self.bot_manager.stop):
                    LOGGER.info("正在停止 Bot Manager..."); self.bot_manager.stop(wait=True); LOGGER.info("Bot Manager 已停止。")
                else: LOGGER.warning("BotManager 对象缺少 stop 方法。")

            except Exception as e: LOGGER.error(f"退出清理过程中出错: {e}", exc_info=True)
            finally: LOGGER.info("退出 Tkinter 主循环。"); self.quit()
        else: LOGGER.info("用户取消退出。")


    def reload_gui(self):
        """Destroy and recreate widgets to reflect major settings changes (e.g., language)."""
        LOGGER.info("正在重新加载 GUI...")
        try:
            if hasattr(self, 'grid_frame') and self.grid_frame.winfo_exists():
                 for widget in self.grid_frame.winfo_children(): widget.destroy()
                 self.grid_frame.destroy()
            else:
                 for widget in self.winfo_children(): widget.destroy()

            self._cached_widget_states.clear()
            # 重新初始化依赖设置/语言的部分
            self._load_fonts() # 如果字体也可能变的话
            self._setup_window() # 重新应用标题和图标
            self._load_icons()   # 重新加载状态图标
            self._create_widgets() # 重新创建所有部件
            self._init_gui_state() # 重新应用初始状态
            self.after(50, self._update_gui_info_safe)
            LOGGER.info("GUI 已成功重新加载。")
        except Exception as e:
            LOGGER.error(f"GUI 重新加载过程中发生严重错误: {e}", exc_info=True)
            messagebox.showerror("错误", "无法完全重新加载 GUI。请重启应用程序。")


    # --- GUI Update Logic (Optimized - 保持不变) ---
    def _schedule_gui_update(self):
        if self.winfo_exists(): self.after(GUI_UPDATE_INTERVAL_MS, self._update_gui_info_safe)

    def _update_gui_info_safe(self):
        try:
            if self.winfo_exists(): self._update_gui_info_inner_optimized()
        except Exception as e: LOGGER.error(f"GUI 更新过程中出错: {e}", exc_info=True)
        finally: self._schedule_gui_update()

    def _update_widget_state(self, cache_key: str, new_value: Any, update_func) -> bool:
        if cache_key not in self._cached_widget_states or self._cached_widget_states[cache_key] != new_value:
            try:
                update_func(new_value); self._cached_widget_states[cache_key] = new_value; return True
            except tk.TclError as e: LOGGER.warning(f"更新部件 '{cache_key}' 时发生 TclError: {e}"); return False
            except Exception as e: LOGGER.warning(f"更新部件 '{cache_key}' 时出错: {e}", exc_info=True); return False
        return False

    def _update_gui_info_inner_optimized(self):
        """Perform the actual GUI updates, checking against cached states."""
        # --- 更新开始浏览器按钮状态 ---
        try:
            is_browser_running = self.bot_manager.browser.is_running()
            is_proxy_client = self.bot_manager.get_game_client_type() == GameClientType.PROXY
            target_state = "disabled" if (is_browser_running or is_proxy_client) else "normal"
            if hasattr(self, 'btn_start_browser') and self.btn_start_browser.winfo_exists():
                self._update_widget_state('start_browser_state', target_state, lambda state: self.btn_start_browser.configure(state=state))
        except Exception as e: LOGGER.warning(f"更新开始浏览器按钮状态时出错: {e}")

        # --- 更新帮助按钮图标 ---
        try:
            update_status = self.updater.update_status
            target_icon_key = 'help_update' if update_status in (UpdateStatus.NEW_VERSION, UpdateStatus.DOWNLOADING, UpdateStatus.UNZIPPING, UpdateStatus.PREPARED) else 'help'
            if hasattr(self, 'toolbar') and hasattr(self, 'btn_help') and self.btn_help.winfo_exists():
                 target_icon_path = self.icons.get(target_icon_key)
                 self._update_widget_state('help_button_icon', target_icon_path, lambda path: self.toolbar.set_img(self.btn_help, path) if path else None)
        except Exception as e: LOGGER.warning(f"更新帮助按钮图标时出错: {e}")

        # --- 更新开关状态 (基于设置) ---
        switch_map = {}
        if hasattr(self, 'switch_overlay'): switch_map['overlay_switch'] = (self.switch_overlay, self.st.enable_overlay)
        if hasattr(self, 'switch_autoplay'): switch_map['autoplay_switch'] = (self.switch_autoplay, self.st.enable_automation)
        if hasattr(self, 'switch_autojoin'): switch_map['autojoin_switch'] = (self.switch_autojoin, self.st.auto_join_game)
        for cache_key, (switch_widget, should_be_on) in switch_map.items():
            if switch_widget.winfo_exists():
                if cache_key not in self._cached_widget_states or self._cached_widget_states[cache_key] != should_be_on:
                    try:
                        current_state = bool(switch_widget.get())
                        if current_state != should_be_on:
                            if should_be_on: switch_widget.select()
                            else: switch_widget.deselect()
                        self._cached_widget_states[cache_key] = should_be_on # 更新缓存为目标状态
                    except Exception as e: LOGGER.warning(f"更新开关 {cache_key} 时出错: {e}")

        # --- 更新 AI 指导文本 ---
        ai_guide_str = ""
        try:
            pending_reaction = self.bot_manager.get_pending_reaction()
            if pending_reaction:
                guide_base, options = mjai_reaction_2_guide(pending_reaction, 3, self.st.lan())
                ai_guide_str = guide_base + '\n' + '\n'.join(f" {ts:<8}  {w*100:4.0f}%" for ts, w in options if ts)
        except Exception as e: LOGGER.warning(f"获取 AI 指导时出错: {e}")
        if hasattr(self, 'text_ai_guide') and self.text_ai_guide.winfo_exists():
            self._update_widget_state('ai_guide_text', ai_guide_str, lambda text: self._update_textbox(self.text_ai_guide, text))

        # --- 更新游戏信息文本 ---
        hand_str = ""
        try:
            gi: Optional[GameInfo] = self.bot_manager.get_game_info()
            if gi and hasattr(gi, 'my_tehai') and gi.my_tehai is not None:
                tehai = gi.my_tehai; tsumohai = getattr(gi, 'my_tsumohai', None)
                hand_str = ''.join(MJAI_TILE_2_UNICODE.get(t, '?') for t in tehai)
                if tsumohai: hand_str += f"   {MJAI_TILE_2_UNICODE.get(tsumohai, '?')}"
        except Exception as e: LOGGER.warning(f"获取游戏信息展示时出错: {e}")
        if hasattr(self, 'gameinfo_var'):
             self._update_widget_state('game_info_text', hand_str, lambda text: self.gameinfo_var.set(text))

        # --- 更新模型信息栏 ---
        if hasattr(self, 'model_bar') and self.model_bar.winfo_exists(): self._update_model_bar_info()
        # --- 更新状态栏 ---
        if hasattr(self, 'status_bar') and self.status_bar.winfo_exists(): self._update_status_bar_info()
        # --- 更新悬浮窗 ---
        try: self.bot_manager.update_overlay()
        except Exception as e: LOGGER.warning(f"调用 update_overlay 时出错: {e}")

    def _update_textbox(self, textbox: ctk.CTkTextbox, new_text: str):
        """Safely updates the content of a CTkTextbox."""
        try:
            textbox.configure(state="normal"); textbox.delete("1.0", "end")
            if new_text: textbox.insert("1.0", new_text)
            textbox.configure(state="disabled")
        except tk.TclError as e: LOGGER.warning(f"更新文本框内容时发生 TclError: {e}")
        except Exception as e: LOGGER.error(f"更新文本框内容失败: {e}", exc_info=True)

    def _update_model_bar_info(self):
        """Updates the model status bar, checking cache."""
        model_text, model_icon_key, info_text = "", None, ""
        try:
            if self.bot_manager.is_bot_created() and hasattr(self.bot_manager, 'bot'):
                supported = getattr(self.bot_manager.bot, 'supported_modes', [])
                mode_strs = [(('✔' if m in supported else '✖') + m.value) for m in GameMode]
                model_text = f"{self.st.lan().MODEL}: {self.st.model_type} ({' | '.join(mode_strs)})"
                model_icon_key = 'green'
                if self.bot_manager.is_game_syncing(): info_text = '⌛ ' + self.st.lan().SYNCING
                elif self.bot_manager.is_bot_calculating(): info_text = '⌛ ' + self.st.lan().CALCULATING
                else: bot_info = getattr(self.bot_manager.bot, 'info_str', ''); info_text = ('ℹ️ ' + bot_info) if bot_info else ''
            else:
                if self.bot_manager.is_loading_bot: model_text, model_icon_key = self.st.lan().MODEL_LOADING, 'yellow'
                else: model_text, model_icon_key = self.st.lan().MODEL_NOT_LOADED, 'red'
            # Update columns using cached checks
            model_icon_path = self.icons.get(model_icon_key)
            self._update_widget_state('model_bar_col0', (model_text, model_icon_path), lambda val: self.model_bar.update_column(0, val[0], val[1]))
            self._update_widget_state('model_bar_col1', (info_text, None), lambda val: self.model_bar.update_column(1, val[0], val[1])) # Col 1 has no icon here
        except Exception as e: LOGGER.warning(f"更新模型信息栏时出错: {e}", exc_info=True)

    def _update_status_bar_info(self):
        """Updates the main status bar, checking cache."""
        try:
            # Col 0: Main Thread
            fps_disp = min(999, int(self.bot_manager.fps_counter.fps))
            main_text = f"{self.st.lan().MAIN_THREAD} ({fps_disp:3d})"
            main_icon_key = 'green' if self.bot_manager.is_running() else 'red'
            main_icon_path = self.icons.get(main_icon_key)
            self._update_widget_state('status_bar_col0', (main_text, main_icon_path), lambda val: self.status_bar.update_column(0, val[0], val[1]))

            # Col 1: Game Client
            client_text, client_icon_key = "", None
            client_type = self.bot_manager.get_game_client_type()
            if client_type == GameClientType.PLAYWRIGHT:
                fps_disp = min(999, int(self.bot_manager.browser.fps_counter.fps))
                client_text = f"{self.st.lan().BROWSER} ({fps_disp:3d})"
                browser_running = hasattr(self.bot_manager, 'browser') and self.bot_manager.browser.is_running()
                client_icon_key = 'green' if browser_running else 'gray'
            elif client_type == GameClientType.PROXY: client_text, client_icon_key = self.st.lan().PROXY_CLIENT, 'green'
            else: client_text, client_icon_key = self.st.lan().GAME_NOT_RUNNING, 'ready'
            client_icon_path = self.icons.get(client_icon_key)
            self._update_widget_state('status_bar_col1', (client_text, client_icon_path), lambda val: self.status_bar.update_column(1, val[0], val[1]))

            # Col 2: Game/Error Status
            gi_status: Optional[GameInfo] = None
            try: gi_status = self.bot_manager.get_game_info()
            except Exception: pass
            status_str, status_icon_key = self._get_status_text_icon_key(gi_status)
            status_icon_path = self.icons.get(status_icon_key)
            self._update_widget_state('status_bar_col2', (status_str, status_icon_path), lambda val: self.status_bar.update_column(2, val[0], val[1]))
        except Exception as e: LOGGER.warning(f"更新状态栏时出错: {e}", exc_info=True)

    def _get_status_text_icon_key(self, gi: Optional[GameInfo]) -> Tuple[str, Optional[str]]:
        """Determines the status text and icon key for status bar column 2."""
        default_icon_key = 'ready'
        try:
            bot_exception = self.bot_manager.main_thread_exception; game_error = self.bot_manager.get_game_error()
            if bot_exception: return error_to_str(bot_exception, self.st.lan()), 'red'
            if game_error: return error_to_str(game_error, self.st.lan()), 'red'
            if self.bot_manager.is_browser_zoom_off(): return self.st.lan().BROWSER_ZOOM_OFF, 'red'

            if self.bot_manager.is_in_game():
                info_str = self.st.lan().GAME_RUNNING; game_mode_value = getattr(gi, 'game_mode', None)
                game_mode_str = f" ({game_mode_value.value})" if game_mode_value else ""
                if self.bot_manager.is_game_syncing(): info_str += " - " + self.st.lan().SYNCING
                elif gi and hasattr(gi, 'bakaze') and gi.bakaze:
                     bakaze_str = self.st.lan().mjai2str(gi.bakaze); kyoku = getattr(gi, 'kyoku', '?'); honba = getattr(gi, 'honba', '?')
                     info_str += f"{game_mode_str} - {bakaze_str} {kyoku}{self.st.lan().KYOKU} {honba}{self.st.lan().HONBA}"
                else: info_str += game_mode_str + " - " + self.st.lan().GAME_STARTING
                return info_str, 'green'
            else:
                state_dict = {UiState.MAIN_MENU: self.st.lan().MAIN_MENU, UiState.GAME_ENDING: self.st.lan().GAME_ENDING, UiState.NOT_RUNNING: self.st.lan().GAME_NOT_RUNNING}
                ui_state = getattr(self.bot_manager.automation, 'ui_state', UiState.NOT_RUNNING)
                state_str = state_dict.get(ui_state, str(ui_state))
                info_str = f"{self.st.lan().READY_FOR_GAME} - {state_str}"
                return info_str, default_icon_key
        except Exception as e:
            LOGGER.warning(f"获取状态文本/图标时出错: {e}", exc_info=True)
            return "状态错误", 'yellow'

    # --- Ensure Folder.RES is set for testing (代码保持不变) ---
    test_res_dir = "test_assets_main_gui"
    # ... (文件夹和 dummy 图片创建逻辑，使用修正后的颜色计算) ...
    img_dir = Folder.RES
    if img_dir:
        print(f"检查/创建 dummy 图片于: {img_dir}")
        icon_files = {
            'green': 'green.png',
            'red': 'red.png',
            'yellow': 'yellow.png',
            'gray': 'gray.png',
            'ready': 'ready.png',
            'help': 'help.png',
            'help_update': 'help_update.png',
            'majsoul': 'majsoul.png',
            'settings': 'settings.png',
            'log': 'log.png',
            'exit': 'exit.png',
            'icon': 'icon.ico',       # 保留 .ico
            'icon_png': 'icon.png'    # 添加 .png
        }
        for img_name in icon_files.values():
             p = sub_file(img_dir, img_name)
             if not os.path.exists(p):
                 try:
                     img_hash = hash(img_name)
                     color_tuple = (abs(img_hash) % 256, abs(img_hash >> 8) % 256, abs(img_hash >> 16) % 256)
                     Image.new('RGB', (16, 16), color=color_tuple).save(p)
                 except Exception as e: print(f"无法创建 dummy 图片 {p}: {e}")
    else: print("跳过 dummy 图片创建: Folder.RES 未设置或目录创建失败。")
