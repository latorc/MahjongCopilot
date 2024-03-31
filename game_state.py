import json
from liqi import MsgType
from liqi import LiqiProto, LiqiMethod, LiqiAction


import libriichi
import mj_helper
from mj_helper import MJAI_TYPE, GameInfo
from mjai.engine import MortalEngine
from log_helper import LOGGER


class ChiPengGang:
    """ majsoul action types"""
    Chi = 0         # chi
    Peng = 1        # pon
    Gang = 2        # kan

class MSGangType:
    """ majsoul kan types"""
    AnGang = 3      # ankan
    AddGang = 2     # kakan/daminkan

WINDS = ['E', 'S', 'W', 'N']

class GameState:
    """ Stores Majsoul game state and processes inputs and outputs"""
    
    no_effact_methods = [
        '.lq.NotifyPlayerLoadGameReady',        # Notify: the game starts
        '.lq.FastTest.checkNetworkDelay',       # REQ/RES: Check network delay
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
        '.lq.NotifyGameBroadcast',              # Notify: emoji? {'id': -1, 'type': <MsgType.Notify: 1>, 'method': '.lq.NotifyGameBroadcast', 'data': {'seat': 2, 'content': '{"emo":7}'}}
        '.lq.NotifyPlayerConnectionState',      # 
    ]
    
    def __init__(self, engine:MortalEngine) -> None:
        """ 
        params:
            engine(MortalEngine): Mortal engine object"""
        self.mjai_bot:libriichi.mjai.Bot = None
        self.engine = engine
        
        self.mjai_pending_input_msgs = []
        self.pending_reach_acc:dict = None  # Pending MJAI reach accepted message        
        
        #### Game Info
        self.bakaze:str = None              # Bakaze (場風)
        self.self_wind:str = None           # jifu (自风)
        self.kyoku:int = None               # Kyoku (局)
        self.honba:int = None               # Honba (本場)
        self.my_tehais:list[str] = None     # tehai(hand) in mjai format
        self.my_tsumohai:str = None         # tsumohai(new draw) in mjai format        
        self.first_round:bool = False       # flag marking if it is the first move in new round
        self.reached:bool = False           # if self is in reach state
        
        self.accountId = 0
        """ Majsoul account id"""
        
        self.seat = 0                       
        """ seat index. seat 0 is chiicha (起家; first dealer; first East)
        1-2-3 then goes counter-clockwise"""
        
        self.AllReady = False
        self.doras:list[str] = []           # list of doras in ms tile format

        self.mode_id = -1                   # to be used
        self.rank = -1                      # to be used
        self.score = -1                     # to be used
        
        #### about last reaction
        self.last_reaction:dict = None
        self.last_reaction_pending:bool = True  # not executed
        self.last_operation:dict = None
        self.last_op_step:int = None
        
        #### Internal Status flags
        self.is_mjai_error:bool = False         # if the mjai bot has encountered errors (and possibly crashed)
        self.is_ms_syncing:bool = False         # if mjai_bot is running syncing from MS (after disconnection)
        self.is_round_started:bool = False      # if any new round has started (so game info is available)
        self.is_game_ended:bool = False         # if game has ended
    
    def _update_game_info(self):
        # update state info from mjai bot. only call this when bot is not running reactions.
        # otherwise it may cause rust runtime error (mutable borrow)
        if self.mjai_bot is None:
            return None
        
        # tehai = self.mjai_bot.get_tehai()
        # aka_doras = self.mjai_bot.get_akas_in_hand()
        # tsumohai = self.mjai_bot.get_tsumohai()
        
        state = self.mjai_bot.state
        tehai = state.tehai # with tsumohai, no aka marked
        aka_doras = state.akas_in_hand
        tsumohai = state.last_self_tsumo()
        # state = self.mjai_bot.state
        # # bakaze = state.bakaze       # Bakaze (場風)
        # # jikaze = state.jikaze       # Jikaze (自風)
        # kyoku = state.kyoku
        # honba = state.honba         # Honba (本場)
        # kyotaku = state.kyotaku     # Kyotaku (供託)
        """
        pub(super) bakaze: Tile,
        pub(super) jikaze: Tile,
        /// Counts from 0 unlike mjai.
        pub(super) kyoku: u8,
        pub(super) honba: u8,
        pub(super) kyotaku: u8,"""
        
        self.my_tehais, self.my_tsumohai = mj_helper.decode_mjai_tehai(tehai, aka_doras, tsumohai)
        self.my_tehais = [t for t in self.my_tehais if t != '?']
        
    def get_game_info(self) -> GameInfo:
        """ Return game info. Return None if N/A"""        
        if self.is_round_started:
            gi = GameInfo()
            gi.bakaze = self.bakaze
            gi.self_wind = self.self_wind
            gi.kyoku = self.kyoku
            gi.honba = self.honba
            gi.my_tehai = self.my_tehais
            gi.my_tsumohai = self.my_tsumohai
            gi.reached = self.reached
            return gi
        else:   # if game not started: None
            return None


            
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
        reaction = self.input_inner(liqi_msg)
        self._update_game_info()    # update game info (tehai tsumohai) after input        
        if reaction is not None:
            # Update last_reaction (not none) and set it to pending
            self.last_reaction = reaction
            self.last_reaction_pending = True
        return reaction
    
    def input_inner(self, liqi_msg: dict) -> dict | None:
        
        liqi_type = liqi_msg['type']
        liqi_method = liqi_msg['method']
        liqi_data = liqi_msg['data']
        
        # TODO: clear last_reaction_pending flag after reaction is acted on/expired
        
        # SyncGame
        if liqi_method == LiqiMethod.syncGame or liqi_method == LiqiMethod.enterGame:
            # syncGame: disconnect and reconnect
            # enterGame: enter game late, while others have started
            return self.ms_sync_game(liqi_data)
        
        # finish syncing
        if liqi_method == LiqiMethod.finishSyncGame:
            self.is_ms_syncing = False
            return None
                
        # All players are ready
        elif liqi_method == LiqiMethod.fetchGamePlayerState:
            if liqi_type == MsgType.Res:
                # liqi_data['stateList'] should be ['READY', 'READY', 'READY', 'READY']:
                self.AllReady = True
                return None
        
        # Game Start
        elif liqi_method == LiqiMethod.authGame:            
            if liqi_type == MsgType.Req:
                # request game info (first entering game)
                # self.__init__()
                self.accountId = liqi_data['accountId']
                return None            
            elif liqi_type == MsgType.Res:
                # response with game info (first entering game)
                return self.ms_auth_game(liqi_data)
            else:
                raise Exception('Unexpected liqi message, method=%s, type=%s', liqi_method, liqi_type)
        
        # Actions        
        elif liqi_method == LiqiMethod.ActionPrototype: 
            # start kyoku
            
            # We assume here, when there is new action, last reaction has done/expired
            self.last_reaction_pending = False
            # when there is new action, accept reach
            if self.pending_reach_acc is not None:
                self.mjai_pending_input_msgs.append(self.pending_reach_acc)
                self.pending_reach_acc = None
            
            # record operation and step no. for later use (automation).
            # newround is step 1 for Game start (where MJStart is step 0), and step 0 for other rounds?
            if 'data' in liqi_data:
                if 'operation' in liqi_data['data']:                    
                    self.last_operation = liqi_data['data']['operation']
                    self.last_op_step = liqi_data['step']       
                    if liqi_data['data']['operation']['seat'] != self.seat:
                        LOGGER.warning(f"liqi_data['data']['operation']['seat'] {liqi_data['data']['operation']['seat']} != self.seat{self.seat}")
                    if 'operationList' not in liqi_data['data']['operation']:
                        LOGGER.warning("No operation List: %s", liqi_data['data']['operation'])
                # else:
                #     self.last_operation = None
                #     self.last_op_step = None            
            
            if liqi_data['name'] == 'ActionNewRound':                
                return self.ms_new_round(liqi_data)
            else:
                if 'data' in liqi_data:
                    # Process dora events
                    # According to mjai.app, in the case of an ankan, the dora event comes first, followed by the tsumo event.
                    if 'doras' in liqi_data['data']:
                        if len(liqi_data['data']['doras']) > len(self.doras):
                            self.mjai_pending_input_msgs.append(
                                {
                                    'type': MJAI_TYPE.DORA,
                                    'dora_marker': mj_helper.cvt_ms2mjai(liqi_data['data']['doras'][-1])
                                }
                            )
                            self.doras = liqi_data['data']['doras']                
                self.first_round = False        
                return self.ms_action_prototype(liqi_data)
        
        # end_game
        elif liqi_method == LiqiMethod.NotifyGameEndResult:
            return self.ms_end_game(liqi_data)
        
        # Game terminate
        elif liqi_method == LiqiMethod.NotifyGameTerminate:
            self.is_game_ended = True
            return None
        
        # message to ignore
        elif liqi_method in self.no_effact_methods:
            return None
        
        # unexpected message
        else:
            LOGGER.warning('Other liqi messages (ignored): %s', liqi_msg)
            return None
        
        
    
    def ms_sync_game(self, liqi_data:dict) -> dict:
        """ Sync Game
        Every game start there is sync message (may contain no data)"""
        self.is_ms_syncing = True
        LOGGER.debug('Start syncing game')
        syncGame_msgs = LiqiProto().parse_syncGame(liqi_data)
        reacts = []
        for msg in syncGame_msgs:
            LOGGER.debug(f"sync msg: {msg}")
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
        except:
            self.mode_id = -1

        seatList = liqi_data['seatList']
        if not seatList:
            LOGGER.debug("No seatList in liqi_data, game has likely ended")
            self.is_game_ended = True
            return None
        self.seat = seatList.index(self.accountId)
        self.initialize_bot(self.seat)
        self.mjai_pending_input_msgs.append(
            {
                'type': MJAI_TYPE.START_GAME,
                'id': self.seat
            }
        )
        self._react_all()
        return None
    
    def ms_new_round(self, liqi_data:dict) -> dict:
        """ Start kyoku """
        self.AllReady = False
        self.reached = False
        self.first_round = True
        self.bakaze = WINDS[liqi_data['data']['chang']]
        dora_marker = mj_helper.cvt_ms2mjai(liqi_data['data']['doras'][0])
        self.doras = [dora_marker]
        self.honba = liqi_data['data']['ben']
        oya = liqi_data['data']['ju']
        self.kyoku = oya + 1
        self.self_wind = WINDS[(self.seat - oya)]
        kyotaku = liqi_data['data']['liqibang']
        scores = liqi_data['data']['scores']
        # if self.is_3p:
        #     scores = scores + [0]
        tehais_mjai = [['?']*13]*4        
        my_tehai_ms = liqi_data['data']['tiles']
        my_tehai_mjai = [mj_helper.cvt_ms2mjai(tile) for tile in my_tehai_ms]
        
        # For starting hand, majsoul gives 14 tiles if player is East
        # mjai accepts 13 tiles, followed by a tsumohai event
        # For Majsoul, last one in sorted tiles is the tsumohai
        my_tehai_mjai = mj_helper.sort_mjai_tiles(my_tehai_mjai)       
        if len(my_tehai_mjai) == 14:            
            tehais_mjai[self.seat] = my_tehai_mjai[:-1] 
            tsumohai = my_tehai_mjai[-1]                     
            tsumo_msg = {
                'type': MJAI_TYPE.TSUMO,
                'actor': self.seat,
                'pai': tsumohai
                }
            
        elif len(my_tehai_mjai) == 13:
            tehais_mjai[self.seat] = my_tehai_mjai
            tsumo_msg = None
        else:
            raise Exception("Unexpected tehai tiles:%d", len(my_tehai_ms))
        
        # append messages and react
        start_kyoku_msg = {
            'type': MJAI_TYPE.START_KYOKU,
            'bakaze': self.bakaze,
            'dora_marker': dora_marker,
            'honba': self.honba,
            'kyoku': self.kyoku,
            'kyotaku': kyotaku,
            'oya': oya,
            'scores': scores,
            'tehais': tehais_mjai
            }    
        self.mjai_pending_input_msgs.append(start_kyoku_msg)
        if tsumo_msg:
            self.mjai_pending_input_msgs.append(tsumo_msg)
        
        self.is_round_started = True
        return self._react_all()
    
    def ms_action_prototype(self, liqi_data:dict) -> dict:
        """ process actionPrototype msg, generate mjai msg and have mjai react to it"""        
        liqi_data_name = liqi_data['name']
        
        # LiqiAction.DealTile -> MJAI_TYPE.TSUMO
        if liqi_data_name == LiqiAction.DealTile:
            actor = liqi_data['data']['seat']
            if liqi_data['data']['tile'] == '':
                tile_mjai = '?'
            else:
                tile_mjai = mj_helper.cvt_ms2mjai(liqi_data['data']['tile'])
                self.my_tsumohai = tile_mjai
            self.mjai_pending_input_msgs.append(
                {
                    'type': MJAI_TYPE.TSUMO,
                    'actor': actor,
                    'pai': tile_mjai
                }
            )
            return self._react_all()
        
        # LiqiAction.DiscardTile -> MJAI_TYPE.DAHAI
        elif liqi_data_name == LiqiAction.DiscardTile:
            actor = liqi_data['data']['seat']
            tile_mjai = mj_helper.cvt_ms2mjai(liqi_data['data']['tile'])
            tsumogiri = liqi_data['data']['moqie']
            
            if liqi_data['data']['isLiqi']:     # Player declares riichi
                if liqi_data['data']['seat'] == self.seat:
                    # Self reach. reach msg already sent to mjai when getting reach dahai msg
                    # fix this together with reach sync issue
                    # no mjai msg sent here
                    self.reached = True
                else:   # Other player reach
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MJAI_TYPE.REACH,
                            'actor': actor
                        }
                    )
                # pending reach accept msg for mjai. this msg will be sent when next liqi action msg is received
                self.pending_reach_acc = {
                    'type': MJAI_TYPE.REACH_ACCEPTED,
                    'actor': actor
                    }
                    
            self.mjai_pending_input_msgs.append(
                {
                    'type': MJAI_TYPE.DAHAI,
                    'actor': actor,
                    'pai': tile_mjai,
                    'tsumogiri': tsumogiri
                }
            )
                
            return self._react_all()        
        
        # LiqiAction.ChiPengGang -> MJAI CHI/PON/DAIMINKAN
        elif liqi_data_name == LiqiAction.ChiPengGang:
            actor = liqi_data['data']['seat']
            target = actor
            consumed = []
            tile_mjai = ''
            for idx, seat in enumerate(liqi_data['data']['froms']):
                if seat != actor:
                    target = seat
                    tile_mjai = mj_helper.cvt_ms2mjai(liqi_data['data']['tiles'][idx])
                else:
                    consumed.append(mj_helper.cvt_ms2mjai(liqi_data['data']['tiles'][idx]))
            assert target != actor
            assert len(consumed) != 0
            assert tile_mjai != ''
            match liqi_data['data']['type']:
                case ChiPengGang.Chi:
                    assert len(consumed) == 2
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MJAI_TYPE.CHI,
                            'actor': actor,
                            'target': target,
                            'pai': tile_mjai,
                            'consumed': consumed
                        }
                    )
                    pass
                case ChiPengGang.Peng:
                    assert len(consumed) == 2
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MJAI_TYPE.PON,
                            'actor': actor,
                            'target': target,
                            'pai': tile_mjai,
                            'consumed': consumed
                        }
                    )
                case ChiPengGang.Gang:
                    assert len(consumed) == 3
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MJAI_TYPE.DAIMINKAN,
                            'actor': actor,
                            'target': target,
                            'pai': tile_mjai,
                            'consumed': consumed
                        }
                    )
                    pass
                case _:
                    raise
            return self._react_all()
                    
        # LiqiAction.AnGangAddGang -> MJAI ANKAN / KAKAN
        elif liqi_data_name == LiqiAction.AnGangAddGang:
            actor = liqi_data['data']['seat']
            match liqi_data['data']['type']:
                case MSGangType.AnGang:
                    tile_mjai = mj_helper.cvt_ms2mjai(liqi_data['data']['tiles'])
                    consumed = [tile_mjai.replace("r", "")]*4
                    if tile_mjai[0] == '5' and tile_mjai[1] != 'z':
                        consumed[0] += 'r'
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MJAI_TYPE.ANKAN,
                            'actor': actor,
                            'consumed': consumed
                        }
                    )
                case MSGangType.AddGang:
                    tile_mjai = mj_helper.cvt_ms2mjai(liqi_data['data']['tiles'])
                    consumed = [tile_mjai.replace("r", "")] * 3
                    if tile_mjai[0] == "5" and not tile_mjai.endswith("r"):
                        consumed[0] = consumed[0] + "r"
                    self.mjai_pending_input_msgs.append(
                        {
                            'type': MJAI_TYPE.KAKAN,
                            'actor': actor,
                            'pai': tile_mjai,
                            'consumed': consumed
                        }
                    )
            return self._react_all()
        
        # (3p Mahjong only) LiqiAction.BaBei -> MJAI NUKIDORA
        elif liqi_data_name == LiqiAction.BaBei:
            actor = liqi_data['data']['seat']
            self.mjai_pending_input_msgs.append(
                {
                    'type': MJAI_TYPE.NUKIDORA,
                    'actor': actor,
                    'pai': 'N'
                }
            )
            return self._react_all()
        
        # LiqiAction.Hule -> MJAI END_KYOKU
        elif liqi_data_name == LiqiAction.Hule:
            self.mjai_pending_input_msgs = []
            self.mjai_pending_input_msgs.append(
                {
                    'type': MJAI_TYPE.END_KYOKU
                }
            )
            return self._react_all()

        # LiqiAction.NoTile -> MJAI END_KYOKU
        elif liqi_data_name == LiqiAction.NoTile:
            self.mjai_pending_input_msgs = []
            self.mjai_pending_input_msgs.append(
                {
                    'type': MJAI_TYPE.END_KYOKU
                }
            )
            return self._react_all()

        # LiqiAction.LiuJu -> MJAI END_KYOKU
        elif liqi_data_name == LiqiAction.LiuJu:
            self.mjai_pending_input_msgs = []
            self.mjai_pending_input_msgs.append(
                {
                    'type': MJAI_TYPE.END_KYOKU
                }
            )
            return self._react_all()

        # LiqiAction.MJStart: once at new game start 
        elif liqi_data_name == LiqiAction.MJStart:
            # no effect. {'name': 'ActionMJStart', 'step': 0, 'data': {}}
            return None
        
        else:
            LOGGER.warning('Unknown liqi_data name %s', liqi_data_name)
            return None
    
        
    def ms_end_game(self, liqi_data:dict) -> dict:
        """ """
        try:
            if 'result' in liqi_data:
                for idx, player in enumerate(liqi_data['result']['players']):
                    if player['seat'] == self.seat:
                        self.rank = idx + 1
                        self.score = player['partPoint1']
                    # game_result_log(self.mode_id, self.rank, self.score, self.mjai_client.bot.model_hash)
        except:
            LOGGER.warning("Error getting game results. liqi_data=%s", liqi_data)
            pass
        self.mjai_pending_input_msgs.append(
            {
                'type': MJAI_TYPE.END_GAME
            }
        )
        self._react_all()
        self.delete_bot()
        self.is_game_ended = True
        # self.initialize_bot(self.seat)
        return None
    
    def ms_template(self, liqi_data:dict) -> dict:
        """ template"""
        pass    
    
    def initialize_bot(self, player_id:int):
        """ initialize the mjai bot"""
        self.mjai_bot = libriichi.mjai.Bot(self.engine, player_id)

        
    def delete_bot(self):
        del self.mjai_bot
        self.mjai_bot = None
            
    def _react_all(self) -> dict:
        """ Feed all pending messages to AI bot and get bot reaction
        ref: https://mjai.app/docs/mjai-protocol
        returns:
            dict: the last reaction(output) from bot, or None
        """
        output_reactions = []
        for msg in self.mjai_pending_input_msgs:
            str_input = json.dumps(msg) 
            #str(msg).replace("\'", "\"").replace("True", "true").replace("False", "false")
            LOGGER.debug("Bot in: %s", str_input)
            try:
                react_str = self.mjai_bot.react(str_input)
                reaction = self.json_str_2_reaction(react_str)
            except Exception as e:
                LOGGER.error("MJAI bot running error! %s", e, exc_info=True)
                self.is_mjai_error = True
                return None
            
            if reaction is not None: 
                # patch for reach            
                if reaction['type'] == MJAI_TYPE.REACH and reaction['actor'] == self.seat:  # Self reach
                    # get the subsequent dahai message (indicating discard tile/options after reach)
                    # reach reaction is modified, appeding the subsequent discard reaction as the 'reach_dahai' key
                    # bot_after_reach = copy.deepcopy(self.mjai_bot)
                    # TODO: reach failed/ skipped in Majsoul, need to sync status. Find a way to clone this mjai.bot
                    reach_msg = {'type': MJAI_TYPE.REACH, 'actor': self.seat}
                    reach_react_str =self.mjai_bot.react(json.dumps(reach_msg))                   
                    reaction['reach_dahai'] = self.json_str_2_reaction(reach_react_str)
                
                LOGGER.debug("Bot out: %s", reaction)
                output_reactions.append(reaction)
        
        self.mjai_pending_input_msgs = [] # clear intput queue       
        
        if not output_reactions:
            return None
        else:        
            if len(output_reactions) > 1:   # not expected: more than one not-none action
                LOGGER.error("More than one action: %s", output_reactions[0:-1]) 
            return output_reactions[-1]        # return the last reaction
        
    def json_str_2_reaction(self, json_str:str):
        """ convert json string to reaction"""
        if json_str is None:
            return None
        else:
            reaction = json.loads(json_str)
            meta = reaction['meta']
            reaction['meta_options'] = mj_helper.meta_to_options(meta)
            return reaction

