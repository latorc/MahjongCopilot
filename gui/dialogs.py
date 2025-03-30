import os
import tkinter as tk
import customtkinter as ctk
from PIL import ImageTk # 导入 ImageTk 以便能识别 PhotoImage 类型（尽管对象是从 master 传来）
# from tkinter import Event # 如果不用 Event 类型提示，可以注释掉
from common.log_helper import LOGGER # 假设可以访问 LOGGER

class ConfirmExitDialog(ctk.CTkToplevel):
    """
    使用 ctk.CTkToplevel 作为基类的退出确认模态对话框。
    它将自动匹配主窗口的外观模式，并尝试正确设置图标。
    """
    def __init__(self, master, title: str, message: str):
        if not isinstance(master, (ctk.CTk, ctk.CTkToplevel)):
             LOGGER.warning(f"对话框的 Master 窗口类型是 {type(master)}, 期望是 CTk 或 CTkToplevel.")
             # raise TypeError("Master 窗口必须是 CTk 对象.") # 可以放宽限制

        super().__init__(master)
        self._master = master
        self._title = title
        self._message = message
        self._result = False

        # CTkToplevel 会自动处理背景和主题

        self._setup_dialog() # 调用设置（包含图标设置）
        self._create_widgets()
        self._center_window()
        self._bind_keys()

        # 设置焦点、模态、等待
        if hasattr(self, 'ok_button'):
            self.ok_button.focus_set()
        self.lift()
        self.attributes("-topmost", True)
        self.grab_set()

    def _setup_dialog(self):
        """配置对话框窗口属性，包括图标。"""
        self.title(self._title)
        self.geometry("350x150")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancel_clicked) # 点击关闭按钮时调用取消

        # --- 设置图标 (核心修改) ---
        # 从主窗口 (master) 获取图标数据
        # master.app_icon_path_ico 是 .ico 文件的路径 (在 main_gui 中设置)
        master_icon_path_ico = getattr(self._master, 'app_icon_path_ico', None)
        # master.app_icon_photo 是 PhotoImage 对象 (在 main_gui 中创建并存储)
        master_icon_photo = getattr(self._master, 'app_icon_photo', None)

        # 1. 【立即尝试】设置 .ico (使用 wm_iconbitmap) - 主要影响任务栏等
        if master_icon_path_ico and os.path.exists(master_icon_path_ico):
            try:
                self.wm_iconbitmap(master_icon_path_ico)
                LOGGER.debug(f"对话框尝试设置 wm_iconbitmap: {master_icon_path_ico}")
            except tk.TclError as e_wm_ico: # 捕获 tk 相关错误
                 LOGGER.warning(f"对话框设置 wm_iconbitmap 时发生 TclError: {e_wm_ico}")
            except Exception as e_wm_ico_gen:
                 LOGGER.warning(f"对话框设置 wm_iconbitmap 失败: {e_wm_ico_gen}", exc_info=True)
        else:
             LOGGER.debug("对话框: 未从主窗口获取到有效的 .ico 路径用于 wm_iconbitmap。")

        # 2. 【延迟执行】使用 after 设置 PhotoImage (关键步骤，用于窗口左上角)
        if master_icon_photo and isinstance(master_icon_photo, ImageTk.PhotoImage): # 检查是否是有效的 PhotoImage 对象
            try:
                # 延迟 250 毫秒后执行 lambda 函数来设置 iconphoto
                self.after(250, lambda: self.iconphoto(False, master_icon_photo))
                LOGGER.debug("对话框: 已安排 iconphoto 设置。")
            except Exception as e_schedule:
                LOGGER.error(f"对话框安排 iconphoto 设置失败: {e_schedule}", exc_info=True)
        else:
             LOGGER.debug("对话框: 未从主窗口获取到有效的 PhotoImage 对象用于 iconphoto。")
        # --- 图标设置结束 ---

    def _create_widgets(self):
        """使用 CTk 部件创建和布局对话框中的部件。"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.message_label = ctk.CTkLabel(
            self,
            text=self._message,
            wraplength=320,
            justify="center",
            font=ctk.CTkFont(size=13),
        )
        self.message_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="nsew")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # 假设 st.lan() 和按钮文本获取逻辑在 master 上下文中有效
        ok_text = getattr(getattr(self._master, 'st', None), 'lan', lambda: type('obj', (object,), {'OK_BUTTON': '确定'}))().OK_BUTTON
        cancel_text = getattr(getattr(self._master, 'st', None), 'lan', lambda: type('obj', (object,), {'CANCEL_BUTTON': '取消'}))().CANCEL_BUTTON

        self.ok_button = ctk.CTkButton(
            button_frame, text=ok_text, command=self._ok_clicked, width=100
        )
        self.ok_button.grid(row=0, column=0, padx=(20, 5), pady=0)

        self.cancel_button = ctk.CTkButton(
            button_frame, text=cancel_text, command=self._cancel_clicked, width=100
        )
        self.cancel_button.grid(row=0, column=1, padx=(5, 20), pady=0)

        if hasattr(self, 'ok_button'): # 确保按钮已创建
            self.ok_button.focus_set()

    def _center_window(self):
        """将对话框居中于其主窗口。"""
        try:
            self.update_idletasks()
            master_x = self._master.winfo_x()
            master_y = self._master.winfo_y()
            master_width = self._master.winfo_width()
            master_height = self._master.winfo_height()
            dialog_width = self.winfo_width()
            dialog_height = self.winfo_height()

            if dialog_width <= 1 or dialog_height <= 1:
                 try:
                     geo_parts = self.geometry().split('+')[0].split('x')
                     dialog_width = int(geo_parts[0])
                     dialog_height = int(geo_parts[1])
                 except:
                     dialog_width = 350; dialog_height = 150
                     LOGGER.warning("无法可靠获取对话框尺寸进行居中，使用默认值。")

            x = master_x + (master_width - dialog_width) // 2
            y = master_y + (master_height - dialog_height) // 2

            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            if x + dialog_width > screen_width: x = screen_width - dialog_width
            if y + dialog_height > screen_height: y = screen_height - dialog_height
            if x < 0: x = 0
            if y < 0: y = 0

            self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        except Exception as e:
            LOGGER.error(f"居中对话框时出错: {e}", exc_info=True)

    def _bind_keys(self):
        """绑定 Enter 和 Escape 键。"""
        self.bind("<Return>", self._ok_clicked_event, add='+')
        self.bind("<Escape>", self._cancel_clicked_event, add='+')

    def _ok_clicked_event(self, event=None):
        self._ok_clicked()

    def _cancel_clicked_event(self, event=None):
        self._cancel_clicked()

    def _ok_clicked(self):
        """处理确定按钮点击。"""
        self._result = True
        self.grab_release()
        self.destroy()

    def _cancel_clicked(self):
        """处理取消按钮点击或窗口关闭。"""
        self._result = False
        self.grab_release()
        self.destroy()

    @classmethod
    def ask(cls, master, title: str, message: str) -> bool:
        """
        类方法：创建、显示对话框、等待并返回结果。
        """
        # 可以在这里预检查 master 是否有需要的图标属性，如果需要更早报错的话
        # if not hasattr(master, 'app_icon_photo'):
        #     LOGGER.warning("调用 ConfirmExitDialog.ask 时，主窗口缺少 'app_icon_photo' 属性。")

        dialog = cls(master, title, message)
        master.wait_window(dialog)
        return getattr(dialog, '_result', False)