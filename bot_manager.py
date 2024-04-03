"""
This file contains the BotManager class, which manages the bot logic, game state, and automation
It also manages the browser and overlay display
The BotManager class is run in a separate thread, and provide interface methods for UI
"""
import time
import queue
import threading
from browser import GameBrowser
import mitm
import liqi
import game_state
import mj_helper
from mj_helper import MJAI_TYPE, MJAI_TILE_2_UNICODE, ActionUnicode, MJAI_TILES_34, MJAI_AKA_DORAS

import log_helper
from log_helper import LOGGER
import settings
import automation
import mj_bot
from lan_str import LanStrings
import utils
from utils import UI_STATE

METHODS_TO_IGNORE = [
    liqi.LiqiMethod.checkNetworkDelay,
    liqi.LiqiMethod.heartbeat,
    liqi.LiqiMethod.loginBeat,
    liqi.LiqiMethod.fetchAccountActivityData,
    liqi.LiqiMethod.fetchServerTime,
]
MAJSOUL_DOMAINS = [
    "maj-soul.com",     # China
    "majsoul.com",      # old?
    "mahjongsoul.com",  # Japan
    "yo-star.com"       # English
]
class BotManager:
    """ Bot logic manager"""
    def __init__(self, setting:settings.Settings) -> None:
        self.settings = setting
        self.game_state:game_state.GameState = None
        self.game_flow_id = None
        self.liqi_parser:liqi.LiqiProto = None
        self.mitm_port = self.settings.mitm_port
        self.mitm_server:mitm.MitmController = mitm.MitmController(self.mitm_port)      # no domain restrictions for now
        self.browser = GameBrowser(self.settings.browser_width, self.settings.browser_height)
        self.automation = automation.Automation(self.browser, self.settings)
        
        self.bot:mj_bot.Bot = None
        
        self._thread:threading.Thread = None
        self._stop_event = threading.Event()
        
        self.bot_calculating = False    
        self._overlay_botleft_text:str = None       # if new text is different, update overlay bot-left
        self._overlay_botleft_last_update:float = 0 # last update time
        self._overlay_reaction:dict = None          # update overlay guidance if new reaction is different
        self._overlay_guide_last_update:float = 0   # last update time
        
        self.main_thread_exception:Exception = None
        """ Exception that had stopped the main thread"""
        self.game_exception:Exception = None   # game run time error (but does not break main thread)        
        self.ui_state:UI_STATE = UI_STATE.NOT_RUNNING   # initially not running
        
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
    
    def get_game_error(self) -> Exception:
        """ return game error msg if any, or none if not  
        These are errors that do not break the main thread, but main impact individual games
        e.g. game state error / ai bot error   
        """  
        return self.game_exception
        
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
        self._overlay_botleft_last_update = 0
        self._overlay_guide_last_update = 0
            
    def disable_overlay(self):
        LOGGER.debug("Bot Manager disabling overlay")
        self.settings.enable_overlay = False
        
    def is_overlay_enabled(self):
        return self.settings.enable_overlay
    
    def update_overlay(self):
        """ update the overlay if conditions are met"""
        if self._update_overlay_conditions_met():
            self._update_overlay_guide()
            self._update_overlay_botleft()
        
    def enable_automation(self):
        LOGGER.debug("Bot Manager enabling automation")
        self.settings.enable_automation = True
        # turn off retry check, so pending action will be done at retry
        
    def disable_automation(self):
        LOGGER.debug("Bot Manager disabling automation")
        self.settings.enable_automation = False
        self.automation.stop_execution()
        
    def is_automation_enabled(self):
        return self.settings.enable_automation
    
    def create_bot(self):
        """ create Bot object based on settings"""
        try:            
            self.bot = mj_bot.get_bot(self.settings)
            self.game_exception = None
            LOGGER.info("Created bot: %s", self.bot.name)                        
        except Exception as e:
            LOGGER.error("Failed to create bot: %s", e, exc_info=True)
            self.bot = None
            self.game_exception = e
            
    def is_bot_created(self):
        return self.bot is not None
    
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
            
            # Attempt to create bot. wait for the bot (gui may re-create)
            self.create_bot()
            while True:
                if self.bot is not None:
                    break
                else:
                    time.sleep(0.5)
            
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
                    LOGGER.error("Error processing msg: %s",e, exc_info=True)
                    self.game_exception = e
                
                self._things_to_do_every_loop()

            LOGGER.info("Shutting down browser")
            self.browser.stop()
            while self.browser.is_running():
                time.sleep(0.2)
            LOGGER.info("Browser stopped")
                
            LOGGER.info("Shutting down MITM")
            self.mitm_server.stop()
            while self.mitm_server.is_running():
                time.sleep(0.2)
            LOGGER.info("MITM stopped")            
            
        except Exception as e:
            self.main_thread_exception = e
            LOGGER.error("Bot Manager Thread Exception: %s", e, exc_info=True)
                
    def _things_to_do_every_loop(self):
        # things to do in every loop
        
        # check mitm
        if self.mitm_server.is_running() == False:
            raise utils.MITMException("MITM server stopped")
        
        # check overlay
        if self.browser and self.browser.is_page_loaded():
            if self.settings.enable_overlay:
                if self.browser.is_overlay_working() == False:
                    LOGGER.debug("Bot manager attempting turning on browser overlay")
                    self.browser.start_overlay()
                    # self._update_overlay_guide()
            else:
                if self.browser.is_overlay_working():
                    LOGGER.debug("Bot manager turning off browser overlay")
                    self.browser.stop_overlay()    
        
        self._retry_failed_automation() # retry failed automation
        # self._update_overlay_botleft() # update overlay bot-left
        
    def _process_msg(self, msg:mitm.WSMessage):
        """ process websocket message from mitm server"""
        
        if msg.type == mitm.WS_TYPE.START:
            LOGGER.debug("Websocket Flow started: %s", msg.flow_id)
        elif msg.type == mitm.WS_TYPE.END:
            LOGGER.debug("Websocket Flow ended: %s", msg.flow_id)
            if msg.flow_id == self.game_flow_id:
                self._process_end_game()
        elif msg.type == mitm.WS_TYPE.MESSAGE:
            # process ws message
            try:
                liqimsg = self.liqi_parser.parse(msg.content)
            except Exception as e:
                LOGGER.warning("Failed to parse liqi msg: %s\nError: %s", msg.content, e, exc_info=True)
                return
            # liqi_id = liqimsg['id']
            liqi_type = liqimsg['type']
            liqi_method = liqimsg['method']
            # liqi_data = liqimsg['data']
            # liqi_datalen = len(liqimsg['data'])
            
            if liqi_method in METHODS_TO_IGNORE:
                pass
            
            elif liqi_method == liqi.LiqiMethod.authGame and liqi_type == liqi.MsgType.REQ:
                # Game Start request msg: found game flow, initialize game state
                LOGGER.info("Game Started. Game Flow ID=%s", msg.flow_id)
                self.game_flow_id = msg.flow_id
                self.game_state = game_state.GameState(self.bot)    # create game state with bot
                self.game_state.input(liqimsg)      # authGame -> mjai:start_game, no reaction
                self.game_exception = None
                
            elif msg.flow_id == self.game_flow_id:
                # Game Flow Message (in-Game message)
                # Feed msg to game_state for processing with AI bot               
                LOGGER.debug('Game msg: %s', liqimsg)
                # self._update_overlay_guide()
                self.bot_calculating = True
                reaction = self.game_state.input(liqimsg)
                self.bot_calculating = False
                # self._update_overlay_guide()
                if reaction:
                    self._do_automation(reaction)
                    self.game_exception = None
                if self.game_state.is_game_ended:
                    self._process_end_game()

            else:
                LOGGER.debug('Other msg: %s', liqimsg)
    
    def _process_end_game(self):
        # End game processes
        self.game_flow_id = None
        self.game_state = None
        if self.browser:    # fix for corner case
            self.browser.overlay_clear_guidance()
        self.game_exception = None
    
    def _update_overlay_conditions_met(self) -> bool:
        if not self.settings.enable_overlay:
            return False
        if self.browser is None:
            return False
        return True
        
    def _update_overlay_guide(self):
        # Update overlay guide given pending reaction
        if self.game_state is None:
            return
        reaction = self.game_state.get_pending_reaction()
        
        # update if reaction has changed, or time elapsed
        if reaction != self._overlay_reaction or time.time() - self._overlay_guide_last_update > 0.5:
            if reaction:
                guide, options = mjai_reaction_2_guide(reaction, 3, self.settings.lan())
                self.browser.overlay_update_guidance(guide, self.settings.lan().OPTIONS_TITLE, options)
            else:
                self.browser.overlay_clear_guidance()
            self._overlay_reaction = reaction
            self._overlay_guide_last_update = time.time()
        
    def _update_overlay_botleft(self):
        # update overlay bottom left text
        if self._update_overlay_conditions_met() == False:
            return
        
        # maj copilot
        text = '😸' + self.settings.lan().APP_TITLE

        # Model
        model_text = '🤖'
        if self.is_bot_created():
            model_text += self.settings.lan().MODEL + ": " + self.bot.type.value
        else:
            model_text += self.settings.lan().AWAIT_BOT
        text += '\n' + model_text
        
        # autoplay
        if self.is_automation_enabled():
            autoplay_text = '✅' + self.settings.lan().AUTOPLAY + ': ' + self.settings.lan().ON
        else:
            autoplay_text = '⬛' + self.settings.lan().AUTOPLAY + ': ' + self.settings.lan().OFF
        text += '\n' + autoplay_text
        
        # line 4
        if self.main_thread_exception:
            line = '❌' + self.settings.lan().MAIN_THREAD_ERROR
        elif self.game_exception:
            line = '❌' + self.settings.lan().GAME_ERROR
        elif self.is_game_syncing():
            line = '⏳'+ self.settings.lan().SYNCING
        elif self.bot_calculating:
            line = '⏳'+ self.settings.lan().CALCULATING
        elif self.is_in_game():
            line = '▶️' + self.settings.lan().GAME_RUNNING
        else:
            line = '🟢' + self.settings.lan().READY_FOR_GAME
        text += '\n' + line
                    
        # update if there is a change or time elapsed
        if text != self._overlay_botleft_text or time.time() - self._overlay_botleft_last_update > 0.5:            
            self.browser.overlay_update_botleft(text)
            self._overlay_botleft_text = text
            self._overlay_botleft_last_update = time.time()
        
    def _automation_conditions_met(self) -> bool:
        # return True if automation conditions met
        # False if:
        # automation not enabled
        # game state is None (not in game)
        # browser is not running
        if not self.settings.enable_automation:
            return False
        if self.game_state is None:
            return False
        if not self.browser.is_running():
            return False
        return True
    
    def _do_automation(self, reaction:dict):
        # auto play given mjai reaction        
        
        if not self._automation_conditions_met():
            return False
        if not reaction:    # no reaction given
            return False
        
        try:
            self.automation.automate_action(reaction, self.game_state)
        except Exception as e:
            LOGGER.error("Failed to automate action for %s: %s", reaction['type'], e, exc_info=True)
            
    def _retry_failed_automation(self):
        # retry pending reaction if enabled
        if not self._automation_conditions_met():
            return False
            
        try:
            self.automation.retry_pending_reaction(self.game_state, self.settings.auto_retry_interval)
        except Exception as e:
            LOGGER.error("Error retrying automation: %s", e, exc_info=True)
            


