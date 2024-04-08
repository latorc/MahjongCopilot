""" Game automation algorithm"""
from collections import namedtuple
from dataclasses import dataclass, field
import time
import random
import threading
from typing import Iterable, Iterator

from common.mj_helper import MJAI_TYPE, MSType, MJAI_TILES_19, MJAI_TILES_28
from common.mj_helper import sort_mjai_tiles, cvt_ms2mjai
from common.log_helper import LOGGER
from common.settings import Settings
from common.utils import UI_STATE, GAME_MODES

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
    
    GAMEOVER = [
        (14.35, 8.12),    # 点击确定按钮，此坐标位于大厅的"商家"和"寻觅"按钮之间
        (6.825, 6.8),     # 点击好感度礼物
    ]
    MENUS = [
        (11.5, 2.75),   #段位场
    ]
    
    LEVELS = [
        (11.5, 3.375),  # 铜之间
        (11.5, 4.825),  # 银之间
        (11.5, 6.15),   # 金之间
        (11.5, 5.425),  # 玉之间    滚轮    
        (11.5, 6.825),  # 王座之间  滚轮
    ]
    
    MODES = [
        (11.6, 3.325), # 四人东
        (11.6, 4.675), # 四人南
        (11.6, 6.1),   # 三人东
        (11.6, 7.35),  # 三人南
    ]



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
    if gi.my_tsumohai and mjai_type == MJAI_TYPE.HORA:
        return MSType.zimo
    else:
        return MJAI_2_MS_TYPE[mjai_type]
    

ActionStepTuple = namedtuple('ActionStepTuple', ['action', 'text'])


@dataclass
class ActionStep:
    """ representing an action step like single click/move/wheel/etc."""
    ignore_step_change:bool = field(default=False, init=False)
    
@dataclass
class ActionStepMove(ActionStep):
    """ Move mouse to x,y"""
    x:float
    y:float
    steps:int = field(default=5)    # playwright mouse move steps
    
@dataclass
class ActionStepClick(ActionStep):
    """ Click mouse left at x,y"""
    x:float
    y:float
    delay:float = field(default=80) # delay before button down/up
    
@dataclass
class ActionStepWheel(ActionStep):
    """ Mouse wheel action"""
    dx:float
    dy:float

@dataclass
class ActionStepDelay(ActionStep):
    """ Delay action"""
    delay:float
        

