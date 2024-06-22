import multiprocessing
from pathlib import Path

from bot.bot import BotMjai, GameMode
from common.log_helper import LOGGER
from common.utils import BotNotSupportingMode, Ot2BotCreationError
import time

model_file_path = "mjai/bot_3p/model.pth"


class BotAkagiOt2(BotMjai):
    """ Bot implementation for Akagi OT2 model """

    def __init__(self) -> None:
        super().__init__("Akagi OT2 Bot")
        self._supported_modes: list[GameMode] = []
        self._is_online = "Waiting"
        self._check()
        self.model_type = "AkagiOT2"

    def _check(self):
        # check model file
        if not Path(model_file_path).exists() or not Path(model_file_path).is_file():
            LOGGER.warning("Cannot find model file for Akagi OT2 model:%s", model_file_path)
        if try_create_ot2_bot():
            self._supported_modes.append(GameMode.MJ3P)
        else:
            LOGGER.warning("Cannot create bot for OT2 model.", exc_info=True)
            LOGGER.warning("Could be missing file: %s", model_file_path)
            raise Ot2BotCreationError("Failed to create bot instance for Akagi OT2 model.")
        pass

    @property
    def supported_modes(self) -> list[GameMode]:
        """ return supported game modes"""
        return self._supported_modes

    # 覆写父类 impl 方法
    def _init_bot_impl(self, mode: GameMode = GameMode.MJ3P):
        if mode == GameMode.MJ3P:
            try:
                import riichi3p
                self.mjai_bot = riichi3p.online.Bot(self.seat)
            except Exception as e:
                LOGGER.warning("Cannot create bot for Akagi OT2 model: %s", e, exc_info=True)
                LOGGER.warning("Could be missing model.pth file in path mjai/bot_3p")
                raise Ot2BotCreationError("Failed to create bot instance for Akagi OT2 model.")
        else:
            raise BotNotSupportingMode(mode)

    # 覆写父类 react 方法
    def react(self, input_msg: dict) -> dict | None:
        reaction = super().react(input_msg)
        if reaction is not None:
            if self.mjai_bot.is_online():
                self._is_online = "Online"
            else:
                self._is_online = "Offline"
        return reaction

    @property
    def is_online(self):
        return self._is_online


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
    start_time = time.time()
    timeout = 10
    try:
        timeout = 10
        success = queue.get(timeout=timeout)
    except Exception as e:
        end_time = time.time()
        LOGGER.error("Failed to retrieve the result from the subprocess: %s", e)
        if end_time - start_time >= timeout:
            LOGGER.error("Timeout when waiting for the result from the subprocess")
            process.terminate()
        success = False

    process.join()

    if not success or process.exitcode != 0:
        LOGGER.error("Failed to create bot or detected a crash in the subprocess with exit code %s", process.exitcode)
        return False
    return True
