""" Bot represents a mjai protocol bot
implement wrappers for supportting different bot types
"""

from abc import ABC, abstractmethod

import common.mj_helper as mj_helper
from common.utils import BotType

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

    def __init__(self, bot_type:BotType, name:str="Bot") -> None:
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
    def react(self, input_msg:dict) -> dict | None:
        """ input mjai msg and get bot output if any, or None if not"""

    def react_batch(self, input_list:list[dict]) -> dict | None:
        """ input list of mjai msg and get the last output, if any"""
        
        # default implementation is to iterate and feed to bot
        if len(input_list) == 0:
            return None
        for msg in input_list[:-1]:
            msg['can_act'] = False
            self.react(msg)
        last_reaction = self.react(input_list[-1])
        return last_reaction


        
        
        
