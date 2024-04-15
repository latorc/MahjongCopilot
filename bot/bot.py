""" Bot represents a mjai protocol bot
implement wrappers for supportting different bot types
"""
from enum import Enum
from abc import ABC, abstractmethod

import common.mj_helper as mj_helper
from common.utils import GameMode

class BotType(Enum):
    """ Model type for bot"""
    LOCAL = "Local"
    MJAPI = "MJAPI"

def reaction_convert_meta(reaction:dict, is_3p:bool=False):
    """ add meta_options to reaction """
    if 'meta' in reaction:
        meta = reaction['meta']
        reaction['meta_options'] = mj_helper.meta_to_options(meta, is_3p)

class Bot(ABC):
    """ Bot Interface class
    bot follows mjai protocol
    ref: https://mjai.app/docs/highlevel-api
    Note: Reach msg has additional 'reach_dahai' key attached,
    which is a 'dahai' msg, representing the subsequent dahai action after reach
    """

    def __init__(self, bot_type:BotType, name:str="Bot") -> None:
        self.type = bot_type
        self.name = name
        self._initialized:bool = False
        self.seat:int = None
    
    @property
    def supported_modes(self) -> list[GameMode]:
        """ return suported game modes"""
        return [GameMode.MJ4P]

    def init_bot(self, seat:int, mode:GameMode=GameMode.MJ4P):
        """ Initialize the bot before the game starts. Bot must be initialized before a new game
        params:
            seat(int): Player seat index
            mode(GameMode): Game mode"""
         
        self.seat = seat
        self._init_bot_impl(mode)
        self._initialized = True

    @property
    def initialized(self) -> bool:
        """ return True if bot is initialized"""
        return self._initialized
       
    @abstractmethod
    def _init_bot_impl(self, mode:GameMode=GameMode.MJ4P):
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

