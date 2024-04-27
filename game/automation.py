""" Game automation classes and algorithm"""
# Design: generate action steps based on mjai action (Automation)
# action steps are individual steps like delay, mouse click, etc. (ActionStep and derivatives)
# Screen positions are in 16x9 resolution, and are translated to client resolution in execution
# Then execute the steps in thread (AutomationTask). It calls the executor (browser for now) to carry out the actions.
# for in-game actions, verify on every ActionStep if the action has expired, and cancel execution if needed
# for example, Majsoul before you finish "Chi", another player may "Pon"/"Ron"/..., which cancels your "Chi" action

from dataclasses import dataclass, field
import time
import random
import threading
from typing import Iterable, Iterator

from common.mj_helper import MjaiType, MSType, MJAI_TILES_19, MJAI_TILES_28, MJAI_TILES_SORTED
from common.mj_helper import sort_mjai_tiles, cvt_ms2mjai
from common.log_helper import LOGGER
from common.settings import Settings
from common.utils import UiState, GAME_MODES

from .img_proc import ImgTemp, GameVisual
from .browser import GameBrowser
from .game_state import GameInfo, GameState


class Positions:
    """ Screen coordinates constants. in 16 x 9 resolution"""
    TEHAI_X = [
        2.23125,    3.021875,   3.8125,     4.603125,   5.39375,    6.184375,   6.975,
        7.765625,   8.55625,    9.346875,   10.1375,    10.928125,  11.71875,   12.509375]
    TEHAI_Y = 8.3625
    TRUMO_SPACE = 0.246875
    BUTTONS:list[tuple] = [
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

    CANDIDATES:list[tuple] = [
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
    
    CANDIDATES_KAN:list[tuple] = [
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
    
    EMOJI_BUTTON = (15.675, 4.9625)
    EMOJIS = [
        (12.4, 3.5), (13.65, 3.5), (14.8, 3.5),    # 1 2 3
        (12.4, 5.0), (13.65, 5.0), (14.8, 5.0),    # 4 5 6
        (12.4, 6.5), (13.65, 6.5), (14.8, 6.5),    # 7 8 9
    ]
    """ emoji positions
    0 1 2
    3 4 5
    6 7 8"""
    
    
    GAMEOVER = [
        (14.35, 8.12),    # OK button 确定按钮
        (6.825, 6.8),     # 点击好感度礼物?
    ]
    MENUS = [
        (11.5, 2.75),   # Ranked 段位场
    ]
    
    LEVELS = [
        (11.5, 3.375),  # Bronze 铜之间
        (11.5, 4.825),  # Silver 银之间
        (11.5, 6.15),   # Gold 金之间
        (11.5, 5.425),  # Jade 玉之间    滚轮    
        (11.5, 6.825),  # Throne 王座之间  滚轮
    ]
    
    MODES = [
        (11.6, 3.325), # 4E 四人东
        (11.6, 4.675), # 4S 四人南
        (11.6, 6.1),   # 3E 三人东
        (11.6, 7.35),  # 3S 三人南
    ]



MJAI_2_MS_TYPE = {
    MjaiType.NONE: MSType.none,
    
    MjaiType.CHI: MSType.chi,
    MjaiType.PON: MSType.pon,
    MjaiType.DAIMINKAN: MSType.daiminkan,
    MjaiType.HORA: MSType.hora,        # MJAI hora might also be mapped to zimo

    MjaiType.ANKAN: MSType.ankan,
    MjaiType.KAKAN: MSType.kakan,
    MjaiType.REACH: MSType.reach,
    MjaiType.RYUKYOKU: MSType.ryukyoku,
    MjaiType.NUKIDORA: MSType.nukidora,
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
    if gi.my_tsumohai and mjai_type == MjaiType.HORA:
        return MSType.zimo
    else:
        return MJAI_2_MS_TYPE[mjai_type]
    
@dataclass
class ActionStep:
    """ representing an atomic action step like single click/move/wheel/etc."""
    ignore_step_change:bool = field(default=False, init=False)
    
@dataclass
class ActionStepMove(ActionStep):
    """ Move mouse to x,y (client res)"""
    x:float
    y:float
    steps:int = field(default=5)    # playwright mouse move steps
    
@dataclass
class ActionStepClick(ActionStep):
    """ Click mouse left at current position"""
    delay:float = field(default=80) # delay before button down/up

@dataclass
class ActionStepMouseDown(ActionStep):
    """ Mouse down action"""
    
@dataclass
class ActionStepMouseUp(ActionStep):
    """ Mouse up action"""

@dataclass
class ActionStepWheel(ActionStep):
    """ Mouse wheel action"""
    dx:float
    dy:float

@dataclass
class ActionStepDelay(ActionStep):
    """ Delay action"""
    delay:float
        
class AutomationTask:
    """ Managing automation task and its thread
    an automation task corresponds to performing a bot reaction on game client (e.g. click dahai on web client)"""
    def __init__(self, br:GameBrowser, name:str, desc:str=""):
        """
        params:
            br(GameBrowser): browser object
            name(str): name for the thread and task
            desc(str): description of the task, for logging and readability"""
        self.name = name
        self.desc = desc
        self.executor = br
        self._stop_event = threading.Event()        # set event to stop running
        self.last_exe_time:float = -1               # timestamp for the last actionstep execution
        
        self._thread:threading.Thread = None        
        
    def stop(self, jointhread:bool=False):
        """ stop the thread"""
        if self._thread:
            self._stop_event.set()
            if jointhread:
                self._thread.join()
    
    def is_running(self):
        """ return true if thread is running"""
        if self._thread and self._thread.is_alive():
            return True
        else:
            return False
        
    def run_step(self, step:ActionStep):
        """ run single action step"""
        if isinstance(step, ActionStepMove):
            self.executor.mouse_move(step.x, step.y, step.steps, True)
        elif isinstance(step, ActionStepClick):
            # self.executor.mouse_click(step.delay, True)
            self.executor.mouse_down(True)
            time.sleep(step.delay/1000) # sleep here instead of in browser thread
            self.executor.mouse_up(True)
        elif isinstance(step, ActionStepMouseDown):
            self.executor.mouse_down(True)
        elif isinstance(step, ActionStepMouseUp):
            self.executor.mouse_up(True)
        elif isinstance(step, ActionStepWheel):
            self.executor.mouse_wheel(step.dx, step.dy, True)
        elif isinstance(step, ActionStepDelay):
            time.sleep(step.delay)
        else:
            raise NotImplementedError(f"Execution not implemented for step type {type(step)}")
        self.last_exe_time = time.time()
        
    def start_action_steps(self, action_steps:Iterable[ActionStep], game_state:GameState = None):
        """ start running action list/iterator in a thread"""
        if self.is_running():
            return
            
        def task():
            if game_state:
                op_step = game_state.last_op_step
            else:
                op_step = None
            msg = f"Start executing task: {self.name}, {self.desc}"
            LOGGER.debug(msg)
            for step in action_steps:
                if self._stop_event.is_set():
                    LOGGER.debug("Cancel executing %s. Stop event set",self.name)
                    return                
                if game_state:  
                    # check step change
                    # operation step change indicates there is new liqi operation, and old action has expired
                    new_step = game_state.last_op_step
                    if op_step != new_step and not step.ignore_step_change:
                        LOGGER.debug("Cancel executing %s due to step change(%d -> %d)", self.name, op_step, new_step)
                        return
                self.run_step(step)
            LOGGER.debug("Finished executing task: %s", self.name)
        
        self._thread = threading.Thread(
            target=task,
            name = self.name,
            daemon=True
        )
        self._thread.start()

END_GAME = "Auto_EndGame"
JOIN_GAME = "Auto_JoinGame"

class Automation:
    """ Convert mjai reaction messages to browser actions, automating the AI actions on Majsoul.
    Screen positions are calculated using pre-defined constants in 16x9 resolution,
    and are translated to client resolution before execution"""
    def __init__(self, browser: GameBrowser, setting:Settings):
        if browser is None:
            raise ValueError("Browser is None")
        self.executor = browser
        self.st = setting
        self.g_v = GameVisual(browser)
        
        self._task:AutomationTask = None        # the task thread        
        self.ui_state:UiState = UiState.NOT_RUNNING   # Where game UI is at. initially not running 
        
        self.last_emoji_time:float = 0.0        # timestamp of last emoji sent   
    
    def is_running_execution(self):
        """ if task is still running"""
        if self._task and self._task.is_running():
            return True
        else:
            return False
    
    def running_task_info(self) -> tuple[str, str]:
        """ return the running task's (name, desc). None if N/A"""
        if self._task and self._task.is_running():
            return (self._task.name, self._task.desc)
        else:
            return None
        
    def stop_previous(self):
        """ stop previous task execution if it is still running"""
        if self.is_running_execution():
            LOGGER.info("Stopping previous action: %s", self._task.name)
            self._task.stop()
            self._task = None
            
    def can_automate(self, cancel_on_running:bool=False, limit_state:UiState=None) -> bool:
        """return True if automation conditions met """
        if not self.st.enable_automation: # automation not enabled
            return False
        if not self.executor.is_page_normal():  # browser is not running
            return False
        if cancel_on_running and self.is_running_execution():   # cancel if previous task is running
            return False
        if limit_state and self.ui_state != limit_state:        # cancel if current state != limit_state
            return False       
            
        return True
        
    def get_delay(self, mjai_action:dict, gi:GameInfo, subtract:float=0.0):
        """ return the action initial delay based on action type and game info"""
        mjai_type = mjai_action['type']
        delay = random.uniform(self.st.delay_random_lower, self.st.delay_random_upper)    # base delay        
        if mjai_type == MjaiType.DAHAI:
            # extra time for first round and East
            if gi.is_first_round and  gi.jikaze  == 'E':
                delay += 4.5
                
            extra_time:float = 0.0
            
            # more time for 19 < 28 < others
            pai = mjai_action['pai']
            if pai in MJAI_TILES_19 or pai == gi.my_tsumohai :
                extra_time += 0.0
            elif pai in MJAI_TILES_28:
                extra_time += 0.5
            else:
                extra_time += random.uniform(0.75, 1.0)            
            if gi.n_other_reach() > 0:    # extra time for other reach
                extra_time += random.uniform(0.20, 0.30) * gi.n_other_reach()
            extra_time = min(extra_time, 3.0)   # cap extra time
            delay += extra_time
                                
        elif mjai_type == MjaiType.REACH:
            delay += 1.0
        elif mjai_type == MjaiType.HORA:
            delay += 0.0
        elif mjai_type == MjaiType.NUKIDORA:
            delay += 0.0
        elif mjai_type == MjaiType.RYUKYOKU: # more time for RYUKYOKU
            if gi.jikaze  == 'E':
                delay += 1.5
            delay += 2.0
        else:       # chi/pon/kan/others
            delay += 0.5
        
        subtract = max(0, subtract-0.5)
        delay = max(0, delay-subtract)    # minimal delay =0
        # LOGGER.debug("Subtract=%.2f, Delay=%.2f", subtract, delay)
        return delay
     
        
    def automate_action(self, mjai_action:dict, game_state:GameState) -> bool:
        """ execute action given by the mjai message
        params:
            mjai_action(dict): mjai output action msg
            game_state(GameState): game state object
        Returns:
            bool: True means automation kicks off. False means not automating."""
        if not self.can_automate():
            return False
        if game_state is None or mjai_action is None:
            return False          
        
        self.stop_previous()
        gi = game_state.get_game_info()
        assert gi is not None, "Game info is None"
        op_step = game_state.last_op_step
        mjai_type = mjai_action['type']        
        
        if self.st.ai_randomize_choice:     # randomize choice
            mjai_action = self.randomize_action(mjai_action, gi) 
        # Dahai action
        if  mjai_type == MjaiType.DAHAI:       
            if gi.self_reached:
                # already in reach state. no need to automate dahai
                LOGGER.info("Skip automating dahai, already in REACH")
                game_state.last_reaction_pending = False        # cancel pending state so i won't be retried
                return False             
            more_steps:list[ActionStep] = self.steps_action_dahai(mjai_action, gi)
        
        # "button" action
        elif mjai_type in [MjaiType.NONE, MjaiType.CHI, MjaiType.PON, MjaiType.DAIMINKAN, MjaiType.ANKAN,
            MjaiType.KAKAN, MjaiType.HORA, MjaiType.REACH, MjaiType.RYUKYOKU, MjaiType.NUKIDORA]:
            liqi_operation = game_state.last_operation
            more_steps:list[ActionStep] = self.steps_button_action(mjai_action, gi, liqi_operation)
        
        else:
            LOGGER.error("No automation for unrecognized mjai type: %s", mjai_type)
            return False
        
        delay = self.get_delay(mjai_action, gi, game_state.last_reaction_time)  # initial delay
        action_steps:list[ActionStep] = [ActionStepDelay(delay)]
        action_steps.extend(more_steps)
        pai = mjai_action.get('pai',"")  
        calc_time = game_state.last_reaction_time
        desc = (
            f"Automating action {mjai_type} {pai}"
            f" (step={op_step},"
            f" calc_time={calc_time:.2f}s, delay={delay:.2f}s, total_delay={calc_time+delay:.2f}s)"
        )
        self._task = AutomationTask(self.executor, f"Auto_{mjai_type}_{pai}", desc)
        self._task.start_action_steps(action_steps, game_state)
        return True
    
    def randomize_action(self, action:dict, gi:GameInfo) -> dict:
        """ Randomize ai choice: pick according to probaility from top 3 options"""
        n = self.st.ai_randomize_choice     # randomize strength. 0 = no random, 5 = according to probability
        if n == 0:
            return action
        mjai_type = action['type']
        if mjai_type == MjaiType.DAHAI:
            orig_pai = action['pai']
            options:dict = action['meta_options']            # e.g. {'1m':0.95, 'P':0.045, 'N':0.005, ...}
            # get dahai options (tile only) from top 3
            top_ops:list = [(k,v) for k,v in options[:3] if k in MJAI_TILES_SORTED]        
            #pick from top3 according to probability
            power = 1 / (0.2 * n)
            sum_probs = sum([v**power for k,v in top_ops])
            top_ops_powered = [(k, v**power/sum_probs) for k,v in top_ops]
            
            # 1. Calculate cumulative probabilities
            cumulative_probs = [top_ops_powered[0][1]]
            for i in range(1, len(top_ops_powered)):
                cumulative_probs.append(cumulative_probs[-1] + top_ops_powered[i][1])

            # 2. Pick an option based on a random number
            rand_prob = random.random()  # Random float: 0.0 <= x < 1.0
            chosen_pai = orig_pai  # Default in case no option is selected, for safety
            prob = top_ops_powered[0][1]
            for i, cum_prob in enumerate(cumulative_probs):
                if rand_prob < cum_prob:
                    chosen_pai = top_ops_powered[i][0]  # This is the selected key based on probability
                    prob = top_ops_powered[i][1]        # the probability
                    orig_prob = top_ops[i][1]
                    break
                
            if chosen_pai == orig_pai:  # return original action if no change
                change_str = f"{action['pai']} Unchanged"
            else:
                change_str = f"{action['pai']} -> {chosen_pai}"
            
            # generate new action for changed tile
            tsumogiri = chosen_pai == gi.my_tsumohai
            new_action = {
                'type': MjaiType.DAHAI,
                'actor': action['actor'],
                'pai': chosen_pai,
                'tsumogiri': tsumogiri
            }
            msg = f"Randomized dahai: {change_str} ([{n}] {orig_prob*100:.1f}% -> {prob*100:.1f}%)"
            LOGGER.debug(msg)
            return new_action
        # other MJAI types
        else:
            return action

    
    def last_exec_time(self) -> float:
        """ return the time of last action execution. return -1 if N/A"""
        if self._task:
            return self._task.last_exe_time
        else:
            return -1
        
    def automate_retry_pending(self, game_state:GameState):
        """ retry pending action from game state"""
        if not self.can_automate(True, UiState.IN_GAME):
            return
        if time.time() - self.last_exec_time() < self.st.auto_retry_interval:
            # interval not reached, cancel
            return False
        if game_state is None:
            return False
        pend_action = game_state.get_pending_reaction()
        if pend_action is None:
            return
        LOGGER.info("Retry automating pending reaction: %s", pend_action['type'])
        self.automate_action(pend_action, game_state)        
                
    
    def automate_send_emoji(self):
        """ Send emoji given chance
        """
        if not self.can_automate(True, UiState.IN_GAME):
            return
        if time.time() - self.last_emoji_time < self.st.auto_emoji_intervel:  # prevent spamming
            return
        roll = random.random()
        if roll > self.st.auto_reply_emoji_rate:   # send when roll < rate
            return

        
        idx = random.randint(0, 8)
        x,y = Positions.EMOJI_BUTTON
        steps = [ActionStepDelay(random.uniform(1.5, 3.0)), ActionStepMove(x*self.scaler, y*self.scaler)]
        steps.append(ActionStepDelay(random.uniform(0.1, 0.2)))
        steps.append(ActionStepClick())
        x,y = Positions.EMOJIS[idx]
        steps.append(ActionStepMove(x*self.scaler,y*self.scaler))
        steps.append(ActionStepDelay(random.uniform(0.1, 0.2)))
        steps.append(ActionStepClick())
        self._task = AutomationTask(self.executor, f"SendEmoji{idx}", f"Send emoji {idx}")
        self._task.start_action_steps(steps, None)
        self.last_emoji_time = time.time()
    
    def automate_idle_mouse_move(self, prob:float):
        """ move mouse around to avoid AFK. according to probability"""
        if not self.can_automate(True, UiState.IN_GAME):
            return False
        if not self.st.auto_idle_move:
            return

        roll = random.random()
        if prob > roll:
            action_steps = self.steps_move_to_center(False)
            action_steps += self.steps_move_to_center(False)
            action_steps += self.steps_move_to_center(False)
            self._task = AutomationTask(self.executor, "IdleMove", "Move mouse around in other's turn")
            self._task.start_action_steps(action_steps, None)
        
    
    def steps_action_dahai(self, mjai_action:dict, gi:GameInfo) -> list[ActionStep]:
        """ generate steps for dahai (discard tile) action
        params:
            mjai_action(dict): mjai output action msg
            gi(GameInfo): game info object
        """
        
        dahai = mjai_action['pai']
        tsumogiri = mjai_action['tsumogiri']
        if tsumogiri:   # tsumogiri: discard right most
            dahai_count = len([tile for tile in gi.my_tehai if tile != '?'])
            assert dahai == gi.my_tsumohai, f"tsumogiri but dahai {dahai} != game tsumohai {gi.my_tsumohai}"
            # Majsoul on East first round: 14-tile tehai + no tsumohai
            if gi.is_first_round and gi.jikaze  == 'E':
                x = Positions.TEHAI_X[dahai_count]
                y = Positions.TEHAI_Y
            else:
                x = Positions.TEHAI_X[dahai_count] + Positions.TRUMO_SPACE
                y = Positions.TEHAI_Y
            steps = self.steps_randomized_move(x, y)         
        else:       # tedashi: find the index and discard
            idx = gi.my_tehai.index(dahai)
            steps = self.steps_randomized_move(Positions.TEHAI_X[idx], Positions.TEHAI_Y)
        
        # drag or click to dahai
        if self.st.auto_dahai_drag:
            steps += self.steps_mouse_drag_to_center()
        else:
            steps += self.steps_mouse_click()
            steps += self.steps_move_to_center(True)  # move to screen center to avoid highlighting a tile.
        return steps
    
    
    
    def _process_oplist_for_kan(self, mstype_from_mjai, op_list:list) -> list:
        """ Process operation list for kan, and return the new op list"""
        # ankan and kakan use one Kan button, and candidates are merged = [kakan, ankan]
        # determine the kan type used by mjai        
        kan_combs:list[str] = []
        idx_to_keep = None
        idx_to_del = None
        for idx, op in enumerate(op_list):
            op_type = op['type']
            if op_type in (MSType.kakan, MSType.ankan):
                if op_type== MSType.kakan:
                    kan_combs = op['combination'] + kan_combs
                elif op_type == MSType.ankan:
                    kan_combs = kan_combs + op['combination']
                if op_type == mstype_from_mjai:
                    idx_to_keep = idx
                else:
                    idx_to_del = idx
        
        # merge kan combinations into the used kan type, delete the other type from operation list
        if idx_to_keep is None:
            LOGGER.error("No matching type %s found in op list: %s", mstype_from_mjai, op_list)
            return op_list
        op_list[idx_to_keep]['combination'] = kan_combs
        if idx_to_del is not None:
            op_list.pop(idx_to_del)
        return op_list        

    
    def steps_button_action(self, mjai_action:dict, gi:GameInfo, liqi_operation:dict) -> list[ActionStep]:
        """Generate action steps for button actions (chi, pon, kan, etc.)"""       
        if 'operationList' not in liqi_operation:   # no liqi operations provided - no buttons to click
            return []
        
        op_list:list = liqi_operation['operationList']
        op_list = op_list.copy()
        op_list.append({'type': 0})                             # add None/Pass button
        op_list.sort(key=lambda x: ACTION_PIORITY[x['type']])   # sort operation list by priority
        
        mjai_type = mjai_action['type']
        mstype_from_mjai = cvt_type_mjai_2_ms(mjai_type, gi)
        
        if mstype_from_mjai in [MSType.ankan, MSType.kakan]:
            op_list = self._process_oplist_for_kan(mstype_from_mjai, op_list)
        
        # Find the button coords and click (None, Chii, Pon, etc.)
        steps = []
        the_op = None
        for idx, op in enumerate(op_list):
            if op['type'] == mstype_from_mjai:
                x, y = Positions.BUTTONS[idx]
                steps += self.steps_randomized_move_click(x,y)
                the_op = op
                break
        if the_op is None:  # something's wrong
            LOGGER.error("for mjai %s liqi msg has no op list. Op list: %s", mjai_type, op_list)            
            return steps

        # Reach: process subsequent reach dahai action
        if mstype_from_mjai == MSType.reach:            
            reach_dahai = mjai_action['reach_dahai']
            delay = self.get_delay(reach_dahai, gi)
            steps.append(ActionStepDelay(delay))
            dahai_steps = self.steps_action_dahai(reach_dahai, gi)
            steps += dahai_steps
            return steps

        # chi / pon / kan: click candidate (choose from options)
        elif mstype_from_mjai in [MSType.chi, MSType.pon, MSType.daiminkan, MSType.kakan, MSType.ankan]:            
            # e.g. {'type': 'chi', 'actor': 3, 'target': 2, 'pai': '4m', 'consumed': ['3m', '5mr'], ...}"""
            mjai_consumed = mjai_action['consumed']
            mjai_consumed = sort_mjai_tiles(mjai_consumed)
            if 'combination' in the_op:
                combs = the_op['combination']
            else:
                combs = []
                
            if len(combs) == 1:     # no need to click. return directly
                return steps
            elif len(combs) == 0:   # something is wrong. no combination offered in liqi msg
                LOGGER.warning("mjai type %s, but no combination in liqi operation list", mjai_type)
                return steps
            for idx, comb in enumerate(combs):
                # for more than one candidate group, click on the matching group
                consumed_liqi = [cvt_ms2mjai(t) for t in comb.split('|')]
                consumed_liqi = sort_mjai_tiles(consumed_liqi) # convert to mjai tile format for comparison
                if mjai_consumed == consumed_liqi:  # match. This is the combination to click on
                    delay = len(combs) * (0.5 + random.random())
                    steps.append(ActionStepDelay(delay))
                    if mstype_from_mjai in [MSType.chi, MSType.pon, MSType.daiminkan]:
                        # well, pon/daiminkan only has 1 combination, wouldn't need choosing
                        candidate_idx = int((-(len(combs)/2)+idx+0.5)*2+5)
                        x,y = Positions.CANDIDATES[candidate_idx]
                        steps += self.steps_randomized_move_click(x,y)
                    elif mstype_from_mjai in [MSType.ankan, MSType.kakan]:
                        candidate_idx = int((-(len(combs)/2)+idx+0.5)*2+3)
                        x,y = Positions.CANDIDATES_KAN[candidate_idx]
                        steps += self.steps_randomized_move_click(x,y)
                    return steps
        
        # other mjai types: no additional clicks
        else:       
            return steps
    
    @property
    def scaler(self):
        """ scaler for 16x9 -> game resolution"""
        return self.executor.width/16
    
    def steps_randomized_move(self, x:float, y:float) -> list[ActionStep]:
        """ generate list of steps for a randomized mouse move
        Params:
            x, y: target position in 16x9 resolution
            random_moves(int): number of random moves before target. None -> use settings"""
        steps = []
        if self.st.auto_random_move:  # random moves, within (-0.5, 0.5) x screen size of target      
            for _i in range(3):
                rx = x + 16*random.uniform(-0.5, 0.5)
                rx = max(0, min(16, rx))
                ry = y + 9*random.uniform(-0.5, 0.5)
                ry = max(0, min(9, ry))
                steps.append(ActionStepMove(rx*self.scaler, ry*self.scaler, random.randint(2, 5)))
                steps.append(ActionStepDelay(random.uniform(0.05, 0.11)))
        # then move to target
        tx, ty = x*self.scaler, y*self.scaler
        steps.append(ActionStepMove(tx, ty, random.randint(2, 5)))
        return steps
    
    def steps_randomized_move_click(self, x:float, y:float) -> list[ActionStep]:
        """ generate list of steps for a randomized mouse move and click
        Params:
            x, y: target position in 16x9 resolution
            random_moves(int): number of random moves before target. None -> use settings"""
        steps = self.steps_randomized_move(x, y)
        steps.append(ActionStepDelay(random.uniform(0.3, 0.5)))
        steps.append(ActionStepClick(random.randint(60, 100)))
        return steps
    
    def steps_mouse_click(self) -> list[ActionStep]:
        """ generate list of steps for a simple mouse click"""
        steps = []
        steps.append(ActionStepDelay(random.uniform(0.2, 0.4)))
        steps.append(ActionStepClick(random.randint(60, 100)))
        return steps
    
    def steps_mouse_drag_to_center(self) -> list[ActionStep]:
        """ steps for dragging to center (e.g. for dahai)"""
        steps = []
        steps.append(ActionStepDelay(random.uniform(0.1, 0.3)))
        steps.append(ActionStepMouseDown())
        steps += self.steps_move_to_center(False)
        steps.append(ActionStepDelay(random.uniform(0.1, 0.3)))
        steps.append(ActionStepMouseUp())
        return steps
    
    def steps_move_to_center(self, ignore_step_change:bool=False) -> list[ActionStep]: 
        """ get action steps for moving the mouse to screen center""" 
        # Ignore step change (even during other players' turns) 
        steps = []
        delay_step = ActionStepDelay(random.uniform(0.2, 0.3))
        delay_step.ignore_step_change = ignore_step_change
        steps.append(delay_step)
        
        xmid, ymid = 16 * random.uniform(0.25, 0.75), 9 * random.uniform(0.25, 0.75)
        move_step = ActionStepMove(xmid*self.scaler, ymid*self.scaler, random.randint(2, 5))
        move_step.ignore_step_change = ignore_step_change
        steps.append(move_step)
        return steps
    
    def steps_random_wheels(self, total_dx:float, total_dy:float) -> list[ActionStep]:
        """ list of steps for mouse wheel
        params:
            total_dx, total_dy: total distance to wheel move"""
        # break the wheel action into several steps
        steps = []
        times = random.randint(4, 6)
        for _i in range(times):
            dx = total_dx / times
            dy = total_dy / times
            steps.append(ActionStepWheel(dx, dy))
            steps.append(ActionStepDelay(random.uniform(0.05, 0.10)))
        return steps

    def on_lobby_login(self, _liqimsg:dict):
        """ lobby login handler"""
        if self.ui_state != UiState.IN_GAME:
            self.stop_previous()
            self.ui_state = UiState.MAIN_MENU

    def on_enter_game(self):
        """ enter game handler"""
        self.stop_previous()
        self.ui_state = UiState.IN_GAME

    def on_end_game(self):
        """ end game handler"""
        self.stop_previous()
        if self.ui_state != UiState.NOT_RUNNING:
            self.ui_state = UiState.GAME_ENDING
        # if auto next. go to lobby, then next
        
    def on_exit_lobby(self):
        """ exit lobby handler"""
        if self.ui_state != UiState.IN_GAME:
            self.stop_previous()
            self.ui_state = UiState.NOT_RUNNING
   
    def automate_end_game(self):
        """Automate Game end go back to menu"""  
        if not self.can_automate():
            return False
        if self.st.auto_join_game is False:
            return False
        self.stop_previous()

        self._task = AutomationTask(self.executor, END_GAME, "Going back to main menu from game ending")
        self._task.start_action_steps(self._end_game_iter(), None)
        return True
        
    def _end_game_iter(self) -> Iterator[ActionStep]:
        # generate action steps for exiting a match until main menu tested
        while True:
            res, diff = self.g_v.comp_temp(ImgTemp.MAIN_MENU)
            if res:     # stop on main menu
                LOGGER.debug("Visual sees main menu with diff %.1f", diff)
                self.ui_state = UiState.MAIN_MENU
                break
            
            yield ActionStepDelay(random.uniform(2,3))
            
            x,y = Positions.GAMEOVER[0]
            for step in self.steps_randomized_move_click(x,y):
                yield step
            
    def automate_join_game(self):
        """ Automate join next game """
        if not self.can_automate():
            return False
        if self.st.auto_join_game is False:
            return False
        self.stop_previous()
        desc = f"Joining game (level={self.st.auto_join_level}, mode={self.st.auto_join_mode})"
        self._task = AutomationTask(self.executor, JOIN_GAME, desc)
        self._task.start_action_steps(self._join_game_iter(), None)
        return True
    
    def _join_game_iter(self) -> Iterator[ActionStep]:
        # generate action steps for joining next game
        
        while True:     # Wait for main menu
            res, diff = self.g_v.comp_temp(ImgTemp.MAIN_MENU)
            if res:
                LOGGER.debug("Visual sees main menu with diff %.1f", diff)
                self.ui_state = UiState.MAIN_MENU
                break
            yield ActionStepDelay(random.uniform(0.5, 1))
        
        # click on Ranked Mode
        x,y = Positions.MENUS[0]
        for step in self.steps_randomized_move_click(x,y):
            yield step
        yield ActionStepDelay(random.uniform(0.5, 1.5))
        
        # click on level        
        if self.st.auto_join_level >= 3:  # jade/throne requires mouse wheel
            wx,wy = Positions.LEVELS[1]         # wheel at this position
            for step in self.steps_randomized_move(wx,wy):
                yield step
            yield ActionStepDelay(random.uniform(0.5, 0.9))
            for step in self.steps_random_wheels(0, 1000):
                yield step
            yield ActionStepDelay(random.uniform(0.5, 1))                
        x,y = Positions.LEVELS[self.st.auto_join_level]
        for step in self.steps_randomized_move_click(x,y):
            yield step        
        yield ActionStepDelay(random.uniform(0.5, 1.5))
        
        # click on mode
        mode_idx = GAME_MODES.index(self.st.auto_join_mode)
        x,y = Positions.MODES[mode_idx]
        for step in self.steps_randomized_move_click(x,y):
            yield step    
    
    def decide_lobby_action(self):
        """ decide what "lobby action" to execute based on current state."""
        if not self.can_automate(True):
            return
        if self._task:      # Cancel if interval not reached
            if time.time() - self._task.last_exe_time < self.st.auto_retry_interval:                
                return False
            
        if self.ui_state == UiState.NOT_RUNNING:
            pass
        elif self.ui_state == UiState.MAIN_MENU:
            self.automate_join_game()
        elif self.ui_state == UiState.IN_GAME:
            pass
        elif self.ui_state == UiState.GAME_ENDING:
            self.automate_end_game()
        else:
            LOGGER.error("Unknow UI state:%s", self.ui_state)
