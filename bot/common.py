""" Bot factory"""

from common.settings import Settings
from common.utils import MODEL_FOLDER, sub_file
from .bot import Bot, BotType, GameMode
from .bot_local import BotMortalLocal
from .bot_mjapi import BotMjapi


def get_bot(settings:Settings) -> Bot:
    """ create the Bot instance based on settings"""
    if settings.model_type == BotType.LOCAL.value:
        model_files:dict = {
            GameMode.MJ4P: sub_file(MODEL_FOLDER, settings.model_file),
            GameMode.MJ3P: sub_file(MODEL_FOLDER, settings.model_file_3p)
        }
        bot = BotMortalLocal(model_files)                
    elif settings.model_type == BotType.MJAPI.value:
        bot = BotMjapi(settings)
    else:
        raise ValueError(f"Unknown model type: {settings.model_type}")

    return bot
