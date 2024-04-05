""" Bot represents a mjai protocol bot
implement wrappers for supportting different bot types
"""
from abc import ABC, abstractmethod
from pathlib import Path
import threading
import json
import libriichi
import mjai.engine
import common.mj_helper as mj_helper
from common.mj_helper import MJAI_TYPE
import common.utils as utils
from common.log_helper import LOGGER
from common.settings import Settings
from . import mjapi
from common.utils import MODEL_FOLDER, BOT_TYPE

# mjai Bot class from rust library
# pylint: disable=no-member
MjaiBot = libriichi.mjai.Bot


def get_bot(settings:Settings) -> 'Bot':
    """ create the Bot instance based on settings"""
    if settings.model_type == BOT_TYPE.LOCAL.value:
        bot = LocalMortalBot(utils.sub_file(MODEL_FOLDER, settings.model_file))                
    elif settings.model_type == BOT_TYPE.MJAPI.value:
        bot = MjapiBot(settings)
    else:
        raise ValueError(f"Unknown model type: {settings.model_type}")

    return bot

def reaction_convert_meta(reaction:dict):
    """ add meta_options to reaction """
    if 'meta' in reaction:
        meta = reaction['meta']
        reaction['meta_options'] = mj_helper.meta_to_options(meta)

class Bot(ABC):
    """ Bot Interface class
    bot follows mjai protocol
    ref: https://mjai.app/docs/highlevel-api
    Note: reach msg is implemented differently. 
    Reach msg has reach_dahai attached, which is a 'dahai' msg, indicating the dahai action after reach
    msgs have 'meta_options', which is a translation of 'meta' into list of (mjai tile, weight)"""

    def __init__(self, bot_type:BOT_TYPE, name:str="Bot") -> None:
        self.type = bot_type
        self.name = name
        self._initialized:bool = False
        self.seat:int = None

    def init_bot(self, seat:int):
        """ Initialize the bot before the game starts. Bot must be initialized before a new game""" 
        self.seat = seat
        self._init_bot_impl()
        self._initialized = True

    @property
    def initialized(self) -> bool:
        """ return True if bot is initialized"""
        return self._initialized
       
    @abstractmethod
    def _init_bot_impl(self):
        """ Initialize the bot before the game starts."""

    @abstractmethod
    def react(self, input_msg:dict) -> dict:
        """ input mjai msg and get bot output if any, or None if not"""

    def react_batch(self, input_list:list[dict]) -> dict:
        """ input list of mjai msg and get the last output, if any"""
        last_reaction:dict = None
        for msg in input_list:
            reaction = self.react(msg)
            if reaction:
                last_reaction = reaction
        return last_reaction

    # @abstractmethod
    # def get_hand_info(self) -> tuple[list[str], str]:
    #     """ return mjai format tehai (at most 13 tiles) + tsumohai if any (or None if no tsumohai)"""
    #     pass


class LocalMortalBot(Bot):
    """ Mortal model based mjai bot"""
    def __init__(self, model_file:str) -> None:
        """ params:
        model_file: path to the mortal model file
        """
        super().__init__(BOT_TYPE.LOCAL, "Local Mortal Bot - " + model_file)
        self.model_file = model_file
        if not Path(self.model_file).exists():
            raise utils.ModelFileException(f"Cannot find model file:{self.model_file}")
        
        self.mjai_bot:MjaiBot = None
        
        self.ignore_next_turn_self_reach:bool = False
        self.str_input_history:list = []
        # thread lock for mjai.bot access
        # "mutable borrow" issue when running multiple methods at the same time        
        self.lock = threading.Lock()        
    
    def _init_bot_impl(self):
        engine = mjai.engine.get_engine(self.model_file)
        self.mjai_bot = MjaiBot(engine, self.seat)
        self.str_input_history.clear()
        
    def react(self, input_msg:dict) -> dict:
        
        if self.ignore_next_turn_self_reach:    # ignore repetitive self reach. only for the very next msg
            if input_msg['type'] == MJAI_TYPE.REACH and input_msg['actor'] == self.seat:
                LOGGER.debug("Ignoring repetitive self reach msg, reach msg already sent to AI last turn")
                return None
            self.ignore_next_turn_self_reach = False
            
        str_input = json.dumps(input_msg)
        self.str_input_history.append(str_input) 
        with self.lock:
            react_str = self.mjai_bot.react(str_input)
            if react_str is None:
                return None
            reaction = json.loads(react_str)
            reaction_convert_meta(reaction)
            # Special treatment for self reach output msg
            # mjai only outputs dahai msg after the reach msg
            if reaction['type'] == MJAI_TYPE.REACH and reaction['actor'] == self.seat:  # Self reach
                # get the subsequent dahai message,
                # appeding it to the reach reaction msg as 'reach_dahai' key
                LOGGER.debug("Send reach msg to get reach_dahai. Cannot go back to unreach!")
                # TODO make a clone of mjai_bot so reach can be tested to get dahai without affecting the game

                reach_msg = {'type': MJAI_TYPE.REACH, 'actor': self.seat}
                reach_dahai_str = self.mjai_bot.react(json.dumps(reach_msg))
                reach_dahai = json.loads(reach_dahai_str)
                reaction_convert_meta(reach_dahai)
                reaction['reach_dahai'] = reach_dahai
                self.ignore_next_turn_self_reach = True     # ignore very next reach msg
            return reaction
    
    # def get_hand_info(self) -> tuple[list[str], str]:
    #     with self.lock:
    #         state = self.mjai_bot.state
    #         tehai = state.tehai # with tsumohai, no aka marked
    #         aka_doras = state.akas_in_hand
    #         tsumohai = state.last_self_tsumo()
    #         my_tehais, my_tsumohai = mj_helper.decode_mjai_tehai(tehai, aka_doras, tsumohai)
    #         my_tehais = [t for t in my_tehais if t != '?']
    #         return my_tehais, my_tsumohai
        
        
        
