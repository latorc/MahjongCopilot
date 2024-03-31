import json
import pathlib
from typing import Callable
from log_helper import LOGGER
import lan_strings
DEFAULT_SETTING_FILE = 'settings.json'
class Settings:
    """ Settings class to load and save settings to json file"""
    def __init__(self, json_file:str=DEFAULT_SETTING_FILE) -> None:
        self._json_file = json_file
        self._settings_dict:dict = self.load_json()
        
        # read settings or set default values
        # variable names must match keys in json, for saving later        
        self.auto_launch_browser:bool = self._get_value("auto_launch_browser", True, Settings.valid_bool)
        self.browser_width:int = self._get_value("browser_width", 1280)
        self.browser_height:int = self._get_value("browser_height", 720)
        self.ms_url:str = self._get_value("ms_url", "https://game.maj-soul.com/1/")
        self.mitm_port:int = self._get_value("mitm_port", 8999)
        self.language:str = self._get_value("language", next(iter(lan_strings.LAN_OPTIONS)), Settings.valid_language)
        self.model_file:str = self._get_value("model_file", "mortal.pth")
        self.enable_automation:bool = self._get_value("enable_automation", False, Settings.valid_bool)
        self.enable_overlay:bool = self._get_value("enable_overlay", True, Settings.valid_bool)
        
    def load_json(self) -> dict:
        if pathlib.Path(self._json_file).exists():
            with open(self._json_file, 'r') as file:
                settings_dict:dict = json.load(file)
        else:
            settings_dict = {}
        return settings_dict
    
    def save_json(self):
        """ Save settings into json file"""
        # save all non-private variables (not starting with "_") into dict
        settings_to_save = {key: value for key, value in self.__dict__.items()
                            if not key.startswith('_') and not callable(value)}
        with open(self._json_file, 'w') as file:
            json.dump(settings_to_save, file, indent=4, separators=(', ', ': '))
    
    def _get_value(self, key:str, default_value:any, validator:Callable[[any],bool]=None) -> any:
        """ Get value from settings dictionary, or return default_value if error"""
        try:
            value = self._settings_dict[key]
            if not validator:
                return value
            if validator(value):
                return value
            else:
                LOGGER.warning(f"setting '{key}' use default value '{default_value}' because original value '{value}' is invalid")
                return default_value
        except Exception as e:
            LOGGER.warning("setting '%s' use default value '%s' because error: %s", key, default_value,e, exc_info=True)
            return default_value
    
    def lan(self) -> lan_strings.LanStrings:
        """ return the LanString instance"""
        return lan_strings.LAN_OPTIONS[self.language]
        
    def valid_language(language:str):
        return (language in lan_strings.LAN_OPTIONS)
    
    def valid_mitm_port(port:int):
        if 1000 <= port <= 65535:
            return True
        else:
            return False
    
    def valid_bool(value):
        if isinstance(value,bool):
            return True
        else:
            return False

    
        
if __name__ == '__main__':
    # Test code
    settings = Settings('settings.json')
    settings.mitm_port = 8999
    settings.save_json()