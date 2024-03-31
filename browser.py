import logging
import time
import threading
import queue
import random
import string

from pathlib import Path
from playwright._impl._errors import TargetClosedError
from playwright.sync_api import sync_playwright, BrowserContext, Page

import utils
from log_helper import LOGGER


DATA_FOLDER = 'browser_data'

class GameBrowser:
    """ Wrapper for Playwright browser controlling maj-soul operations"""  
    
    def __init__(self, width:int, height:int):
        """ Set browser with viewport size (width, height)"""
        self.width = width
        self.height = height
        self._action_queue = queue.Queue()       # thread safe queue for actions
        self._stop_event = threading.Event()    # set this event to stop processing actions
        self._browser_thread = None
        self.context:BrowserContext = None
        self.page:Page = None        # playwright page, only used by thread
        
        # for tracking page info
        self._page_title:str = None
        self._viewport_pos = None
        self._last_update_time:float = time.time()
        
        self._canvas_id = None
        
    def __del__(self):
        self.stop()
    
    def start(self, url:str, proxy:str=None, width:int=None, height:int=None):
        """ Launch the browser in a thread, and start processing action queue
        params:
            url(str): url of the page to open upon browser launch
            proxy(str): proxy server to use. e.g. http://1.2.3.4:555"
        """
        # using thread here to avoid playwright sync api not usable in async context (textual) issue
        if self.is_running():
            logging.info('Browser already running.')
            return
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        self._clear_action_queue()
        self._stop_event.clear()
        self._browser_thread = threading.Thread(
            target=self._run_browser_and_action_queue,
            args=(url, proxy),
            name="BrowserThread",
            daemon=True)
        self._browser_thread.start()
    
    def _run_browser_and_action_queue(self, url:str, proxy:str):
        """ run browser and keep processing action queue (blocking)"""
        if proxy:
            proxy_object = {"server": proxy}
        else:
            proxy_object = None
            
        LOGGER.info(f'Starting Chromium, viewport={self.width}x{self.height}, proxy={proxy}')
        with sync_playwright() as playwright:
            try:
                # Initilize browser
                chromium = playwright.chromium
                self.context = chromium.launch_persistent_context(
                    user_data_dir=Path(__file__).parent / DATA_FOLDER,
                    headless=False,
                    viewport={'width': self.width, 'height': self.height},
                    proxy=proxy_object,
                    ignore_default_args=["--enable-automation"],
                    args=["--noerrdialogs","--no-sandbox"]
                )
            except Exception as e:
                LOGGER.error('Error launching the browser: %s', e, exc_info=True)
                return            
            
            try:            
                self.page = self.context.new_page()
                self.page.goto(url)
            except Exception as e:
                LOGGER.error('Error opening page. Check if certificate is installed. \n%s',e)            
            
            # Do not allow new page tab
            def on_page(page:Page):
                LOGGER.info("Closing additional page. Only one Majsoul page is allowed")
                page.close()
            self.context.on("page", on_page)
            
            self._clear_action_queue()
            # keep running actions until stop event is set
            while self._stop_event.is_set() == False:
                # check if page is closed, break and exit
                try:
                    self._update_page_info()
                except Exception as e:
                    LOGGER.warning('Browser page not found')
                    break
                
                try:
                    action = self._action_queue.get(timeout=1)
                    action()
                except queue.Empty:                
                    pass
                except Exception as e:
                    LOGGER.error('Error processing action: %s', e, exc_info=True)
            
            # stop event is set: close browser
            LOGGER.debug("Closing browser")
            self._canvas_id = None  
            try:                
                if self.page.is_closed() == False:
                    self.page.close()
                self.page = None
                if self.context:
                    self.context.close()
                    self.context = None                
            except TargetClosedError as e:
                # ok if closed already
                pass                
            except Exception as e:
                LOGGER.error('Error closing browser: %s', e ,exc_info=True)            
        
        return
            
    def _clear_action_queue(self):        
        """ Clear the action queue"""
        while True:
            try:
                self._action_queue.get_nowait()
            except queue.Empty:
                break
            
    def stop(self):
        """ Shutdown browser thread"""
        self._stop_event.set()

    def is_running(self):
        """ return True if browser thread is still running"""
        if self._browser_thread and self._browser_thread.is_alive():
            return True
        else:
            return False
        
    def is_page_loaded(self):
        """ return True if page is loaded """
        if self.page:
            return True
        else:
            return False
    
    def is_overlay_on(self):
        """ return True if overlay is on and working"""
        if self.page is None:
            return False
        if self._canvas_id is None:
            return False
        return True        
    
    def mouse_click(self, x:int, y:int):
        """ Queue action: mouse click at (x,y) on viewport"""
        self._action_queue.put(lambda: self._mouse_click_action(x, y))
        
    def auto_hu(self):
        """ Queue action: Autohu action"""
        self._action_queue.put(lambda: self._auto_hu_action())
        
    def start_overlay(self):
        """ Queue action: Start showing the overlay"""
        self._action_queue.put(lambda: self._start_overlay_action())
        pass
    
    def stop_overlay(self):
        """ Queue action: Stop showing the overlay"""
        self._action_queue.put(lambda: self._stop_overlay_action())
        pass
    
    def overlay_update_text(self, guide_str:str, option_subtitle:str, options:list):
        """ Queue action: update text area
        params:
            guide_str(str): AI guide str (recommendation action)
            option_subtitle(str): subtitle for options (display before option list)
            options(list): list of (str, float), indicating action/tile with its probability """
        self._action_queue.put(lambda: self._overlay_update_text(guide_str, option_subtitle, options))
        pass
    
    def overlay_clear_text(self):
        """ Queue action: clear overlay text area"""
        self._action_queue.put(lambda: self._overlay_clear_text())
        pass
    
    def draw_bars(self, bars:list[float]):
        pass
        
    
        
    def _mouse_click_action(self, x:int, y:int):
        """ mouse click on page at (x,y)"""
        if self.page:
            # LOGGER.debug(f"Clicking on page ({x},{y})")
            self.page.mouse.move(x=x, y=y)
            time.sleep(0.15)
            self.page.mouse.click(x=x, y=y, delay=100)
            time.sleep(0.05)
            self.page.mouse.move(x=self.width/2, y=self.height/2)   # move mouse to center
        else:
            LOGGER.debug("No page, no click")
    
    def _auto_hu_action(self):
        """ call autohu function in page"""
        if self.page:
            # LOGGER.debug(f"Setting AutoHu")
            self.page.evaluate("() => view.DesktopMgr.Inst.setAutoHule(true)") 
        else:
            LOGGER.debug("No page, no autohu")
        
    def _start_overlay_action(self):
        """ Display overlay on page. Will ignore if already exist, or page is None"""
        # random 8-byte alpha-numeric string
        
        if self._canvas_id:     # if exist, skip and return
            return
        if self.page is None:
            return
        # LOGGER.debug("browser Start overlay")
        self._canvas_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        font_size = int(self.height/48)
        prompt:str = "Mahjong Copilot"
        js_code = f"""(() => {{
            // Create a canvas element and add it to the document body
            const canvas = document.createElement('canvas');
            canvas.id = '{self._canvas_id}';
            canvas.width = {self.width}; // Width of the canvas
            canvas.height = {self.height}; // Height of the canvas
            
            // Set styles to ensure the canvas is on top
            canvas.style.position = 'fixed'; // Use 'fixed' or 'absolute' positioning
            canvas.style.left = '0'; // Position at the top-left corner of the viewport
            canvas.style.top = '0';
            canvas.style.zIndex = '1000'; // High z-index to ensure it is on top
            canvas.style.pointerEvents = 'none'; // Make the canvas click-through
            document.body.appendChild(canvas);
            
            // Bot-left text
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = "#FFFFFF";
            ctx.textBaseline = "top"
            ctx.font = "{font_size}px Arial";       //double size for first line
            ctx.fillText("{prompt}", {self.width}*0.01, {self.height}*0.95);
            
            }})()"""
        self.page.evaluate(js_code)
        
    def _stop_overlay_action(self):
        """ Remove overlay from page. Will ignore if page is None, or overlay not on"""
        
        if self.is_overlay_on() == False:
            return
        # LOGGER.debug("browser Stop overlay")
        js_code = f"""(() => {{
            const canvas = document.getElementById('{self._canvas_id}');
            if (canvas) {{
                canvas.remove();
            }}
            }})()"""
        self.page.evaluate(js_code)
        self._canvas_id = None
    
    def _overlay_text_params(self):
        font_size = int(self.height/45)  # e.g., 22
        line_space = int(self.height/45/2)
        min_box_width = font_size * 15  # Minimum box width
        initial_box_height = line_space * 2 + (font_size + line_space) * 6  # based on number of lines
        box_top = int(self.height * 0.44)  # Distance from the top
        box_left = int(self.width * 0.14)  # Distance from the left
        return (font_size, line_space, min_box_width, initial_box_height, box_top, box_left)    
    
    def _overlay_update_text(self, line1: str, option_title: str, options: list[tuple[str, float]]):        
        if not self.is_overlay_on():
            return        
        font_size, line_space, min_box_width, initial_box_height, box_top, box_left = self._overlay_text_params()

        options_data = [[text, f"{perc*100:4.0f}%"] for text, perc in options]
        js_code = f"""
        (() => {{
            const canvas = document.getElementById('{self._canvas_id}');
            if (!canvas || !canvas.getContext) {{
                return;
            }}
            const ctx = canvas.getContext('2d');

            // Measure the first line of text to determine box width
            ctx.font = "{font_size * 2}px Arial";
            const firstLineMetrics = ctx.measureText("{line1}");
            let box_width = Math.max(firstLineMetrics.width + {font_size}*2, {min_box_width}); // set minimal width
            let box_height = {initial_box_height}; // Pre-defined box height based on number of lines
            
            // Clear the drawing area
            ctx.clearRect({box_left}, {box_top}, {self.width}-{box_left}, {initial_box_height});            
            // Draw the semi-transparent background box
            ctx.clearRect({box_left}, {box_top}, box_width, box_height);
            ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
            ctx.fillRect({box_left}, {box_top}, box_width, box_height);

            // Reset font to draw the first line
            ctx.fillStyle = "#FFFFFF";
            ctx.textBaseline = "top";
            ctx.fillText("{line1}", {box_left} + {font_size}, {box_top} + {line_space} * 2);

            // Adjust y-position for the subtitle and option lines
            let yPos = {box_top} + {font_size * 2} + {line_space} * 4; // Position after the first line
            ctx.font = "{font_size}px Arial"; // Font size for options subtitle and lines
            
            // Draw options subtitle
            ctx.fillText("{option_title}", {box_left} + {font_size}*2, yPos);
            yPos += {font_size} + {line_space}; // Adjust yPos for option lines

            // Draw each option line
            const options = {options_data};
            options.forEach(option => {{
                const [text, perc] = option;
                ctx.fillText(text, {box_left} + {font_size}*2, yPos); // Draw option text
                // Calculate right-aligned percentage position and draw
                const percWidth = ctx.measureText(perc).width;
                ctx.fillText(perc, {box_left} + {font_size}*11, yPos);
                yPos += {font_size} + {line_space}; // Adjust yPos for the next line
            }});
        }})();"""
        self.page.evaluate(js_code)
    
    def _overlay_clear_text(self):
        """ delete text and the background box"""
        if self.is_overlay_on() == False:
            return
        font_size, line_space, min_box_width, initial_box_height, box_top, box_left = self._overlay_text_params()
        
        js_code = f"""(() => {{
            const canvas = document.getElementById('{self._canvas_id}');
            if (!canvas || !canvas.getContext) {{
                return;
            }}
            const ctx = canvas.getContext('2d');

            // Clear the drawing area
            ctx.clearRect({box_left}, {box_top}, {self.width}-{box_left}, {initial_box_height});
        }});"""
        self.page.evaluate(js_code)
    
    def _overlay_update_indicators(self, reaction:dict):        
        pass
        
    def _update_page_info(self):
        """ update page title and url"""
        if time.time()-self._last_update_time > 0.5:
            self._last_update_time = time.time()
            self._page_title = self.page.title()
            self._viewport_pos = self.page.evaluate("""() => {
                return {
                    screenX: window.screenX,
                    screenY: window.screenY,
                    outerWidth: window.outerWidth,
                    innerWidth: window.innerWidth,
                    outerHeight: window.outerHeight,
                    innerHeight: window.innerHeight
                };
                }""")    
            
    def get_page_info(self):
        if self._page_title is not None and self._viewport_pos is not None:
            return self._page_title, self._viewport_pos
            # return get_window_positions_by_title(title), offsets
    
        # try:
        #     browser_path = self.context._impl_obj._parent.executable_path
        # except Exception as e:
        #     return None
        
        # pids = list(find_pids_by_executable(browser_path))





