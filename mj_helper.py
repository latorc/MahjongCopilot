# Helper methods / constants
# that deal with tile converting / mjai message parsing / etc.

import numpy as np
from functools import cmp_to_key
from lan_strings import LanStrings

TILES_MS_2_MJAI = {
    '0m': '5mr',
    '0p': '5pr',
    '0s': '5sr',
    '1z': 'E',
    '2z': 'S',
    '3z': 'W',
    '4z': 'N',
    '5z': 'P',
    '6z': 'F',
    '7z': 'C'
}
TILES_MJAI_2_MS = {value: key for key, value in TILES_MS_2_MJAI.items()}    # swap keys and values

def cvt_ms2mjai(ms_tile:str) -> str:
    """ convert majsoul tile to mjai tile"""
    if ms_tile in TILES_MS_2_MJAI:
        return TILES_MS_2_MJAI[ms_tile]
    else:
        return ms_tile

def cvt_mjai2ms(mjai_tile:str) -> str:
    """ convert mjai tile to majsoul tile"""
    if mjai_tile in TILES_MJAI_2_MS:
        return TILES_MJAI_2_MS[mjai_tile]
    else:
        return mjai_tile

class MJAI_TYPE:
    """ MJAI message type string constants
    ref: https://mjai.app/docs/mjai-protocol
    """
    NONE = 'none'
    START_GAME = 'start_game'
    START_KYOKU = 'start_kyoku'
    DORA = 'dora'
    TSUMO = 'tsumo'
    DAHAI = 'dahai'
    PON = 'pon'
    CHI = 'chi'
    KAKAN = 'kakan'
    DAIMINKAN = 'daiminkan'
    ANKAN = 'ankan'
    REACH = 'reach'
    REACH_ACCEPTED = 'reach_accepted'
    HORA = 'hora'
    RYUKYOKU = 'ryukyoku'
    NUKIDORA = "nukidora"       # extra added. 3P Mahjong only
    END_KYOKU = 'end_kyoku'
    END_GAME = 'end_game'


def mask_bits_to_binary_string(mask_bits):
    binary_string = bin(mask_bits)[2:]
    binary_string = binary_string.zfill(46)
    return binary_string

def mask_bits_to_bool_list(mask_bits):
    binary_string = mask_bits_to_binary_string(mask_bits)
    bool_list = []
    for bit in binary_string[::-1]:
        bool_list.append(bit == '1')
    return bool_list

def eq(l, r):
    # Check for approximate equality using numpy's floating-point epsilon
    return np.abs(l - r) <= np.finfo(float).eps

def softmax(arr, temperature=1.0):
    arr = np.array(arr, dtype=float)  # Ensure the input is a numpy array of floats
    
    if arr.size == 0:
        return arr  # Return the empty array if input is empty

    if not eq(temperature, 1.0):
        arr /= temperature  # Scale by temperature if temperature is not approximately 1

    # Shift values by max for numerical stability
    max_val = np.max(arr)
    arr = arr - max_val
    
    # Apply the softmax transformation
    exp_arr = np.exp(arr)
    sum_exp = np.sum(exp_arr)
    
    softmax_arr = exp_arr / sum_exp
    
    return softmax_arr

MJAI_MASK_LIST = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "E",  "S",  "W",  "N",  "P",  "F",  "C",
    '5mr', '5pr', '5sr', 
    'reach', 'chi_low', 'chi_mid', 'chi_high', 'pon', 'kan_select', 'hora', 'ryukyoku', 'none'
]

MJAI_TILES_34 = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "E",  "S",  "W",  "N",  "P",  "F",  "C",  "?"
]

MJAI_AKA_DORAS = [
    "5mr", "5pr", "5sr"
]

