# coding: utf-8
"""使用 customtkinter 的帮助窗口 (整合优化与图标设置)"""

import os
import threading
from typing import Callable
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from tkhtmlview import HTMLScrolledText
from PIL import Image, ImageTk  # 确保导入 Image

# Assuming these are correctly imported from your project structure
from common.log_helper import LOGGER
from common.settings import Settings
from updater import (
    Updater,
    UpdateStatus,
)  # Ensure UpdateStatus has all required members
from common.utils import Folder, sub_file


class HelpWindow(ctk.CTkToplevel):
    """使用 customtkinter 实现的帮助信息和更新对话框 (优化版 + 图标)"""

    WIN_WIDTH = 750
    WIN_HEIGHT = 700

    def __init__(self, parent: ctk.CTkFrame, st: Settings, updater: Updater):
        super().__init__(parent)
        self.st = st
        self.updater = updater
        self._refresh_timer_id = None  # 用于取消 after 定时器
        self.html_text = None  # 缓存加载的 HTML
        self._app_icon_photo = None  # 存储 PhotoImage 引用

        # --- 基本窗口设置 ---
        title_str = (
            f"{st.lan().HELP} {st.lan().APP_TITLE} v{self.updater.local_version}"
        )
        self.title(title_str)
        self._parent = parent

        # --- 窗口几何与位置 (优化版) ---
        try:
            # 确保父窗口完全初始化以获取准确信息
            parent.update_idletasks()  # Crucial for getting accurate dimensions immediately
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()
            if parent_w > 0 and parent_h > 0:
                new_x = parent_x + (parent_w // 2) - (self.WIN_WIDTH // 2)
                new_y = parent_y + (parent_h // 2) - (self.WIN_HEIGHT // 2)
                self.geometry(f"{self.WIN_WIDTH}x{self.WIN_HEIGHT}+{new_x}+{new_y}")
                LOGGER.debug(
                    f"HelpWindow centered relative to parent at {new_x},{new_y}"
                )
            else:
                # 如果父窗口尺寸为0，可能父窗口还未完全绘制或被隐藏
                LOGGER.warning("父窗口尺寸报告为零，尝试屏幕居中。")
                raise ValueError("Parent window dimensions reported as zero.")
        except Exception as e:
            LOGGER.warning(f"无法基于父窗口居中 ({e}), 尝试屏幕居中。")
            try:
                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                new_x = (screen_w // 2) - (self.WIN_WIDTH // 2)
                new_y = (screen_h // 2) - (self.WIN_HEIGHT // 2)
                self.geometry(f"{self.WIN_WIDTH}x{self.WIN_HEIGHT}+{new_x}+{new_y}")
                LOGGER.debug(f"HelpWindow centered on screen at {new_x},{new_y}")
            except Exception as e2:
                LOGGER.error(
                    f"屏幕居中失败 ({e2}), 使用固定偏移量 +100+100。", exc_info=True
                )
                self.geometry(f"{self.WIN_WIDTH}x{self.WIN_HEIGHT}+100+100")  # 最终回退

        # --- 窗口行为 ---
        self.lift()  # 将窗口置于顶层
        self.attributes("-topmost", True)  # 初始保持窗口在最前
        self.after(
            200, lambda: self.attributes("-topmost", False)
        )  # 稍后允许其他窗口置于其上
        self.protocol("WM_DELETE_WINDOW", self._on_close)  # 处理关闭按钮

        # --- HTML 显示区域 ---
        self.html_box = HTMLScrolledText(
            self,
            html=f"<h1>{st.lan().HELP}</h1><p>{st.lan().LOADING}...</p>",  # 初始加载HTML提示
            height=25,  # 大约的行高，实际高度由pack决定
        )
        self.html_box.configure(state=tk.DISABLED)  # 初始禁用编辑
        self.html_box.pack(
            padx=10, pady=(10, 5), side=tk.TOP, fill=tk.BOTH, expand=True
        )

        # --- 底部控制区域 Frame ---
        self.frame_bot = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.frame_bot.pack(
            expand=False, fill=tk.X, padx=10, pady=(5, 10), side=tk.BOTTOM
        )

        # 配置网格权重以实现响应式布局
        self.frame_bot.grid_columnconfigure(0, weight=2)  # Update button column
        self.frame_bot.grid_columnconfigure(
            1, weight=8
        )  # Status label column (takes most space)
        self.frame_bot.grid_columnconfigure(2, weight=1)  # OK button column
        self.frame_bot.grid_rowconfigure(0, weight=1)  # Single row

        # --- 更新器按钮 ---
        self.update_button = ctk.CTkButton(
            self.frame_bot,
            text=st.lan().CHECK_FOR_UPDATE,  # 初始文本
            state="disabled",  # 初始禁用, 等待 _refresh_ui 确定状态
            command=lambda: None,  # 占位符
        )
        self.update_button.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=5)

        # --- 更新状态标签 ---
        self.update_str_var = tk.StringVar(value=st.lan().LOADING + "...")  # 初始状态
        self.update_label = ctk.CTkLabel(
            self.frame_bot,
            textvariable=self.update_str_var,
            anchor="w",  # Align text to the left
            justify=tk.LEFT,
        )
        self.update_label.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # --- OK 按钮 ---
        self.ok_button = ctk.CTkButton(
            self.frame_bot,
            text=st.lan().OK_BUTTON,
            command=self._on_close,
            width=100,  # Fixed width might be better than default for consistency
        )
        self.ok_button.grid(row=0, column=2, sticky="e", padx=(5, 0), pady=5)

        # --- 启动 UI 刷新循环 ---
        self.after(100, self._refresh_ui)  # 稍作延迟启动刷新

        # --- !!! 延迟设置图标 !!! ---
        # 安排在 210 毫秒后调用 _setup_icon 方法
        # 这个时间点应该在 CustomTkinter 完成其初始绘制之后
        delay_ms = 210
        self.after(delay_ms, self._setup_icon)
        LOGGER.debug(f"已安排在 {delay_ms}ms 后调用 _setup_icon。")
        # ---------------------------

    def _setup_icon(self):
        """设置窗口图标 (优先 PNG for iconphoto, ICO for iconbitmap) - 修正版 v2"""
        LOGGER.debug("开始设置 HelpWindow 图标...")
        icon_path_png = None
        icon_path_ico = None
        photo_icon_set = False  # 标记 iconphoto 是否成功设置
        bitmap_icon_set = False  # 标记 iconbitmap 是否成功设置

        # --- 步骤 1: 尝试设置任务栏/WM 图标 (使用 .ico) ---
        try:
            icon_path_ico = sub_file(Folder.RES, "icon.ico")
            LOGGER.debug(f"尝试获取 .ico 路径: {icon_path_ico}")
            if icon_path_ico and os.path.exists(icon_path_ico):
                LOGGER.debug(".ico 文件存在，尝试设置 iconbitmap...")
                try:
                    self.iconbitmap(icon_path_ico)
                    bitmap_icon_set = True  # 标记 iconbitmap 调用成功（无异常）
                    LOGGER.debug("已尝试使用 .ico 设置图标 (通过 iconbitmap)")
                except Exception as e_ico_bitmap:
                    LOGGER.warning(f"使用 iconbitmap 设置 .ico 失败: {e_ico_bitmap}")
            else:
                LOGGER.debug(f".ico 文件不存在或路径无效: {icon_path_ico}")
        except Exception as e_ico:
            LOGGER.warning(f"处理 .ico 文件路径时出错: {e_ico}", exc_info=True)

        # --- 步骤 2: 尝试设置窗口左上角图标 (优先使用 .png) ---
        try:
            icon_path_png = sub_file(Folder.RES, "icon.png")
            LOGGER.debug(f"尝试获取 .png 路径: {icon_path_png}")
            if icon_path_png and os.path.exists(icon_path_png):
                LOGGER.debug(".png 文件存在，尝试使用 Pillow 加载并设置 iconphoto...")
                try:
                    pil_image = Image.open(icon_path_png)
                    photo_icon = ImageTk.PhotoImage(pil_image)
                    self._app_icon_photo = photo_icon
                    LOGGER.debug(f"PNG PhotoImage 已创建并存储: {self._app_icon_photo}")
                    # 检查窗口是否仍然存在，以防在延迟期间被关闭
                    if self.winfo_exists():
                        self.iconphoto(False, self._app_icon_photo)
                        self.iconphoto(False, self._app_icon_photo)
                        photo_icon_set = True  # 标记 iconphoto 调用成功（无异常）
                        LOGGER.debug("已使用 .png 设置图标 (通过 Pillow + iconphoto)")
                    else:
                        LOGGER.debug("窗口在延迟设置 iconphoto 之前已关闭。")
                except ImportError:
                    LOGGER.error(
                        "Pillow (PIL) 库未安装或导入失败。无法加载 PNG 图标。请运行 'pip install Pillow'"
                    )
                except FileNotFoundError:
                    LOGGER.error(f"图标文件 .png 未找到 (路径: {icon_path_png})")
                except Exception as e_png:
                    LOGGER.error(f"加载或设置 .png 图标时出错: {e_png}", exc_info=True)
            else:
                LOGGER.warning(f".png 文件不存在或路径无效: {icon_path_png}")

        except Exception as e_png_path:
            LOGGER.warning(f"处理 .png 文件路径时出错: {e_png_path}", exc_info=True)

        # --- 步骤 3: 如果 PNG 失败，最后尝试用 tk.PhotoImage 加载 ICO 设置 iconphoto (成功率低) ---
        if not photo_icon_set and icon_path_ico and os.path.exists(icon_path_ico):
            LOGGER.debug(
                "PNG 设置 iconphoto 失败或未执行，尝试用 tk.PhotoImage 加载 ICO 设置 iconphoto..."
            )
            try:
                ico_photo = tk.PhotoImage(file=icon_path_ico)
                self.iconphoto(False, ico_photo)
                self._app_icon_photo = ico_photo  # 存储引用
                photo_icon_set = True
                LOGGER.debug(
                    "已尝试使用 tk.PhotoImage 加载 .ico 设置 iconphoto (可能失败)"
                )
            except tk.TclError as e_ico_photo:
                LOGGER.warning(
                    f"tk.PhotoImage 加载 .ico 用于 iconphoto 再次失败: {e_ico_photo}"
                )
            except Exception as e_ico_generic:
                LOGGER.error(
                    f"尝试用 tk.PhotoImage 加载 ICO 设置 iconphoto 时发生意外错误: {e_ico_generic}",
                    exc_info=True,
                )

        # --- 最终日志 ---
        if photo_icon_set:
            LOGGER.info("窗口左上角图标 (iconphoto) 已成功设置。")
        else:
            LOGGER.warning("未能成功设置窗口左上角图标 (iconphoto)。")
        if bitmap_icon_set:
            LOGGER.info("任务栏/WM 图标 (iconbitmap) 已成功设置。")
        else:
            LOGGER.warning("未能成功设置任务栏/WM 图标 (iconbitmap)。")

        LOGGER.debug("HelpWindow 图标设置结束。")

    # _safe_set_iconphoto 不再需要，已集成到 _setup_icon

    # ... (其他方法 _run_in_thread, _check_for_update 等保持不变) ...

    def _run_in_thread(self, target_func: Callable, *args):
        """辅助函数：在单独的线程中运行目标函数"""
        thread = threading.Thread(target=target_func, args=args, daemon=True)
        thread.start()
        LOGGER.debug(f"启动后台线程: {target_func.__name__}")

    def _check_for_update(self):
        """检查更新 (在线程中运行)"""
        LOGGER.info("请求检查更新...")
        if self.winfo_exists():
            self.update_button.configure(state="disabled")
            self._run_in_thread(self.updater.check_update)
        else:
            LOGGER.warning("请求检查更新时窗口已不存在。")

    def _download_update(self):
        """下载并解压更新 (在线程中运行)"""
        LOGGER.info("请求下载并准备更新...")
        if self.winfo_exists():
            self.update_button.configure(state="disabled")
            self._run_in_thread(self.updater.prepare_update)
        else:
            LOGGER.warning("请求下载更新时窗口已不存在。")

    def _start_update(self):
        """开始更新过程 (确认后执行)"""
        LOGGER.info("询问用户是否开始更新...")
        confirm_message = getattr(
            self.st.lan(), "UPDATE_PREPARED_CONFIRM", self.st.lan().UPDATE_PREPARED
        )

        # 确保 messagebox 的父窗口是 HelpWindow
        if messagebox.askokcancel(
            self.st.lan().START_UPDATE, confirm_message, parent=self
        ):
            LOGGER.info("用户确认更新。执行启动命令...")
            if not self.winfo_exists():
                LOGGER.warning("确认更新后，窗口在启动前关闭。")
                return

            self.update_button.configure(state="disabled")
            try:
                self.updater.start_update()
                # 如果 start_update 不退出应用，可能需要手动关闭 HelpWindow
                # self._on_close()
            except Exception as e:
                LOGGER.error(f"启动更新进程失败: {e}", exc_info=True)
                if self.winfo_exists():
                    messagebox.showerror(
                        self.st.lan().ERROR,
                        f"{self.st.lan().ERROR_STARTING_UPDATE}: {e}",
                        parent=self,
                    )
                    # 启动失败后，恢复按钮状态以便重试
                    self.update_button.configure(
                        state="normal",
                        text=self.st.lan().CHECK_FOR_UPDATE,
                        command=self._check_for_update,
                    )
                    self.update_str_var.set(
                        f"{self.st.lan().ERROR}: {self.st.lan().ERROR_STARTING_UPDATE}"
                    )
        else:
            LOGGER.info("用户取消了更新过程。")
            if self.winfo_exists():
                # 用户取消，保持“开始更新”按钮可用
                self.update_button.configure(state="normal")

    def _refresh_ui(self):
        """定期根据 Updater 状态更新 UI (优化版)"""
        if not self.winfo_exists():
            LOGGER.debug("_refresh_ui 检测到窗口已销毁，停止刷新。")
            if self._refresh_timer_id:
                try:
                    self.after_cancel(self._refresh_timer_id)
                except tk.TclError:
                    pass
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
                LOGGER.debug("帮助 HTML 内容已更新。")
            except Exception as e:
                LOGGER.error(f"设置 HTML 内容时出错: {e}", exc_info=True)
                try:
                    self.html_box.configure(state=tk.NORMAL)
                    self.html_box.set_html(
                        f"<h3>{lan.ERROR}</h3><p>无法加载帮助内容。</p><p><small>{e}</small></p>"
                    )
                    self.html_box.configure(state=tk.DISABLED)
                except:
                    pass  # 避免错误循环

        # --- 根据状态确定新 UI 状态 ---
        new_label_text = ""
        new_button_text = self.update_button.cget("text")
        new_button_state = "disabled"
        new_button_command = lambda: None  # 默认为无操作

        # 使用 match-case (Python 3.10+) 或 if/elif/else
        # (假设 UpdateStatus 是 Enum 或类似常量)
        if current_status == UpdateStatus.NONE:
            new_label_text = getattr(lan, "READY_TO_CHECK", "")  # 可选的“就绪”消息
            new_button_text = lan.CHECK_FOR_UPDATE
            new_button_state = "normal"
            new_button_command = self._check_for_update
        elif current_status == UpdateStatus.CHECKING:
            new_label_text = lan.CHECKING_UPDATE + "..."
            new_button_text = lan.CHECKING_UPDATE  # 可选地更改按钮文本
            new_button_state = "disabled"
        elif current_status == UpdateStatus.NO_UPDATE:
            new_label_text = lan.NO_UPDATE_FOUND + f" (v{updater.web_version})"
            new_button_text = lan.CHECK_FOR_UPDATE
            new_button_state = "normal"
            new_button_command = self._check_for_update
        elif current_status == UpdateStatus.NEW_VERSION:
            new_label_text = lan.UPDATE_AVAILABLE + f" v{updater.web_version}"
            new_button_text = lan.DOWNLOAD_UPDATE
            new_button_state = "normal"
            new_button_command = self._download_update
        elif current_status == UpdateStatus.DOWNLOADING:
            progress = updater.dl_progress
            # 格式化进度，处理非数字情况
            progress_str = (
                f"{progress:.1f}%"
                if isinstance(progress, (int, float))
                else str(progress)
            )
            new_label_text = lan.DOWNLOADING + f" {progress_str}"
            new_button_text = lan.DOWNLOADING
            new_button_state = "disabled"
        elif current_status == UpdateStatus.UNZIPPING:
            new_label_text = lan.UNZIPPING + "..."
            new_button_text = lan.UNZIPPING
            new_button_state = "disabled"
        elif current_status == UpdateStatus.PREPARED:
            new_label_text = lan.UPDATE_PREPARED
            new_button_text = lan.START_UPDATE
            new_button_state = "normal"
            new_button_command = self._start_update
        elif current_status == UpdateStatus.ERROR:
            err_msg = (
                str(updater.update_exception)
                if updater.update_exception
                else "未知错误"
            )
            new_label_text = (
                f"{lan.ERROR}: {getattr(lan, 'UPDATE_FAILED_SEE_LOG', '更新失败')}"
            )
            LOGGER.error(
                f"更新错误状态: {err_msg}",
                exc_info=(updater.update_exception is not None),
            )
            new_button_text = lan.CHECK_FOR_UPDATE  # 允许重试
            new_button_state = "normal"
            new_button_command = self._check_for_update
        else:  # 未知状态处理
            new_label_text = f"{lan.ERROR}: 未知状态 ({current_status})"
            LOGGER.warning(f"UI 刷新遇到未处理的更新状态: {current_status}")
            new_button_text = lan.ERROR
            new_button_state = "disabled"

        # --- 仅在必要时更新 UI 元素 ---
        if self.update_str_var.get() != new_label_text:
            self.update_str_var.set(new_label_text)

        # 优化按钮更新：仅当状态、文本或命令需要更改时才调用 configure
        current_button_state = self.update_button.cget("state")
        current_button_text = self.update_button.cget("text")
        # 获取当前命令可能比较复杂，这里简化为：如果状态或文本变了，就更新所有三个
        if (
            current_button_state != new_button_state
            or current_button_text != new_button_text
        ):
            self.update_button.configure(
                text=new_button_text, state=new_button_state, command=new_button_command
            )
        # 特殊情况：如果状态从 disabled 变为 normal，即使文本没变，也需要确保命令是正确的
        elif new_button_state == "normal" and current_button_state != "normal":
            self.update_button.configure(
                state=new_button_state, command=new_button_command
            )

        # --- 安排下一次刷新 ---
        self._refresh_timer_id = self.after(200, self._refresh_ui)  # 200ms 刷新间隔

    def _on_close(self):
        """当窗口关闭时调用"""
        LOGGER.debug("HelpWindow 关闭...")
        if self._refresh_timer_id:
            try:
                self.after_cancel(self._refresh_timer_id)
                LOGGER.debug("刷新定时器已取消。")
            except tk.TclError:
                LOGGER.warning("取消刷新定时器时 TclError (可能在解释器关闭期间)。")
            self._refresh_timer_id = None
        # 清理 PhotoImage 引用 (虽然 Python 垃圾回收通常会处理，但显式清理无害)
        self._app_icon_photo = None
        self.destroy()
        LOGGER.debug("HelpWindow 已销毁。")