def mjai_reaction_2_guide(
    reaction:dict, 
    max_options:int=3,
    lan_str:LanStrings=LanStrings()
    ) -> tuple[str, list]:
    """ Convert mjai reaction message to language specific AI guide 
    params:
        reaction(dict): reaction (output) message from mjai bot
        max_options(int): number of options to display. 0 to display no options
        lan_str(LanString): language specific string constants
        
    return:
        (action_str, options): action_str is the recommended action
        options is a list of options (str, float), each option being a tuple of tile str and a percentage number 
        
        sample output for Chinese:
        ("立直,切[西]", [("[西]", 0.9111111), ("立直", 0.077777), ("[一索]", 0.0055555)])        
        """
                
    if reaction is None:
        raise ValueError("Input reaction is None")
    re_type = reaction['type']
    pai = reaction.get('pai', None)
    def get_tile_str(mjai_tile:str):    # unicode + language specific name
        return MJAI_TILE_2_UNICODE[mjai_tile] + lan_str.mjai2str(mjai_tile)
    
    if pai:
        tile_str =  get_tile_str(pai)
    
    if re_type == MJAI_TYPE.DAHAI:
        action_str = f"{lan_str.DISCARD}{tile_str}"
    elif re_type == MJAI_TYPE.NONE:
        action_str = ActionUnicode.PASS + lan_str.PASS
    elif re_type == MJAI_TYPE.PON:
        action_str = f"{ActionUnicode.PON}{lan_str.PON}{tile_str}"
    elif re_type == MJAI_TYPE.CHI:
        comsumed = reaction['consumed']
        comsumed_strs = [f"{get_tile_str(x)}" for x in comsumed]
        action_str = f"{ActionUnicode.CHI}{lan_str.CHI}{tile_str}({''.join(comsumed_strs)})"
         
    elif re_type == MJAI_TYPE.KAKAN:
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.KAKAN})"
    elif re_type == MJAI_TYPE.DAIMINKAN:
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.DAIMINKAN})"
    elif re_type == MJAI_TYPE.ANKAN:
        tile_str = get_tile_str(reaction['consumed'][1])
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.ANKAN})"
    elif re_type == MJAI_TYPE.REACH: # attach reach dahai options
        reach_dahai_reaction = reaction['reach_dahai']
        dahai_action_str, dahai_options = mjai_reaction_2_guide(reach_dahai_reaction, 0, lan_str)
        action_str = f"{ActionUnicode.REACH}{lan_str.RIICHI}," + dahai_action_str
    elif re_type == MJAI_TYPE.HORA:
        if reaction['actor'] == reaction['target']:
            action_str = f"{ActionUnicode.AGARI}{lan_str.AGARI}({lan_str.TSUMO})"
        else:
            action_str = f"{ActionUnicode.AGARI}{lan_str.AGARI}({lan_str.RON})"
    elif re_type == MJAI_TYPE.RYUKYOKU:
        action_str = f"{ActionUnicode.RYUKYOKU}{lan_str.RYUKYOKU}"
    elif re_type == MJAI_TYPE.NUKIDORA:
        action_str = f"{lan_str.NUKIDORA}"
    else:
        action_str = lan_str.mjai2str(re_type)
    
    options = []
    if max_options > 0 and 'meta_options' in reaction:
        # process options. display top options with their weights
        meta_options = reaction['meta_options'][:max_options]
        if meta_options:
            for (code, q) in meta_options:      # code is in MJAI_MASK_LIST
                name_str = lan_str.mjai2str(code)
                if code in MJAI_TILES_34 or code in MJAI_AKA_DORAS:
                    # if it is a tile
                    name_str = get_tile_str(code)
                options.append((name_str, q))
        
    return (action_str, options)
                
if __name__ == "__main__":
    # Test code: a simple CLI to run BotManager
    log_helper.config_logging('TestBotManager')
    manager = BotManager(settings.Settings())
    manager.start() 

    commands = {
        'sb': manager.start_browser,
        'hud on': manager.enable_overlay,
        'hud off': manager.disable_overlay,
        'auto on': manager.enable_automation,
        'auto off': manager.disable_automation,
        'hud text': lambda: manager.browser.overlay_update_botleft("Sample text\n123456"),
        'hud text clear': manager.browser.overlay_clear_botleft,
        'quit': lambda: manager.stop(True),
    }
    
    while True:
        cmd = input("Input command:")
        if cmd in commands:
            commands[cmd]()
        else:
            LOGGER.info("Invalid command. Valid commands: %s", commands.keys())
        if manager.is_running() == False:
            break

    LOGGER.info("Manager stopped. End")



