""" Bot Mortal Local """

from pathlib import Path
import threading

from common.utils import LocalModelException
from common.log_helper import LOGGER
from bot.local.engine import get_engine
from bot.bot import BotMjai, GameMode


class BotMortalLocal(BotMjai):
    """ Mortal model based mjai bot"""
    def __init__(self, model_files:dict[GameMode, str]) -> None:
        """ params:
        model_files(dicty): model files for different modes {mode, file_path}
        """
        super().__init__("Local Mortal Bot")   
        self._supported_modes: list[GameMode] = []  
        self.model_files = model_files
        self._engines:dict[GameMode, any] = {}
        for k,v in model_files.items():
            if not Path(v).exists() or not Path(v).is_file():
                # test file exists
                LOGGER.warning("Cannot find model file for mode %s:%s", k,v)
            else:
                if k == GameMode.MJ4P:
                    try:
                        self._engines[k] = get_engine(self.model_files[k])
                    except Exception as e:
                        LOGGER.warning("Cannot create engine for mode %s: %s", k, e, exc_info=True)
                elif k == GameMode.MJ3P:
                    # test import libraries for 3p
                    try:
                        import libriichi3p
                        from bot.local.engine3p import get_engine as get_engine_3p
                        self._engines[k] = get_engine_3p(self.model_files[k])
                    except Exception as e: # pylint: disable=broad-except
                        LOGGER.warning("Cannot create engine for mode %s: %s", k, e, exc_info=True)
        self._supported_modes = list(self._engines.keys())
        if not self._supported_modes:
            raise LocalModelException("No valid model files found")
        
        self.mjai_bot = None
        self.ignore_next_turn_self_reach:bool = False
        # thread lock for mjai.bot access
        # "mutable borrow" issue when running multiple methods at the same time        
        self.lock = threading.Lock()
    
    @property 
    def supported_modes(self) -> list[GameMode]:
        return self._supported_modes
    
    
    def _get_engine(self, mode: GameMode):
        return self._engines.get(mode, None)
    