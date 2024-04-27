"""
This file contains the BotManager class, which manages the bot logic, game state, and automation
It also manages the browser and overlay display
The BotManager class is run in a separate thread, and provide interface methods for UI
"""
# pylint: disable=broad-exception-caught
import time
import queue
import threading

from game.browser import GameBrowser
from game.game_state import GameState
from game.automation import Automation, UiState, JOIN_GAME, END_GAME
import mitm
import proxinject
import liqi
from common.mj_helper import MjaiType, GameInfo, MJAI_TILE_2_UNICODE, ActionUnicode, MJAI_TILES_34, MJAI_AKA_DORAS
from common.log_helper import LOGGER
from common.settings import Settings
from common.lan_str import LanStr
from common import utils
from common.utils import FPSCounter
from bot import Bot, get_bot


METHODS_TO_IGNORE = [
    liqi.LiqiMethod.checkNetworkDelay,
    liqi.LiqiMethod.heartbeat,
    liqi.LiqiMethod.loginBeat,
    liqi.LiqiMethod.fetchAccountActivityData,
    liqi.LiqiMethod.fetchServerTime,
]

class BotManager:
    """ Bot logic manager"""
    def __init__(self, setting:Settings) -> None:
        self.st = setting
        self.game_state:GameState = None

        self.liqi_parser = liqi.LiqiProto()
        self.mitm_server:mitm.MitmController = mitm.MitmController()      # no domain restrictions for now
        self.proxy_injector = proxinject.ProxyInjector()
        self.browser = GameBrowser(self.st.browser_width, self.st.browser_height)
        self.automation = Automation(self.browser, self.st)
        self.bot:Bot = None

        self._thread:threading.Thread = None
        self._stop_event = threading.Event()
        self.fps_counter = FPSCounter()

        self.lobby_flow_id:str = None                   # websocket flow Id for lobby
        self.game_flow_id = None                        # websocket flow that corresponds to the game/match
       
        self.bot_need_update:bool = True                # set this True to update bot in main thread
        self.mitm_proxinject_need_update:bool = False    # set this True to update mitm and prox inject in main thread
        self.is_loading_bot:bool = False                # is bot being loaded
        self.main_thread_exception:Exception = None     # Exception that had stopped the main thread
        self.game_exception:Exception = None            # game run time error (but does not break main thread)        
        
        
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
        
        
    def get_game_info(self) -> GameInfo:
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
    
    
    def get_game_client_type(self) -> utils.GameClientType:
        """ return the running game client type. return None if none is running"""
        if self.browser.is_running():
            return utils.GameClientType.PLAYWRIGHT
        elif self.lobby_flow_id or self.game_flow_id:
            return utils.GameClientType.PROXY
        else:
            return None        
        
    def start_browser(self):
        """ Start the browser thread, open browser window """
        ms_url = self.st.ms_url
        proxy = self.mitm_server.proxy_str
        self.browser.start(ms_url, proxy, self.st.browser_width, self.st.browser_height, self.st.enable_chrome_ext)
    
    def is_browser_zoom_off(self):
        """ check browser zoom level, return true if zoomlevel is not 1"""
        if self.browser and self.browser.is_page_normal():
            zoom = self.browser.zoomlevel_check
            if zoom is not None:
                if abs(zoom - 1) > 0.001:
                    return True
        return False
        
    # mitm restart not working for now. disable this.        
    # def set_mitm_proxinject_update(self):
    #     """ restart mitm proxy server"""
    #     self.mitm_proxinject_need_update = True
        
        
    def set_bot_update(self):
        """ mark bot needs update"""
        self.bot_need_update = True
        
    
    def is_bot_created(self):
        """ return true if self.bot is not None"""
        return self.bot is not None
        

    def is_bot_calculating(self):
        """ return true if bot is calculating"""
        if self.game_state and self.game_state.is_bot_calculating:
            return True
        else:
            return False
        
        
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
        self.st.enable_overlay = True
        
            
    def disable_overlay(self):
        """ disable browser overlay"""
        LOGGER.debug("Bot Manager disabling overlay")
        self.st.enable_overlay = False
        
    
    def update_overlay(self):
        """ update the overlay if conditions are met"""
        if self._update_overlay_conditions_met():
            self._update_overlay_guide()
            self._update_overlay_botleft()
            
        
    def enable_automation(self):
        """ enable automation"""
        LOGGER.debug("Bot Manager enabling automation")
        self.st.enable_automation = True
        self.automation.decide_lobby_action()
        
        
    def disable_automation(self):
        """ disable automation"""
        LOGGER.debug("Bot Manager disabling automation")
        self.st.enable_automation = False
        self.automation.stop_previous()
        
        
    def enable_autojoin(self):
        """ enable autojoin"""
        LOGGER.debug("Enabling Auto Join")
        self.st.auto_join_game = True
        
        
    def disable_autojoin(self):
        """ disable autojoin"""
        LOGGER.debug("Disabling Auto Join")
        self.st.auto_join_game = False
        # stop any lobby tasks
        if self.automation.is_running_execution():
            name, _d = self.automation.running_task_info()
            if name in (JOIN_GAME, END_GAME):
                self.automation.stop_previous()
        
    def _create_bot(self):
        """ create Bot object based on settings"""
        try:            
            self.is_loading_bot = True
            self.bot = None
            self.bot = get_bot(self.st)
            self.game_exception = None
            LOGGER.info("Created bot: %s. Supported Modes: %s", self.bot.name, self.bot.supported_modes)
        except Exception as e:
            LOGGER.warning("Failed to create bot: %s", e, exc_info=True)
            self.bot = None
            self.game_exception = e
        self.is_loading_bot = False
        
    def _create_mitm_and_proxinject(self):
        # create mitm and proxinject threads
        # enable proxyinject requires socks5, which disables upstream proxy
        if self.st.enable_proxinject:
            mode = mitm.SOCKS5
            LOGGER.debug("Enabling proxyinject requires socks5, and it disables upstream proxy")
        else:
            mode = mitm.HTTP

        self.mitm_server.start(self.st.mitm_port, mode, self.st.upstream_proxy)
        res = self.mitm_server.install_mitm_cert()
        if not res:
            self.main_thread_exception = utils.MitmCertNotInstalled(self.mitm_server.cert_file)
        
        if self.st.enable_proxinject:
            self.proxy_injector.start(self.st.inject_process_name, "127.0.0.1", self.st.mitm_port)
        

    def _run(self):
        """ Keep running the main loop (blocking)"""
        try:
            self._create_mitm_and_proxinject()
            if self.st.auto_launch_browser:
                self.start_browser()

            while self._stop_event.is_set() is False:   # thread main loop
                # keep processing majsoul game messages forwarded from mitm server
                self.fps_counter.frame()
                self._loop_pre_msg()
                try:                    
                    msg = self.mitm_server.get_message()
                    self._process_msg(msg)                                  
                except queue.Empty:
                    time.sleep(0.002)
                except Exception as e:
                    LOGGER.error("Error processing msg: %s",e, exc_info=True)
                    self.game_exception = e                    
                self._loop_post_msg()
                                    
            # loop ended, clean up before exit
            LOGGER.info("Shutting down browser")
            self.browser.stop(True)                
            LOGGER.info("Shutting down MITM")
            self.mitm_server.stop()
            if self.proxy_injector.is_running():
                LOGGER.info("Shutting down proxy injector")
                self.proxy_injector.stop(True)
            LOGGER.info("Bot manager thread ending.")         
            
        except Exception as e:
            self.main_thread_exception = e
            LOGGER.error("Bot Manager Thread Exception: %s", e, exc_info=True)
            
    
    def _loop_pre_msg(self):
        """ things to do every loop before processing msg"""
        #  update bot if needed
        if self.bot_need_update and self.is_in_game() is False:
            self._create_bot()
            self.bot_need_update = False
            
        # update mitm if needed: when no one is using mitm
        if self.mitm_proxinject_need_update:
            if not (self.browser.is_running()):
                LOGGER.debug("Updating mitm and proxy injector")
                self.proxy_injector.stop(True)
                self.mitm_server.stop()
                self._create_mitm_and_proxinject()
                self.mitm_proxinject_need_update = False
        
                
    def _loop_post_msg(self):
        # things to do in every loop after processing msg
        # check mitm
        if self.mitm_server.is_running() is False:
            self.game_exception = utils.MITMException("MITM server stopped")
        else:   # clear exception
            if isinstance(self.game_exception, utils.MITMException):
                self.game_exception = None
                
        # check overlay
        if self.browser and self.browser.is_page_normal():
            if self.st.enable_overlay:
                if self.browser.is_overlay_working() is False:
                    LOGGER.debug("Bot manager attempting turning on browser overlay")
                    self.browser.start_overlay()
                    # self._update_overlay_guide()
            else:
                if self.browser.is_overlay_working():
                    LOGGER.debug("Bot manager turning off browser overlay")
                    self.browser.stop_overlay()
        
        self.automation.automate_retry_pending(self.game_state)            # retry failed automation
        
        if not self.game_exception:     # skip on game error
            self.automation.decide_lobby_action()
            
        
    def _process_msg(self, msg:mitm.WSMessage):
        """ process websocket message from mitm server"""
        
        if msg.type == mitm.WsType.START:
            LOGGER.debug("Websocket Flow started: %s", msg.flow_id)
            
        elif msg.type == mitm.WsType.END:
            LOGGER.debug("Websocket Flow ended: %s", msg.flow_id)
            if msg.flow_id == self.game_flow_id:
                LOGGER.info("Game flow ended. processing end game")
                self._process_end_game()
                self.game_flow_id = None
            if msg.flow_id == self.lobby_flow_id:
                # lobby flow ended
                LOGGER.info("Lobby flow ended.")
                self.lobby_flow_id = None
                self.automation.on_exit_lobby()
                
        elif msg.type == mitm.WsType.MESSAGE:
            # process ws message
            try:
                liqimsg = self.liqi_parser.parse(msg.content)
            except Exception as e:
                LOGGER.warning("Failed to parse liqi msg: %s\nError: %s", msg.content, e)
                return
            liqi_id = liqimsg.get("id")
            liqi_type = liqimsg.get('type')
            liqi_method = liqimsg.get('method')
            # liqi_data = liqimsg['data']
            # liqi_datalen = len(liqimsg['data'])
            
            if liqi_method in METHODS_TO_IGNORE:
                ...
            
            elif (liqi_type, liqi_method) == (liqi.MsgType.RES, liqi.LiqiMethod.oauth2Login):
                # lobby login msg
                if self.lobby_flow_id is None:  # record first time in lobby
                    LOGGER.info("Lobby oauth2Login msg: %s", liqimsg)
                    LOGGER.info("Lobby login done. lobby flow ID = %s", msg.flow_id)                   
                    self.lobby_flow_id = msg.flow_id
                    self.automation.on_lobby_login(liqimsg)                    
                else:
                    LOGGER.warning("Lobby flow exists %s, ignoring new lobby flow %s", self.lobby_flow_id, msg.flow_id)
            
            elif (liqi_type, liqi_method) == (liqi.MsgType.REQ, liqi.LiqiMethod.authGame):
                # Game Start request msg: found game flow, initialize game state
                if self.game_flow_id is None:
                    LOGGER.info("authGame msg: %s", liqimsg)
                    LOGGER.info("Game Started. Game Flow ID=%s", msg.flow_id)
                    self.game_flow_id = msg.flow_id
                    self.game_state = GameState(self.bot)    # create game state with bot
                    self.game_state.input(liqimsg)      # authGame -> mjai:start_game, no reaction
                    self.game_exception = None
                    self.automation.on_enter_game()
                else:
                    LOGGER.warning("Game flow %s already started. ignoring new game flow %s", self.game_flow_id, msg.flow_id)
                
            elif msg.flow_id == self.game_flow_id:
                # Game Flow Message (in-Game message)
                # Feed msg to game_state for processing with AI bot
                LOGGER.debug('Game msg: %s', str(liqimsg))
                reaction = self.game_state.input(liqimsg)
                if reaction:
                    self._do_automation(reaction)
                else:
                    self._process_idle_automation(liqimsg)
                # if self.game_state.is_game_ended:
                #     self._process_end_game()
            
            elif msg.flow_id == self.lobby_flow_id:
                LOGGER.debug(
                    'Lobby msg(suppressed): id=%s, type=%s, method=%s, len=%d',
                    liqi_id, liqi_type, liqi_method, len(str(liqimsg)))

            else:
                LOGGER.debug('Other msg (ignored): %s', liqimsg)
                
    def _process_idle_automation(self, liqimsg:dict):
        """ do some idle action based on liqi msg"""
        liqi_method = liqimsg['method']
        if liqi_method == liqi.LiqiMethod.NotifyGameBroadcast:  # reply to emoji
        # {'id': -1, 'type': <MsgType.Notify: 1>, 'method': '.lq.NotifyGameBroadcast',
        # 'data': {'seat': 2, 'content': '{"emo":7}'}}
            if liqimsg["data"]["seat"] != self.game_state.seat: # not self
                self.automation.automate_send_emoji()
        else:           # move mouse around randomly
            self.automation.automate_idle_mouse_move(0.05)
        
    def _process_end_game(self):
        # End game processes
        # self.game_flow_id = None
        self.game_state = None
        if self.browser:    # fix for corner case
            self.browser.overlay_clear_guidance()
        self.game_exception = None
        self.automation.on_end_game()
            
    
    def _update_overlay_conditions_met(self) -> bool:
        if not self.st.enable_overlay:
            return False
        if self.browser is None:
            return False
        if self.browser.is_page_normal() is False:
            return False
        return True
    
        
    def _update_overlay_guide(self):
        # Update overlay guide given pending reaction
        reaction = self.get_pending_reaction()
        if reaction:
            guide, options = mjai_reaction_2_guide(reaction, 3, self.st.lan())
            self.browser.overlay_update_guidance(guide, self.st.lan().OPTIONS_TITLE, options)
        else:
            self.browser.overlay_clear_guidance()
            
        
    def _update_overlay_botleft(self):
        # update overlay bottom left text        
        # maj copilot
        text = '😸' + self.st.lan().APP_TITLE

        # Model
        model_text = '🤖'
        if self.is_bot_created():
            model_text += self.st.lan().MODEL + ": " + self.st.model_type
        else:
            model_text += self.st.lan().MODEL_NOT_LOADED
        
        # autoplay
        if self.st.enable_automation:
            autoplay_text = '✅' + self.st.lan().AUTOPLAY + ': ' + self.st.lan().ON
        else:
            autoplay_text = '⬛' + self.st.lan().AUTOPLAY + ': ' + self.st.lan().OFF
        if self.automation.is_running_execution():
            autoplay_text += "🖱️⏳"

        # line 4
        if self.main_thread_exception:
            line = '❌' + self.st.lan().MAIN_THREAD_ERROR
        elif self.game_exception:
            line = '❌' + self.st.lan().GAME_ERROR
        elif self.is_browser_zoom_off():
            line = '❌' + self.st.lan().CHECK_ZOOM
        elif self.is_game_syncing():
            line = '⏳'+ self.st.lan().SYNCING
        elif self.is_bot_calculating():
            line = '⏳'+ self.st.lan().CALCULATING
        elif self.is_in_game():
            line = '▶️' + self.st.lan().GAME_RUNNING
        else:
            line = '🟢' + self.st.lan().READY_FOR_GAME            
        
        text = '\n'.join((text, model_text, autoplay_text, line))       
        self.browser.overlay_update_botleft(text)

    
    def _do_automation(self, reaction:dict):
        # auto play given mjai reaction        
        if not reaction:    # no reaction given
            return False
        
        try:
            self.automation.automate_action(reaction, self.game_state)
        except Exception as e:
            LOGGER.error("Failed to automate action for %s: %s", reaction['type'], e, exc_info=True)


