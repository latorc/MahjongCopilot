""" Helper methods / constants that deal with tile converting / mjai message parsing / etc.
"""

from dataclasses import dataclass, field
from functools import cmp_to_key

import numpy as np
from common.utils import GameMode

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

class MSType:
    """ Majsoul operation type constants"""
    none = 0        # extra type added represeting the None/Pass button. not actually used by Majsoul
    dahai = 1
    chi = 2
    pon = 3
    ankan = 4
    daiminkan = 5
    kakan = 6
    reach = 7
    zimo = 8
    hora = 9
    ryukyoku = 10
    nukidora = 11

class ChiPengGang:
    """ majsoul action types"""
    Chi = 0         # chi
    Peng = 1        # pon
    Gang = 2        # kan

class MSGangType:
    """ majsoul kan types"""
    AnGang = 3      # ankan
    AddGang = 2     # kakan/daminkan

class MjaiType:
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

MJAI_MASK_LIST_3P = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "E",  "S",  "W",  "N",  "P",  "F",  "C",
    '5mr', '5pr', '5sr',
    'reach', 'pon', 'kan_select', 'nukidora', 'hora', 'ryukyoku', 'none'
]

MJAI_TILES_34 = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "E",  "S",  "W",  "N",  "P",  "F",  "C",  "?"
]

MJAI_AKA_DORAS = ["5mr", "5pr", "5sr"]

MJAI_TILES_SORTED = [       # for sorting tiles, with aka doras
    "1m", "2m", "3m", "4m", "5mr", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5pr", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5sr", "5s", "6s", "7s", "8s", "9s",
    "E",  "S",  "W",  "N",  "P",  "F",  "C",  "?"
]

MJAI_TILES_19 = [
    "1m", "9m", "1p", "9p", "1s", "9s",
    "E", "S", "W", "N", "P", "F", "C"
]

MJAI_TILES_28 = ["2m", "8m", "2p", "8p", "2s", "8s"]

MJAI_WINDS = ['E', 'S', 'W', 'N']

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
    """ unicode symbols for ms actions"""
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


# sample data structure for mjai reaction - meta
_sample_meta = {
    "q_values":[
        -9.0919, -9.4669, -8.36597, -8.84972, -9.4357, -10.0071,
        -9.29505, -0.7369096, -9.2746, -9.37585, 0.322028, -2.779459
    ],      # Q values for each option
    "mask_bits": 2697207348,             # Mask bits related to MJAI_MASK_LIST
    "is_greedy": True,
    "eval_time_ns": 357088300
}


def meta_to_options(meta: dict, is_3p:bool=False) -> list:
    """ Convert meta from mjai reaction msg to readable list of tiles with weights
    params:
        meta object from bot reaction msg, see sample above
    returns:
        list of (tile, weights): e.g. [('1m', 0.987532), ('P', 0.011123), ...]
    """
    if is_3p:
        mask_list = MJAI_MASK_LIST_3P
    else:
        mask_list = MJAI_MASK_LIST

    q_values = meta['q_values']
    mask_bits = meta['mask_bits']
    mask = mask_bits_to_bool_list(mask_bits)
    weight_values = softmax(q_values)

    q_value_idx = 0
    option_list = []
    for i in range(46):
        if mask[i]:
            option_list.append((mask_list[i], weight_values[q_value_idx]))
            q_value_idx += 1

    option_list = sorted(option_list, key=lambda x: x[1], reverse=True)
    return option_list


def decode_mjai_tehai(tehai34, akas, tsumohai) -> tuple[list[str], str]:
    """ return tehai and trumohai from mjai.bot.state
    returns:
        ([list of tehai], trumohai) in mjai tiles format"""
    # tehai34 is with tsumohai, no aka marked

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


def normalize_pai(pai):
    """Turn red dora to normal pai"""
    return pai.replace('r', '')


def determine_kan_type(last_action, hand):
    """
    Determines the type of kan based on the last action taken and the player's hand.

    Description:
    This function assumes it is called only when a kan is possible and
    distinguishes which type of kan it is: Ankan, Kakan, or Daiminkan.
    It first normalizes all tiles in the hand, converting red dora tiles
    to their regular counterparts for uniformity in processing.

    Parameters:
    last_action (dict): Information about the last action taken, including the type of action
                        ('tsumo' for a self-draw or 'dahai' for a discard),
                        the actor's identifier, and the tile involved.
                        Example: {'type': 'tsumo', 'actor': 0, 'pai': '5mr'}
    hand (list of str): List of tiles in the player's hand, excluding the tile drawn most recently,
                        which is added during processing if necessary.
                        Example: ['1m', '1m', '1m', '2p', '2p', '2p', '3s', '3s', '3s',
                        '7m', '7m', '7m', '4p', '5m', '5m', '5m']

    Returns:
    MjaiType: ANKAN, KAKAN, or DAIMINKAN.
    The function will return the appropriate enum value based on the conditions met.

    """
    normalized_hand = [normalize_pai(p) for p in hand]
    pai = normalize_pai(last_action['pai'])

    if last_action['type'] == 'tsumo':
        normalized_hand.append(pai)  # Include the drawn tile in the hand

    pai_counts = {p: normalized_hand.count(p) for p in set(normalized_hand)}

    if pai_counts[pai] == 4:
        if last_action['type'] == 'tsumo':
            return MjaiType.ANKAN
        else:
            return MjaiType.KAKAN
    elif last_action['type'] == 'dahai':
        return MjaiType.DAIMINKAN


