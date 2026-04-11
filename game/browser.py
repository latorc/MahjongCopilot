""" Game Broswer class for controlling maj-soul web client operations"""
import base64
import logging
import time
import threading
import queue
import os

from io import BytesIO
from playwright._impl._errors import TargetClosedError, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright, BrowserContext, Page
from common import utils
from common.utils import Folder, FPSCounter, list_children
from common.log_helper import LOGGER

class GameBrowser:
    """ Wrapper for Playwright browser controlling maj-soul operations
    Browser runs in a thread, and actions are queued to be processed by the thread"""
    CLIENT_SIZE_TOLERANCE_PX = 4
    LAUNCH_CONTEXT_TIMEOUT_MS = 6000
    LAUNCH_TIMEOUT_RETRY_DELAY_S = 2.0
    BROWSER_STOP_JOIN_TIMEOUT = 5.0
    STARTUP_CLICK_POS = (5, 5)
    TRANSIENT_PAGE_ERROR_PATTERNS = (
        "execution context was destroyed",
        "cannot find context with specified id",
        "most likely because of a navigation",
    )

    def __init__(self, width:int, height:int):
        """ Set browser with viewport size (width, height)"""
        self.width = width
        self.height = height
        self._action_queue = queue.Queue()       # thread safe queue for actions
        self._stop_event = threading.Event()    # set this event to stop processing actions
        self._browser_thread = None

        self.init_vars()

    def init_vars(self):
        """ initialize internal variables"""
        self.context:BrowserContext = None
        self.page:Page = None        # playwright page, only used by thread
        self._page_cdp_session = None
        self.fps_counter = FPSCounter()

        # for tracking page info
        self._page_title:str = None
        self._last_update_time:float = 0
        self.zoomlevel_check:float = None
        self.client_size_check:tuple[int, int] | None = None

        # overlay info
        self._canvas_id = None              # for overlay
        self._last_botleft_text = None
        self._last_guide = None

    def __del__(self):
        self.stop()

    def _build_launch_args(self, url:str, enable_chrome_ext:bool, extensions_list:list[str] | None = None) -> list[str]:
        """ Build Chromium launch args.
        Use app mode to hide browser tabs/address bar while keeping a native title bar."""
        args = [
            "--noerrdialogs",
            f"--app={url}",
            f"--window-size={self.width},{self.height}",
            # Chromium upstream test harnesses use this flag to suppress the
            # "Google API keys are missing" infobar.
            "--test-type=gpu",
        ]
        if os.name != "nt":
            args.append("--no-sandbox")
        if enable_chrome_ext and extensions_list:
            args.extend([
                "--disable-extensions-except=" + ",".join(extensions_list),
                "--load-extension=" + ",".join(extensions_list),
            ])
        return args

    def _build_launch_options(self, url:str, proxy_object:dict | None, enable_chrome_ext:bool, extensions_list:list[str]) -> dict:
        """ Build launch kwargs for Playwright Chromium persistent context."""
        launch_options = {
            "user_data_dir": utils.sub_folder(Folder.BROWSER_DATA),
            "headless": False,
            "no_viewport": True,
            "timeout": self.LAUNCH_CONTEXT_TIMEOUT_MS,
            "proxy": proxy_object,
            "ignore_default_args": ["--enable-automation"],
            "args": self._build_launch_args(url, enable_chrome_ext, extensions_list),
        }

        if os.name == "nt":
            launch_options["chromium_sandbox"] = True

        return launch_options

    def _get_primary_page(self, timeout_ms:int=10000) -> Page:
        """ Return the main non-extension page created by Chromium app mode."""
        timeout_at = time.time() + timeout_ms / 1000
        while time.time() < timeout_at:
            for page in self.context.pages:
                if not page.url.startswith("chrome-extension://"):
                    return page
            time.sleep(0.05)
        raise RuntimeError("Timed out waiting for Chromium app page")

    def _get_window_metrics(self) -> dict:
        """ Return current browser/page size metrics."""
        return self.page.evaluate("""() => ({
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            outerWidth: window.outerWidth,
            outerHeight: window.outerHeight,
            devicePixelRatio: window.devicePixelRatio,
        })""")

    def _calibrate_window_bounds(self, max_attempts:int=6):
        """ Resize the outer Chromium app window until the page client area matches target size.

        App mode with Playwright Chromium can leave extra client-area space after browser UI
        infobars are suppressed, which shows up as a bottom black bar. We keep the content area
        exactly at the configured automation resolution so coordinates remain valid.
        """
        cdp = self.context.new_cdp_session(self.page)
        try:
            for _ in range(max_attempts):
                metrics = self._get_window_metrics()
                delta_w = int(round(self.width - metrics['innerWidth']))
                delta_h = int(round(self.height - metrics['innerHeight']))
                if (
                    abs(delta_w) <= self.CLIENT_SIZE_TOLERANCE_PX and
                    abs(delta_h) <= self.CLIENT_SIZE_TOLERANCE_PX
                ):
                    LOGGER.info(
                        "Browser client area calibrated: inner=%sx%s outer=%sx%s dpr=%s tolerance=%spx",
                        metrics['innerWidth'],
                        metrics['innerHeight'],
                        metrics['outerWidth'],
                        metrics['outerHeight'],
                        metrics['devicePixelRatio'],
                        self.CLIENT_SIZE_TOLERANCE_PX,
                    )
                    return

                window_info = cdp.send("Browser.getWindowForTarget")
                bounds = window_info.get('bounds', {})
                current_outer_w = bounds.get('width', metrics['outerWidth'])
                current_outer_h = bounds.get('height', metrics['outerHeight'])
                new_bounds = {
                    'width': max(100, int(round(current_outer_w + delta_w))),
                    'height': max(100, int(round(current_outer_h + delta_h))),
                }
                cdp.send(
                    "Browser.setWindowBounds",
                    {
                        'windowId': window_info['windowId'],
                        'bounds': new_bounds,
                    }
                )
                time.sleep(0.12)

            metrics = self._get_window_metrics()
            LOGGER.warning(
                "Browser client area not fully calibrated: inner=%sx%s target=%sx%s tolerance=%spx",
                metrics['innerWidth'],
                metrics['innerHeight'],
                self.width,
                self.height,
                self.CLIENT_SIZE_TOLERANCE_PX,
            )
        finally:
            cdp.detach()

    def start(self, url:str, proxy:str=None, width:int=None, height:int=None, enable_chrome_ext:bool=False):
        """ Launch the browser in a thread, and start processing action queue
        params:
            url(str): url of the page to open upon browser launch
            proxy(str): proxy server to use. e.g. http://1.2.3.4:555"
            width, height: viewport width and height
            enable_ext: True to enable chrome extensions
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
            args=(url, proxy, enable_chrome_ext),
            name="BrowserThread",
            daemon=True)
        self._browser_thread.start()


    def _run_browser_and_action_queue(self, url:str, proxy:str, enable_chrome_ext:bool=False):
        """ run browser and keep processing action queue (blocking)"""
        
        if proxy:
            proxy_object = {"server": proxy}
        else:
            proxy_object = None

        # read all subfolder names from Folder.CRX and form extension list
        extensions_list = []
        if enable_chrome_ext:
            extensions_list = list_children(Folder.CHROME_EXT, True, False, True)
            LOGGER.info('Extensions loaded: %s', extensions_list)
        launch_options = self._build_launch_options(url, proxy_object, enable_chrome_ext, extensions_list)

        with sync_playwright() as playwright:
            chromium = playwright.chromium
            launch_attempt = 0

            while not self._stop_event.is_set():
                launch_attempt += 1
                LOGGER.info(
                    'Starting Chromium, viewport=%dx%d, proxy=%s (attempt %d)',
                    self.width,
                    self.height,
                    proxy,
                    launch_attempt,
                )
                try:
                    self.context = chromium.launch_persistent_context(**launch_options)
                    self.page = self._get_primary_page()
                    if self.page.url != url:
                        self.page.goto(url)
                    self._page_cdp_session = self.context.new_cdp_session(self.page)
                    self._calibrate_window_bounds()
                    click_x, click_y = self.STARTUP_CLICK_POS
                    self.page.mouse.click(x=click_x, y=click_y, delay=60)
                    break
                except PlaywrightTimeoutError as e:
                    LOGGER.warning(
                        "Browser startup timed out after %dms (attempt %d). Closing and retrying in %.1fs.",
                        self.LAUNCH_CONTEXT_TIMEOUT_MS,
                        launch_attempt,
                        self.LAUNCH_TIMEOUT_RETRY_DELAY_S,
                    )
                    LOGGER.debug("Startup timeout details: %s", e)
                    self._cleanup_after_init_failure()
                    if self._stop_event.wait(self.LAUNCH_TIMEOUT_RETRY_DELAY_S):
                        return
                except RuntimeError as e:
                    if "Timed out waiting for Chromium app page" in str(e):
                        LOGGER.warning(
                            "Browser startup timed out waiting for app page (attempt %d). Closing and retrying in %.1fs.",
                            launch_attempt,
                            self.LAUNCH_TIMEOUT_RETRY_DELAY_S,
                        )
                        self._cleanup_after_init_failure()
                        if self._stop_event.wait(self.LAUNCH_TIMEOUT_RETRY_DELAY_S):
                            return
                        continue
                    LOGGER.error('Error opening page. Browser init aborted.\n%s', e, exc_info=True)
                    self._cleanup_after_init_failure()
                    return
                except Exception as e:
                    LOGGER.error('Error launching the browser: %s', e, exc_info=True)
                    self._cleanup_after_init_failure()
                    return
            else:
                return

            # # Do not allow new page tab
            # def on_page(page:Page):
            #     LOGGER.info("Closing additional page. Only one Majsoul page is allowed")
            #     page.close()

            # if not enable_extensions:
            #     self.context.on("page", on_page)

            self._clear_action_queue()
            # keep running actions until stop event is set
            while self._stop_event.is_set() is False:
                self.fps_counter.frame()
                try:        # test if page is stil alive
                    if time.time() - self._last_update_time > 1:
                        self._page_title = self.page.title()
                        metrics = self._get_window_metrics()
                        self.zoomlevel_check = metrics['devicePixelRatio']
                        self.client_size_check = (metrics['innerWidth'], metrics['innerHeight'])
                        self._last_update_time = time.time()
                except Exception as e:
                    if self._stop_event.is_set():
                        break
                    if self._is_transient_page_error(e):
                        LOGGER.debug("Transient page error during navigation: %s", e)
                        time.sleep(0.05)
                        continue
                    LOGGER.warning("Page error %s. exiting.", e)
                    break

                try:
                    action = self._action_queue.get_nowait()
                    action()
                    # LOGGER.debug("Browser action %s",str(action))
                except queue.Empty:
                    time.sleep(0.002)
                except Exception as e:
                    LOGGER.error('Error processing action: %s', e, exc_info=True)

            # stop event is set: close browser
            LOGGER.debug("Closing browser")
            try:
                if self.page.is_closed() is False:
                    self.page.close()
                if self.context:
                    self.context.close()
            except TargetClosedError as e:
                # ok if closed already
                pass
            except Exception as e:
                LOGGER.error('Error closing browser: %s', e ,exc_info=True)
            self.init_vars()
        return

    def _cleanup_after_init_failure(self):
        """Best-effort cleanup when browser startup fails before entering main loop."""
        try:
            if self.page and self.page.is_closed() is False:
                self.page.close()
            if self.context:
                self.context.close()
        except TargetClosedError:
            pass
        except Exception as e:
            LOGGER.debug("Ignore cleanup error after init failure: %s", e)
        finally:
            self.init_vars()

    def _clear_action_queue(self):
        """ Clear the action queue"""
        while True:
            try:
                self._action_queue.get_nowait()
            except queue.Empty:
                break

    def _is_transient_page_error(self, err:Exception) -> bool:
        """Return True for temporary navigation errors that should not kill the browser loop."""
        err_text = str(err).lower()
        return any(pattern in err_text for pattern in self.TRANSIENT_PAGE_ERROR_PATTERNS)

    def stop(self, join_thread:bool=False):
        """ Shutdown browser thread"""
        thread = self._browser_thread
        if thread is None:
            return True

        if thread.is_alive():
            self._stop_event.set()
            if join_thread:
                thread.join(timeout=self.BROWSER_STOP_JOIN_TIMEOUT)
                if thread.is_alive():
                    LOGGER.error(
                        "Timed out waiting %.1fs for browser thread to stop",
                        self.BROWSER_STOP_JOIN_TIMEOUT,
                    )
                    return False

        if not thread.is_alive():
            self._browser_thread = None
        return not thread.is_alive()

    def is_running(self):
        """ return True if browser thread is still running"""
        if self._browser_thread and self._browser_thread.is_alive():
            return True
        else:
            return False

    def is_page_normal(self):
        """ return True if page is loaded """
        if self.page:
            if self._page_title:
                return True
        else:
            return False

    def is_overlay_working(self):
        """ return True if overlay is on and working"""
        if self.page is None:
            return False
        if self._canvas_id is None:
            return False
        return True

    def mouse_move(self, x:int, y:int, steps:int=5, blocking:bool=False):
        """ Queue action: mouse move to (x,y) on viewport
        if block, wait until action is done"""
        finish_event = threading.Event()
        self._action_queue.put(lambda: self._action_mouse_move(x, y, steps, finish_event))
        if blocking:
            finish_event.wait()

    def mouse_click(self, delay:float=80, blocking:bool=False):
        """ Queue action: mouse click at (x,y) on viewport
        if block, wait until action is done"""
        finish_event = threading.Event()
        self._action_queue.put(lambda: self._action_mouse_click(delay, finish_event))
        if blocking:
            finish_event.wait()

    def mouse_down(self, blocking:bool=False):
        """ Queue action: mouse down on page"""
        finish_event = threading.Event()
        self._action_queue.put(lambda: self._action_mouse_down(finish_event))
        if blocking:
            finish_event.wait()

    def mouse_up(self,blocking:bool=False):
        """ Queue action: mouse up on page"""
        finish_event = threading.Event()
        self._action_queue.put(lambda: self._action_mouse_up(finish_event))
        if blocking:
            finish_event.wait()

    def mouse_wheel(self, dx:float, dy:float, blocking:bool=False):
        """ Queue action for mouse wheel"""
        finish_event = threading.Event()
        self._action_queue.put(lambda: self._action_mouse_wheel(dx, dy, finish_event))
        if blocking:
            finish_event.wait()

    def auto_hu(self):
        """ Queue action: Autohu action"""
        self._action_queue.put(self._action_autohu)

    def start_overlay(self):
        """ Queue action: Start showing the overlay"""
        self._last_botleft_text = None
        self._last_guide = None
        self._action_queue.put(self._action_start_overlay)

    def stop_overlay(self):
        """ Queue action: Stop showing the overlay"""
        self._action_queue.put(self._action_stop_overlay)

    def overlay_update_guidance(self, guide_str:str, option_subtitle:str, options:list):
        """ Queue action: update text area
        params:
            guide_str(str): AI guide str (recommendation action)
            option_subtitle(str): subtitle for options (display before option list)
            options(list): list of (str, float), indicating action/tile with its probability """
        if self._last_guide == (guide_str, option_subtitle, options):  # skip if same guide
            return
        self._action_queue.put(lambda: self._action_overlay_update_guide(guide_str, option_subtitle, options))

    def overlay_clear_guidance(self):
        """ Queue action: clear overlay text area"""
        if self._last_guide is None:  # skip if already cleared
            return
        self._action_queue.put(self._action_overlay_clear_guide)

    def overlay_update_botleft(self, text:str):
        """ update bot-left corner text area
        params:
            text(str): Text, can have linebreak '\n'. None to clear text
        """
        if text == self._last_botleft_text:     # skip if same text
            return
        self._action_queue.put(lambda: self._action_overlay_update_botleft(text))


    def screen_shot(self) -> bytes | None:
        """ Take broswer page screenshot and return buff if success, or None if not"""
        if not self.is_page_normal():
            return None
        res_queue = queue.Queue()
        try:
            self._action_queue.put(lambda: self._action_screen_shot(res_queue))
            res:BytesIO = res_queue.get(True,5)
        except queue.Empty:
            return None
        except Exception as e:
            LOGGER.error("Error taking screenshot: %s", e, exc_info=True)
            return None

        if res is None:
            return None
        else:
            return res

    def _action_mouse_move(self, x:int, y:int, steps:int, finish_event:threading.Event):
        """ move mouse to (x,y) with steps, and set finish_event when done"""
        self.page.mouse.move(x=x, y=y, steps=steps)
        finish_event.set()

    def _action_mouse_click(self, delay:float, finish_event:threading.Event):
        """ mouse click on page at (x,y)"""
        # self.page.mouse.click(x=x, y=y, delay=delay)
        self.page.mouse.down()
        time.sleep(delay/1000)
        self.page.mouse.up()
        finish_event.set()

    def _action_mouse_down(self, finish_event:threading.Event):
        """ mouse down on page"""
        self.page.mouse.down()
        finish_event.set()

    def _action_mouse_up(self, finish_event:threading.Event):
        """ mouse up on page"""
        self.page.mouse.up()
        finish_event.set()

    def _action_mouse_wheel(self, dx:float, dy:float, finish_event:threading.Event):
        self.page.mouse.wheel(dx, dy)
        finish_event.set()

    def _action_autohu(self):
        """ call autohu function in page"""
        self.page.evaluate("() => view.DesktopMgr.Inst.setAutoHule(true)")

    def _action_start_overlay(self):
        """ Display overlay on page. Will ignore if already exist, or page is None"""

        if self.is_overlay_working():   # skip if overlay already working
            return
        self._canvas_id = utils.random_str(8) # random 8-byte alpha-numeric string
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
            canvas.style.zIndex = '9999999'; // High z-index to ensure it is on top
            canvas.style.pointerEvents = 'none'; // Make the canvas click-through
            document.body.appendChild(canvas);            
            }})()"""
        self.page.evaluate(js_code)

    def _action_stop_overlay(self):
        """ Remove overlay from page"""

        if self.is_overlay_working() is False:
            return
        js_code = f"""(() => {{
            const canvas = document.getElementById('{self._canvas_id}');
            if (canvas) {{
                canvas.remove();
            }}
            }})()"""
        self.page.evaluate(js_code)
        self._canvas_id = None
        self._botleft_text = None
        self._last_guide = None

    def _overlay_text_params(self):
        font_size = int(self.height/45)  # e.g., 22
        line_space = int(self.height/45/2)
        min_box_width = font_size * 15  # Minimum box width
        initial_box_height = line_space * 2 + (font_size + line_space) * 6  # based on number of lines
        box_top = int(self.height * 0.44)  # Distance from the top
        box_left = int(self.width * 0.14)  # Distance from the left
        return (font_size, line_space, min_box_width, initial_box_height, box_top, box_left)

    def _action_overlay_update_guide(self, line1: str, option_title: str, options: list[tuple[str, float]]):
        if not self.is_overlay_working():
            return

        font_size, line_space, min_box_width, initial_box_height, box_top, box_left = self._overlay_text_params()
        if options:
            options_data = [[text, f"{perc*100:4.0f}%"] for text, perc in options]
        else:
            options_data = []

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
        self._last_guide = (line1, option_title, options)

    def _action_overlay_clear_guide(self):
        """ delete text and the background box"""
        if self.is_overlay_working() is False:
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
        self._last_guide = None

    def _action_overlay_update_botleft(self, text:str=None):
        if self.is_overlay_working() is False:
            return

        font_size = int(self.height/48)
        box_top = 0.885
        box_left = 0
        box_width = 0.115
        box_height = 1- box_top

        # Escape JavaScript special characters and convert newlines
        js_text = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') if text else ''

        js_code = f"""(() => {{
            // find canvas context
            const canvas = document.getElementById('{self._canvas_id}');
            if (!canvas || !canvas.getContext) {{
                return;
            }}
            const ctx = canvas.getContext('2d');  
            
            // clear box          
            const box_left = canvas.width * {box_left};
            const box_top = canvas.height * {box_top};
            const box_width = canvas.width * {box_width};
            const box_height = canvas.height * {box_height};
            ctx.clearRect(box_left, box_top, box_width, box_height);
            
            // transparent box background
            ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
            ctx.fillRect(box_left, box_top, box_width, box_height);            
            
            // draw text
            const text = "{js_text}"
            if (!text) {{
                return; // Skip drawing if text is empty
            }}
            
            ctx.fillStyle = "#FFFFFF";
            ctx.textBaseline = "top"
            ctx.font = "{font_size}px Arial";
            
            // Split text into lines and draw each line
            const lines = text.split('\\n');
            const textX = {font_size} * 0.25
            let startY = canvas.height * {box_top} + {font_size}*0.5;
            const lineHeight = {font_size} * 1.2; // Adjust line height as needed
            lines.forEach((line, index) => {{
                ctx.fillText(line, canvas.width * {box_left} + textX, startY + (lineHeight * index));
            }});            
        }})()"""
        self.page.evaluate(js_code)
        self._last_botleft_text = text

    def _overlay_update_indicators(self, bars:list):
        """ Update the indicators on overlay """
        # TODO
        for x,y,height in bars:
            pass


    def _action_screen_shot(self, res_queue:queue.Queue, time_ms:int=5000):
        """ take screen shot from browser page
        Params:
            res_queue: queue for saving the image buff data"""
        if self.is_page_normal():
            try:
                if self._page_cdp_session is None:
                    self._page_cdp_session = self.context.new_cdp_session(self.page)
                payload = self._page_cdp_session.send(
                    "Page.captureScreenshot",
                    {
                        "format": "png",
                        "fromSurface": True,
                        "captureBeyondViewport": False,
                        "optimizeForSpeed": True,
                    },
                )
                ss_bytes = base64.b64decode(payload["data"])
                res_queue.put(ss_bytes)
            except Exception as cdp_error:
                LOGGER.warning("CDP screenshot failed, falling back to Playwright screenshot: %s", cdp_error)
                self._page_cdp_session = None
                try:
                    ss_bytes:BytesIO = self.page.screenshot(
                        timeout=time_ms,
                        animations="disabled",
                        caret="hide",
                        scale="css",
                    )
                    res_queue.put(ss_bytes)
                except Exception as e:
                    LOGGER.error("Error taking screenshot: %s", e, exc_info=True)
                    res_queue.put(None)
        else:
            res_queue.put(None)
            LOGGER.debug("Page not loaded, no screenshot")
