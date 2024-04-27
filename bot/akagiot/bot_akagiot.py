""" Bot for Akagi online-trained API"""
import requests
from bot.bot import Bot, GameMode

class BotAkagiOt(Bot):
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
            return True
        
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
        
        

    
    def react(self, input_msg:dict) -> dict | None:
        """ input mjai msg and get bot output if any, or None if not"""


    def react_batch(self, input_list:list[dict]) -> dict | None:
        """ input list of mjai msg and get the last output, if any"""
        