if __name__ == '__main__':
    # Test code for Browser
    import log_helper
    log_helper.config_logging('Browser')
    # Test for Browser
    MS_URL = 'https://game.maj-soul.com/1/'
    # proxy = None
    PROXY = "http://10.0.0.32:8002"
    browser = GameBrowser(1600, 900)
    browser.mouse_click(300, 300)
    browser.start(MS_URL, PROXY)
    browser.start(MS_URL, PROXY)

    LOGGER.info(f"browser on:{browser.is_running()}")
    while True:
        numbers_input = input("Enter x y :")
        numbers = numbers_input.split()
        x = int(numbers[0])
        y = int(numbers[1])
        if x==0 and y==0:
            break
        if x==-1:
            # a = browser.get_viewport_position()
            # print("viewport: ", a)
            browser.start_overlay()
            options = [("立直", 0.95123), ("[发]", 0.03123123), ("[六万]", 0.01111)]
            browser.overlay_update_text("立直,切[六万]","备选项:", options)
            continue
        if x == -2:
            browser.stop_overlay()
            continue
        browser.mouse_click(x, y)
    browser.auto_hu()
    time.sleep(1)
    browser.stop()
    browser.stop()
    browser.mouse_click(300, 300)
    time.sleep(1)
    print(f"browser on:{browser.is_running()}")
