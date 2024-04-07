""" Bot Mortal Local """

from pathlib import Path
import threading
import json
import libriichi
from mjai.engine import get_engine
from common.utils import ModelFileException
from common.mj_helper import MJAI_TYPE
from common.log_helper import LOGGER
from .bot import Bot, BOT_TYPE, reaction_convert_meta

# mjai Bot class from rust library
# pylint: disable=no-member
MjaiBot = libriichi.mjai.Bot

class BotMortalLocal(Bot):
    """ Mortal model based mjai bot"""
    def __init__(self, model_file:str) -> None:
        """ params:
        model_file: path to the mortal model file
        """
        super().__init__(BOT_TYPE.LOCAL, "Local Mortal Bot - " + model_file)
        self.model_file = model_file
        if not Path(self.model_file).exists():
            raise ModelFileException(f"Cannot find model file:{self.model_file}")
        
        self.mjai_bot:MjaiBot = None
        
        self.ignore_next_turn_self_reach:bool = False
        self.str_input_history:list = []
        # thread lock for mjai.bot access
        # "mutable borrow" issue when running multiple methods at the same time        
        self.lock = threading.Lock()        
    
    def _init_bot_impl(self):
        engine = get_engine(self.model_file)
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