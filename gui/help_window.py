# coding: utf-8 # Add encoding declaration for potentially non-ASCII characters in comments/strings
""" 使用 customtkinter 的帮助窗口 (整合优化与图标设置) """

import os # Needed for os.path.exists
import threading
from typing import Callable
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from tkhtmlview import HTMLScrolledText
from PIL import ImageTk # Needed for iconphoto if using PIL images

# Assuming these are correctly imported from your project structure
from common.log_helper import LOGGER
from common.settings import Settings
from updater import Updater, UpdateStatus # Ensure UpdateStatus has all required members

class HelpWindow(ctk.CTkToplevel):
    """ 使用 customtkinter 实现的帮助信息和更新对话框 (优化版 + 图标) """
    WIN_WIDTH = 750
    WIN_HEIGHT = 700

    def __init__(self, parent: ctk.CTkFrame, st: Settings, updater: Updater):
        super().__init__(parent)
        self.st = st
        self.updater = updater
        self._refresh_timer_id = None # 用于取消 after 定时器
        self.html_text = None         # 缓存加载的 HTML

        # --- 基本窗口设置 ---
        title_str = f"{st.lan().HELP} {st.lan().APP_TITLE} v{self.updater.local_version}"
        self.title(title_str)

        # --- 窗口几何与位置 (优化版) ---
        try:
            # 确保父窗口完全初始化以获取准确信息
            parent.update_idletasks() # Crucial for getting accurate dimensions immediately
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()
            if parent_w > 0 and parent_h > 0:
                new_x = parent_x + (parent_w // 2) - (self.WIN_WIDTH // 2)
                new_y = parent_y + (parent_h // 2) - (self.WIN_HEIGHT // 2)
                # 基本边界检查，防止窗口完全移出屏幕 (可选)
                # screen_w = self.winfo_screenwidth()
                # screen_h = self.winfo_screenheight()
                # new_x = max(0, min(new_x, screen_w - self.WIN_WIDTH))
                # new_y = max(0, min(new_y, screen_h - self.WIN_HEIGHT))
                self.geometry(f'{self.WIN_WIDTH}x{self.WIN_HEIGHT}+{new_x}+{new_y}')
                LOGGER.debug(f"HelpWindow centered relative to parent at {new_x},{new_y}")
            else:
                raise ValueError("Parent window dimensions reported as zero.")
        except Exception as e:
            LOGGER.warning(f"无法基于父窗口居中 ({e}), 尝试屏幕居中。")
            try:
                # 回退到屏幕居中
                self.update_idletasks() # Ensure screen dimensions are available
                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                new_x = (screen_w // 2) - (self.WIN_WIDTH // 2)
                new_y = (screen_h // 2) - (self.WIN_HEIGHT // 2)
                self.geometry(f'{self.WIN_WIDTH}x{self.WIN_HEIGHT}+{new_x}+{new_y}')
                LOGGER.debug(f"HelpWindow centered on screen at {new_x},{new_y}")
            except Exception as e2:
                LOGGER.warning(f"屏幕居中失败 ({e2}), 使用固定偏移量 +100+100。")
                self.geometry(f'{self.WIN_WIDTH}x{self.WIN_HEIGHT}+100+100') # 最终回退

        # --- 窗口行为 ---
        # self.resizable(False, False) # 取消注释以禁用缩放
        self.lift()  # 将窗口置于顶层
        self.attributes("-topmost", True)  # 初始保持窗口在最前
        # 稍后允许其他窗口置于其上 (200ms 应该足够)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.protocol("WM_DELETE_WINDOW", self._on_close)  # 处理关闭按钮
        
        
        try:
            # 使用 winfo_toplevel() 获取包含此窗口的顶级窗口 (即主程序窗口)
            top_level_window = self.winfo_toplevel()
            LOGGER.debug(f"HelpWindow: Found top_level_window: {top_level_window}")

            # 从顶级窗口获取图标属性
            master_icon_path_ico = getattr(top_level_window, 'app_icon_path_ico', None)
            master_icon_photo = getattr(top_level_window, 'app_icon_photo', None)
            LOGGER.debug(f"HelpWindow: Icon path from top_level: {master_icon_path_ico}")
            LOGGER.debug(f"HelpWindow: Icon photo obj from top_level: {'Exists' if master_icon_photo else 'None'}")

        except Exception as e:
            # 如果获取顶级窗口或属性时出错，则记录错误并继续
            LOGGER.error(f"HelpWindow: Failed to get top_level_window or icon attributes: {e}", exc_info=True)
            master_icon_path_ico = None
            master_icon_photo = None

        # 1. 尝试设置 .ico (影响任务栏等)
        if master_icon_path_ico and isinstance(master_icon_path_ico, str) and os.path.exists(master_icon_path_ico):
            try:
                self.wm_iconbitmap(master_icon_path_ico)
                LOGGER.debug(f"HelpWindow: wm_iconbitmap set to {master_icon_path_ico}")
            except tk.TclError as e_wm_ico:
                LOGGER.warning(f"HelpWindow: TclError setting wm_iconbitmap: {e_wm_ico}")
            except Exception as e_wm_ico_gen:
                LOGGER.warning(f"HelpWindow: Failed to set wm_iconbitmap: {e_wm_ico_gen}", exc_info=False)
        else:
            # 提供更详细的日志，说明为什么没有设置 .ico
            if not master_icon_path_ico:
                 LOGGER.debug("HelpWindow: No 'app_icon_path_ico' attribute found on top_level_window.")
            elif not isinstance(master_icon_path_ico, str):
                 LOGGER.debug(f"HelpWindow: 'app_icon_path_ico' is not a string: {type(master_icon_path_ico)}")
            elif not os.path.exists(master_icon_path_ico):
                 LOGGER.debug(f"HelpWindow: Icon file path does not exist: {master_icon_path_ico}")
            else:
                 LOGGER.debug("HelpWindow: No valid .ico path found on master for wm_iconbitmap (unknown reason).")


        # 2. 尝试设置 PhotoImage (影响窗口左上角), 延迟执行以提高兼容性
        if master_icon_photo and isinstance(master_icon_photo, ImageTk.PhotoImage):
            try:
                # 延迟设置 iconphoto，增加成功率
                self.after(250, lambda: self._safe_set_iconphoto(master_icon_photo))
                LOGGER.debug("HelpWindow: Scheduled iconphoto setting.")
            except Exception as e_schedule:
                LOGGER.error(f"HelpWindow: Failed to schedule iconphoto setting: {e_schedule}", exc_info=True)
        else:
            # 提供更详细的日志
            if not master_icon_photo:
                 LOGGER.debug("HelpWindow: No 'app_icon_photo' attribute found on top_level_window.")
            elif not isinstance(master_icon_photo, ImageTk.PhotoImage):
                 LOGGER.debug(f"HelpWindow: 'app_icon_photo' is not a PhotoImage: {type(master_icon_photo)}")
            else:
                 LOGGER.debug("HelpWindow: No valid PhotoImage found on master for iconphoto (unknown reason).")

        # 1. 尝试设置 .ico (影响任务栏等)
        if master_icon_path_ico and isinstance(master_icon_path_ico, str) and os.path.exists(master_icon_path_ico):
            try:
                self.wm_iconbitmap(master_icon_path_ico)
                LOGGER.debug(f"HelpWindow: wm_iconbitmap set to {master_icon_path_ico}")
            except tk.TclError as e_wm_ico:
                LOGGER.warning(f"HelpWindow: TclError setting wm_iconbitmap: {e_wm_ico}")
            except Exception as e_wm_ico_gen:
                LOGGER.warning(f"HelpWindow: Failed to set wm_iconbitmap: {e_wm_ico_gen}", exc_info=False) # exc_info=False for less noise
        else:
            LOGGER.debug("HelpWindow: No valid .ico path found on master for wm_iconbitmap.")

        # 2. 尝试设置 PhotoImage (影响窗口左上角), 延迟执行以提高兼容性
        if master_icon_photo and isinstance(master_icon_photo, ImageTk.PhotoImage):
            try:
                # 延迟设置 iconphoto，增加成功率
                self.after(250, lambda: self._safe_set_iconphoto(master_icon_photo))
                LOGGER.debug("HelpWindow: Scheduled iconphoto setting.")
            except Exception as e_schedule:
                LOGGER.error(f"HelpWindow: Failed to schedule iconphoto setting: {e_schedule}", exc_info=True)
        else:
             LOGGER.debug("HelpWindow: No valid PhotoImage found on master for iconphoto.")
        # --- 图标设置结束 ---

        # --- HTML 显示区域 ---
        self.html_box = HTMLScrolledText(
            self,
            html=f"<h1>{st.lan().HELP}</h1><p>{st.lan().LOADING}...</p>", # 初始加载HTML提示
            height=25, # 大约的行高，实际高度由pack决定
        )
        self.html_box.configure(state=tk.DISABLED) # 初始禁用编辑
        self.html_box.pack(padx=10, pady=(10, 5), side=tk.TOP, fill=tk.BOTH, expand=True)

        # --- 底部控制区域 Frame ---
        self.frame_bot = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.frame_bot.pack(expand=False, fill=tk.X, padx=10, pady=(5, 10), side=tk.BOTTOM)

        # 配置网格权重以实现响应式布局
        self.frame_bot.grid_columnconfigure(0, weight=2)  # Update button column
        self.frame_bot.grid_columnconfigure(1, weight=8)  # Status label column (takes most space)
        self.frame_bot.grid_columnconfigure(2, weight=1)  # OK button column
        self.frame_bot.grid_rowconfigure(0, weight=1)     # Single row

        # --- 更新器按钮 ---
        self.update_button = ctk.CTkButton(
            self.frame_bot,
            text=st.lan().CHECK_FOR_UPDATE, # 初始文本
            state="disabled", # 初始禁用, 等待 _refresh_ui 确定状态
            command=lambda: None # 占位符
        )
        # Use sticky="ew" to make the button expand horizontally within its grid cell
        self.update_button.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=5)

        # --- 更新状态标签 ---
        self.update_str_var = tk.StringVar(value=st.lan().LOADING + "...") # 初始状态
        self.update_label = ctk.CTkLabel(
            self.frame_bot,
            textvariable=self.update_str_var,
            anchor="w",  # Align text to the left
            justify=tk.LEFT
        )
        # Use sticky="ew" to make the label expand horizontally
        self.update_label.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # --- OK 按钮 ---
        self.ok_button = ctk.CTkButton(
            self.frame_bot,
            text=st.lan().OK_BUTTON,
            command=self._on_close,
            width=100 # Fixed width might be better than default for consistency
        )
        # Use sticky="e" to align the button to the right of its grid cell
        self.ok_button.grid(row=0, column=2, sticky="e", padx=(5, 0), pady=5)

        # --- 启动 UI 刷新循环 ---
        # Short delay before first refresh to allow window rendering
        self.after(100, self._refresh_ui)

    def _safe_set_iconphoto(self, icon_photo: ImageTk.PhotoImage):
        """ Safely sets the iconphoto, checking if the window still exists. """
        try:
            if self.winfo_exists():
                self.iconphoto(False, icon_photo)
                LOGGER.debug("HelpWindow: iconphoto set successfully.")
            else:
                LOGGER.debug("HelpWindow: Window destroyed before iconphoto could be set.")
        except tk.TclError as e:
            LOGGER.warning(f"HelpWindow: TclError setting iconphoto: {e}")
        except Exception as e:
            LOGGER.error(f"HelpWindow: Unexpected error setting iconphoto: {e}", exc_info=True)


    def _run_in_thread(self, target_func: Callable, *args):
        """辅助函数：在单独的线程中运行目标函数"""
        # Ensure the target function handles its own exceptions or updates state safely
        thread = threading.Thread(target=target_func, args=args, daemon=True)
        thread.start()
        LOGGER.debug(f"Started background thread for: {target_func.__name__}")

    def _check_for_update(self):
        """检查更新 (在线程中运行)"""
        LOGGER.info("Requesting update check...")
        # Immediately disable button, text/status updates handled by _refresh_ui
        if self.winfo_exists(): # Check window exists before configuring
             self.update_button.configure(state="disabled")
             # Updater needs to set status to CHECKING for UI feedback
             self._run_in_thread(self.updater.check_update)
        else:
             LOGGER.warning("Update check requested but window no longer exists.")


    def _download_update(self):
        """下载并解压更新 (在线程中运行)"""
        LOGGER.info("Requesting update download and preparation...")
        if self.winfo_exists():
            self.update_button.configure(state="disabled")
            # Updater needs to set status to DOWNLOADING etc.
            self._run_in_thread(self.updater.prepare_update)
        else:
            LOGGER.warning("Update download requested but window no longer exists.")


    def _start_update(self):
        """开始更新过程 (确认后执行)"""
        LOGGER.info("Asking user to confirm starting the update...")
        # messagebox is modal and blocks, which is acceptable for user confirmation
        # Ensure parent=self so the messagebox appears over the help window
        confirm_message = getattr(self.st.lan(), 'UPDATE_PREPARED_CONFIRM', self.st.lan().UPDATE_PREPARED) # More specific msg if available

        if messagebox.askokcancel(self.st.lan().START_UPDATE, confirm_message, parent=self):
            LOGGER.info("User confirmed update. Executing start command...")
            if not self.winfo_exists():
                 LOGGER.warning("Window closed before update could be started after confirmation.")
                 return

            self.update_button.configure(state="disabled") # Disable button after confirmation
            try:
                # Assuming start_update initiates the external updater and quits
                # This call itself should be quick, but the *consequence* is app exit
                self.updater.start_update()
                # If start_update doesn't exit the app itself, you might need:
                # LOGGER.info("Update process started, closing help window.")
                # self._on_close()
            except Exception as e:
                LOGGER.error(f"Failed to start the update process: {e}", exc_info=True)
                if self.winfo_exists():
                    messagebox.showerror(self.st.lan().ERROR, f"{self.st.lan().ERROR_STARTING_UPDATE}: {e}", parent=self)
                    # Re-enable check button after failed start
                    self.update_button.configure(state="normal", text=self.st.lan().CHECK_FOR_UPDATE, command=self._check_for_update)
                    self.update_str_var.set(f"{self.st.lan().ERROR}: {self.st.lan().ERROR_STARTING_UPDATE}")
        else:
            LOGGER.info("User cancelled the update process.")
            # Keep the "Start Update" button active if user cancels
            if self.winfo_exists():
                self.update_button.configure(state="normal")


    def _refresh_ui(self):
        """ 定期根据 Updater 状态更新 UI (优化版) """
        # Primary exit condition: Window destroyed
        if not self.winfo_exists():
            LOGGER.debug("_refresh_ui called but window destroyed. Stopping.")
            # Attempt to cancel timer one last time if needed
            if self._refresh_timer_id:
                try: self.after_cancel(self._refresh_timer_id)
                except tk.TclError: pass # Ignore errors during shutdown
                self._refresh_timer_id = None
            return

        lan = self.st.lan()
        updater = self.updater
        current_status = updater.update_status

        # --- 更新 HTML (仅一次) ---
        if not self.html_text and updater.help_html:
            self.html_text = updater.help_html
            try:
                self.html_box.configure(state=tk.NORMAL)
                self.html_box.set_html(self.html_text, strip=True)
                self.html_box.configure(state=tk.DISABLED)
                LOGGER.debug("Help HTML content updated.")
            except Exception as e:
                 LOGGER.error(f"Error setting HTML content: {e}", exc_info=True)
                 # Display error within the box itself
                 try:
                     self.html_box.configure(state=tk.NORMAL)
                     self.html_box.set_html(f"<h3>{lan.ERROR}</h3><p>Could not load help content.</p><p><small>{e}</small></p>")
                     self.html_box.configure(state=tk.DISABLED)
                 except: pass # Avoid error loops

        # --- 根据状态确定新 UI 状态 ---
        new_label_text = ""
        # Default to current button text to detect changes easily
        new_button_text = self.update_button.cget("text")
        new_button_state = "disabled"
        new_button_command = lambda: None

        match current_status:
            case UpdateStatus.NONE:
                new_label_text = getattr(lan, 'READY_TO_CHECK', "") # Optional "Ready" message
                new_button_text = lan.CHECK_FOR_UPDATE
                new_button_state = "normal"
                new_button_command = self._check_for_update
            case UpdateStatus.CHECKING:
                new_label_text = lan.CHECKING_UPDATE + "..."
                new_button_text = lan.CHECKING_UPDATE # Optionally change button text too
                new_button_state = "disabled"
                # Keep command as None or previous, button is disabled anyway
            case UpdateStatus.NO_UPDATE:
                new_label_text = lan.NO_UPDATE_FOUND + f" (v{updater.web_version})"
                new_button_text = lan.CHECK_FOR_UPDATE
                new_button_state = "normal"
                new_button_command = self._check_for_update
            case UpdateStatus.NEW_VERSION:
                new_label_text = lan.UPDATE_AVAILABLE + f" v{updater.web_version}"
                new_button_text = lan.DOWNLOAD_UPDATE
                new_button_state = "normal"
                new_button_command = self._download_update
            case UpdateStatus.DOWNLOADING:
                progress = updater.dl_progress
                progress_str = f"{progress:.1f}%" if isinstance(progress, (int, float)) else str(progress)
                new_label_text = lan.DOWNLOADING + f" {progress_str}"
                new_button_text = lan.DOWNLOADING # Optionally change button text
                new_button_state = "disabled"
            case UpdateStatus.UNZIPPING:
                new_label_text = lan.UNZIPPING + "..."
                new_button_text = lan.UNZIPPING # Optionally change button text
                new_button_state = "disabled"
            case UpdateStatus.PREPARED:
                new_label_text = lan.UPDATE_PREPARED
                new_button_text = lan.START_UPDATE
                new_button_state = "normal"
                new_button_command = self._start_update
            case UpdateStatus.ERROR:
                # Generic error in label, specific in log
                err_msg = str(updater.update_exception) if updater.update_exception else "Unknown error"
                new_label_text = f"{lan.ERROR}: {getattr(lan, 'UPDATE_FAILED_SEE_LOG', 'Update failed')}"
                LOGGER.error(f"Update error state reached: {err_msg}", exc_info=(updater.update_exception is not None))
                new_button_text = lan.CHECK_FOR_UPDATE # Allow retry
                new_button_state = "normal"
                new_button_command = self._check_for_update
            case _:
                new_label_text = f"{lan.ERROR}: Unknown status ({current_status})"
                LOGGER.warning(f"Unhandled update status in UI refresh: {current_status}")
                new_button_text = lan.ERROR # Indicate error on button too
                new_button_state = "disabled"

        # --- 仅在必要时更新 UI 元素 ---
        # Update label text if changed
        if self.update_str_var.get() != new_label_text:
            self.update_str_var.set(new_label_text)

        # Update button if state, text, or command needs changing
        current_button_state = self.update_button.cget("state")
        current_button_text = self.update_button.cget("text")
        # Comparing command objects is tricky, safer to update if state/text changes,
        # or if the state is 'normal' and command might need setting.
        needs_configure = False
        config_options = {}

        if current_button_state != new_button_state:
            config_options["state"] = new_button_state
            needs_configure = True
        if current_button_text != new_button_text:
            config_options["text"] = new_button_text
            needs_configure = True
        # Always update command when configuring state/text to ensure consistency
        if needs_configure:
             config_options["command"] = new_button_command
             self.update_button.configure(**config_options)
        # Consider if command needs update even if state/text didn't change
        # (e.g. from lambda:None to a real command when state becomes 'normal')
        # This can be complex, the above usually covers most cases.
        # If issues arise, explicitly check and set command if needed.


        # --- 安排下一次刷新 ---
        # Schedule the next call to this method
        self._refresh_timer_id = self.after(200, self._refresh_ui) # 200ms interval


    def _on_close(self):
        """ 当窗口关闭时调用 (WM_DELETE_WINDOW or OK button) """
        LOGGER.debug("HelpWindow closing...")
        # Cancel the pending refresh timer
        if self._refresh_timer_id:
            try:
                self.after_cancel(self._refresh_timer_id)
                LOGGER.debug("Refresh timer cancelled.")
            except tk.TclError:
                 LOGGER.warning("TclError cancelling refresh timer, likely during interpreter shutdown.")
            self._refresh_timer_id = None
        # Destroy the window
        self.destroy()
        LOGGER.debug("HelpWindow destroyed.")