""" Bot for mjapi"""

import time
from common.settings import Settings
from common.log_helper import LOGGER
from common.utils import random_str
from common.mj_helper import MJAI_TYPE
from .mjapi import MJAPI_Client

from .bot import Bot, BOT_TYPE, reaction_convert_meta



class BotMjapi(Bot):
    """ Bot using mjapi online API"""
    batch_size = 24
    retries = 3
    retry_interval = 1
    bound = 256

    """ MJAPI based mjai bot"""
    def __init__(self, setting:Settings) -> None:
        super().__init__(BOT_TYPE.MJAPI, "MJAPI Bot - " + setting.mjapi_url)
        self.settings = setting
        self.mjapi = MJAPI_Client(self.settings.mjapi_url)
        self._login_or_reg()
        self.id = -1
        self.ignore_next_turn_self_reach:bool = False
        
    def _login_or_reg(self):
        if not self.settings.mjapi_user:
            self.settings.mjapi_user = random_str(6)
            LOGGER.info("Set random mjapi username:%s", self.settings.mjapi_user)        
        try:
            self.mjapi.login(self.settings.mjapi_user, self.settings.mjapi_secret)
        except Exception as e:
            LOGGER.warning("Error login: %s", e)            
            # try register            
            res_reg = self.mjapi.register(self.settings.mjapi_user)
            self.settings.mjapi_secret = res_reg['secret']
            self.settings.save_json()
            LOGGER.info("Registered new user [%s] with MJAPI. User name and secret saved to settings.", self.settings.mjapi_user)
            self.mjapi.login(self.settings.mjapi_user, self.settings.mjapi_secret)

        model_list = self.mjapi.list_models()
        if not model_list:
            raise RuntimeError("No models available in MJAPI")
        self.settings.mjapi_models = model_list
        if self.settings.mjapi_model_select in model_list:
            # OK
            pass
        else:
            LOGGER.debug(
                "mjapi selected model %s N/A, using last one from available list %s",
                self.settings.mjapi_model_select, model_list[-1])
            self.settings.mjapi_model_select = model_list[-1]
        self.model_name = self.settings.mjapi_model_select
        LOGGER.info("Login to MJAPI successful with user: %s, model_name=%s", self.settings.mjapi_user, self.model_name)

    def __del__(self):
        self.mjapi.stop_bot()
        self.mjapi.logout()

    def _init_bot_impl(self):
        self.mjapi.start_bot(self.seat, BotMjapi.bound, self.model_name)
        self.id = -1

    def _process_reaction(self, reaction, recurse):
        if reaction:
            reaction_convert_meta(reaction)
        else:
            return None

        # process self reach
        if recurse and reaction['type'] == MJAI_TYPE.REACH and reaction['actor'] == self.seat:
            LOGGER.debug("Send reach msg to get reach_dahai.")
            reach_msg = {'type': MJAI_TYPE.REACH, 'actor': self.seat}
            reach_dahai = self.react(reach_msg, recurse=False)
            reaction['reach_dahai'] = self._process_reaction(reach_dahai, False)
            self.ignore_next_turn_self_reach = True

        return reaction

    def react(self, input_msg:dict, recurse=True) -> dict | None:
        # input_msg['can_act'] = True
        msg_type = input_msg['type']
        if msg_type in [MJAI_TYPE.START_GAME, MJAI_TYPE.END_GAME, MJAI_TYPE.END_KYOKU]:
            # ignore no effect msgs
            return None
        if self.ignore_next_turn_self_reach:
            if  msg_type == MJAI_TYPE.REACH and input_msg['actor'] == self.seat:
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
            if input_list[0]['type'] == MJAI_TYPE.REACH and input_list[0]['actor'] == self.seat:
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
                can_act=(i + 1 == num_batches))
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
