""" Calc risks
ref: https:#github.com/EndlessCheng/mahjong-helper/blob/master/util/risk_base.go"""
# Work in progress
from enum import IntEnum, auto

from common.mj_helper import MJAI_TILES_34


class Tile34(IntEnum):
    """ tile index in 34-tile format. Follows MJAI naming"""
    E = 27
    S = 28
    W = 29
    N = 30
    P = 31
    F = 32
    C = 33

class RiskCatSuji(IntEnum):
    """ Risk Category, column headers (and column index) for risk table"""
    #                           # For turn 9 in RISK_TABLE
    SAFE = 0                    # 0.0 no risk e.g. genbutsu 现物
    NOSUJI_5 = auto()           # 12.8
    NOSUJI_46 = auto()          # 13.1
    NOSUJI_37 = auto()          # 9.5
    NOSUJI_28 = auto()          # 8.6
    NOSUJI_19 = auto()          # 7.4
    HALFSUJI_5 = auto()         # 7.4
    HALFSUJI_46_G19 = auto()    # 7.2 genbutsu 现物为19
    HALFSUJI_46_G37 = auto()    # 7.9 genbutsu 现物为73
    SUJI_37 = auto()            # 5.5
    SUJI_28 = auto()            # 3.9
    SUJI_19 = auto()            # 1.8
    DOUBLESUJI_5 = auto()       # 2.2
    DOUBLESUJI_46 = auto()      # 2.3

    YAKU_3LEFT = auto()         # 4.6 Yaku hai - 3 left 字牌-役牌-剩余3
    YAKU_2LEFT = auto()         # 1.9 Yaku hai - 2 left 字牌-役牌-剩余2
    YAKU_1LEFT = auto()         # 0.3 Yaku hai - 1 left 字牌-役牌-剩余1
    OTAKAZE_3LEFT = auto()      # 4.0 Otakaze 3 left 字牌-客风-剩余3
    OTAKAZE_2LEFT = auto()      # 1.8 Otakaze 2 left 字牌-客风-剩余2
    OTAKAZE_1LEFT = auto()      # 0.2 Otakaze 1 left 字牌-客风-剩余1