def generate_chi_consume_sequence(tile, chi_type):
    """Generate the other two tiles in a sequence based on the type of chi and a given tile."""
    base_number = int(tile[0])
    suit = tile[1]

    # Calculate the other two tiles in the sequence based on the chi_type
    if chi_type == 'chi_low':
        return [str(base_number + 1) + suit, str(base_number + 2) + suit]
    elif chi_type == 'chi_mid':
        return [str(base_number - 1) + suit, str(base_number + 1) + suit]
    elif chi_type == 'chi_high':
        return [str(base_number - 2) + suit, str(base_number - 1) + suit]
    else:
        raise ValueError("Invalid chi type")


def determine_chi_tiles(chi_type, called_tile, hand):
    """
    Determine the tiles used for a chi action based on the type of chi and the tile that was called.

    Parameters:
    chi_type (str): 'chi_low', 'chi_mid', or 'chi_high', representing the position of the called tile in the sequence.
    called_tile (str): The tile that was called, formatted as '5m'.
    hand (list of str): Current list of tiles in hand.

    Returns:
    list of str: Returns a list of two tiles needed to complete the chow, defaulting to not choosing red
    dora tiles when multiple combinations are possible.
    """
    sequence_tiles = generate_chi_consume_sequence(called_tile, chi_type)

    # Check if each tile in the sequence is in the hand, considering red dora tiles
    needed_tiles = []
    for tile in sequence_tiles:
        if tile in hand:
            needed_tiles.append(tile)
        else:
            # Check if the normalized tile (in case of red dora tiles) is in the hand
            normalized_tile = normalize_pai(tile)
            for hand_tile in hand:
                if normalize_pai(hand_tile) == normalized_tile:
                    needed_tiles.append(hand_tile)
                    break
        # Switch needed_tiles to red dora tile if possible
        needed_tiles = [f"{tile}r" if f"{tile}r" in hand else tile for tile in needed_tiles]

    if len(needed_tiles) == len(sequence_tiles):
        return needed_tiles
    else:
        return []

def determine_pon_tiles(called_tile, hand):
    if called_tile[0] != 5:
        return [called_tile] * 2
    else:
        pon_tiles_count = 0
        exists_dora = False
        tiles_list = []
        for tile in hand:
            if tile[0:1] == called_tile[0:1]:
                pon_tiles_count += 1
                if tile[2] == 'r':
                    exists_dora = True
                tiles_list.append(tile)
        if pon_tiles_count == 3 and exists_dora:
            return [called_tile] * 2
        else:
            return tiles_list


def determine_kan_tiles(called_tile):
    if called_tile[0] != 5:
        return [called_tile] * 4
    else:
        tiles_list = []
        if called_tile[2] == 'r':
            tiles_list = [called_tile[0:1]] * 3
            tiles_list.append(called_tile)
        else:
            tiles_list = [called_tile[0:1]] * 3
            tiles_list.append(f"{called_tile}r")
        return tiles_list


@dataclass
class GameInfo:
    """ data class containing game info"""
    game_mode:GameMode              # game mode
    bakaze:str = None               # bakaze 场风
    jikaze:str = None               # self_wind 自风
    kyoku:int = None                # kyoku 局 (under bakaze)
    honba:int = None                # honba 本场 (times of consequetive dealing)
    my_tehai:list = None            # tiles in hand
    my_tsumohai:str = None          # new drawn tile if any
    self_reached:bool = False       # if self is in REACH state
    self_seat:int = None            # self seat index
    player_reached:list[bool] = field(default_factory=lambda: [False]*4)  # players in REACH state
    is_first_round:bool = False     # if self first round has not passed

    def n_other_reach(self) -> int:
        """ number of other players in reach state"""
        other_reach = self.player_reached.copy()
        other_reach.pop(self.self_seat)
        n = sum(1 for r in other_reach if r)
        return n