MJAI_TILES_SORTED = [       # for sorting tiles, with aka doras
    "1m", "2m", "3m", "4m", "5mr", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5pr", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5sr", "5s", "6s", "7s", "8s", "9s",
    "E",  "S",  "W",  "N",  "P",  "F",  "C",  "?"
]
MJAI_TILE_2_UNICODE = {      # https://en.wikipedia.org/wiki/Mahjong_Tiles_(Unicode_block)
    '1m': '🀇',    '2m': '🀈',    '3m': '🀉',    '4m': '🀊',    '5mr':'🀋',
    '5m': '🀋',    '6m': '🀌',    '7m': '🀍',    '8m': '🀎',    '9m': '🀏',
    '1p': '🀙',    '2p': '🀚',    '3p': '🀛',    '4p': '🀜',    '5pr':'🀝',
    '5p': '🀝',    '6p': '🀞',    '7p': '🀟',    '8p': '🀠',    '9p': '🀡',
    '1s': '🀐',    '2s': '🀑',    '3s': '🀒',    '4s': '🀓',    '5sr':'🀔',
    '5s': '🀔',    '6s': '🀕',    '7s': '🀖',    '8s': '🀗',    '9s': '🀘',
    'E': '🀀',    'S': '🀁',    'W': '🀂',    'N': '🀃',
    'P': '🀆',    'F': '🀅',    'C': '🀄',
    '?': '🀫'
}
class ActionUnicode:
    PASS = "✖️"
    CHI = "🟩"
    PON = "🟦"
    KAN = "🟪"
    REACH = "🟧"
    AGARI = "🟥"
    RYUKYOKU = "⬛"

def cmp_mjai_tiles(tile1: str, tile2: str):
    """ compare function for sorting tiles"""
    return MJAI_TILES_SORTED.index(tile1) - MJAI_TILES_SORTED.index(tile2)

def sort_mjai_tiles(mjai_tiles:list[str]) -> list[str]:
    """ sort mjai tiles"""
    return sorted(mjai_tiles, key=cmp_to_key(cmp_mjai_tiles))

# sample data structure for meta
_sample_meta = {
    "q_values":[
        -9.0919, -9.4669, -8.36597, -8.84972, -9.4357, -10.0071,
        -9.29505, -0.7369096, -9.2746, -9.37585, 0.322028, -2.779459
    ],      # Q values for each option
    "mask_bits": 2697207348,             # Mask bits related to MJAI_MASK_LIST
    "is_greedy": True,
    "eval_time_ns": 357088300
}

def meta_to_options(meta: dict) -> list:
    """ Convert meta from mjai reaction msg to readable list of tiles with weights
    params:
        meta object from bot reaction msg, see sample above
    returns:
        list of (tile, weights): e.g. [('1m', 0.987532), ('P', 0.011123), ...]
    """
    
    q_values = meta['q_values']
    mask_bits = meta['mask_bits']
    mask = mask_bits_to_bool_list(mask_bits)
    weight_values = softmax(q_values)
    # further square the numbers and normalize
    weight_values = [w*w for w in weight_values]
    sum_weight = sum(weight_values)
    weight_values = [w/sum_weight for w in weight_values]
    # sum_weight should ~= 1.0
    
    q_value_idx = 0
    option_list = []
    for i in range(46):
        if mask[i]:
            option_list.append((MJAI_MASK_LIST[i], weight_values[q_value_idx]))
            q_value_idx += 1

    option_list = sorted(option_list, key=lambda x: x[1], reverse=True)
    return option_list


def decode_mjai_tehai(tehai34, akas, tsumohai) -> tuple[list[str], str]:
    """ return tehai and trumohai from mjai.bot.state
    returns:
        ([list of tehai], trumohai) in mjai tiles format"""
    # tehai34 is with tsumohai, no aka marked

    """pub(super) chis: ArrayVec<[u8; 4]>,
    pub(super) pons: ArrayVec<[u8; 4]>,
    pub(super) minkans: ArrayVec<[u8; 4]>,
    pub(super) ankans: ArrayVec<[u8; 4]>,
    """
    
    tile_list = []
    for tile_id, tile_count in enumerate(tehai34):
        for _ in range(tile_count):
            tile_list.append(MJAI_TILES_34[tile_id])
    for idx, akas in enumerate(akas):
        if akas:
            tile_list[tile_list.index("5" + ["m", "p", "s"][idx])] = MJAI_AKA_DORAS[idx]
    if len(tile_list)%3 == 2 and tsumohai is not None:
        tile_list.remove(tsumohai)
    else:
        tsumohai = "?"
    len_tile_list = len(tile_list)
    if len_tile_list < 13:
        tile_list += ["?"]*(13-len_tile_list)

    return (tile_list, tsumohai)
 

