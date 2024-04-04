""" a command line interface for testing bot manager and other modules """

from PIL import Image, ImageChops, ImageStat
from utils import RES_FOLDER, TEMP_FOLDER
import img_proc
from img_proc import ImgTemp
import utils
import log_helper
import browser
from browser import GameBrowser
import automation
import settings
import bot_manager
    
def cli():
    log_helper.config_logging('test_CLI')
    st = settings.Settings()
    bm = bot_manager.BotManager(st)
    bm.start()
    while True:
        cmd = input("Command:")
        match cmd:
            case 'q':   # quit
                bm.stop(True)
                break
            case 'sb':  # start browser
                bm.start_browser()
            case 'ss':  # screenshot
                file = bm.browser.screen_shot()
                print('screenshot: ', file)
            case 'ct':
                res, diff = bm.automation.g_v.comp_temp(ImgTemp.main_menu, 30)
                print(f"Test main menu:{res} (diff={diff})")
            case 'st load':     # settings load
                st.load_json()
            case 'st print':    # settings print
                print(st.__dict__)
            case 'auto enable':
                bm.enable_automation()
            case 'auto disable':
                bm.disable_automation()
            case _:
                print("unknow cmd")
                
    print("Exited. Done.")
        
if __name__ == "__main__":
    cli()