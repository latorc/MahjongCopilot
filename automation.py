from collections import namedtuple
import time
import random
import threading
from browser import GameBrowser
from game_state import GameInfo, GameState
import mj_helper
from mj_helper import MJAI_TYPE
from log_helper import LOGGER


class Positions:
    """ Screen coordinates constants. in 16 x 9 resolution"""
    TEHAI_X = [
        2.23125,    3.021875,   3.8125,     4.603125,   5.39375,    6.184375,   6.975,
        7.765625,   8.55625,    9.346875,   10.1375,    10.928125,  11.71875,   12.509375]
    TEHAI_Y = 8.3625
    TRUMO_SPACE = 0.246875
    BUTTONS = [
        (10.875, 7),        # 0 (None)
        (8.6375, 7),        # 1
        (6.4   , 7),        # 2
        (10.875, 5.9),      # 3
        (8.6375, 5.9),      # 4
        (6.4   , 5.9),      # 5
        (10.875, 4.8),      # Not used
        (8.6375, 4.8),      # Not used
        (6.4   , 4.8),      # Not used
    ]
    """ button layout:
    5   4   3
    2   1   0
    where action with higher priority takes lower position
    None is always at 0
    """

    CANDIDATES = [
        (3.6625,  6.3),         # 
        (4.49625, 6.3),
        (5.33 ,   6.3),
        (6.16375, 6.3),
        (6.9975,  6.3),
        (7.83125, 6.3),         # 5 mid
        (8.665,   6.3),
        (9.49875, 6.3),
        (10.3325, 6.3),
        (11.16625,6.3),
        (12,      6.3),
    ]
    """ chi/pon/daiminkan candidates (combinations) positions
    index = (-(len/2)+idx+0.5)*2+5 """
    
    CANDIDATES_KAN = [
        (4.325,   6.3),         #
        (5.4915,  6.3),
        (6.6583,  6.3),
        (7.825,   6.3),         # 3 mid
        (8.9917,  6.3),
        (10.1583, 6.3),
        (11.325,  6.3),
    ]
    """ kakan/ankan candidates (combinations) positions
    idx_kan = int((-(len/2)+idx+0.5)*2+3)"""
    
    
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
    

MJAI_2_MS_TYPE = {
    MJAI_TYPE.NONE: MSType.none,
    
    MJAI_TYPE.CHI: MSType.chi,
    MJAI_TYPE.PON: MSType.pon,
    MJAI_TYPE.DAIMINKAN: MSType.daiminkan,
    MJAI_TYPE.HORA: MSType.hora,        # MJAI hora might also be mapped to zimo

    MJAI_TYPE.ANKAN: MSType.ankan,
    MJAI_TYPE.KAKAN: MSType.kakan,
    MJAI_TYPE.REACH: MSType.reach,
    MJAI_TYPE.RYUKYOKU: MSType.ryukyoku,
    MJAI_TYPE.NUKIDORA: MSType.nukidora,
}
""" Map mjai type to Majsoul operation type """

ACTION_PIORITY = [
    0,  # none      #
    99, # Discard   # There is no discard button. Make it off the chart and positioned last in the operation list
    4,  # Chi       # Opponent Discard
    3,  # Pon       # Opponent Discard
    3,  # Ankan     # Self Discard      # If Ankan and Kakan are both available, use only kakan.
    2,  # Daiminkan # Opponent Discard
    3,  # Kakan     # Self Discard
    2,  # Reach     # Self Discard
    1,  # Zimo      # Self Discard
    1,  # Rong      # Opponent Discard
    5,  # Ryukyoku  # Self Discard
    4,  # Nukidora  # Self Discard
]
""" Priority of the actions when allocated to buttons in Majsoul
None is always the lowest, at bottom-right corner"""

def cvt_type_mjai_2_ms(mjai_type:str, gi:GameInfo) -> MSType:
    """ Convert mjai type str to MSType enum"""
    if gi.my_tsumohai != '?' and mjai_type == 'hora':
        return MSType.zimo
    else:
        return MJAI_2_MS_TYPE[mjai_type]

