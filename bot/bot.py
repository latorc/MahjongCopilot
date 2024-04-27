""" Bot represents a mjai protocol bot
implement wrappers for supportting different bot types
"""
import json
from abc import ABC, abstractmethod

from common.log_helper import LOGGER
from common.mj_helper import meta_to_options, MjaiType
from common.utils import GameMode, BotNotSupportingMode


def reaction_convert_meta(reaction:dict, is_3p:bool=False):
    """ add meta_options to reaction """
    if 'meta' in reaction:
        meta = reaction['meta']
        reaction['meta_options'] = meta_to_options(meta, is_3p)

class Bot(ABC):
    """ Bot Interface class
    bot follows mjai protocol
    ref: https://mjai.app/docs/highlevel-api
    Note: Reach msg has additional 'reach_dahai' key attached,
    which is a 'dahai' msg, representing the subsequent dahai action after reach
    """

    def __init__(self, name:str="Bot") -> None:
        self.name = name
        self._initialized:bool = False
        self.seat:int = None
    
    @property
    def supported_modes(self) -> list[GameMode]:
        """ return suported game modes"""
        return [GameMode.MJ4P]
    
    @property
    def info_str(self) -> str:
        """ return description info"""
        return self.name

    def init_bot(self, seat:int, mode:GameMode=GameMode.MJ4P):
        """ Initialize the bot before the game starts. Bot must be initialized before a new game
        params:
            seat(int): Player seat index
            mode(GameMode): Game mode, defaults to normal 4p mahjong"""
        if mode not in self.supported_modes:
            raise BotNotSupportingMode(mode)
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


class BotMjai(Bot):
    """ base class for libriichi.mjai Bots"""
    def __init__(self, name:str) -> None:
        super().__init__(name)
        
        self.mjai_bot = None
        self.ignore_next_turn_self_reach:bool = False
        
    
    @property
    def info_str(self) -> str:
        return f"{self.name}: [{','.join([m.value for m in self.supported_modes])}]"
    
    
    def _get_engine(self, mode:GameMode):
        # return MortalEngine object
        raise NotImplementedError("Subclass must implement this method")
    
    
    def _init_bot_impl(self, mode:GameMode=GameMode.MJ4P):
        engine = self._get_engine(mode)
        if not engine:
            raise BotNotSupportingMode(mode)
        if mode == GameMode.MJ4P:
            try:
                import libriichi
            except:
                import riichi as libriichi
            self.mjai_bot = libriichi.mjai.Bot(engine, self.seat)
        elif mode == GameMode.MJ3P:
            import libriichi3p
            self.mjai_bot = libriichi3p.mjai.Bot(engine, self.seat)
        else:
            raise BotNotSupportingMode(mode)          
            
        
    def react(self, input_msg:dict) -> dict:
        if self.mjai_bot is None:
            return None        
        if self.ignore_next_turn_self_reach:    # ignore repetitive self reach. only for the very next msg
            if input_msg['type'] == MjaiType.REACH and input_msg['actor'] == self.seat:
                LOGGER.debug("Ignoring repetitive self reach msg, reach msg already sent to AI last turn")
                return None
            self.ignore_next_turn_self_reach = False
            
        str_input = json.dumps(input_msg)

        react_str = self.mjai_bot.react(str_input)
        if react_str is None:
            return None
        reaction = json.loads(react_str)
        # Special treatment for self reach output msg
        # mjai only outputs dahai msg after the reach msg
        if reaction['type'] == MjaiType.REACH and reaction['actor'] == self.seat:  # Self reach
            # get the subsequent dahai message,
            # appeding it to the reach reaction msg as 'reach_dahai' key
            LOGGER.debug("Send reach msg to get reach_dahai. Cannot go back to unreach!")
            # TODO make a clone of mjai_bot so reach can be tested to get dahai without affecting the game

            reach_msg = {'type': MjaiType.REACH, 'actor': self.seat}
            reach_dahai_str = self.mjai_bot.react(json.dumps(reach_msg))
            reach_dahai = json.loads(reach_dahai_str)
            reaction['reach_dahai'] = reach_dahai
            self.ignore_next_turn_self_reach = True     # ignore very next reach msg
        return reaction