def mjai_reaction_2_guide(reaction:dict, max_options:int=3, lan_str:LanStr=LanStr()) -> tuple[str, list]:
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
    
    def get_tile_str(mjai_tile:str):    # unicode + language specific name
        return MJAI_TILE_2_UNICODE[mjai_tile] + lan_str.mjai2str(mjai_tile)
    pai = reaction.get('pai', None)
    if pai:
        tile_str =  get_tile_str(pai)
    
    if re_type == MjaiType.DAHAI:
        action_str = f"{lan_str.DISCARD}{tile_str}"
    elif re_type == MjaiType.NONE:
        action_str = ActionUnicode.PASS + lan_str.PASS
    elif re_type == MjaiType.PON:
        action_str = f"{ActionUnicode.PON}{lan_str.PON}{tile_str}"
    elif re_type == MjaiType.CHI:
        comsumed = reaction['consumed']
        comsumed_strs = [f"{get_tile_str(x)}" for x in comsumed]
        action_str = f"{ActionUnicode.CHI}{lan_str.CHI}{tile_str}({''.join(comsumed_strs)})"         
    elif re_type == MjaiType.KAKAN:
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.KAKAN})"
    elif re_type == MjaiType.DAIMINKAN:
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.DAIMINKAN})"
    elif re_type == MjaiType.ANKAN:
        tile_str = get_tile_str(reaction['consumed'][1])
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.ANKAN})"
    elif re_type == MjaiType.REACH: # attach reach dahai options
        reach_dahai_reaction = reaction['reach_dahai']
        dahai_action_str, _dahai_options = mjai_reaction_2_guide(reach_dahai_reaction, 0, lan_str)
        action_str = f"{ActionUnicode.REACH}{lan_str.RIICHI}," + dahai_action_str
    elif re_type == MjaiType.HORA:
        if reaction['actor'] == reaction['target']:
            action_str = f"{ActionUnicode.AGARI}{lan_str.AGARI}({lan_str.TSUMO})"
        else:
            action_str = f"{ActionUnicode.AGARI}{lan_str.AGARI}({lan_str.RON})"
    elif re_type == MjaiType.RYUKYOKU:
        action_str = f"{ActionUnicode.RYUKYOKU}{lan_str.RYUKYOKU}"
    elif re_type == MjaiType.NUKIDORA:
        action_str = f"{lan_str.NUKIDORA}{MJAI_TILE_2_UNICODE['N']}"
    else:
        action_str = lan_str.mjai2str(re_type)
    
    options = []
    if max_options > 0 and 'meta_options' in reaction:
        # process options. display top options with their weights
        meta_options = reaction['meta_options'][:max_options]
        if meta_options:
            for (code, q) in meta_options:      # code is in MJAI_MASK_LIST                
                if code in MJAI_TILES_34 or code in MJAI_AKA_DORAS:
                    # if it is a tile
                    name_str = get_tile_str(code)
                elif code == MjaiType.NUKIDORA:
                    name_str = lan_str.mjai2str(code) + MJAI_TILE_2_UNICODE['N']
                else:
                    name_str = lan_str.mjai2str(code)                
                options.append((name_str, q))
        
    return (action_str, options)