RISK_TABLE_SUJI = [
	[],                                                                             # Honor tiles                       # 巡目 Turn
	[0, 5.7, 5.7, 5.8, 4.7, 3.4, 2.5, 2.5, 3.1, 5.6, 3.8, 1.8, 0.8, 2.6,            2.1, 1.2, 0.5, 2.4, 1.4, 1.2],      # 1
	[0, 6.6, 6.9, 6.3, 5.2, 4.0, 3.5, 3.5, 4.1, 5.3, 3.5, 1.9, 0.8, 2.6,            2.3, 1.2, 0.5, 2.7, 1.3, 0.4],
	[0, 7.7, 8.0, 6.7, 5.8, 4.6, 4.3, 4.1, 4.9, 5.2, 3.6, 1.8, 1.6, 2.0,            2.4, 1.2, 0.3, 2.6, 1.2, 0.3],
	[0, 8.5, 8.9, 7.1, 6.2, 5.1, 4.8, 4.7, 5.6, 5.2, 3.8, 1.7, 1.6, 2.0,            2.6, 1.1, 0.2, 2.6, 1.2, 0.2],
	[0, 9.4, 9.7, 7.5, 6.7, 5.5, 5.3, 5.1, 6.0, 5.3, 3.7, 1.7, 1.7, 2.0,            2.9, 1.2, 0.2, 2.8, 1.2, 0.2],      # 5
	[0, 10.2, 10.5, 7.9, 7.1, 5.9, 5.8, 5.6, 6.4, 5.2, 3.7, 1.7, 1.8, 2.0,          3.2, 1.3, 0.2, 2.9, 1.3, 0.2],
	[0, 11.0, 11.3, 8.4, 7.5, 6.3, 6.3, 6.1, 6.8, 5.3, 3.7, 1.7, 2.0, 2.1,          3.6, 1.4, 0.2, 3.2, 1.4, 0.2],
	[0, 11.9, 12.2, 8.9, 8.0, 6.8, 6.9, 6.6, 7.4, 5.3, 3.8, 1.7, 2.1, 2.2,          4.0, 1.6, 0.2, 3.5, 1.6, 0.2],
	[0, 12.8, 13.1, 9.5, 8.6, 7.4, 7.4, 7.2, 7.9, 5.5, 3.9, 1.8, 2.2, 2.3,          4.6, 1.9, 0.3, 4.0, 1.8, 0.2],      # 9
	[0, 13.8, 14.1, 10.1, 9.2, 8.0, 8.0, 7.8, 8.5, 5.6, 4.0, 1.9, 2.4, 2.4,         5.3, 2.2, 0.3, 4.6, 2.1, 0.3],
	[0, 14.9, 15.1, 10.8, 9.9, 8.7, 8.7, 8.5, 9.2, 5.7, 4.2, 2.0, 2.5, 2.6,         6.0, 2.6, 0.4, 5.1, 2.5, 0.3],
	[0, 16.0, 16.3, 11.6, 10.6, 9.4, 9.4, 9.2, 9.9, 6.0, 4.4, 2.2, 2.7, 2.7,        6.8, 3.1, 0.4, 5.1, 2.5, 0.3],
	[0, 17.2, 17.5, 12.4, 11.4, 10.2, 10.2, 10.0, 10.6, 6.2, 4.6, 2.4, 3.0, 3.0,    7.8, 3.7, 0.5, 6.6, 3.7, 0.5],
	[0, 18.5, 18.8, 13.3, 12.3, 11.1, 11.0, 10.9, 11.4, 6.6, 4.9, 2.7, 3.2, 3.1,    8.8, 4.4, 0.7, 7.4, 4.4, 0.6],
	[0, 19.9, 20.1, 14.3, 13.3, 12.0, 11.9, 11.8, 12.3, 7.0, 5.3, 3.0, 3.4, 3.4,    9.9, 5.2, 0.8, 8.4, 5.3, 0.8],      # 15
	[0, 21.3, 21.7, 15.4, 14.3, 13.1, 12.9, 12.8, 13.3, 7.4, 5.7, 3.3, 3.7, 3.6,    11.2, 6.2, 1.0, 9.4, 6.5, 0.9],
	[0, 22.9, 23.2, 16.6, 15.4, 14.2, 14.0, 13.8, 14.4, 8.0, 6.1, 3.6, 3.9, 3.9,    12.4, 7.3, 1.3, 10.5, 7.7, 1.2],
	[0, 24.7, 24.9, 17.9, 16.7, 15.4, 15.2, 15.0, 15.6, 8.5, 6.6, 4.0, 4.3, 4.2,    13.9, 8.5, 1.7, 11.8, 9.4, 1.6],    # 18
	[0, 27.5, 27.8, 20.4, 19.1, 17.8, 17.5, 17.5, 17.5, 9.8, 7.4, 5.0, 5.1, 5.1,    18.1, 12.1, 2.8, 14.7, 12.6, 2.1],  # 19
]
"""
筋牌相关分类危险度
RISK_TABLE_SUJI[1-based turn #][risk category] = hoju rate, [巡目][种类] = 铳率
统计学麻雀战术 表20-1, 20-2"""

class RiskCatOC(IntEnum):
    """ No-chance / One-chance related categories"""
    ALL = 0                 #
    NC = auto()             # No chance: n-1, n+1 both 0 left (wall)
    OC = auto()             #
    OC_SELF = auto()
    OC_OTHER = auto()
    DOC = auto()
    DTC = auto()
    OTHER = auto()


# 图表 22-1 早外危险度
# 23-1, 23-2 23-3 立直宣言引卦牌危险度
# 24-1 25-1 立直宣言牌 同色牌的危险度

RISK_DORA_MULTI:list[float] = [
    1.0,
	14.9 / 12.8 * 78 / 58,
	15.0 / 13.1 * 78 / 58,
	12.1 / 9.5 * 75 / 56,
	10.3 / 8.6 * 75 / 54,
	8.9 / 7.4 * 77 / 53,

	9.7 / 7.4 * 81 / 60,
	8.9 / 7.2 * 81 / 60,
	10.4 / 7.9 * 81 / 60,
	8.0 / 5.5 * 75 / 56,
	5.5 / 3.9 * 81 / 56,
	3.5 / 1.8 * 92 / 58,
	4.1 / 2.2 * 88 / 62,
	4.1 / 2.3 * 88 / 62,

	5.2 / 4.6 * 96 / 67,
	2.9 / 1.9 * 96 / 67,
	1.1 / 0.3 * 96 / 67,
	5.1 / 4.0 * 92 / 56,
	3.0 / 1.8 * 92 / 56,
	0.8 / 0.2 * 92 / 56,
]
""" Dora risk multiplier for each Risk Category (See RiskCat)
图表 29-1~4"""


