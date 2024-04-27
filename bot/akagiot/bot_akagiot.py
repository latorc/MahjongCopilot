""" Bot for Akagi online-trained API"""
import requests
from common.log_helper import LOGGER
from bot.bot import BotMjai, GameMode
from bot.akagiot.engine import MortalEngineAkagiOt
    
    
class BotAkagiOt(BotMjai):
    """ Bot implementation for Akagi online-trained API """
    
    def __init__(self, url:str, apikey:str) -> None:
        super().__init__("Akagi OT API Bot")
        self.url = url
        self.apikey = apikey        
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
   

    def _get_engine(self, mode: GameMode):
        engine = MortalEngineAkagiOt(self.apikey, self.url, mode)
        return engine
