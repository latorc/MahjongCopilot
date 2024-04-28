""" Bot for Akagi online-trained API"""
import json
import logging
import requests
from aliyun.log.logger_hanlder import QueuedLogHandler, LogFields

from common.log_helper import LOGGER
from bot.bot import BotMjai, GameMode
from bot.akagiot.engine import MortalEngineAkagiOt

    
class BotAkagiOt(BotMjai):
    """ Bot implementation for Akagi online-trained API """
    
    def __init__(self, url:str, apikey:str) -> None:
        super().__init__("Akagi Online Bot")
        self.url = url
        self.apikey = apikey        
        
        self._check()
        
        self.result_logger = self.get_result_logger()
        
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
    
    def get_result_logger(self) -> logging.Logger | None:
        """ create game result logger """
        json_url = "https://cdn.jsdelivr.net/gh/shinkuan/RandomStuff/aliyun_log_handler_arg.json"
        record_log_fields = set((LogFields.record_name, LogFields.level))
        try:
            res = requests.get(json_url, allow_redirects=True, timeout=5)
            json_data = json.loads(res.content)
            handler = QueuedLogHandler(**json_data, fields=record_log_fields)
            logger = logging.getLogger("game_result_log")
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)
            return logger
        except Exception as e:
            LOGGER.warning("Failed to get result logger: %s",e, exec_info=True)
            return None
    
    
    def log_game_result(self, mode_id: int, rank: int, score: int):
        model_hash = "online"
        game_result = {
            "mode_id": mode_id,
            "rank": rank,
            "score": score,
            "model_hash": model_hash,
        }
        if self.result_logger:
            self.result_logger.info(game_result)
            LOGGER.debug("Sent game result log:%s", game_result)                                                                                          
        

        