SUJI_TYPE_TABLE = [
    [RiskCatSuji.NOSUJI_19, RiskCatSuji.SUJI_19],       # 0 [has i+3(4)]
    [RiskCatSuji.NOSUJI_28, RiskCatSuji.SUJI_28],       # 1 [has i+3(5)]
    [RiskCatSuji.NOSUJI_37, RiskCatSuji.SUJI_37],       # 2 [has i+3(6)]
    [[RiskCatSuji.NOSUJI_46, RiskCatSuji.HALFSUJI_46_G19], [RiskCatSuji.HALFSUJI_46_G37, RiskCatSuji.DOUBLESUJI_46]],   # 3 [has i-3][has i+3]
    [[RiskCatSuji.NOSUJI_5, RiskCatSuji.HALFSUJI_5], [RiskCatSuji.HALFSUJI_5, RiskCatSuji.DOUBLESUJI_5]],     # 4 [has i-3][has i+3]
    [[RiskCatSuji.NOSUJI_46, RiskCatSuji.HALFSUJI_46_G37], [RiskCatSuji.HALFSUJI_46_G19, RiskCatSuji.DOUBLESUJI_46]],   # 5 [has i-3][has i+3]
    [RiskCatSuji.NOSUJI_37, RiskCatSuji.SUJI_37],       # [has i-3(4)]
    [RiskCatSuji.NOSUJI_28, RiskCatSuji.SUJI_28],       # [has i-3(5)]
    [RiskCatSuji.NOSUJI_19, RiskCatSuji.SUJI_19],       # [has i-3(6)]
]


# genbutsu / safe tile

def list_2_array_34(tile_list:list[int]) -> list[int]:
    """ convert list of tiles in 34-format to 34-array foramt"""
    tile_array = [0] * 34
    for t in tile_list:
        tile_array[t] += 1
    return tile_array


def calc_tile_riskcat(
    safe_tiles_34t:set[int],        # set of safe tiles (34-tile format)
    tiles_left_34a:list[int],       # numbers of tiles left (34-array)
    round_wind:int,                 # round wind    27=E, 28=S, 29=W, 30=N
    player_wind:int                 # player wind   27=E, 28=S, 29=W, 30=N
    ) -> list[RiskCatSuji]:
    """ determine risk category for each of the 34 tiles
    returns: list of RiskCatSuju (34-array)
    """
    # mark safe tiles in 34-array
    safe_tiles_34a:list[bool] = [False] * 34  # False = risky, True = safe
    for tile in safe_tiles_34t:
        safe_tiles_34a[tile] = True

    # compute risk category (suji category) for m/p/s tiles
    risk_cat_34a = [None] * 34
    for idx in range(27):
        num = idx // 9
        if num < 3:
            risk_cat_34a[idx] = SUJI_TYPE_TABLE[num][safe_tiles_34a[idx+3]]
            if num == 0 and safe_tiles_34a[idx+3] and tiles_left_34a[idx] == 0:
                # 数牌1: 两面 对碰单骑 都不可能 -> 安牌
                risk_cat_34a[idx] = RiskCatSuji.SAFE
            if num == 2 and tiles_left_34a[idx+2] == 0:
                # 5壁，37视为筋
                risk_cat_34a[idx] = RiskCatSuji.SUJI_37
        elif 3 <= num < 6:
            risk_cat_34a[idx] = SUJI_TYPE_TABLE[num][safe_tiles_34a[idx-3]][safe_tiles_34a[idx+3]]
        else: # num 6 7 8
            risk_cat_34a[idx] = SUJI_TYPE_TABLE[num][safe_tiles_34a[idx-3]]
            if num == 8 and safe_tiles_34a[idx-3] and tiles_left_34a[idx] == 0:
                # 9: 两面 对碰单骑 都不可能 -> 安牌
                risk_cat_34a[idx] = RiskCatSuji.SAFE
            if num == 6 and tiles_left_34a[idx-2] == 0:
                # 5壁，37视为筋
                risk_cat_34a[idx] = RiskCatSuji.SUJI_37

    honor_risk_type = {     # (is yaku, tiles left): RiskCat
        (True, 1):  RiskCatSuji.YAKU_1LEFT,
        (True, 2):  RiskCatSuji.YAKU_2LEFT,
        (True, 3):  RiskCatSuji.YAKU_3LEFT,
        (True, 4):  RiskCatSuji.YAKU_3LEFT,
        (False, 1):  RiskCatSuji.OTAKAZE_1LEFT,
        (False, 2):  RiskCatSuji.OTAKAZE_2LEFT,
        (False, 3):  RiskCatSuji.OTAKAZE_3LEFT,
        (False, 4):  RiskCatSuji.OTAKAZE_3LEFT,
        # 剩余数为 0 可以视作安牌（忽略国士）
        (True, 0):  RiskCatSuji.SAFE,
        (False, 0): RiskCatSuji.SAFE,
    }
    for idx in range(27,34):  # for honor tiles
        num = idx//9
        if num in (round_wind, player_wind, Tile34.P, Tile34.F, Tile34.C):
            is_yaku = True  # 该玩家的役牌 = 场风/自风/白/发/中
        risk_cat_34a[idx] = honor_risk_type[(is_yaku, tiles_left_34a[idx])]

    return risk_cat_34a


