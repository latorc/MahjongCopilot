try:
    from .libriichi import *

    __doc__ = libriichi.__doc__
    if hasattr(libriichi, "__all__"):
        __all__ = libriichi.__all__
except Exception as e:
    from .riichi import *

    __doc__ = riichi.__doc__
    if hasattr(riichi, "__all__"):
        __all__ = riichi.__all__
"""
Submodule: arena
Module: libriichi.libriichi.arena
    Class: OneVsThree
    : ako_vs_py
        Docstring: Returns the rankings of the challenger (akochan in this case).
    : py_vs_ako
        Docstring: Returns the rankings of the challenger (python agent in this case).
    : py_vs_py
        Docstring: Returns the rankings of the challenger.
    Class: TwoVsTwo
    : ako_vs_py
    : py_vs_ako
    : py_vs_ako_one
    : py_vs_py
    
Submodule: consts
Module: libriichi.libriichi.consts
    Variable: ACTION_SPACE
    Variable: GRP_SIZE
    Variable: MAX_VERSION
    Variable: obs_shape
    Variable: oracle_obs_shape
    
Submodule: dataset
Module: libriichi.libriichi.dataset
    Class: Gameplay
    : take_actions
    : take_apply_gamma
    : take_at_kyoku
    : take_at_turns
    : take_dones
    : take_grp
    : take_invisible_obs
    : take_masks
    : take_obs
    : take_player_id
    : take_shantens
    Class: GameplayLoader
    : always_include_kan_select
    : augmented
    : excludes
    : load_gz_log_files
    : load_log
    : oracle
    : player_names
    : trust_seed
    : version
    Class: Grp
    : load_gz_log_files
    : load_log
    : take_feature
        Docstring: Returns List[List[np.ndarray]]
    : take_final_scores
    : take_rank_by_player
    
Submodule: mjai
Module: libriichi.libriichi.mjai
    Class: Bot
    : react
        Docstring: Returns the reaction to `line`, if it can react, `None` otherwise.

            Set `can_act` or `line_json['can_act']` to `False` to force the bot to
            only update its state without making any reaction.

            Both `line` and the return value are JSON strings representing one
            single mjai event.
            
Submodule: stat
Module: libriichi.libriichi.stat
    Class: Stat
    Docstring: Notes:

    - All the Δscore about riichi do not cover the 1000 kyotaku of its
    sengenhai, but do cover all other kyotakus.
    - Deal-in After Riichi is recognized at the moment the sengenhai is
    discarded.
    - Every other Δscore cover kyotakus.
    - Ankan is not recognized as fuuro.
    : agari
    : agari_as_oya
    : agari_as_oya_rate
    : agari_jun
    : agari_point_ko
    : agari_point_oya
    : agari_rate
    : agari_rate_after_fuuro
    : agari_rate_after_riichi
    : agari_rate_as_oya
    : avg_agari_jun
    : avg_dama_agari_jun
    : avg_fuuro_agari_jun
    : avg_fuuro_num
    : avg_fuuro_point
    : avg_houjuu_jun
    : avg_point_per_agari
    : avg_point_per_dama_agari
    : avg_point_per_fuuro_agari
    : avg_point_per_game
    : avg_point_per_houjuu
    : avg_point_per_houjuu_to_ko
    : avg_point_per_houjuu_to_oya
    : avg_point_per_ko_agari
    : avg_point_per_oya_agari
    : avg_point_per_riichi_agari
    : avg_point_per_round
    : avg_point_per_ryukyoku
    : avg_pt
    : avg_rank
    : avg_riichi_agari_jun
    : avg_riichi_jun
    : avg_riichi_point
    : chasing_riichi
    : chasing_riichi_rate
    : dama_agari
    : dama_agari_jun
    : dama_agari_point
    : from_dir
    : from_log
    : fuuro
    : fuuro_agari
    : fuuro_agari_jun
    : fuuro_agari_point
    : fuuro_houjuu
    : fuuro_num
    : fuuro_point
    : fuuro_rate
    : game
    : houjuu
    : houjuu_jun
    : houjuu_point_to_ko
    : houjuu_point_to_oya
    : houjuu_rate
    : houjuu_rate_after_fuuro
    : houjuu_rate_after_riichi
    : houjuu_to_oya
    : houjuu_to_oya_rate
    : nagashi_mangan
    : nagashi_mangan_rate
    : oya
    : point
    : rank_1
    : rank_1_rate
    : rank_2
    : rank_2_rate
    : rank_3
    : rank_3_rate
    : rank_4
    : rank_4_rate
    : riichi
    : riichi_agari
    : riichi_agari_jun
    : riichi_agari_point
    : riichi_as_oya
    : riichi_chased_rate
    : riichi_got_chased
    : riichi_houjuu
    : riichi_jun
    : riichi_point
    : riichi_rate
    : riichi_ryukyoku
    : round
    : ryukyoku
    : ryukyoku_point
    : ryukyoku_rate
    : tobi
    : tobi_rate
    : total_pt
    : yakuman
    : yakuman_rate
    
Submodule: state
Module: libriichi.libriichi.state
    Class: ActionCandidate
    : can_act
    : can_agari
    : can_ankan
    : can_chi
    : can_chi_high
    : can_chi_low
    : can_chi_mid
    : can_daiminkan
    : can_discard
    : can_kakan
    : can_kan
    : can_pass
    : can_pon
    : can_riichi
    : can_ron_agari
    : can_ryukyoku
    : can_tsumo_agari
    : target_actor
    Class: PlayerState
    Docstring: `PlayerState` is the core of the lib, which holds all the observable game
        state information from a specific seat's perspective with the ability to
        identify the legal actions the specified player can make upon an incoming
        mjai event, along with some helper functions to build an actual agent.
        Notably, `PlayerState` encodes observation features into numpy arrays which
        serve as inputs for deep learning model.
    : akas_in_hand
    : ankan_candidates
    : ankans
    : at_furiten
    : at_turn
    : brief_info
        Docstring: For debug only.

        Return a human readable description of the current state.
    : can_w_riichi
    : chis
    : encode_obs
        Docstring: Returns `(obs, mask)`
    : honba
    : is_oya
    : kakan_candidates
    : kyoku
    : kyotaku
    : last_cans
    : last_kawa_tile
    : last_self_tsumo
    : minkans
    : player_id
    : pons
    : self_riichi_accepted
    : self_riichi_declared
    : shanten
    : tehai
    : update
        Docstring: Returns an `ActionCandidate`.
    : validate_reaction
        Docstring: Raises an exception if the action is not valid.
    : waits
"""