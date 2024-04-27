""" Settings file and options """

import json
from typing import Callable
from .log_helper import LOGGER
from .lan_str import LanStr, LAN_OPTIONS
from . import utils

DEFAULT_SETTING_FILE = 'settings.json'

class Settings:
    """ Settings class to load and save settings to json file"""
    def __init__(self, json_file:str=DEFAULT_SETTING_FILE) -> None:
        self._json_file = json_file
        self._settings_dict:dict = self.load_json()        
        # read settings or set default values
        # variable names must match keys in json, for saving later

        # UI settings
        self.update_url:str = self._get_value("update_url", "https://update.mjcopilot.com", self.valid_url) # not shown
        self.auto_launch_browser:bool = self._get_value("auto_launch_browser", False, self.valid_bool)
        self.gui_set_dpi:bool = self._get_value("gui_set_dpi", True, self.valid_bool)
        self.browser_width:int = self._get_value("browser_width", 1280, lambda x: 0 < x < 19999)
        self.browser_height:int = self._get_value("browser_height", 720, lambda x: 0 < x < 19999)
        self.ms_url:str = self._get_value("ms_url", "https://game.maj-soul.com/1/",self.valid_url)
        self.enable_chrome_ext:bool = self._get_value("enable_chrome_ext", False, self.valid_bool)
        self.mitm_port:int = self._get_value("mitm_port", 10999, self.valid_mitm_port)
        self.upstream_proxy:str = self._get_value("upstream_proxy","")  # mitm upstream proxy server e.g. http://ip:port
        self.enable_proxinject:bool = self._get_value("enable_proxinject", False, self.valid_bool)
        self.inject_process_name:str = self._get_value("inject_process_name", "jantama_mahjongsoul")
        self.language:str = self._get_value("language", list(LAN_OPTIONS.keys())[-1], self.valid_language)  # language code
        self.enable_overlay:bool = self._get_value("enable_overlay", True, self.valid_bool) # not shown
        
        # AI Model settings
        self.model_type:str = self._get_value("model_type", "Local")
        """ model type: local, mjapi"""
        # for local model
        self.model_file:str = self._get_value("model_file", "mortal.pth")
        self.model_file_3p:str = self._get_value("model_file_3p", "mortal_3p.pth")
        # akagi ot model
        self.akagi_ot_url:str = self._get_value("akagi_ot_url", "")
        self.akagi_ot_apikey:str = self._get_value("akagi_ot_apikey", "")
        # for mjapi
        self.mjapi_url:str = self._get_value("mjapi_url", "https://mjai.7xcnnw11phu.eu.org", self.valid_url)
        self.mjapi_user:str = self._get_value("mjapi_user", "")
        self.mjapi_secret:str = self._get_value("mjapi_secret", "")
        self.mjapi_models:list = self._get_value("mjapi_models",[])
        self.mjapi_model_select:str = self._get_value("mjapi_model_select","baseline")
        
        # Automation settings
        self.enable_automation:bool = self._get_value("enable_automation", False, self.valid_bool)
        self.auto_idle_move:bool = self._get_value("auto_idle_move", False, self.valid_bool)
        self.auto_random_move:bool = self._get_value("auto_random_move", False, self.valid_bool)
        self.auto_reply_emoji_rate:float = self._get_value("auto_reply_emoji_rate", 0.3, lambda x: 0 <= x <= 1)
        self.auto_emoji_intervel:float = self._get_value("auto_emoji_intervel", 5.0, lambda x: 1.0 < x < 30.0)
        self.auto_dahai_drag:bool = self._get_value("auto_dahai_drag", True, self.valid_bool)
        self.ai_randomize_choice:int = self._get_value("ai_randomize_choice", 1, lambda x: 0 <= x <= 5)
        self.delay_random_lower:float = self._get_value("delay_random_lower", 1, lambda x: 0 <= x )
        self.delay_random_upper:float = self._get_value(
            "delay_random_upper",max(2, self.delay_random_lower), lambda x: x >= self.delay_random_lower)
        self.auto_retry_interval:float = self._get_value("auto_retry_interval", 1.5, lambda x: 0.5 < x < 30.0)  # not shown
        
        self.auto_join_game:bool = self._get_value("auto_join_game", False, self.valid_bool)
        self.auto_join_level:int = self._get_value("auto_join_level", 1, self.valid_game_level)
        self.auto_join_mode:int = self._get_value("auto_join_mode", utils.GAME_MODES[0], self.valid_game_mode)
        
        self.save_json()
        LOGGER.info("Settings initialized and saved to %s", self._json_file)
        
    def load_json(self) -> dict:
        """ Load settings from json file into dict"""
        try:
            full  = utils.sub_file(".", self._json_file)
            with open(full, 'r',encoding='utf-8') as file:
                settings_dict:dict = json.load(file)
        except Exception as e:
            LOGGER.warning("Error loading settings. Will use defaults. Error: %s", e)
            settings_dict = {}
        
        return settings_dict
    
    def save_json(self):
        """ Save settings into json file"""
        # save all non-private variables (not starting with "_") into dict
        settings_to_save = {key: value for key, value in self.__dict__.items()
                            if not key.startswith('_') and not callable(value)}
        with open(self._json_file, 'w', encoding='utf-8') as file:
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
                LOGGER.warning("setting %s uses default value '%s' because original value '%s' is invalid"
                    , key, default_value, value)
                return default_value
        except Exception as e:
            LOGGER.warning("setting '%s' use default value '%s' due to error: %s", key, default_value,e)
            return default_value
    
    def lan(self) -> LanStr:
        """ return the LanString instance"""
        return LAN_OPTIONS[self.language]
    
    ### Validate functions: return true if the value is valid
       
    def valid_language(self, lan_code:str):
        """ return True if given language code is valid"""
        return (lan_code in LAN_OPTIONS)
    
    def valid_mitm_port(self, port:int):
        """ return true if port number if valid"""
        if 1000 <= port <= 65535:
            return True
        else:
            return False
    
    def valid_bool(self, value):
        """ return true if value is bool"""
        if isinstance(value,bool):
            return True
        else:
            return False
        
    def valid_username(self, username:str) -> bool:
        """ return true if username valid"""
        if username:
            if len(username) > 1:
                return True
        else:
            return False
    
    def valid_game_level(self, level:int) -> bool:
        """ return true if game level is valid"""
        if 0 <= level <= 4:
            # 0 Bronze 1 Silver  2 Gold  3 Jade  4 Throne
            return True
        else:
            return False
        
    def valid_game_mode(self, mode:str) -> bool:
        """ return true if game mode is valid"""
        if mode in utils.GAME_MODES:
            return True
        else:
            return False
        
    def valid_url(self, url:str) -> bool:
        """ validate url"""
        valid_prefix = ["https://", "http://"]
        for p in valid_prefix:
            if url.startswith(p):
                return True
        return False