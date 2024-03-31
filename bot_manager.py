import utils
import time
import mitm
import queue
import threading
from browser import GameBrowser
import liqi
import game_state
import mj_helper
import lan_strings
from pathlib import Path

from log_helper import LOGGER, config_logging
import settings
import automation
from mjai.engine import get_engine
from utils import MODEL_FOLDER

METHODS_TO_IGNORE = [
    liqi.LiqiMethod.checkNetworkDelay,
    liqi.LiqiMethod.heartbeat,
    liqi.LiqiMethod.loginBeat,
    liqi.LiqiMethod.fetchAccountActivityData,
    liqi.LiqiMethod.fetchServerTime,
]

class BotManager:
    """ Bot logic manager"""
    def __init__(self, setting:settings.Settings) -> None:
        self.settings = setting
        self.game_state:game_state.GameState = None
        self.game_flow_id = None
        self.liqi_parser:liqi.LiqiProto = None
        self.mitm_port = self.settings.mitm_port
        self.mitm_server:mitm.MitmController = mitm.MitmController(self.mitm_port, ["maj-soul.com"])
        self.browser = GameBrowser(self.settings.browser_width, self.settings.browser_height)
        self.automation = automation.Automation(self.browser)
        
        self.lan_str:lan_strings.LanStrings = lan_strings.LAN_OPTIONS[setting.language]
        self.model_file = None
        
        self._thread:threading.Thread = None
        self._stop_event = threading.Event()
        
        self.exception:Exception = None
        """ Exception that had stopped the main thread"""
    

    def _methods(self):
        # api methods
        if 0<1:
            return
        self.mitm_server.is_running()
        self.mitm_server.install_mitm_cert()
        
        self.browser.is_running()
        
        self.start()
        self.stop()
        self.is_running()
        self.is_in_game()
        
    def start(self):
        """ Start bot manager thread"""
        self._thread = threading.Thread(
            target=self._run,
            name="BotThread",
            daemon=True
        )
        self._thread.start()
    
    def stop(self, join_thread:bool):
        """ Stop bot manager thread"""
        self._stop_event.set()
        if join_thread:
            self._thread.join()
        
    def is_running(self) -> bool:
        """ return True if bot manager thread is running"""
        if self._thread and self._thread.is_alive():
            return True
        else:
            return False
        
    def is_in_game(self) -> bool:
        """ return True if the bot is currently in a game """
        if self.game_state:
            return True
        else:
            return False
        
    def get_game_info(self) -> mj_helper.GameInfo:
        """ Get gameinfo derived from game_state. can be None"""
        if self.game_state is None:
            return None
        
        return self.game_state.get_game_info()
    
    def is_game_syncing(self) -> bool:
        """ is mjai syncing game messages (from disconnection) """
        if self.game_state:
            return self.game_state.is_ms_syncing
    
    def is_mjai_error(self) -> bool:
        """ return True if mjai bot has encountered running errors 
        (possibly from wrong inputs/unexpected states, and possibly has crashed)"""
        if self.game_state:
            return self.game_state.is_mjai_error
        
    def start_browser(self):
        """ Start the browser thread, open browser window """
        ms_url = self.settings.ms_url
        proxy = r'http://localhost:' + str(self.mitm_port)    
        self.browser.start(ms_url, proxy, self.settings.browser_width, self.settings.browser_height)
        
    def get_pending_reaction(self) -> dict:
        """ returns the pending mjai output reaction (which hasn't been acted on)"""
        if self.game_state:
            reaction = self.game_state.get_pending_reaction()                      
            return reaction
        else:   # None
            return None
    
    def enable_overlay(self):
        """ Start the overlay thread"""
        LOGGER.debug("Bot Manager enabling overlay")
        self.settings.enable_overlay = True
        self.settings.save_json()
            
    def disable_overlay(self):
        LOGGER.debug("Bot Manager disabling overlay")
        self.settings.enable_overlay = False
        self.settings.save_json()
        
    def is_overlay_enabled(self):
        return self.settings.enable_overlay        
        
    def enable_automation(self):
        LOGGER.debug("Bot Manager enabling automation")
        self.settings.enable_automation = True
        self.settings.save_json()
        self.automation.allow_execution()
        # turn off retry check, so pending action will be done at retry
        self.automation.last_exe_step = None
        self.automation.last_exe_time = time.time()
        
    def disable_automation(self):
        LOGGER.debug("Bot Manager disabling automation")
        self.settings.enable_automation = False
        self.settings.save_json()
        self.automation.stop_execution()
        
    def is_automation_enabled(self):
        return self.settings.enable_automation
    
    def _run(self):
        """ Keep running the main loop (blocking)"""
        try:
            LOGGER.info("Starting MITM proxy server")
            self.mitm_server.start()
            LOGGER.info("Installing MITM certificate")
            if self.mitm_server.install_mitm_cert():
                LOGGER.info("MITM certificate installed")
            else:
                LOGGER.error("MITM certificate installation failed")
            
            # Validate model file
            self.model_file = Path(MODEL_FOLDER)/self.settings.model_file
            if not self.model_file.exists():
                raise utils.ModelFileException(f"Cannot find model file:{self.model_file}")            
            
            self.liqi_parser = liqi.LiqiProto()
            if self.settings.auto_launch_browser:
                self.start_browser()
            
            while self._stop_event.is_set() == False:
                # keep processing majsoul game messages forwarded from mitm server
                try:
                    msg = self.mitm_server.get_message()
                    self._process_msg(msg)                   
                except queue.Empty:
                    time.sleep(0.1)
                except Exception as e:
                    LOGGER.error("Error ")
                
                self._things_to_do_every_loop()

                
            LOGGER.info("Shutting down MITM")
            self.mitm_server.stop()
            while self.mitm_server.is_running():
                time.sleep(0.2)
            LOGGER.info("MITM stopped")
            
            LOGGER.info("Shutting down browser")
            self.browser.stop()
            while self.browser.is_running():
                time.sleep(0.2)
            LOGGER.info("Browser stopped")
        except Exception as e:
            self.exception = e
            LOGGER.error("Thread Exception: %s", e, exc_info=True)
                
    def _things_to_do_every_loop(self):
        # things to do in every loop
        
        # check overlay
        if self.browser and self.browser.is_page_loaded():
            if self.settings.enable_overlay:
                if self.browser.is_overlay_on() == False:
                    LOGGER.debug("Bot manager attempting turning on browser overlay")
                    self.browser.start_overlay()
                    self._overlay_show_pending_action()
            else:
                if self.browser.is_overlay_on():
                    LOGGER.debug("Bot manager turning off browser overlay")
                    self.browser.stop_overlay()    
        # retry failed automation
        self._retry_failed_automation()
        
    def _process_msg(self, msg:mitm.WSMessage):
        """ process websocket message from mitm server"""
        
        if msg.type == mitm.WS_START:
            LOGGER.debug("WS Flow started: %s", msg.flow_id)
        elif msg.type == mitm.WS_END:
            LOGGER.debug("WS Flow ended: %s", msg.flow_id)
            if msg.flow_id == self.game_flow_id:
                self._process_end_game()
        elif msg.type == mitm.WS_MESSAGE:
            # process ws message              
            liqimsg = self.liqi_parser.parse(msg.content)
            if liqimsg is None:
                LOGGER.warning("Failed to parse liqi message: %s", msg.content)
                return
            liqi_id = liqimsg['id']
            liqi_type = liqimsg['type']
            liqi_method = liqimsg['method']
            liqi_data = liqimsg['data']
            liqi_datalen = len(liqimsg['data'])
            
            if liqi_method in METHODS_TO_IGNORE:
                pass
            
            elif liqi_method == liqi.LiqiMethod.authGame and liqi_type == liqi.MsgType.Req:
                # Game Start request msg
                LOGGER.info("Game Started. Game Flow ID=%s", msg.flow_id)
                self.game_flow_id = msg.flow_id
                
                engine = get_engine(self.model_file)
                self.game_state = game_state.GameState(engine)
                self.game_state.input(liqimsg)      # authGame -> mjai:start_game, no reaction
                
            elif msg.flow_id == self.game_flow_id:
                # Game Flow Message (in-Game message)
                # Feed msg to game_state for processing with AI bot               
                LOGGER.debug('Game msg: %s', liqimsg)                    
                reaction = self.game_state.input(liqimsg)
                self._overlay_show_pending_action()
                self._do_automation(reaction)
                if self.game_state.is_game_ended:
                    self._process_end_game()                    

            else:
                LOGGER.debug('Other msg: %s', liqimsg)
    
    def _process_end_game(self):
        # End game processes
        self.game_flow_id = None
        self.game_state = None
        if self.browser:    # fix for corner case
            self.browser.overlay_clear_text()
        
    def _overlay_show_pending_action(self):
        # process pending reaction
        if self.game_state is None:
            return
        if not self.settings.enable_overlay:
            return
        if self.browser is None:
            return
        
        reaction = self.game_state.get_pending_reaction()
        # update overlay if needed
        if self.browser.is_overlay_on() == False:
            self.browser.start_overlay()
        if reaction:
            guide, options = mj_helper.mjai_reaction_2_guide(reaction, 3, self.lan_str)
            self.browser.overlay_update_text(guide, self.lan_str.OPTIONS_TITLE, options)
        else:
            self.browser.overlay_clear_text()
    
    def _do_automation(self, reaction:dict):
        # auto play given mjai reaction
        if not self.settings.enable_automation:
            return 
        if self.game_state is None:
            return
        if reaction is None:
            return
        try:
            self.automation.execute_action(reaction, self.game_state)
        except Exception as e:
            LOGGER.error("Failed to automate action for %s: %s", reaction['type'], e, exc_info=True)
            
    def _retry_failed_automation(self):
        # retry pending reaction if enabled
        if self.game_state is None:
            return
        if not self.settings.enable_automation:
            return
        
        try:
            self.automation.retry_pending_reaction(self.game_state)
        except Exception as e:
            LOGGER.error("Error retrying automation: %s", e, exc_info=True)
            
                
if __name__ == "__main__":
    config_logging('SimpleClient')
    manager = BotManager(settings.Settings())
    manager.start()    

    while True:
        cmd = input()
        if cmd == 'q':
            break
        if cmd == 'sb':
            manager.start_browser()
    manager.stop()
    while manager.is_running() == True:
        time.sleep(0.1)
    LOGGER.info("Manager stopped")
    