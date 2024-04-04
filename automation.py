from collections import namedtuple
import time
import random
import threading
from typing import Iterator
from browser import GameBrowser
from game_state import GameInfo, GameState
import mj_helper
from mj_helper import MJAI_TYPE, MSType
from log_helper import LOGGER
import img_proc
from img_proc import ImgTemp
import settings
from utils import UI_STATE, GAME_MODES


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

ActionStep = namedtuple('ActionStep', ['action', 'text'])

class AutomationTask():
    NEXT_GAME_TASK_NAME = "Join next game"
    """ represeting a thread executing actions"""
    def __init__(self):
        self._stop_event = threading.Event()        # set event to stop running
        self._thread:threading.Thread = None
        self.last_exe_time:float = -1
        
    @property
    def name(self):
        if self._thread:
            return self._thread.name
        else:
            return None
        
    def stop(self, jointhread:bool=False):
        """ stop the thread"""
        self._stop_event.set()
        if jointhread:
            if self._thread:
                self._thread.join()
                
    def is_running(self):
        """ return true if thread is running"""
        if self._thread and self._thread.is_alive():
            return True
        else:
            return False
        
    def start_action_list(self, action_list:list[ActionStep], game_state:GameState = None):
        """ start running action list in a thread"""
        if self._thread:
            return
               
        if game_state:
            op_step = game_state.last_op_step
        else:
            op_step = None
            
        def run_action_list():
            for step in action_list:
                # verify if op_step changed, which indicates there is new liqi action, and old action has expired
                # for example, when executing Chi, there might be another player Pon before Chi is finished
                # upon which any action steps related to Chi should be canceled
                if self._stop_event.is_set():
                    LOGGER.debug("Cancel execution. Stop event set")
                    return
                
                if game_state:
                    game_step = game_state.last_op_step
                    if op_step != game_step:
                        LOGGER.debug("Cancel execution. origin step = %d, current step = %d", op_step, game_step)
                        return
                                
                LOGGER.debug("Executing step: %s", step.text)
                step.action()
                # record execution info for possible retry
                self.last_exe_time = time.time()
            LOGGER.debug("Finished executing task: %s", self.name)
        
        self._thread = threading.Thread(
            target=run_action_list,
            name=f"Auto_step_{op_step}",
            daemon=True
        )
        self._thread.start()
        
    def start_action_iter(self, action_iter:Iterator[ActionStep], name:str=None):
        """ Start running action steps from iterator in a thread
        Params:
            action_iter(Iterator[ActionStep]): iterator of action steps
            name: name for the task
        """
        if self._thread:
            return
        if name is None:
            name = ""
            
        def run_iter():
            for step in action_iter:
                if self._stop_event.is_set():
                    LOGGER.debug("Cancel execution. Stop event set")
                    return
                LOGGER.debug("Executing step: %s", step.text)
                step.action()
                self.last_exe_time = time.time()
            LOGGER.debug("Finished executing task: %s", self.name)
            
        self._thread = threading.Thread(
            target=run_iter,
            name=name,
            daemon=True
        )
        self._thread.start()