def mjai_reaction_2_guide(
    reaction:dict, 
    max_options:int=3,
    lan_str:LanStrings=LanStrings()
    ) -> tuple[str, list]:
    """ Convert mjai reaction message to language specific AI guide 
    params:
        reaction(dict): reaction (output) message from mjai bot
        max_options(int): number of options to display. 0 to display no options
        lan_str(LanString): language specific string constants
        
    return:
        (action_str, options): action_str is the recommended action
        options is a list of options (str, float), each option being a tuple of tile str and a percentage number 
        
        sample output for Chinese:
        ("立直,切[西]", [("[西]", 0.9111111), ("立直", 0.077777), ("[一索]", 0.0055555)])        
        """
                
    if reaction is None:
        raise Exception("Input reaction is None")
    re_type = reaction['type']
    pai = reaction.get('pai', None)
    def get_tile_str(mjai_tile:str):    # unicode + language specific name
        return MJAI_TILE_2_UNICODE[mjai_tile] + lan_str.mjai2str(mjai_tile)
    
    if pai:
        tile_str =  get_tile_str(pai)
    
    if re_type == 'dahai':
        action_str = f"{lan_str.DISCARD}{tile_str}"
    elif re_type == 'none':
        action_str = ActionUnicode.PASS + lan_str.PASS
    elif re_type == 'pon':
        action_str = f"{ActionUnicode.PON}{lan_str.PON}{tile_str}"
    elif re_type == 'chi':
        comsumed = reaction['consumed']
        comsumed_strs = [f"{get_tile_str(x)}" for x in comsumed]
        action_str = f"{ActionUnicode.CHI}{lan_str.CHI}{tile_str}({''.join(comsumed_strs)})"
        action_str = action_str            
    elif re_type == 'kakan':
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.KAKAN})"
    elif re_type == 'daiminkan':
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.DAIMINKAN})"
    elif re_type == 'ankan':
        tile_str = get_tile_str(reaction['consumed'][1])
        action_str = f"{ActionUnicode.KAN}{lan_str.KAN}{tile_str}({lan_str.ANKAN})"
    elif re_type =='reach': # attach reach dahai options
        reach_dahai_reaction = reaction['reach_dahai']
        dahai_action_str, dahai_options = mjai_reaction_2_guide(reach_dahai_reaction, 0, lan_str)
        action_str = f"{ActionUnicode.REACH}{lan_str.RIICHI}," + dahai_action_str
    elif re_type =='hora':
        if reaction['actor'] == reaction['target']:
            action_str = f"{ActionUnicode.AGARI}{lan_str.AGARI}({lan_str.TSUMO})"
        else:
            action_str = f"{ActionUnicode.AGARI}{lan_str.AGARI}({lan_str.RON})"
    elif re_type == 'ryukyoku':
        action_str = f"{ActionUnicode.RYUKYOKU}{lan_str.RYUKYOKU}"
    else:
        action_str = lan_str.mjai2str(re_type)
    
    options = []
    if max_options > 0:
        # process options. display top options with their weights
        meta_options = reaction['meta_options'][:max_options]
        if meta_options:
            for (code, q) in meta_options:      # code is in MJAI_MASK_LIST
                name_str = lan_str.mjai2str(code)
                if code in MJAI_TILES_34 or code in MJAI_AKA_DORAS:
                    # if it is a tile
                    name_str = get_tile_str(code)
                options.append((name_str, q))
        
    return (action_str, options)


class GameInfo:
    """ data class containing game info"""
    bakaze:str = None       # bakaze 场风
    self_wind:str = None    # self_wind 自风
    kyoku:int = None        # kyoku 局 (under bakaze)
    honba:int = None        # honba 本场 (times of consequetive dealing)
    my_tehai:list = None    # tiles in hand
    my_tsumohai = None      # new drawn tile if any
    reached:bool = False