ActionStep = namedtuple('ActionStep', ['action', 'text'])
def get_delay_step(delay:float):
    """ Generate a delay step"""
    action = lambda: time.sleep(delay)
    text = f"delay {delay:.1f}s "
    return ActionStep(action, text)

class Automation:
    """ Convert mjai reaction messages to browser actions, automating the AI actions on Majsoul"""
    def __init__(self, browser: GameBrowser):
        self.browser = browser
        self.last_exe_time:float = -1     # last time an action execution was finished
        self.last_exe_step:int = None
        """Majsoul operation step number of the last action finished execution
        retry automation will perform if last_exe_step == game_state step no, or when last_exe_step is None"""
        self._execution_thread:threading.Thread = None
        self._thread_stop_event = threading.Event() #set the event to abort the thread
        
    def mouse_click(self, x, y):
        scalar = self.browser.width/16
        self.browser.mouse_click(x * scalar, y * scalar)

    def get_delay(self, mjai_action:dict, game_state:GameState):
        """ return the delay based on action type and game info"""
        mjai_type = mjai_action['type']
        delay = 1.0 + 1.0 * random.random()
        if mjai_type == MJAI_TYPE.DAHAI:
            if game_state.first_round:
                delay += 1
                if game_state.self_wind == 'E':
                    delay += 1.5
        elif mjai_type == MJAI_TYPE.REACH:
            delay += 1
        elif mjai_type == MJAI_TYPE.HORA:
            delay += 0
        else:
            delay += 0.5       
        
        return delay
        
    def execute_action(self, mjai_action:dict, game_state:GameState):
        """ execute action given by the mjai message
        params:
            mjai_action(dict): mjai output action msg
            game_state(GameState): game state object"""
        if game_state is None:
            return False
        if mjai_action is None:
            return False
        if self.is_running_execution():
            LOGGER.warning("Previous action is still executing. Expect previous one to be canceled.")
        gi = game_state.get_game_info()
        liqi_operation = game_state.last_operation
        op_step = game_state.last_op_step        
        mjai_type = mjai_action['type']
        LOGGER.debug("Automating action '%s', ms step = %d", mjai_type, op_step)
        
        # Design: generate action steps based on mjai action
        # action steps are individual steps like delay, mouse click, etc.
        # Then execute the steps in thread.
        # verify if the action has expired (Majsoul has new action/operation), and cancel executing if so
        if  mjai_type == 'dahai':
            more_steps:list[ActionStep] = self._dahai_action_steps(mjai_action, gi, game_state.first_round)
        elif mjai_type in ['none', 'chi', 'pon', 'daiminkan', 'ankan', 'kakan', 'hora', 'reach', 'ryukyoku', 'nukidora']:
            more_steps:list[ActionStep] = self._button_action_steps(mjai_action, gi, liqi_operation)
        else:
            LOGGER.error("Exit Automation for unrecognized mjai type %s", mjai_type)
            return
        
        delay = self.get_delay(mjai_action, game_state)  # first action is delay
        action_steps:list[ActionStep] = [get_delay_step(delay)]
        action_steps.extend(more_steps)
        
        def execute_action_steps():
            # task method for thread            
            for step in action_steps:
                # verify if op_step changed, which indicates there is new liqi action, and old action has expired
                # for example, when executing Chi, there might be another player Pon before Chi is finished
                # upon which any action steps related to Chi should be canceled
                game_step = game_state.last_op_step
                if op_step != game_step:  
                    LOGGER.debug("Cancel execution. origin step = %d, current step = %dd", op_step, game_step)
                    return
                if self._thread_stop_event.is_set():
                    LOGGER.debug("Cancel execution. Stop event set")
                    return                
                LOGGER.debug("Executing step: %s", step.text)
                step.action()
                # record execution info for possible retry
                self.last_exe_time = time.time()
                self.last_exe_step = op_step
                           
        if action_steps:
            # Execute actions in thread to avoid blocking bot manager main thread
            self._execution_thread = threading.Thread(
                target = execute_action_steps,
                name=f"Auto_step_{op_step}",
                daemon=True
            )
            self._execution_thread.start()
        else:
            LOGGER.warning("Exit Automation. Action step list empty.")
    
    def stop_execution(self):
        """ Stop ongoing execution if any"""
        self._thread_stop_event.set()
        
    def allow_execution(self):
        """ allow execution thread"""
        self._thread_stop_event.clear()
    
    def is_running_execution(self):
        if self._execution_thread and self._execution_thread.is_alive():
            return True
        else:
            return False
    
    def retry_pending_reaction(self, game_state:GameState, min_interval:float=1):
        """ Retry pending action from game state. if current time > last execution time + min interval"""
        if self.is_running_execution():
            # last action still executing, quit
            return
        
        if time.time() - self.last_exe_time < min_interval:
            # interval not reached, cancel
            return
        
        if game_state is None:
            LOGGER.warning("Exit Automation. Game State is none!")
            return
        
        game_step = game_state.last_op_step
        if self.last_exe_step is not None:
            if game_step != self.last_exe_step:
                # already new step. cancel retry old action             
                return

        mjai_action = game_state.get_pending_reaction()
        if mjai_action is None:
            return
        
        LOGGER.debug("Retry automating pending reaction: %s", mjai_action['type'])
        self.execute_action(mjai_action, game_state)
        
    
    def _dahai_action_steps(self, mjai_action:dict, gi:GameInfo, is_first_round:bool) -> list[ActionStep]:
        """ generate dahai (discard tile) action
        params:
            is_east_first(bool): if currently self is East and it's the first move"""
        dahai = mjai_action['pai']
        tsumogiri = mjai_action['tsumogiri']
        
        if gi.reached:
            # already in reach state. no need to manual dahai
            LOGGER.debug("Skip automating dahai %s because already in reach state.", dahai)
            return []
        
        if tsumogiri:   # tsumogiri: discard right most
            dahai_count = len([tile for tile in gi.my_tehai if tile != '?'])
            assert dahai == gi.my_tsumohai, "mjai tsumogiri but mjai dahai != game tsumohai"
            # 14-tile tehai + no tsumohai treatment for East first round
            if is_first_round and gi.self_wind == 'E':
                action = lambda: self.mouse_click(Positions.TEHAI_X[dahai_count], Positions.TEHAI_Y)
            else:
                action = lambda: self.mouse_click(Positions.TEHAI_X[dahai_count] + Positions.TRUMO_SPACE, Positions.TEHAI_Y)
            return [ActionStep(action, f"Dahai [{dahai}]")]
        else:       # tedashi: find the index and discard
            idx = gi.my_tehai.index(dahai)            
            action = lambda: self.mouse_click(Positions.TEHAI_X[idx], Positions.TEHAI_Y)
            return [ActionStep(action, f"Dahai [{dahai}]")]
    
    def _process_oplist_for_kan(self, mstype_from_mjai, op_list:list) -> list:
        """ Process operation list for kan, and return the new op list"""
        # ankan and kakan use one Kan button, and candidates are merged = [kakan, ankan]
        # merge kan combinations into one of the kan type, delete the other from operation list
        kan_combs:list[str] = []
        idx_to_keep = None
        idx_to_del = None
        for idx in range(len(op_list)):
            op_type = op_list[idx]['type']
            if op_type in (MSType.kakan, MSType.ankan):
                if op_type== MSType.kakan:
                    kan_combs = op_list[idx]['combination'] + kan_combs
                elif op_type == MSType.ankan:
                    kan_combs = kan_combs + op_list[idx]['combination']
                if op_type == mstype_from_mjai:
                    idx_to_keep = idx
                else:
                    idx_to_del = idx
        
        if idx_to_keep is None:
            LOGGER.error("No matching type %s found in op list: %s", mstype_from_mjai, op_list)
            return op_list
        op_list[idx_to_keep]['combination'] = kan_combs
        if idx_to_del is not None:
            op_list.pop(idx_to_del)
        return op_list        

    
    def _button_action_steps(self, mjai_action:dict, gi:GameInfo, liqi_operation:dict) -> list[ActionStep]:
        """Generate button click related actions (chi, pon, kan, etc.)"""       

        actions = []
        # if mjai_action['type'] == 'none':
        #     action = lambda: self.mouse_click(Positions.BUTTONS[0][0], Positions.BUTTONS[0][1])
        #     actions.append(action)
        #     return actions
        
        # sort operation list by priority
        if 'operationList' not in liqi_operation:
            return actions
        op_list:list = liqi_operation['operationList']
        op_list = op_list.copy()
        op_list.append({'type': 0})     # add None/Pass button
        op_list.sort(key=lambda x: ACTION_PIORITY[x['type']])        
        
        mjai_type = mjai_action['type']
        mstype_from_mjai = cvt_type_mjai_2_ms(mjai_type, gi)
        
        if mstype_from_mjai in [MSType.ankan, MSType.kakan]:
            op_list = self._process_oplist_for_kan(mstype_from_mjai, op_list)
        
        # Click on the corresponding button (None, Chii, Pon, etc.)
        the_op = None
        for idx, operation in enumerate(op_list):
            if operation['type'] == mstype_from_mjai:
                text = f"clicking button {idx} ({mjai_type})"
                action = lambda: self.mouse_click(Positions.BUTTONS[idx][0], Positions.BUTTONS[idx][1])
                actions.append(ActionStep(action, text))
                the_op = operation
                break
        if the_op is None:
            # no liqi operation but mjai indicates operation. mismatch(e.g. last round no pon)
            LOGGER.error("No matching operation for mjai %s. Op list: %s", mjai_type, op_list)            
            return actions
        
        # process reach dahai action
        if mstype_from_mjai == MSType.reach:            
            reach_dahai = mjai_action['reach_dahai']
            delay = 0.5 + 1.0 * random.random()
            actions.append(get_delay_step(delay))
            dahai_actions = self._dahai_action_steps(reach_dahai, gi, False)
            actions.extend(dahai_actions)
            return actions
        
        # chi / pon / kan: click candidate
        elif mstype_from_mjai in [MSType.chi, MSType.pon, MSType.daiminkan, MSType.kakan, MSType.ankan]:            
            # e.g. {'type': 'chi', 'actor': 3, 'target': 2, 'pai': '4m', 'consumed': ['3m', '5mr'], ...}"""
            mjai_consumed = mjai_action['consumed']
            mjai_consumed = mj_helper.sort_mjai_tiles(mjai_consumed)
            if 'combination' in the_op:
                combs = the_op['combination']
            else:
                combs = []
                
            if len(combs) == 1:
                # no need to click. return directly
                return actions
            elif len(combs) == 0:
                # something is wrong. no combination offered in liqi msg
                return actions
            for idx, comb in enumerate(combs):  
                # for more than one candidate group, click on the matching group
                # groups in liqi msg are converted to mjai tile format for comparison
                consumed_liqi = [mj_helper.cvt_ms2mjai(t) for t in comb.split('|')]
                consumed_liqi = mj_helper.sort_mjai_tiles(consumed_liqi)
                if mjai_consumed == consumed_liqi:  # match. This is the combination to click on
                    delay = len(combs) * (0.5 + random.random())
                    actions.append(get_delay_step(delay))                    
                    text = f"clicking candidate {mjai_consumed}"
                    
                    if mstype_from_mjai in [MSType.chi, MSType.pon, MSType.daiminkan]:
                        candidate_idx = int((-(len(combs)/2)+idx+0.5)*2+5)
                        action = lambda: self.mouse_click(
                            Positions.CANDIDATES[candidate_idx][0],
                            Positions.CANDIDATES[candidate_idx][1])
                        
                    elif mstype_from_mjai in [MSType.ankan, MSType.kakan]:
                        candidate_idx = int((-(len(combs)/2)+idx+0.5)*2+3)
                        action = lambda: self.mouse_click(
                            Positions.CANDIDATES_KAN[candidate_idx][0],
                            Positions.CANDIDATES_KAN[candidate_idx][1])
                    
                    actions.append(ActionStep(action,text))
                    return actions
        else:
            return actions