class MjapiBot(Bot):
    """ MJAPI based mjai bot"""
    def __init__(self, setting:Settings) -> None:
        super().__init__(BOT_TYPE.MJAPI, "MJAPI Bot - " + setting.mjapi_url)
        self.settings = setting
        self.mjapi = mjapi.MJAPI_Client(self.settings.mjapi_url)
        self._login_or_reg()
        self.id = -1
        self.ignore_next_turn_self_reach:bool = False
        
    def _login_or_reg(self):
        res = self.mjapi.login(self.settings.mjapi_user, self.settings.mjapi_secret)
        if 'error' in res:
            LOGGER.warning("Error in MJAPI login: %s", res['error'])
            # try register
            if not self.settings.mjapi_user:
                self.settings.mjapi_user = utils.random_str(6)
                LOGGER.info("Set random mjapi username:%s", self.settings.mjapi_user)
            res_reg = self.mjapi.register(self.settings.mjapi_user)
            if 'secret' in res_reg:
                self.settings.mjapi_secret = res_reg['secret']
                self.settings.save_json()
                LOGGER.info("Registered new user [%s] with MJAPI. User name and secret saved to settings.", self.settings.mjapi_user)
                res = self.mjapi.login(self.settings.mjapi_user, self.settings.mjapi_secret)
            elif 'error' in res_reg:
                LOGGER.error("Error in MJAPI register: %s", res_reg['error'])
                raise RuntimeError(f"Cannot log into MJAPI: {res_reg['error']}")
            else:
                msg = f"Unknown response registering: {res_reg}"
                LOGGER.error(msg)
                raise RuntimeError(msg)

        token = res['id']
        self.mjapi.set_bearer_token(token)
        res = self.mjapi.list_models()
        model_list = res['models']
        if model_list:
            self.settings.mjapi_models = model_list
        if self.settings.mjapi_model_select in model_list:
            # OK
            pass
        else:
            LOGGER.debug(
                "mjapi selected model %s N/A, using last one from available list %s",
                self.settings.mjapi_model_select, model_list[-1])
            self.settings.mjapi_model_select = model_list[-1]
        self.model_name = self.settings.mjapi_model_select
        LOGGER.info("Login to MJAPI successful with user: %s, model_name=%s", self.settings.mjapi_user, self.model_name)

    def __del__(self):
        self.mjapi.stop_bot()
        self.mjapi.logout()

    def _init_bot_impl(self):
        res = self.mjapi.start_bot(self.seat, 256, self.model_name)
        self.id = -1
        
    def react(self, input_msg:dict) -> dict:
        # input_msg['can_act'] = True
        if self.ignore_next_turn_self_reach:
            if input_msg['type'] == MJAI_TYPE.REACH and input_msg['actor'] == self.seat:
                LOGGER.debug("Ignoring repetitive self reach msg, reach msg already sent to AI last turn")
                return None
            self.ignore_next_turn_self_reach = False
        
        self.id += 1
        reaction = self.mjapi.act(self.id, input_msg)
        if reaction:
            reaction_convert_meta(reaction)
        else:
            return None
        
        # process self reach
        if reaction['type'] == MJAI_TYPE.REACH and reaction['actor'] == self.seat:
            LOGGER.debug("Send reach msg to get reach_dahai. Cannot go back to unreach!") 
            reach_msg = {'type': MJAI_TYPE.REACH, 'actor': self.seat}
            reach_dahai = self.react(reach_msg)
            reaction_convert_meta(reach_dahai)
            reaction['reach_dahai'] = reach_dahai
            self.ignore_next_turn_self_reach = True

        return reaction
    
    def react_batch(self, input_list: list[dict]) -> dict:
        batch_data = []
        for msg in input_list:
            self.id += 1
            action = {'seq': self.id, 'data': msg}
            batch_data.append(action)
        res = self.mjapi.batch(batch_data)
        if res:
            reaction = res['act']
            reaction_convert_meta(reaction)
        else:
            reaction = None
        return reaction
    
    def get_hand_info(self) -> tuple[list[str], str]:
        return [], None