""" Bot factory"""

from common.settings import Settings
from common.utils import MODEL_FOLDER, sub_file
from .bot import Bot, BotType
from .bot_local import BotMortalLocal
from .bot_mjapi import BotMjapi


def get_bot(settings:Settings) -> Bot:
    """ create the Bot instance based on settings"""
    if settings.model_type == BotType.LOCAL.value:
        bot = BotMortalLocal(sub_file(MODEL_FOLDER, settings.model_file))                
    elif settings.model_type == BotType.MJAPI.value:
        bot = BotMjapi(settings)
    else:
        raise ValueError(f"Unknown model type: {settings.model_type}")

    return bot
