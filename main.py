""" Main Entry Point for Mahjong Copilot """
import ctypes
import sys
from gui.main_gui import MainGUI
from common.log_helper import LogHelper
from common.settings import Settings
from bot_manager import BotManager

def set_dpi_awareness():
    """ Set DPI Awareness """
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # for Windows 8.1 and later
        except AttributeError:
            ctypes.windll.user32.SetProcessDPIAware()       # for Windows Vista and later
        except: #pylint:disable=bare-except
            pass

def main():
    """ Main entry point """
    LogHelper.config_logging()
    setting = Settings()
    # set_dpi_awareness()
    bot_manager = BotManager(setting)
    gui = MainGUI(setting, bot_manager)
    gui.mainloop()

if __name__ == "__main__":
    main()
