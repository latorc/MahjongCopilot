""" Bot Mortal Local """

from pathlib import Path
import threading

from common.utils import LocalModelException
from common.log_helper import LOGGER
from bot.local.engine import get_engine
from bot.bot import BotMjai, GameMode
from common.settings import Settings
import multiprocessing

# 尝试获取mjai.bot实例，该方法可能会导致 panick，需要在分离进程中使用
def create_bot_instance(queue):
    import riichi3p
    try:
        # 尝试创建一个mjai.bot实例
        riichi3p.online.Bot(1)
        queue.put(True)  # 将成功的标志放入队列
    except Exception as e:
        LOGGER.warning("Cannot create bot: %s", e, exc_info=True)
        LOGGER.warning("Could be missing model.pth file in path ./mjai/bot_3p")
        queue.put(False)  # 将失败的标志放入队列

# 使用分离进程尝试创建bot实例
def try_create_ot2_bot():
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=create_bot_instance, args=(queue,))
    process.start()

    # 尝试从队列中获取结果，设置超时时间防止无限等待
    try:
        success = queue.get(timeout=3)  # 设置适当的超时时间，例如10秒
    except Exception as e:
        LOGGER.error("Failed to retrieve the result from the subprocess: %s", e)
        success = False

    process.join()

    if not success or process.exitcode != 0:
        LOGGER.error("Failed to create bot or detected a crash in the subprocess with exit code %s", process.exitcode)
        return False
    return True


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
                    settings = Settings()
                    if settings.enable_ot2_for_3p:
                        import riichi3p
                        try :
                            # 用分离进程尝试创建一个mjai.bot实例
                            if try_create_ot2_bot():
                                self._engines[k] = "./mjai/bot_3p/model.pth"
                            else:
                                LOGGER.warning("Cannot create bot for OT2 model %s.", k, exc_info=True)
                                LOGGER.warning("Could be missing model.pth file in path ./mjai/bot_3p")
                        except Exception as e:
                            LOGGER.warning("Cannot create bot for OT2 model %s: %s", k, e, exc_info=True)
                            LOGGER.warning("Could be missing model.pth file in path ./mjai/bot_3p")
                        pass
                    else:
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
    