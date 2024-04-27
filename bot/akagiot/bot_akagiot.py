""" Bot for Akagi online-trained API"""
import requests
from common.log_helper import LOGGER
from common.utils import BotNotSupportingMode
from bot.bot import Bot, GameMode
try:
    import libriichi
except ImportError:
    import riichi as libriichi
    
    
class BotAkagiOt(Bot):
    """ Bot implementation for Akagi online-trained API """
    
    def __init__(self, url:str, apikey:str) -> None:
        super().__init__("Akagi OT API Bot")
        self.url = url
        self.apikey = apikey
        self.engines:dict[GameMode, any] = {}
        self._check()
        
    def _check(self):
        # check authorization
        headers = {
            'Authorization': self.apikey,
        }
        r = requests.post(f"{self.url}/check", headers=headers, timeout=5)
        r_json = r.json()
        if r_json["result"] == "success":
            LOGGER.info("Akagi OT API check success")
        
    @property
    def supported_modes(self) -> list[GameMode]:
        """ return suported game modes"""
        return [GameMode.MJ4P, GameMode.MJ3P]
    
    
    @property
    def info_str(self) -> str:
        """ return description info"""
        return self.name
    
       
    def _init_bot_impl(self, mode:GameMode=GameMode.MJ4P):
        """ Initialize the bot before the game starts."""
        engine = self.engines.get(mode, None)
        if not engine:
            raise BotNotSupportingMode(mode)
        if mode == GameMode.MJ4P:
            self.mjai_bot = libriichi.mjai.Bot(engine, self.seat)
        elif mode == GameMode.MJ3P:
            import libriichi3p
            self.mjai_bot = libriichi3p.mjai.Bot(engine, self.seat)
        else:
            raise BotNotSupportingMode(mode)      

    
    def react(self, input_msg:dict) -> dict | None:
        """ input mjai msg and get bot output if any, or None if not"""


    def react_batch(self, input_list:list[dict]) -> dict | None:
        """ input list of mjai msg and get the last output, if any"""
        