def calc_low_risk_tiles27(tiles_safe_34:list[bool], tile_left_34:list[int]) -> list[bool]:
    """ 根据实际信息，某些牌的危险度远低于无筋（如现物、NC），这些牌可以用来计算筋牌的危险度
    TODO: 早外产生的筋牌可能要单独计算
    params:
    """
    low_risk_tiles27 = tiles_safe_34[:27]

    for i in range(3):
        # 2壁，当做打过1
        if tile_left_34[9 * i + 1] == 0:
            low_risk_tiles27[9 * i] = True
        # 3壁，当做打过12
        if tile_left_34[9 * i + 2] == 0:
            low_risk_tiles27[9 * i] = True
            low_risk_tiles27[9 * i + 1] = True
        # 4壁，当做打过23
        if tile_left_34[9 * i + 3] == 0:
            low_risk_tiles27[9 * i + 1] = True
            low_risk_tiles27[9 * i + 2] = True
        # 6壁，当做打过78
        if tile_left_34[9 * i + 5] == 0:
            low_risk_tiles27[9 * i + 6] = True
            low_risk_tiles27[9 * i + 7] = True
        # 7壁，当做打过89
        if tile_left_34[9 * i + 6] == 0:
            low_risk_tiles27[9 * i + 7] = True
            low_risk_tiles27[9 * i + 8] = True
        # 8壁，当做打过9
        if tile_left_34[9 * i + 7] == 0:
            low_risk_tiles27[9 * i + 8] = True
    return low_risk_tiles27



def calc_risk_tile34(
    turn:int,               # turn number starting from 1
    discard_list:list[int], # list discarded tiles, in 34 format. same for following parameters
    riichi_idx:int,         # index in discard list where riichi was declared
    safe_list:list[int],    # safe tiles (from others' discard after riichi)
    tiles_left_34:list[int],   # number of tiles left for index tile
    dora_list:list[int],    # dora list of tile34 indices
    round_wind:int,         # round wind  27=E, 28=S, 29=W, 30=N
    player_wind:int,        # player wind 27=E, 28=S, 29=W, 30=N
    ) -> list[float]:
    """ calculate risk rate for each of the 34 tiles, given the reach opponent
    Returns:
        list of risk rates (34-array) for each tile34 index. i.e. list[tile_index_34] = hoju rate
    """

    def dora_multi(tile_idx:int, risk_cat:RiskCatSuji) -> float:
        """ risk multiplier considering whether tile is dora and its risk category"""
        if tile_idx in dora_list:
            return RISK_DORA_MULTI[risk_cat]
        else:
            return 1.0


    # 各类牌和牌方式:
	# 19 - 单骑, 对碰, 两面
	# 28 - 单骑, 对碰, 两面, 坎张
	# 37 - 单骑, 对碰, 两面, 坎张, 边张
	# 456- 单骑, 对碰, 两面x2, 坎张
    # 字 - 单骑, 对碰

    # 首先，根据现物和 No Chance 计算有没有两面的可能
	# 生成用来计算筋牌的「安牌」
    tiles_safe_34 = list_2_array_34(discard_list + safe_list)
    tile_lowrisk_27 = calc_low_risk_tiles27(tiles_safe_34, tiles_left_34)

    # 利用「安牌」计算无筋、筋、半筋、双筋的铳率
	# TODO: 特殊处理宣言牌的筋牌、宣言牌的同色牌的铳率
    tile_riskcat_27 = calc_tile_riskcat(tile_lowrisk_27)
    for idx in range():


    tile_risk_34 = [RISK_TABLE_SUJI[turn][t] * dora_multi(idx//9, t) for idx, t in enumerate(tile_riskcat_27)]

