""" Settings file and options """

import json
import pathlib
import shutil
import sys
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
        self.browser_fullscreen:bool = self._get_value("browser_fullscreen", False, self.valid_bool)
        self.browser_high_quality:bool = self._get_value(
            "browser_high_quality", sys.platform == "darwin", self.valid_bool)
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
        self.use_real_mouse:bool = self._get_value("use_real_mouse", False, self.valid_bool)
        self.real_mouse_speed_pps:float = self._get_value(
            "real_mouse_speed_pps", 2200.0, lambda x: 300 <= x <= 20000)
        self.real_mouse_jitter_px:float = self._get_value(
            "real_mouse_jitter_px", 2.0, lambda x: 0 <= x <= 20)
        self.real_mouse_click_offset_px:float = self._get_value(
            "real_mouse_click_offset_px", 2.0, lambda x: 0 <= x <= 30)
        self.ai_randomize_choice:int = self._get_value("ai_randomize_choice", 1, lambda x: 0 <= x <= 5)
        self.delay_random_lower:float = self._get_value("delay_random_lower", 1, lambda x: 0 <= x )
        self.delay_random_upper:float = self._get_value(
            "delay_random_upper",max(2, self.delay_random_lower), lambda x: x >= self.delay_random_lower)
        self.auto_retry_interval:float = self._get_value("auto_retry_interval", 1.5, lambda x: 0.5 < x < 30.0)  # not shown
        
        self.auto_join_game:bool = self._get_value("auto_join_game", False, self.valid_bool)
        self.auto_join_level:int = self._get_value("auto_join_level", 1, self.valid_game_level)
        self.auto_join_mode:int = self._get_value("auto_join_mode", utils.GAME_MODES[0], self.valid_game_mode)

        self._apply_platform_defaults()
        self._seed_models_from_bundle()
        self._sync_local_model_files()
        self.save_json()
        LOGGER.info("Settings initialized and saved to %s", self._json_file)

    def _apply_platform_defaults(self):
        """Apply platform-specific defaults after loading persisted settings."""
        if sys.platform != "darwin":
            return
        # macOS minimal build: fixed language/model and no proxy/real-mouse features.
        self.language = "ZHS"
        self.model_type = "Local"
        self.use_real_mouse = False
        self.enable_proxinject = False
        self.upstream_proxy = ""
        self.enable_chrome_ext = False
        self.auto_launch_browser = False

    def _seed_models_from_bundle(self):
        """Copy bundled models into writable macOS model directory on first launch."""
        if sys.platform != "darwin":
            return
        if not getattr(sys, "frozen", False):
            return
        try:
            bundle_models_dir = pathlib.Path(sys.executable).resolve().parent / utils.Folder.MODEL
            if not bundle_models_dir.is_dir():
                return
            dst_dir = pathlib.Path(utils.sub_folder(utils.Folder.MODEL))
            copied:list[str] = []
            for src in sorted(bundle_models_dir.glob("*.pth"), key=lambda p: p.name.lower()):
                dst = dst_dir / src.name
                if dst.exists():
                    continue
                shutil.copy2(src, dst)
                copied.append(src.name)
            if copied:
                LOGGER.info("Seeded %d bundled model(s): %s", len(copied), ", ".join(copied))
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.warning("Failed to seed bundled models: %s", e)

    def _sync_local_model_files(self):
        """Auto-detect local model files on startup and keep selections valid."""
        if self.model_type != "Local":
            return

        model_dir = pathlib.Path(utils.sub_folder(utils.Folder.MODEL))
        model_files = sorted(
            [f.name for f in model_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pth"],
            key=str.lower
        )
        if not model_files:
            return

        def exists_in_model_dir(name:str) -> bool:
            return bool(name) and (model_dir / name).is_file()

        def looks_like_3p(name:str) -> bool:
            lowered = name.lower()
            three_p_keys = ("3p", "3-p", "sanma", "3player", "3_player", "3mahjong", "三麻", "三人")
            return any(k in lowered for k in three_p_keys)

        placeholder_names = {"mortal.pth", "mortal_3p.pth"}
        three_p_candidates = [m for m in model_files if looks_like_3p(m)]
        four_p_candidates = [m for m in model_files if not looks_like_3p(m)] or list(model_files)

        preferred_four_p = [m for m in four_p_candidates if m not in placeholder_names] or four_p_candidates
        preferred_three_p = [m for m in three_p_candidates if m not in placeholder_names] or three_p_candidates

        if (not exists_in_model_dir(self.model_file)) or (self.model_file in placeholder_names):
            new_4p = preferred_four_p[0]
            if self.model_file != new_4p:
                LOGGER.info("Auto-selected 4P local model: %s", new_4p)
                self.model_file = new_4p

        # If no obvious 3P model exists, keep 3P empty to avoid loading a 4P file as 3P.
        if (not exists_in_model_dir(self.model_file_3p)) or (self.model_file_3p in placeholder_names):
            new_3p = preferred_three_p[0] if preferred_three_p else ""
            if self.model_file_3p != new_3p:
                if new_3p:
                    LOGGER.info("Auto-selected 3P local model: %s", new_3p)
                else:
                    LOGGER.info("No 3P local model detected; 3P model selection cleared.")
                self.model_file_3p = new_3p
        
    def load_json(self) -> dict:
        """ Load settings from json file into dict"""
        try:
            full = self._settings_file()
            # Be tolerant of UTF-8 BOM (common on Windows editors/PowerShell).
            with open(full, 'r',encoding='utf-8-sig') as file:
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
        with open(self._settings_file(), 'w', encoding='utf-8') as file:
            json.dump(settings_to_save, file, indent=4, separators=(', ', ': '))

    def _settings_file(self) -> str:
        """Return settings.json path for current platform."""
        if sys.platform == "darwin":
            base = pathlib.Path.home() / "Library" / "Application Support" / "mortal_mac_v0.2"
            base.mkdir(parents=True, exist_ok=True)
            return str((base / self._json_file).resolve())
        return utils.sub_file(".", self._json_file)
    
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
