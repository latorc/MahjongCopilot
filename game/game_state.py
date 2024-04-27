""" Game State Module for Majsoul
This module processes Majsoul game state and take liqi messages as inputs,
and interfaces with AI bot to generate reactions.
"""
import time

from liqi import MsgType
from liqi import LiqiProto, LiqiMethod, LiqiAction

import common.mj_helper as mj_helper
from common.mj_helper import MjaiType, GameInfo, MJAI_WINDS, ChiPengGang, MSGangType
from common.log_helper import LOGGER
from common.utils import GameMode
from bot import Bot, reaction_convert_meta

NO_EFFECT_METHODS = [
    '.lq.NotifyPlayerLoadGameReady',        # Notify: the game starts
    LiqiMethod.checkNetworkDelay,       # REQ/RES: Check network delay
    '.lq.FastTest.inputOperation',          # REQ/RES: Send operations (discard/reach/etc.)
    '.lq.FastTest.inputChiPengGang',        # REQ/RES: send Chi/Peng/Gang operations
    '.lq.FastTest.confirmNewRound',         # REQ/RES: confirm results and ask for new round start
    '.lq.PlayerLeaving',                    # Player leaving
    '.lq.FastTest.clearLeaving',            # Player get back in game
    LiqiMethod.terminateGame,               # REQ: request terminate game
    '.lq.NotifyGameFinishReward',           # Notify: game finish reward (after game end)
    '.lq.NotifyActivityReward',             #
    '.lq.NotifyLeaderboardPoint',           #
    '.lq.FastTest.broadcastInGame',         # emoji?
    LiqiMethod.NotifyGameBroadcast,         # Notify: emoji    
    '.lq.NotifyPlayerConnectionState',      # 
]

class KyokuState:
    """ data class for kyoku info, will be reset every newround"""
    def __init__(self) -> None:
        self.bakaze:str = None              # Bakaze (場風)
        self.jikaze :str = None             # jikaze jifu (自风)
        self.kyoku:int = None               # Kyoku (局)
        self.honba:int = None               # Honba (本場)
        self.my_tehai:list = None           # list of tehai in mjai format
        self.my_tsumohai:str = None         # tsumohai in mjai format, or None
        self.doras_ms:list[str] = []        # list of doras in ms tile format

        ### flags
        self.pending_reach_acc:dict = None  # Pending MJAI reach accepted message
        self.first_round:bool = True        # flag marking if it is the first move in new round
        self.self_in_reach:bool = False     # if self is in reach state
        self.player_reach:list = [False]*4  # list of player reach states

