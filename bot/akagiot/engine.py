""" Engine for Akagi OT model"""

import json
import gzip
import requests
from common.utils import BotNotSupportingMode
from bot import GameMode

class MortalEngineAkagiOt:
    """ Mortal Engine for Akagi OT"""
    def __init__(self, api_key:str = None, server:str = None, mode:GameMode=GameMode.MJ4P):
        self.api_key = api_key
        self.server = server
        self.mode = mode
        if self.mode == GameMode.MJ4P:
            self.path = r"/react_batch"
        elif self.mode == GameMode.MJ3P:
            self.path = r"/react_batch_3p"
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
        
        r = requests.post(f'{self.server}/react_batch',
            headers=headers,
            data=compressed_data,
            timeout=2)
        if r.status_code != 200:
            r.raise_for_status()
        r_json = r.json()
        return r_json['actions'], r_json['q_out'], r_json['masks'], r_json['is_greedy']