class Automation:
    """ Convert mjai reaction messages to browser actions, automating the AI actions on Majsoul"""
    def __init__(self, browser: GameBrowser, setting:settings.Settings):
        if browser is None:
            raise ValueError("Browser is None")
        self.browser = browser
        self.settings = setting
        self.g_v = img_proc.GameVisual(browser)
        
        self._task:AutomationTask = None        # the task thread
        
        self.ui_state:UI_STATE = UI_STATE.NOT_RUNNING   # Where game UI is at. initially not running
        
    
        
    def get_delay(self, mjai_action:dict, game_state:GameState):
        """ return the delay based on action type and game info"""
        mjai_type = mjai_action['type']
        delay = random.uniform(0.5, 1.5)    # base delay
        
        if mjai_type == MJAI_TYPE.DAHAI:
            # extra time for first round and East
            if game_state.first_round:
                delay += 1
                if game_state.jikaze  == 'E':
                    delay += 1.5
            pai = mjai_action['pai']
            
            # more time for 19>28>others
            if pai in mj_helper.MJAI_TILES_19:
                delay += 0.0
            elif pai in mj_helper.MJAI_TILES_28:
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
    
    def can_automation(self) -> bool:
        """return True if automation conditions met 
        params:
            in_game(bool): True if must in game"""
        # False if:
        # automation not enabled
        # browser is not running
        if not self.settings.enable_automation:
            return False
        if not self.browser.is_page_normal():
            return False
        return True
    
        
    def automate_action(self, mjai_action:dict, game_state:GameState):
        """ execute action given by the mjai message
        params:
            mjai_action(dict): mjai output action msg
            game_state(GameState): game state object"""
        if not self.can_automation():
            return False
        if game_state is None or mjai_action is None:
            return False
        
        self.stop_previous()
        gi = game_state.get_game_info()
        assert gi is not None, "Game info is None"
        op_step = game_state.last_op_step
        mjai_type = mjai_action['type']        
        
        # Design: generate action steps based on mjai action
        # action steps are individual steps like delay, mouse click, etc.
        # Then execute the steps in thread.
        # verify if the action has expired (Majsoul has new action/operation), and cancel executing if so
        if  mjai_type == MJAI_TYPE.DAHAI:
            if gi.reached:
                # already in reach state. no need to automate dahai
                LOGGER.info("Skip automating dahai, already in REACH")
                game_state.last_reaction_pending = False        # cancel pending state so i won't be retried
                return False
            LOGGER.info("Automating action '%s', ms step = %d", mjai_type, op_step)            
            more_steps:list[ActionStep] = self._dahai_action_steps(mjai_action, gi, game_state.first_round)
        elif mjai_type in [
            MJAI_TYPE.NONE, MJAI_TYPE.CHI, MJAI_TYPE.PON, MJAI_TYPE.DAIMINKAN, MJAI_TYPE.ANKAN,
            MJAI_TYPE.KAKAN, MJAI_TYPE.HORA, MJAI_TYPE.REACH, MJAI_TYPE.RYUKYOKU, MJAI_TYPE.NUKIDORA
            ]:
            LOGGER.info("Automating action '%s', ms step = %d", mjai_type, op_step)
            liqi_operation = game_state.last_operation
            more_steps:list[ActionStep] = self._button_action_steps(mjai_action, gi, liqi_operation)
        else:
            LOGGER.error("No automation, unrecognized mjai type: %s", mjai_type)
            return
        
        delay = self.get_delay(mjai_action, game_state)  # first action is delay
        action_steps:list[ActionStep] = [self._get_delay_step(delay)]
        action_steps.extend(more_steps)
        
        self._task = AutomationTask()
        self._task.start_action_list(action_steps, game_state)

        
    def stop_previous(self):
        """ stop previous task execution if it is still running"""
        if self.is_running_execution():
            LOGGER.warning("Previous action '%s' is still executing, stopping it", self._task.name)
            self._task.stop()
            self._task = None
    
    def is_running_execution(self):
        """ if task is still running"""
        if self._task and self._task.is_running():
            return True
        else:
            return False
    
    def retry_pending_reaction(self, game_state:GameState, min_interval:float=2):
        """ Retry pending action from game state. if current time > last execution time + min interval"""
        if not self.can_automation():
            return False
        if self.is_running_execution():
            # last action still executing, quit
            return False
        if self.ui_state != UI_STATE.IN_GAME:
            return False
        
        if self._task:
            if time.time() - self._task.last_exe_time < min_interval:
                # interval not reached, cancel
                return False
        
        if game_state is None:
            LOGGER.warning("Exit Automation. Game State is none!")
            return

        mjai_action = game_state.get_pending_reaction()
        if mjai_action is None:
            return
        
        LOGGER.info("Retry automating pending reaction: %s", mjai_action['type'])
        self.automate_action(mjai_action, game_state)
        
    
    def _dahai_action_steps(self, mjai_action:dict, gi:GameInfo, is_first_round:bool) -> list[ActionStep]:
        """ generate dahai (discard tile) action
        params:
            is_east_first(bool): if currently self is East and it's the first move"""
        dahai = mjai_action['pai']
        tsumogiri = mjai_action['tsumogiri']
        text = f"Dahai [{dahai}]"
        if tsumogiri:   # tsumogiri: discard right most
            dahai_count = len([tile for tile in gi.my_tehai if tile != '?'])
            assert dahai == gi.my_tsumohai, f"tsumogiri but dahai {dahai} != game tsumohai {gi.my_tsumohai}"
            # 14-tile tehai + no tsumohai treatment for East first round
            if is_first_round and gi.jikaze  == 'E':
                x = Positions.TEHAI_X[dahai_count]
                y = Positions.TEHAI_Y
            else:
                x = Positions.TEHAI_X[dahai_count] + Positions.TRUMO_SPACE
                y = Positions.TEHAI_Y
            step = self._get_moveclick_step(x,y,text)
            return [step]
        else:       # tedashi: find the index and discard
            idx = gi.my_tehai.index(dahai)
            step = self._get_moveclick_step(Positions.TEHAI_X[idx], Positions.TEHAI_Y, text)            
            return [step]
    
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
        if 'operationList' not in liqi_operation:
            return actions
        op_list:list = liqi_operation['operationList']
        op_list = op_list.copy()
        op_list.append({'type': 0})     # add None/Pass button
        op_list.sort(key=lambda x: ACTION_PIORITY[x['type']])   # sort operation list by priority       
        
        mjai_type = mjai_action['type']
        mstype_from_mjai = cvt_type_mjai_2_ms(mjai_type, gi)
        
        if mstype_from_mjai in [MSType.ankan, MSType.kakan]:
            op_list = self._process_oplist_for_kan(mstype_from_mjai, op_list)
        
        # Click on the corresponding button (None, Chii, Pon, etc.)
        the_op = None
        for idx, operation in enumerate(op_list):
            if operation['type'] == mstype_from_mjai:
                click_what = f"button {idx} ({mjai_type})"
                step = self._get_moveclick_step(Positions.BUTTONS[idx][0], Positions.BUTTONS[idx][1],click_what)
                actions.append(step)
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
            actions.append(self._get_delay_step(delay))
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
                LOGGER.warning("mjai type %s, but no combination in liqi operation list", mjai_type)
                return actions
            for idx, comb in enumerate(combs):  
                # for more than one candidate group, click on the matching group
                # groups in liqi msg are converted to mjai tile format for comparison
                consumed_liqi = [mj_helper.cvt_ms2mjai(t) for t in comb.split('|')]
                consumed_liqi = mj_helper.sort_mjai_tiles(consumed_liqi)
                if mjai_consumed == consumed_liqi:  # match. This is the combination to click on
                    delay = len(combs) * (0.5 + random.random())
                    actions.append(self._get_delay_step(delay))
                    click_what = f"candidate {mjai_consumed}"

                    if mstype_from_mjai in [MSType.chi, MSType.pon, MSType.daiminkan]:
                        candidate_idx = int((-(len(combs)/2)+idx+0.5)*2+5)
                        x,y = Positions.CANDIDATES[candidate_idx]
                        action = self._get_moveclick_step(x,y,click_what)

                    elif mstype_from_mjai in [MSType.ankan, MSType.kakan]:
                        candidate_idx = int((-(len(combs)/2)+idx+0.5)*2+3)
                        x,y = Positions.CANDIDATES_KAN[candidate_idx]
                        action = self._get_moveclick_step(x,y,click_what)

                    actions.append(action)
                    return actions
        else:
            return actions

    def mouse_move_click(self, x, y, random_moves:int=3, blocking:bool=False):
        """ call browser move n click function with 16x9 resolution"""
        if self.browser:
            scalar = self.browser.width/16
            self.browser.mouse_move_click(x * scalar, y * scalar, random_moves, blocking)
            
    def mouse_move(self,x,y,steps:int,blocking:bool=True):
        """ call browser mouse move. 16x9"""
        if self.browser:
            scalar = self.browser.width/16
            self.browser.mouse_move(x * scalar, y * scalar, steps, blocking)
    
    def mouse_click(self, x, y, delay:float, blocking:bool=True):
        """ call browser mouse click"""
        if self.browser:
            scalar = self.browser.width/16
            self.browser.mouse_click(x * scalar, y * scalar, delay, blocking)
    
    def mouse_wheel(self, dx:float, dy:float, blocking:bool=True):
        """ call browser mouse wheel"""
        if self.browser:
            self.browser.mouse_wheel(dx, dy, blocking)
    
    def _get_delay_step(self, delay:float) -> ActionStep:
        """ Generate a delay step"""
        text = f"delay {delay:.1f}s "
        return ActionStep(lambda: time.sleep(delay), text)
    
    def _get_moveclick_step(self, x:float, y:float, what:str, blocking:bool=True) -> ActionStep:
        """Generate a mouse click step
        params:
            x,y: in 16x9 resolution
            what(str): describe what is clicked"""
        text = f"clicking {what}"
        
        # Add random moves
        if self.settings.auto_random_move:
            random_moves = random.randint(1,5)
        else:
            random_moves = 0
        return ActionStep(lambda: self.mouse_move_click(x, y, random_moves, blocking), text)
    
    def _get_move_step(self, x:float, y:float, random_moves:int=3) -> ActionStep:
        """ generate mouse move with random move step
        Params:
            tx, ty: target position in 16x9 resolution"""
        text = f"Mouse move ({x}, {y}) (random={random_moves})"
        def move():
            for i in range(random_moves):   # random moves, within (-0.5, 0.5) of target
                rx = int(x + random.uniform(-0.5, 0.5))
                rx = max(0, min(1, rx))
                ry = int(y + random.uniform(-0.5, 0.5))
                ry = max(0, min(1, ry))
                self.mouse_move(x=rx, y=ry, steps=random.randint(5,15))
                time.sleep(0.11)
            self.mouse_move(x=rx, y=ry, steps=random.randint(5,15))
            # move to target
            self.mouse_move(x, y, random.randint(5,10))
            time.sleep(0.1)
        return ActionStep(move, text)
            
            
        return ActionStep(lambda: self.mouse_move(x, y, random_moves), text)
    
    def _get_random_move_click_step(
        self, x:float, y:float, what:str, random_moves:int=3, delay:float=80, blocking:bool=True) -> ActionStep:
        """ generate mirror browser move click"""
        # TODO tba
        text = f"clicking {what} (random_moves={random_moves})"
        
        def move_click():
            # random move and click in one action
            self.mouse_click(x, y, delay, blocking)
            
        return ActionStep(move_click, text)
    
    def _get_wheel_step(self, dx:float, dy:float, times:int, blocking:bool=True) -> ActionStep:
        """ generate mouse wheel step"""
        text = f"mouse wheel ({dx}, {dy}) x {times}"
        def wheel_action():
            for _ in range(times):
                self.mouse_wheel(dx, dy, blocking)
                time.sleep(0.1)                
        return ActionStep(wheel_action, text)


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
        """Game end go back to lobby"""  
        if not self.can_automation():
            return False
        if self.settings.auto_join_game is False:
            return False
        self.stop_previous()
        
        LOGGER.info("Automating game end to lobby")
        self._task = AutomationTask()
        self._task.start_action_iter(self._end_game_iter(), "End game to lobby")
        return
        
    def _end_game_iter(self) -> Iterator[ActionStep]:
        # generate action steps until main menu tested
        while True:
            res, diff = self.g_v.comp_temp(ImgTemp.main_menu)
            if res:
                LOGGER.debug("Main menu tested true with diff %.1f", diff)
                self.ui_state = UI_STATE.MAIN_MENU
                break
            
            yield self._get_delay_step(random.uniform(1,3))
            
            x,y = Positions.GAMEOVER[0]
            yield self._get_moveclick_step(x,y,"click OK until main menu")
            
    def automate_next_game(self):
        """ Automate from lobby to next game """
        if not self.can_automation():
            return False
        if self.settings.auto_join_game is False:
            return False
        self.stop_previous()
        
        LOGGER.info("Automating entering next game")
        self._task = AutomationTask()
        self._task.start_action_iter(self._next_game_action_iter(), AutomationTask.NEXT_GAME_TASK_NAME)
        return    
    
    def _next_game_action_iter(self) -> Iterator[ActionStep]:
        # generate action steps for next_game
        # Start from lobby
        while True:
            res, diff = self.g_v.comp_temp(ImgTemp.main_menu)
            if res:
                LOGGER.debug("Main menu tested true with diff %.1f", diff)
                self.ui_state = UI_STATE.MAIN_MENU
                break
            yield self._get_delay_step(random.uniform(1,3))
        
        # click on competitive
        x,y = Positions.MENUS[0]
        yield self._get_moveclick_step(x,y, "click menu [0]")
        yield self._get_delay_step(random.uniform(1.5,3))
        
        # click on level
        x,y = Positions.LEVELS[self.settings.auto_join_level]
        if self.settings.auto_join_level >= 3: # jade/throne requires mouse wheel
            wx,wy = Positions.LEVELS[1]     # wheel at this position
            yield self._get_move_step(wx, wy, random.randint(2,5))            
            yield self._get_wheel_step(dx=0, dy=random.uniform(0,100), times= random.randint(4,7))
        
        yield self._get_moveclick_step(x,y,f"click level [{self.settings.auto_join_level}]")
        
        yield self._get_delay_step(random.uniform(1.5,3))
        
        # click on mode
        mode_idx = GAME_MODES.index(self.settings.auto_join_mode)
        x,y = Positions.MODES[mode_idx]
        yield self._get_moveclick_step(x,y,f"click Mode [{self.settings.auto_join_mode}]")
    
    
    def check_what_to_do(self):
        """ check what task to do next. called on bot thread loop"""
        if not self.can_automation():
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
            self.automate_next_game()
        elif self.ui_state == UI_STATE.IN_GAME:
            pass
        elif self.ui_state == UI_STATE.GAME_ENDING:
            self.automate_end_game()
            
    def on_automation_disable(self):
        """ call this when automation is disabled """
        self.stop_previous()
        
        
        