class GameState:
    """ Stores Majsoul game state and processes inputs outputs to/from Bot"""

    def __init__(self, bot:Bot) -> None:
        """ 
        params:
            bot (Bot): Bot implemetation"""

        self.mjai_bot:Bot = bot         # mjai bot for generating reactions
        if self.mjai_bot is None:
            raise ValueError("Bot is None")
        self.mjai_pending_input_msgs = []   # input msgs to be fed into bot
        self.game_mode:GameMode = None      # Game mode
        
        ### Game info
        self.account_id = 0                     # Majsoul account id
        self.mode_id:int = -1                   # game mode        
        self.seat = 0                           # seat index
        #seat 0 is chiicha (起家; first dealer; first East)
        #1-2-3 then goes counter-clockwise        
        self.player_scores:list = None          # player scores        
        self.kyoku_state:KyokuState = KyokuState()  # kyoku info - cleared every newround        
        
        ### about last reaction
        self.last_reaction:dict = None          # last bot output reaction
        self.last_reaction_pending:bool = True  # reaction pending until there is new liqi msg indicating the reaction is done/expired
        self.last_reaction_time:float = None    # last bot reaction calculation time
        self.last_operation:dict = None         # liqi msg 'operation' element
        self.last_op_step:int = None            # liqi msg 'step' element
        
        ### Internal Status flags        
        self.is_bot_calculating:bool = False    # if bot is calculating reaction
        self.is_ms_syncing:bool = False         # if mjai_bot is running syncing from MS (after disconnection)
        self.is_round_started:bool = False
        """ if any new round has started (so game info is available)"""
        self.is_game_ended:bool = False         # if game has ended    
             
    def get_game_info(self) -> GameInfo:
        """ Return game info. Return None if N/A"""        
        if self.is_round_started:
            gi = GameInfo(
                bakaze = self.kyoku_state.bakaze,
                jikaze = self.kyoku_state.jikaze,
                kyoku = self.kyoku_state.kyoku,
                honba = self.kyoku_state.honba,
                my_tehai = self.kyoku_state.my_tehai,
                my_tsumohai = self.kyoku_state.my_tsumohai,
                self_reached = self.kyoku_state.self_in_reach,
                self_seat = self.seat,
                player_reached = self.kyoku_state.player_reach.copy(),
                is_first_round = self.kyoku_state.first_round,                
            )
            return gi
        else:   # if game not started: None
            return None
    
    # def _update_info_from_bot(self):
    #     if self.is_round_started:
    #         self.my_tehai, self.my_tsumohai = self.mjai_bot.get_hand_info()
            
    def get_pending_reaction(self) -> dict:
        """ Return the last pending reaction (not acted on)
        returns:
            dict | None: mjai action, or None if no pending reaction"""
        if self.is_ms_syncing:
            return None
        if self.last_reaction_pending:
            return self.last_reaction
        else:
            return None    
        
    def input(self, liqi_msg: dict) -> dict | None:
        """ Input Majsoul liqi msg for processing and return result MJAI msg if any. 
        
        params:
            liqi_msg(dict): parsed Majsoul message in liqi dict format
        returns:
            dict: Mjai message in dict format (i.e. AI's reaction) if any. May be None.
        """
        self.is_bot_calculating = True
        start_time = time.time()
        reaction = self._input_inner(liqi_msg)
        time_used = time.time() - start_time
        if reaction is not None:
            # Update last_reaction (not none) and set it to pending
            self.last_reaction = reaction
            self.last_reaction_pending = True
            self.last_reaction_time = time_used
        self.is_bot_calculating = False
        return reaction
    
    def _input_inner(self, liqi_msg: dict) -> dict | None:        
        liqi_type = liqi_msg['type']
        liqi_method = liqi_msg['method']
        liqi_data = liqi_msg['data']
        
        # SyncGame
        if (liqi_method == LiqiMethod.syncGame or liqi_method == LiqiMethod.enterGame) and liqi_type == MsgType.RES:
            # syncGame: disconnect and reconnect
            # enterGame: enter game late, while others have started
            return self.ms_sync_game(liqi_data)
        
        # finish syncing
        if liqi_method == LiqiMethod.finishSyncGame:
            self.is_ms_syncing = False
            return None
                
        # All players are ready
        elif liqi_method == LiqiMethod.fetchGamePlayerState:
            if liqi_type == MsgType.RES:
                # seems it's always all ready: 'data': {'stateList': ['READY', 'READY', 'READY', 'READY']}
                return None
        
        # Game Start
        elif liqi_method == LiqiMethod.authGame:
            if liqi_type == MsgType.REQ:
                # request entering game. account id for seat index
                self.account_id = liqi_data['accountId']
                return None
            elif liqi_type == MsgType.RES:
                # response with game info (first entering game)
                return self.ms_auth_game(liqi_data)
            else:
                raise RuntimeError(f'Unexpected liqi message, method={liqi_method}, type={liqi_type}')
        
        # Actions
        elif liqi_method == LiqiMethod.ActionPrototype: # assert all ActionPrototype are notify type
            # We assume here, when there is new action, last reaction has done/expired
            self.last_reaction_pending = False
            
            # record operation and step no. for later use (automation).
            # newround is step 1 for Game start (where MJStart is step 0), and step 0 for other rounds?
            if 'step' in liqi_data:
                self.last_op_step = liqi_data['step']
            if 'data' in liqi_data:
                if 'operation' in liqi_data['data']:
                    self.last_operation = liqi_data['data']['operation']
                    if liqi_data['data']['operation']['seat'] != self.seat:
                        LOGGER.warning("operation seat %s != self.seat %s", liqi_data['data']['operation']['seat'], self.seat)
                    if 'operationList' not in liqi_data['data']['operation']:
                        LOGGER.warning("No operation List: %s", liqi_data['data']['operation'])
            else:
                LOGGER.warning("No data in liqi_data: %s", liqi_data)
            
            if liqi_data['name'] == LiqiAction.NewRound:
                self.kyoku_state.first_round = True
                return self.ms_new_round(liqi_data)
            
            else:   # other rounds                             
                self.kyoku_state.first_round = False        # not first round       
                return self.ms_action_prototype(liqi_data) 
        
        # end_game
        elif liqi_method == LiqiMethod.NotifyGameEndResult:
            return self.ms_game_end_results(liqi_data)
        
        # Game terminate
        elif liqi_method == LiqiMethod.NotifyGameTerminate:
            self.is_game_ended = True
            return None
        
        # message to ignore
        elif liqi_method in NO_EFFECT_METHODS:
            return None
        
        # unexpected message
        else:
            LOGGER.warning('Other liqi msg (ignored): %s', liqi_msg)
            return None        
        
    
    def ms_sync_game(self, liqi_data:dict) -> dict:
        """ Sync Game
        Every game start there is sync message (may contain no data)"""
        self.is_ms_syncing = True
        LOGGER.debug('Start syncing game')
        sync_msgs = LiqiProto().parse_syncGame(liqi_data)
        reacts = []
        for msg in sync_msgs:
            LOGGER.debug("sync msg: %s", msg)
            react = self.input(msg)
            reacts.append(react)
        LOGGER.debug('Finished syncing game')
        self.is_ms_syncing = False
        if reacts:
            return reacts[-1]
        else:
            return None
    
    def ms_auth_game(self, liqi_data:dict) -> dict:
        """ Game start, initial info"""
        try:
            self.mode_id = liqi_data['gameConfig']['meta']['modeId']
        except Exception:
            LOGGER.warning("No modeId in liqi_data['gameConfig']['meta']['modeId']")
            self.mode_id = -1

        seatList:list = liqi_data['seatList']
        if not seatList:
            LOGGER.debug("No seatList in liqi_data, game has likely ended")
            self.is_game_ended = True
            return None
        if len(seatList) == 4:
            self.game_mode = GameMode.MJ4P            
        elif len(seatList) == 3:
            self.game_mode = GameMode.MJ3P
        else:
            raise RuntimeError(f"Unexpected seat len:{len(seatList)}")
        LOGGER.info("Game Mode: %s", self.game_mode.name)
        
        self.seat = seatList.index(self.account_id)
        self.mjai_bot.init_bot(self.seat, self.game_mode)
        # Start_game has no effect for mjai bot, omit here
        self.mjai_pending_input_msgs.append(
            {
                'type': MjaiType.START_GAME,
                'id': self.seat
            }
        )        
        self._react_all()
        return None     # no reaction for start_game     
    
    def ms_new_round(self, liqi_data:dict) -> dict:
        """ Start kyoku """
        self.kyoku_state = KyokuState()
        self.mjai_pending_input_msgs = []

        liqi_data_data = liqi_data['data']
        self.kyoku_state.bakaze = MJAI_WINDS[liqi_data_data['chang']]
        dora_marker = mj_helper.cvt_ms2mjai(liqi_data_data['doras'][0])
        self.kyoku_state.doras_ms = [dora_marker]
        self.kyoku_state.honba = liqi_data_data['ben']
        oya = liqi_data_data['ju']           # oya is also the seat id of East
        self.kyoku_state.kyoku = oya + 1
        self.kyoku_state.jikaze  = MJAI_WINDS[(self.seat - oya)]
        kyotaku = liqi_data_data['liqibang']
        self.player_scores = liqi_data_data['scores']
        if self.game_mode in [GameMode.MJ3P]:
            self.player_scores = self.player_scores + [0]
        tehais_mjai = [['?']*13]*4        
        my_tehai_ms = liqi_data_data['tiles']
        self.kyoku_state.my_tehai = [mj_helper.cvt_ms2mjai(tile) for tile in my_tehai_ms]
        self.kyoku_state.my_tehai = mj_helper.sort_mjai_tiles(self.kyoku_state.my_tehai)
        
        # For starting hand, if player is East, majsoul gives 14 tiles + no tsumohai
        # mjai accepts 13 tiles + following tsumohai event
        # In Majsoul, last one of sorted tiles is the tsumohai
        if len(self.kyoku_state.my_tehai) == 14:        # self is East
            assert self.seat == oya
            self.kyoku_state.my_tsumohai = self.kyoku_state.my_tehai[-1]
            self.kyoku_state.my_tehai.pop()
            tehais_mjai[self.seat] = self.kyoku_state.my_tehai     # take first 13 tiles

            tsumo_msg = {
                'type': MjaiType.TSUMO,
                'actor': self.seat,
                'pai': self.kyoku_state.my_tsumohai
                }
            
        elif len(self.kyoku_state.my_tehai) == 13:      # self not East
            tehais_mjai[self.seat] = self.kyoku_state.my_tehai
            tsumo_msg = {
                'type': MjaiType.TSUMO,
                'actor': oya,
                'pai': '?'
                }
        else:
            raise RuntimeError(f"Unexpected tehai tiles: {len(my_tehai_ms)=}")
        
        # append messages and react
        start_kyoku_msg = {
            'type': MjaiType.START_KYOKU,
            'bakaze': self.kyoku_state.bakaze,
            'dora_marker': dora_marker,
            'honba': self.kyoku_state.honba,
            'kyoku': self.kyoku_state.kyoku,
            'kyotaku': kyotaku,
            'oya': oya,
            'scores': self.player_scores,
            'tehais': tehais_mjai
            }
        self.mjai_pending_input_msgs.append(start_kyoku_msg)
        if tsumo_msg:
            self.mjai_pending_input_msgs.append(tsumo_msg)
        
        self.is_round_started = True
        return self._react_all(liqi_data_data)
    
    def ms_action_prototype(self, liqi_data:dict) -> dict:
        """ process actionPrototype msg, generate mjai msg and have mjai react to it"""        
        liqi_data_name = liqi_data['name']
        # when there is new action, accept reach, unless it is agari
        if not liqi_data_name == LiqiAction.Hule:
            if self.kyoku_state.pending_reach_acc is not None:
                self.mjai_pending_input_msgs.append(self.kyoku_state.pending_reach_acc)
                self.kyoku_state.pending_reach_acc = None
        
        liqi_data_data = liqi_data['data']
        if 'data' in liqi_data:
            # Process dora events
            # According to mjai.app, in the case of an ankan, the dora event comes first, followed by the tsumo event.
            if 'doras' in liqi_data_data:
                if len(liqi_data_data['doras']) > len(self.kyoku_state.doras_ms):
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MjaiType.DORA,
                            'dora_marker': mj_helper.cvt_ms2mjai(liqi_data_data['doras'][-1])
                        }
                    )
                    self.kyoku_state.doras_ms = liqi_data_data['doras']        
        
        # LiqiAction.DealTile -> MJAI_TYPE.TSUMO
        if liqi_data_name == LiqiAction.DealTile:
            actor = liqi_data_data['seat']
            if liqi_data_data['tile'] == '':     # other player's tsumo
                tile_mjai = '?'
            else:           # my tsumo
                tile_mjai = mj_helper.cvt_ms2mjai(liqi_data_data['tile'])
                self.kyoku_state.my_tsumohai = tile_mjai
            self.mjai_pending_input_msgs.append(
                {
                    'type': MjaiType.TSUMO,
                    'actor': actor,
                    'pai': tile_mjai
                }
            )
            return self._react_all(liqi_data_data)
        
        # LiqiAction.DiscardTile -> MJAI_TYPE.DAHAI
        elif liqi_data_name == LiqiAction.DiscardTile:
            actor = liqi_data_data['seat']
            tile_mjai = mj_helper.cvt_ms2mjai(liqi_data_data['tile'])
            tsumogiri = liqi_data_data['moqie']
            if actor == self.seat:  # update self hand info
                if self.kyoku_state.my_tsumohai:                
                    self.kyoku_state.my_tehai.append(self.kyoku_state.my_tsumohai)
                    self.kyoku_state.my_tsumohai = None
                self.kyoku_state.my_tehai.remove(tile_mjai)
                self.kyoku_state.my_tehai = mj_helper.sort_mjai_tiles(self.kyoku_state.my_tehai)            
            
            if liqi_data_data['isLiqi']:     # Player declares reach
                if liqi_data_data['seat'] == self.seat:  # self reach
                    self.kyoku_state.self_in_reach = True                    
                
                self.kyoku_state.player_reach[actor] = True
                self.mjai_pending_input_msgs.append(
                    {
                        'type': MjaiType.REACH,
                        'actor': actor
                    }
                )
                # pending reach accept msg for mjai. this msg will be sent when next liqi action msg is received
                self.kyoku_state.pending_reach_acc = {
                    'type': MjaiType.REACH_ACCEPTED,
                    'actor': actor
                    }
                    
            self.mjai_pending_input_msgs.append(
                {
                    'type': MjaiType.DAHAI,
                    'actor': actor,
                    'pai': tile_mjai,
                    'tsumogiri': tsumogiri
                }
            )
                
            return self._react_all(liqi_data_data)        
        
        # LiqiAction.ChiPengGang -> MJAI CHI/PON/DAIMINKAN
        elif liqi_data_name == LiqiAction.ChiPengGang:
            actor = liqi_data_data['seat']
            target = actor
            consumed_mjai = []
            tile_mjai = ''
            for idx, fr in enumerate(liqi_data_data['froms']):
                if fr != actor:
                    target = fr
                    tile_mjai = mj_helper.cvt_ms2mjai(liqi_data_data['tiles'][idx])
                else:
                    consumed_mjai.append(mj_helper.cvt_ms2mjai(liqi_data_data['tiles'][idx]))
            if actor == self.seat:  # update my hand info
                for c in consumed_mjai:
                    self.kyoku_state.my_tehai.remove(c)                
                self.kyoku_state.my_tehai = mj_helper.sort_mjai_tiles(self.kyoku_state.my_tehai)
                
            assert target != actor
            assert len(consumed_mjai) != 0
            assert tile_mjai != ''
            match liqi_data_data['type']:
                case ChiPengGang.Chi:
                    assert len(consumed_mjai) == 2
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MjaiType.CHI,
                            'actor': actor,
                            'target': target,
                            'pai': tile_mjai,
                            'consumed': consumed_mjai
                        }
                    )
                case ChiPengGang.Peng:
                    assert len(consumed_mjai) == 2
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MjaiType.PON,
                            'actor': actor,
                            'target': target,
                            'pai': tile_mjai,
                            'consumed': consumed_mjai
                        }
                    )
                case ChiPengGang.Gang:
                    assert len(consumed_mjai) == 3
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MjaiType.DAIMINKAN,
                            'actor': actor,
                            'target': target,
                            'pai': tile_mjai,
                            'consumed': consumed_mjai
                        }
                    )
                case _:
                    raise ValueError(f"Unknown ChiPengGang type {liqi_data_data['type']}")
            return self._react_all(liqi_data_data)
                    
        # LiqiAction.AnGangAddGang -> MJAI ANKAN / KAKAN
        elif liqi_data_name == LiqiAction.AnGangAddGang:
            actor = liqi_data_data['seat']
            match liqi_data_data['type']:
                case MSGangType.AnGang:
                    tile_mjai = mj_helper.cvt_ms2mjai(liqi_data_data['tiles'])
                    consumed_mjai = [tile_mjai.replace("r", "")]*4
                    if tile_mjai[0] == '5' and tile_mjai[1] != 'z':
                        consumed_mjai[0] += 'r'
                    
                    if actor == self.seat:      # update hand info. ankan is after tsumo, so there is tsumohai
                        self.kyoku_state.my_tehai.append(self.kyoku_state.my_tsumohai)
                        self.kyoku_state.my_tsumohai = None
                        for c in consumed_mjai:
                            self.kyoku_state.my_tehai.remove(c)
                        self.kyoku_state.my_tehai = mj_helper.sort_mjai_tiles(self.kyoku_state.my_tehai)                        

                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MjaiType.ANKAN,
                            'actor': actor,
                            'consumed': consumed_mjai
                        }
                    )
                case MSGangType.AddGang:
                    tile_mjai = mj_helper.cvt_ms2mjai(liqi_data_data['tiles'])
                    consumed_mjai = [tile_mjai.replace("r", "")] * 3
                    if tile_mjai[0] == "5" and not tile_mjai.endswith("r"):
                        consumed_mjai[0] = consumed_mjai[0] + "r"
                    
                    if actor == self.seat:      # update hand info. kakan is after tsumo, so there is tsumohai
                        self.kyoku_state.my_tehai.append(self.kyoku_state.my_tsumohai)
                        self.kyoku_state.my_tsumohai = None
                        self.kyoku_state.my_tehai.remove(tile_mjai)
                        self.kyoku_state.my_tehai = mj_helper.sort_mjai_tiles(self.kyoku_state.my_tehai)
                        
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MjaiType.KAKAN,
                            'actor': actor,
                            'pai': tile_mjai,
                            'consumed': consumed_mjai
                        }
                    )
            return self._react_all(liqi_data_data)
        
        # (3p Mahjong only) LiqiAction.BaBei -> MJAI NUKIDORA
        elif liqi_data_name == LiqiAction.BaBei:
            actor = liqi_data_data['seat']
            if actor == self.seat:      # update hand info. babei is after tsumo, so there is tsumohai
                self.kyoku_state.my_tehai.append(self.kyoku_state.my_tsumohai)
                self.kyoku_state.my_tsumohai = None
                self.kyoku_state.my_tehai.remove('N')
                self.kyoku_state.my_tehai = mj_helper.sort_mjai_tiles(self.kyoku_state.my_tehai)
            
            self.mjai_pending_input_msgs.append(
                {
                    'type': MjaiType.NUKIDORA,
                    'actor': actor,
                    'pai': 'N'
                }
            )
            return self._react_all(liqi_data_data)
        
        # LiqiAction.Hule -> MJAI END_KYOKU
        elif liqi_data_name in LiqiAction.Hule:
            return self.ms_end_kyoku()

        # LiqiAction.NoTile -> MJAI END_KYOKU
        elif liqi_data_name == LiqiAction.NoTile:
            return self.ms_end_kyoku()

        # LiqiAction.LiuJu -> MJAI END_KYOKU
        elif liqi_data_name == LiqiAction.LiuJu:
            return self.ms_end_kyoku()

        # LiqiAction.MJStart: once at new game start 
        elif liqi_data_name == LiqiAction.MJStart:
            # no effect. {'name': 'ActionMJStart', 'step': 0, 'data': {}}
            return None
        
        else:
            LOGGER.warning('Unknown liqi_data name %s', liqi_data_name)
            return None
        
    def ms_end_kyoku(self) -> dict | None:
        """ End kyoku and get None as reaction"""
        self.mjai_pending_input_msgs = []
        # self.mjai_pending_input_msgs.append(
        #     {
        #         'type': MJAI_TYPE.END_KYOKU
        #     }
        # )
        # self._react_all()
        return None     # no reaction for end_kyoku
    
        
    def ms_game_end_results(self, liqi_data:dict) -> dict:
        """ End game in normal way (getting results)"""
        if 'result' in liqi_data:
            # process end result
            pass
        
        # self.mjai_pending_input_msgs.append(
        #     {
        #         'type': MJAI_TYPE.END_GAME
        #     }
        # )
        # self._react_all()
        self.is_game_ended = True
        return None     # no reaction for end_game
    
    def ms_template(self, liqi_data:dict) -> dict:
        """ template"""
            
    def _react_all(self, data=None) -> dict | None:
        """ Feed all pending messages to AI bot and get bot reaction
        ref: https://mjai.app/docs/mjai-protocol
        Params:
            data (dict): liqimsg['data'] / ['data']['data'] 
        returns:
            dict: the last reaction(output) from bot, or None
        """
        if data: 
            if 'operation' not in data or 'operationList' not in data['operation'] or len(data['operation']['operationList']) == 0:
                return None
        try:
            if len(self.mjai_pending_input_msgs) == 1:
                LOGGER.info("Bot in: %s", self.mjai_pending_input_msgs[0])
                output_reaction = self.mjai_bot.react(self.mjai_pending_input_msgs[0])
            else:
                LOGGER.info("Bot in (batch):\n%s", '\n'.join(str(m) for m in self.mjai_pending_input_msgs))
                output_reaction = self.mjai_bot.react_batch(self.mjai_pending_input_msgs)
        except Exception as e:
            LOGGER.error("Bot react error: %s", e, exc_info=True)
            output_reaction = None
        self.mjai_pending_input_msgs = [] # clear intput queue
        
        if output_reaction is None:
            return None
        else:
            LOGGER.info("Bot out: %s", output_reaction)
            if self.game_mode == GameMode.MJ3P:
                is_3p = True
            else:
                is_3p = False
                
            reaction_convert_meta(output_reaction,is_3p)
            return output_reaction
