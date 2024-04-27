""" Bot factory"""
from common.settings import Settings
from common.utils import Folder, sub_file
from .bot import Bot, GameMode
from .local.bot_local import BotMortalLocal
from .mjapi.bot_mjapi import BotMjapi
from .akagiot.bot_akagiot import BotAkagiOt


MODEL_TYPE_STRINGS = ["Local", "AkagiOT", "MJAPI"]


def get_bot(settings:Settings) -> Bot:
    """ create the Bot instance based on settings"""
    
    match settings.model_type:
        case "Local":   
            model_files:dict = {
                GameMode.MJ4P: sub_file(Folder.MODEL, settings.model_file),
                GameMode.MJ3P: sub_file(Folder.MODEL, settings.model_file_3p)
            }
            bot = BotMortalLocal(model_files)
        case "AkagiOT":
            bot = BotAkagiOt(settings.akagi_ot_url, settings.akagi_ot_apikey)
        case "MJAPI":
            bot = BotMjapi(settings)
        case _:
            raise ValueError(f"Unknown model type: {settings.model_type}")

    return bot


