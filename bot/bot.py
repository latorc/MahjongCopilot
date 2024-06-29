""" Bot represents a mjai protocol bot
implement wrappers for supportting different bot types
"""
import json
import time
from abc import ABC, abstractmethod

from common.log_helper import LOGGER
from common.mj_helper import meta_to_options, MjaiType
from common.utils import GameMode, BotNotSupportingMode


def reaction_convert_meta(reaction: dict, is_3p: bool = False):
    """ add meta_options to reaction """
    if 'meta' in reaction:
        meta = reaction['meta']
        reaction['meta_options'] = meta_to_options(meta, is_3p)


class Bot(ABC):
    """ Bot Interface class
    bot follows mjai protocol
    ref: https://mjai.app/docs/highlevel-api
    """

    def __init__(self, name: str = "Bot") -> None:
        self.name = name
        self._initialized: bool = False
        self.seat: int = None
        self.mode = None
        self.ignore_next_turn_self_reach: bool = False
        self.reach_dahai:dict = None

    @property
    def supported_modes(self) -> list[GameMode]:
        """ return suported game modes"""
        return [GameMode.MJ4P]

    @property
    def info_str(self) -> str:
        """ return description info"""
        return self.name

    def init_bot(self, seat: int, mode: GameMode = GameMode.MJ4P):
        """ Initialize the bot before the game starts. Bot must be initialized before a new game
        params:
            seat(int): Player seat index
            mode(GameMode): Game mode, defaults to normal 4p mahjong"""
        if mode not in self.supported_modes:
            raise BotNotSupportingMode(mode)
        self.seat = seat
        self.mode = mode
        self._init_bot_impl(mode)
        self._initialized = True

    @property
    def initialized(self) -> bool:
        """ return True if bot is initialized"""
        return self._initialized

    @abstractmethod
    def _init_bot_impl(self, mode: GameMode = GameMode.MJ4P):
        """ Initialize the bot before the game starts."""

    @abstractmethod
    def react(self, input_msg: dict) -> dict | None:
        """ input mjai msg and get bot output if any, or None if not"""

    def react_batch(self, input_list: list[dict]) -> dict | None:
        """ input list of mjai msg and get the last output, if any"""

        # default implementation is to iterate and feed to bot
        if len(input_list) == 0:
            return None
        for msg in input_list[:-1]:
            msg['can_act'] = False
            self.react(msg)
        last_reaction = self.react(input_list[-1])
        return last_reaction

    def log_game_result(self, mode_id: int, rank: int, score: int):
        """ log game results"""
        return

    def get_reach_dahai(self) -> dict:
        """
        get the reach_dahai message
        Only call this method when it is reachable.
        """
        if self.reach_dahai is not None:
            return self.reach_dahai
        else:
            self.generate_reach_dahai()
            return self.reach_dahai


    def generate_reach_dahai(self):
        reach_msg = {'type': MjaiType.REACH, 'actor': self.seat}
        reach_dahai_from_originalbot = self.react(reach_msg)
        self.reach_dahai = reach_dahai_from_originalbot
        LOGGER.debug(f"Generated and saved reach_dahai: {self.reach_dahai}")
        self.ignore_next_turn_self_reach = True


class BotMjai(Bot):
    """ base class for libriichi.mjai Bots"""

    def __init__(self, name: str) -> None:
        super().__init__(name)

        self.mjai_bot = None

    @property
    def info_str(self) -> str:
        return f"{self.name}: [{','.join([m.value for m in self.supported_modes])}]"

    def _get_engine(self, mode: GameMode):
        # return MortalEngine object
        raise NotImplementedError("Subclass must implement this method")

    def _init_bot_impl(self, mode: GameMode = GameMode.MJ4P):
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

    def react(self, input_msg: dict) -> dict:
        msg_type = input_msg['type']
        if self.mjai_bot is None:
            return None
        if self.ignore_next_turn_self_reach == True:
            if msg_type == MjaiType.REACH and input_msg['actor'] == self.seat:
                LOGGER.debug("Ignoring Reach msg, already fed reach msg to the bot.")
                self.ignore_next_turn_self_reach = False
                return None


        str_input = json.dumps(input_msg)

        react_str = self.mjai_bot.react(str_input)
        if react_str is None:
            return None
        reaction = json.loads(react_str)
        return reaction
