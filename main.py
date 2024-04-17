""" Main Entry Point for Mahjong Copilot """
import ctypes
import sys
from gui.main_gui import MainGUI
from common.log_helper import LogHelper
from common.settings import Settings
from bot_manager import BotManager


def main():
    """ Main entry point """
    LogHelper.config_logging()
    setting = Settings()
    if setting.gui_set_dpi and sys.platform == "win32":
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    bot_manager = BotManager(setting)
    gui = MainGUI(setting, bot_manager)
    gui.mainloop()

if __name__ == "__main__":
    main()
