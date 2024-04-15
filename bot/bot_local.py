""" Bot Mortal Local """

from pathlib import Path
import threading
import json
from mjai.engine import get_engine
from mjai.engine3p import get_engine as get_engine_3p
from common.utils import ModelFileException
from common.mj_helper import MJAI_TYPE
from common.log_helper import LOGGER
try:
    import libriichi
except: # pylint: disable=bare-except
    import riichi as libriichi
import libriichi3p

from .bot import Bot, BotType, GameMode


class BotMortalLocal(Bot):
    """ Mortal model based mjai bot"""
    def __init__(self, model_files:dict[GameMode, str]) -> None:
        """ params:
        model_files(dicty): model files for different modes {mode, file_path}
        """
        super().__init__(BotType.LOCAL, "Local Mortal Bot")   
        self._supported_modes: list[GameMode] = list(model_files.keys())     
        self.model_files = model_files
        for k,v in model_files.items():
            if not Path(v).exists() or not Path(v).is_file():
                LOGGER.warning("Cannot find model file for mode %s:%s", k,v)
                self._supported_modes.remove(k)
        if not self._supported_modes:
            raise ModelFileException("No valid model files found")
        
        self.mjai_bot = None
        self.ignore_next_turn_self_reach:bool = False
        self.str_input_history:list = []
        # thread lock for mjai.bot access
        # "mutable borrow" issue when running multiple methods at the same time        
        self.lock = threading.Lock()
    
    @property 
    def supported_modes(self) -> list[GameMode]:
        return self._supported_modes
    
    def _init_bot_impl(self, mode:GameMode=GameMode.MJ4P):
        if mode == GameMode.MJ4P:
            engine = get_engine(self.model_files[mode])
            self.mjai_bot = libriichi.mjai.Bot(engine, self.seat)
        elif mode == GameMode.MJ3P:
            engine = get_engine_3p(self.model_files[mode])
            self.mjai_bot = libriichi3p.mjai.Bot(engine, self.seat)
        else:
            raise NotImplementedError(f"Mode {mode} not supported")
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
                reaction['reach_dahai'] = reach_dahai
                self.ignore_next_turn_self_reach = True     # ignore very next reach msg
            return reaction
