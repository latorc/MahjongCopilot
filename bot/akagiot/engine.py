""" Engine for Akagi OT model"""

import json
import gzip
import requests

from common.log_helper import LOGGER
from common.utils import BotNotSupportingMode, GameMode


class MortalEngineAkagiOt:
    """ Mortal Engine for Akagi OT"""
    def __init__(
        self,
        api_key:str = None, server:str = None,
        mode:GameMode=GameMode.MJ4P,
        timeout:int=3, retries:int=3):
        
        self.name = "MortalEngineAkagiOt"
        self.is_oracle = False
        self.version = 4
        self.enable_quick_eval = False
        self.enable_rule_based_agari_guard = False
        
        self.api_key = api_key
        self.server = server
        self.mode = mode
        self.timeout = timeout
        self.retries = retries
        
        if self.mode == GameMode.MJ4P:
            self.api_path = r"/react_batch"
        elif self.mode == GameMode.MJ3P:
            self.api_path = r"/react_batch_3p"
        else:
            raise BotNotSupportingMode(self.mode)
        
        
    def react_batch(self, obs, masks, _invisible_obs):
        """ react_batch for mjai.Bot to call"""
        list_obs = [o.tolist() for o in obs]
        list_masks = [m.tolist() for m in masks]
        post_data = {
            'obs': list_obs,
            'masks': list_masks,
        }
        data = json.dumps(post_data, separators=(',', ':'))
        compressed_data = gzip.compress(data.encode('utf-8'))
        headers = {
            'Authorization': self.api_key,
            'Content-Encoding': 'gzip',
        }
        
        # retry multiple times to post and get response
        for attempt in range(self.retries):
            try:
                r = requests.post(f'{self.server}{self.api_path}',
                    headers=headers,
                    data=compressed_data,
                    timeout=self.timeout)
                break
            except requests.exceptions.Timeout:
                LOGGER.warning("AkagiOT api timeout, attempt %d/%d", attempt+1, self.retries)
                r = None
                continue
        
        if r is None:
            raise RuntimeError("AkagiOT API all retries failed.")            
            
        if r.status_code != 200:
            r.raise_for_status()
        r_json = r.json()
        return r_json['actions'], r_json['q_out'], r_json['masks'], r_json['is_greedy']

# Mortal Engine Parameters:
#
##         boltzmann_temp:
# 1
# brain:
# Brain(
#   (encoder): ResNet(
#     (net): Sequential(
#       (0): Conv1d(1012, 256, kernel_size=(3,), stride=(1,), padding=(1,), bias=False)
#       (1): ResBlock(
#         (res_unit): Sequential(
#           (0): BatchNorm1d(256, eps=0.001, momentum=0.01, affine=True, track_running_stats=True)
#           (1): Mish(inplace=True)
#           (2): Conv1d(256, 256, kernel_size=(3,), stride=(1,), padding=(1,), bias=False)
#           (3): BatchNorm1d(256, eps=0.001, momentum=0.01, affine=True, track_running_stats=True)
#           (4): Mish(inplace=True)
#           (5): Conv1d(256, 256, kernel_size=(3,), stride=(1,), padding=(1,), bias=False)
#         )
#         (ca): ChannelAttention(
#           (shared_mlp): Sequential(
#             (0): Linear(in_features=256, out_features=16, bias=True)
#             (1): Mish(inplace=True)
#             (2): Linear(in_features=16, out_features=256, bias=True)
#           )
#         )
#       )
#       (2): ResBlock(
#         (res_unit): Sequential(
#           (0): BatchNorm1d(256, eps=0.001, momentum=0.01, a...
# device:
# device(type='cpu')
# dqn:
# DQN(
#   (net): Linear(in_features=1024, out_features=47, bias=True)
# )
# enable_amp:
# False
# enable_quick_eval:
# False
# enable_rule_based_agari_guard:
# False
# engine_type:
# 'mortal'
# is_oracle:
# False
# name:
# 'mortal'
# stochastic_latent:
# False
# top_p:
# 1
# version:
# 4
