""" Bot for mjapi"""

import time
from common.settings import Settings
from common.log_helper import LOGGER
from common.utils import random_str
from common.mj_helper import MjaiType
from bot.mjapi.mjapi import MjapiClient

from bot.bot import Bot, GameMode


class BotMjapi(Bot):
    """ Bot using mjapi online API"""
    batch_size = 24
    retries = 3
    retry_interval = 1
    bound = 256

    """ MJAPI based mjai bot"""
    def __init__(self, setting:Settings) -> None:
        super().__init__("MJAPI Bot")
        self.st = setting
        self.api_usage = None
        self.mjapi = MjapiClient(self.st.mjapi_url)
        self._login_or_reg()
        self.id = -1
        self.ignore_next_turn_self_reach:bool = False
        
    @property
    def info_str(self):
        return f"{self.name} [{self.st.mjapi_model_select}] (Usage: {self.api_usage})"
        
    def _login_or_reg(self):
        if not self.st.mjapi_user:
            self.st.mjapi_user = random_str(6)
            LOGGER.info("Created  random mjapi username:%s", self.st.mjapi_user)        
        if self.st.mjapi_secret:    # login
            LOGGER.debug("Logging in with user: %s", self.st.mjapi_user)
            self.mjapi.login(self.st.mjapi_user, self.st.mjapi_secret)
        else:         # try register  
            LOGGER.debug("Registering in with user: %s", self.st.mjapi_user)          
            res_reg = self.mjapi.register(self.st.mjapi_user)
            self.st.mjapi_secret = res_reg['secret']
            self.st.save_json()
            LOGGER.info("Registered new user [%s] with MJAPI. User name and secret saved to settings.", self.st.mjapi_user)
            self.mjapi.login(self.st.mjapi_user, self.st.mjapi_secret)

        model_list = self.mjapi.list_models()
        if not model_list:
            raise RuntimeError("No models available in MJAPI")
        self.st.mjapi_models = model_list
        if self.st.mjapi_model_select in model_list:
            # OK
            pass
        else:
            LOGGER.debug(
                "mjapi selected model %s N/A, using last one from available list %s",
                self.st.mjapi_model_select, model_list[-1])
            self.st.mjapi_model_select = model_list[-1]
        self.model_name = self.st.mjapi_model_select
        self.api_usage = self.mjapi.get_usage()
        self.st.save_json()
        LOGGER.info("Login to MJAPI successful with user: %s, model_name=%s", self.st.mjapi_user, self.model_name)

    def __del__(self):
        LOGGER.debug("Deleting bot %s", self.name)
        if self.initialized:
            self.mjapi.stop_bot()
        if self.mjapi.token:    # update usage and logout on deleting
            self.api_usage = self.mjapi.get_usage()
            self.st.save_json()
            self.mjapi.logout()

    def _init_bot_impl(self, _mode:GameMode=GameMode.MJ4P):
        self.mjapi.start_bot(self.seat, BotMjapi.bound, self.model_name)
        self.id = -1

    def _process_reaction(self, reaction, recurse):
        if reaction:
            pass
        else:
            return None

        # process self reach
        if recurse and reaction['type'] == MjaiType.REACH and reaction['actor'] == self.seat:
            LOGGER.debug("Send reach msg to get reach_dahai.")
            reach_msg = {'type': MjaiType.REACH, 'actor': self.seat}
            reach_dahai = self.react(reach_msg, recurse=False)
            reaction['reach_dahai'] = self._process_reaction(reach_dahai, False)
            self.ignore_next_turn_self_reach = True

        return reaction

    def react(self, input_msg:dict, recurse=True) -> dict | None:
        # input_msg['can_act'] = True
        msg_type = input_msg['type']
        if self.ignore_next_turn_self_reach:
            if  msg_type == MjaiType.REACH and input_msg['actor'] == self.seat:
                LOGGER.debug("Ignoring repetitive self reach msg, reach msg already sent to AI last turn")
                return None
            self.ignore_next_turn_self_reach = False

        old_id = self.id
        err = None
        self.id = (self.id + 1) % BotMjapi.bound
        reaction = None
        for _ in range(BotMjapi.retries):
            try:
                reaction = self.mjapi.act(self.id, input_msg)
                err = None
                break
            except Exception as e:
                err = e
                time.sleep(BotMjapi.retry_interval)
        if err:
            self.id = old_id
            raise err
        return self._process_reaction(reaction, recurse)

    def react_batch(self, input_list: list[dict]) -> dict | None:
        if self.ignore_next_turn_self_reach and len(input_list) > 0:
            if input_list[0]['type'] == MjaiType.REACH and input_list[0]['actor'] == self.seat:
                LOGGER.debug("Ignoring repetitive self reach msg, reach msg already sent to AI last turn")
                input_list = input_list[1:]
            self.ignore_next_turn_self_reach = False
        if len(input_list) == 0:
            return None
        num_batches = (len(input_list) - 1) // BotMjapi.batch_size + 1
        reaction = None
        for (i, start) in enumerate(range(0, len(input_list), BotMjapi.batch_size)):
            reaction = self._react_batch_impl(
                input_list[start:start + BotMjapi.batch_size],
                can_act= i + 1 == num_batches)
        return reaction

    def _react_batch_impl(self, input_list, can_act):
        if len(input_list) == 0:
            return None
        batch_data = []

        old_id = self.id
        err = None
        for (i, msg) in enumerate(input_list):
            self.id = (self.id + 1) % BotMjapi.bound
            if i + 1 == len(input_list) and not can_act:
                msg = msg.copy()
                msg['can_act'] = False
            action = {'seq': self.id, 'data': msg}
            batch_data.append(action)
        reaction = None
        for _ in range(BotMjapi.retries):
            try:
                reaction = self.mjapi.batch(batch_data)
                err = None
                break
            except Exception as e:
                err = e
                time.sleep(BotMjapi.retry_interval)
        if err:
            self.id = old_id
            raise err
        return self._process_reaction(reaction, True)