# Design: generate action steps based on mjai action (Automation)
# action steps are individual steps like delay, mouse click, etc. (ActionStep and derivatives)
# Then execute the steps in thread (AutomationTask).
# for in-game actions, verify if the action has expired, and cancel execution if needed
# for example, Majsoul before you finish "Chi", another player may "Pon"/"Ron"/..., which cancels your "Chi" action
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
            self.executor.mouse_click(step.x, step.y, step.delay, True)
        elif isinstance(step, ActionStepWheel):
            self.executor.mouse_wheel(step.dx, step.dy, True)
        elif isinstance(step, ActionStepDelay):
            time.sleep(step.delay)
        else:
            raise NotImplementedError(f"Execution not implemented for step type {type(step)}")
        self.last_exe_time = time.time()
        
    def start_action_steps(self, action_list:Iterable[ActionStep], game_state:GameState = None):
        """ start running action list/iterator in a thread"""
        if self.is_running():
            return
            
        def task():
            if game_state:
                op_step = game_state.last_op_step
            else:
                op_step = None
            LOGGER.debug("Start executing task: %s, %s", self.name, self.desc)    
            for step in action_list:
                if self._stop_event.is_set():
                    LOGGER.debug("Cancel executing %s. Stop event set",self.name)
                    return                
                if game_state:  
                    # check step change
                    # op step change indicates there is new liqi action, and old action has expired
                    # for example, when executing Chi, there might be another player Pon before Chi is finished
                    # upon which any action steps related to Chi should be canceled
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
    """ Convert mjai reaction messages to browser actions, automating the AI actions on Majsoul"""
    def __init__(self, browser: GameBrowser, setting:Settings):
        if browser is None:
            raise ValueError("Browser is None")
        self.executor = browser
        self.st = setting
        self.g_v = GameVisual(browser)
        
        self._task:AutomationTask = None        # the task thread        
        self.ui_state:UI_STATE = UI_STATE.NOT_RUNNING   # Where game UI is at. initially not running    
    
    def is_running_execution(self):
        """ if task is still running"""
        if self._task and self._task.is_running():
            return True
        else:
            return False
        
    def stop_previous(self):
        """ stop previous task execution if it is still running"""
        if self.is_running_execution():
            LOGGER.warning("Stopping previous action: %s", self._task.name)
            self._task.stop()
            self._task = None
            
    def can_automate(self) -> bool:
        """return True if automation conditions met 
        params:
            in_game(bool): True if must in game"""
        if not self.st.enable_automation: # automation not enabled
            return False
        if not self.executor.is_page_normal():  # browser is not running
            return False
        return True
        
    def get_delay(self, mjai_action:dict, gi:GameInfo):
        """ return the delay based on action type and game info"""
        mjai_type = mjai_action['type']
        delay = random.uniform(self.st.delay_random_lower, self.st.delay_random_upper)    # base delay        
        if mjai_type == MJAI_TYPE.DAHAI:
            # extra time for first round and East
            if gi.is_first_round:
                delay += 2
                if gi.jikaze  == 'E':
                    delay += 1.5
            pai = mjai_action['pai']
            
            # more time for 19>28>others
            if pai in MJAI_TILES_19:
                delay += 0.0
            elif pai in MJAI_TILES_28:
                delay += 0.5
            else:
                delay += 1.0
                
        elif mjai_type == MJAI_TYPE.REACH:
            delay += 1
        elif mjai_type == MJAI_TYPE.HORA:
            delay += 0
        else:       # chi/pon/kan/others
            delay += 0.5
        
        return delay
     
        
    def automate_action(self, mjai_action:dict, game_state:GameState):
        """ execute action given by the mjai message
        params:
            mjai_action(dict): mjai output action msg
            game_state(GameState): game state object"""
        if not self.can_automate():
            return False
        if game_state is None or mjai_action is None:
            return False
        
        self.stop_previous()
        gi = game_state.get_game_info()
        assert gi is not None, "Game info is None"
        op_step = game_state.last_op_step
        mjai_type = mjai_action['type']
        
        if 'pai' in mjai_action:
            pai = f"{mjai_action['pai']}"
        else:
            pai = ""        
        desc = f"Automating action {mjai_type} {pai} (step = {op_step})" 
        
        
        if  mjai_type == MJAI_TYPE.DAHAI:
            if gi.reached:
                # already in reach state. no need to automate dahai
                LOGGER.info("Skip automating dahai, already in REACH")
                game_state.last_reaction_pending = False        # cancel pending state so i won't be retried
                return False                        
            more_steps:list[ActionStep] = self.steps_action_dahai(mjai_action, gi)
            
        elif mjai_type in [MJAI_TYPE.NONE, MJAI_TYPE.CHI, MJAI_TYPE.PON, MJAI_TYPE.DAIMINKAN, MJAI_TYPE.ANKAN,
            MJAI_TYPE.KAKAN, MJAI_TYPE.HORA, MJAI_TYPE.REACH, MJAI_TYPE.RYUKYOKU, MJAI_TYPE.NUKIDORA]:
            liqi_operation = game_state.last_operation
            more_steps:list[ActionStep] = self.steps_button_action(mjai_action, gi, liqi_operation)
        
        else:
            LOGGER.error("No automation for unrecognized mjai type: %s", mjai_type)
            return
        
        delay = self.get_delay(mjai_action, gi)  # first action is delay
        action_steps:list[ActionStep] = [ActionStepDelay(delay)]
        action_steps.extend(more_steps)
        self._task = AutomationTask(self.executor, f"Auto_{mjai_type}_{pai}", desc)
        self._task.start_action_steps(action_steps, game_state)
    
    def last_exec_time(self):
        """ return the time of last action execution. return -1 if N/A"""
        if self._task:
            return self._task.last_exe_time
        else:
            return -1        
    
    def steps_action_dahai(self, mjai_action:dict, gi:GameInfo) -> list[ActionStepTuple]:
        """ generate dahai (discard tile) action
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
            steps = self.steps_randomized_move_click(x, y)         
        else:       # tedashi: find the index and discard
            idx = gi.my_tehai.index(dahai)
            steps = self.steps_randomized_move_click(Positions.TEHAI_X[idx], Positions.TEHAI_Y)
        # move to mid to avoid highlighting a tile 
        delay_step = ActionStepDelay(random.uniform(0.5, 0.1))
        delay_step.ignore_step_change = True
        steps.append(delay_step)
        
        xmid, ymid = random.uniform(0.2,0.8), random.uniform(0.2, 0.8)
        move_step = ActionStepMove(xmid*self.scaler, ymid*self.scaler, random.randint(3,5))
        move_step.ignore_step_change = True        
        steps.append(move_step)
        
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

    
    def steps_button_action(self, mjai_action:dict, gi:GameInfo, liqi_operation:dict) -> list[ActionStepTuple]:
        """Generate action steps for button actions (chi, pon, kan, etc.)"""       
        if 'operationList' not in liqi_operation:
            return []
        
        op_list:list = liqi_operation['operationList']
        op_list = op_list.copy()
        op_list.append({'type': 0})                             # add None/Pass button
        op_list.sort(key=lambda x: ACTION_PIORITY[x['type']])   # sort operation list by priority
        
        mjai_type = mjai_action['type']
        mstype_from_mjai = cvt_type_mjai_2_ms(mjai_type, gi)
        
        if mstype_from_mjai in [MSType.ankan, MSType.kakan]:
            op_list = self._process_oplist_for_kan(mstype_from_mjai, op_list)
        
        # Click on the corresponding button (None, Chii, Pon, etc.)
        steps = []
        the_op = None
        for idx, op in enumerate(op_list):
            if op['type'] == mstype_from_mjai:
                x, y = Positions.BUTTONS[idx]
                steps += self.steps_randomized_move_click(x,y)
                the_op = op
                break
        if the_op is None:
            # no liqi operation but mjai indicates operation. mismatch(e.g. last round no pon)
            LOGGER.error("No matching operation for mjai %s. Op list: %s", mjai_type, op_list)            
            return steps

        # process reach dahai action
        if mstype_from_mjai == MSType.reach:            
            reach_dahai = mjai_action['reach_dahai']
            delay = self.get_delay(reach_dahai, gi)
            steps.append(ActionStepDelay(delay))
            dahai_steps = self.steps_action_dahai(reach_dahai, gi)
            steps += dahai_steps
            return steps

        # chi / pon / kan: click candidate
        elif mstype_from_mjai in [MSType.chi, MSType.pon, MSType.daiminkan, MSType.kakan, MSType.ankan]:            
            # e.g. {'type': 'chi', 'actor': 3, 'target': 2, 'pai': '4m', 'consumed': ['3m', '5mr'], ...}"""
            mjai_consumed = mjai_action['consumed']
            mjai_consumed = sort_mjai_tiles(mjai_consumed)
            if 'combination' in the_op:
                combs = the_op['combination']
            else:
                combs = []
                
            if len(combs) == 1:
                # no need to click. return directly
                return steps
            elif len(combs) == 0:
                # something is wrong. no combination offered in liqi msg
                LOGGER.warning("mjai type %s, but no combination in liqi operation list", mjai_type)
                return steps
            for idx, comb in enumerate(combs):
                # for more than one candidate group, click on the matching group
                # groups in liqi msg are converted to mjai tile format for comparison
                consumed_liqi = [cvt_ms2mjai(t) for t in comb.split('|')]
                consumed_liqi = sort_mjai_tiles(consumed_liqi)
                if mjai_consumed == consumed_liqi:  # match. This is the combination to click on
                    delay = len(combs) * (0.5 + random.random())
                    steps.append(ActionStepDelay(delay))
                    if mstype_from_mjai in [MSType.chi, MSType.pon, MSType.daiminkan]:
                        candidate_idx = int((-(len(combs)/2)+idx+0.5)*2+5)
                        x,y = Positions.CANDIDATES[candidate_idx]
                        steps += self.steps_randomized_move_click(x,y)
                    elif mstype_from_mjai in [MSType.ankan, MSType.kakan]:
                        candidate_idx = int((-(len(combs)/2)+idx+0.5)*2+3)
                        x,y = Positions.CANDIDATES_KAN[candidate_idx]
                        steps += self.steps_randomized_move_click(x,y)
                    return steps
        
        # no additional clicks for other types
        else:
            return steps
    
    @property
    def scaler(self):
        """ scaler for 16x9 -> game resolution"""
        return self.executor.width/16
    
    def steps_randomized_move(self, x:float, y:float, random_moves:int=None) -> list[ActionStep]:
        """ generate list of steps for a randomized mouse move
        Params:
            x, y: target position in 16x9 resolution
            random_moves(int): number of random moves before target. None -> use randint"""
        steps = []
        if random_moves is None:
            random_moves = self.st.auto_random_moves
        
        for _i in range(random_moves):   # random moves, within (-0.5, 0.5) of target
            rx = x + 16*random.uniform(-0.5, 0.5)
            rx = max(0, min(16, rx))
            ry = y + 9*random.uniform(-0.5, 0.5)
            ry = max(0, min(9, ry))
            steps.append(ActionStepMove(rx*self.scaler, ry*self.scaler, random.randint(3,5)))
            steps.append(ActionStepDelay(random.uniform(0.05, 0.15)))
        tx, ty = x*self.scaler, y*self.scaler
        steps.append(ActionStepMove(tx, ty, random.randint(3,5)))
        return steps
    
    def steps_randomized_move_click(self, x:float, y:float, random_moves:int=None) -> list[ActionStep]:
        """ generate list of steps for a randomized mouse move and click
        Params:
            x, y: target position in 16x9 resolution
            random_moves(int): number of random moves before target. None -> use randint"""
        steps = self.steps_randomized_move(x, y, random_moves)
        steps.append(ActionStepDelay(random.uniform(0.25, 0.3)))
        steps.append(ActionStepClick(x*self.scaler, y*self.scaler, random.randint(60, 100)))
        return steps
    
    def steps_random_wheels(self, total_dx:float, total_dy:float) -> list[ActionStep]:
        """ list of steps for mouse wheel
        params:
            total_dx, total_dy: total distance to wheel move"""
        steps = []
        times = random.randint(4,6)
        for i in range(times):
            dx = total_dx / times
            dy = total_dy / times
            steps.append(ActionStepWheel(dx, dy))
            steps.append(ActionStepDelay(random.uniform(0.05, 0.1)))
        return steps

    def on_lobby_login(self, liqimsg:dict):
        """ lobby login handler"""
        self.stop_previous()
        self.ui_state = UI_STATE.MAIN_MENU

    def on_enter_game(self):
        """ enter game handler"""
        self.stop_previous()
        self.ui_state = UI_STATE.IN_GAME


    def on_end_game(self):
        """ end game handler"""
        self.stop_previous()
        self.ui_state = UI_STATE.GAME_ENDING
        # if auto next. go to lobby, then next
        
    def on_exit_lobby(self):
        """ exit lobby handler"""
        self.stop_previous()
        self.ui_state = UI_STATE.NOT_RUNNING
   
    def automate_end_game(self):
        """Automate Game end go back to menu"""  
        if not self.can_automate():
            return False
        if self.st.auto_join_game is False:
            return False
        self.stop_previous()

        self._task = AutomationTask(self.executor, END_GAME, "End game go back to main menu")
        self._task.start_action_steps(self._end_game_iter(), None)
        return
        
    def _end_game_iter(self) -> Iterator[ActionStep]:
        # generate action steps until main menu tested
        while True:
            res, diff = self.g_v.comp_temp(ImgTemp.main_menu)
            if res:
                LOGGER.debug("Visual sees main menu with diff %.1f", diff)
                self.ui_state = UI_STATE.MAIN_MENU
                break
            
            yield ActionStepDelay(random.uniform(1,2))
            
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
        desc = f"Join the next game level={self.st.auto_join_level}, mode={self.st.auto_join_mode}"
        self._task = AutomationTask(self.executor, JOIN_GAME, desc)
        self._task.start_action_steps(self._join_game_iter(), None)
        return   
    
    def _join_game_iter(self) -> Iterator[ActionStep]:
        # generate action steps for joining next game
        
        # Wait for main menu
        while True:
            res, diff = self.g_v.comp_temp(ImgTemp.main_menu)
            if res:
                LOGGER.debug("Visual sees main menu with diff %.1f", diff)
                self.ui_state = UI_STATE.MAIN_MENU
                break
            yield ActionStepDelay(random.uniform(1,2))
        
        # click on competitive
        x,y = Positions.MENUS[0]
        for step in self.steps_randomized_move_click(x,y):
            yield step
        yield ActionStepDelay(random.uniform(1.5,2))
        
        # click on level        
        if self.st.auto_join_level >= 3:  # jade/throne requires mouse wheel
            wx,wy = Positions.LEVELS[1]         # wheel at this position
            for step in self.steps_randomized_move(wx,wy):
                yield step
            for step in self.steps_random_wheels(0, 500):
                yield step                
        x,y = Positions.LEVELS[self.st.auto_join_level]
        for step in self.steps_randomized_move_click(x,y):
            yield step        
        yield ActionStepDelay(random.uniform(1.5,2))
        
        # click on mode
        mode_idx = GAME_MODES.index(self.st.auto_join_mode)
        x,y = Positions.MODES[mode_idx]
        for step in self.steps_randomized_move_click(x,y):
            yield step    
    
    def check_what_to_do(self):
        """ check what task to do next. called on bot thread loop"""
        if not self.can_automate():
            return
        if self.is_running_execution():
             # don't do anything if previous task is still running
            return
        if self._task:
            if time.time() - self._task.last_exe_time < 2.0:
                # interval not reached, cancel
                return False
            
        if self.ui_state == UI_STATE.NOT_RUNNING:
            pass
        elif self.ui_state == UI_STATE.MAIN_MENU:
            self.automate_join_game()
        elif self.ui_state == UI_STATE.IN_GAME:
            pass
        elif self.ui_state == UI_STATE.GAME_ENDING:
            self.automate_end_game()
            
    def on_automation_disable(self):
        """ call this when automation is disabled """
        self.stop_previous()
        
