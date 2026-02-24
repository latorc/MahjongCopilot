""" Game Broswer class for controlling maj-soul web client operations"""
import json
import logging
import sys
import time
import threading
import queue
import os
import pathlib
import ctypes
import math
import random

from io import BytesIO
from playwright._impl._errors import TargetClosedError
from playwright.sync_api import sync_playwright, BrowserContext, Page
from common import utils
from common.utils import Folder, FPSCounter, list_children
from common.log_helper import LOGGER

class GameBrowser:
    """ Wrapper for Playwright browser controlling maj-soul operations
    Browser runs in a thread, and actions are queued to be processed by the thread"""

    def __init__(self, width:int, height:int):
        """ Set browser with viewport size (width, height)"""
        self.width = width
        self.height = height
        self.real_mouse_offset_x = self._read_env_int("MJ_REAL_MOUSE_OFFSET_X", 0)
        self.real_mouse_offset_y = self._read_env_int("MJ_REAL_MOUSE_OFFSET_Y", 0)
        self.real_mouse_speed_pps = max(300.0, self._read_env_float("MJ_REAL_MOUSE_SPEED_PPS", 2200.0))
        self.real_mouse_jitter_px = max(0.0, self._read_env_float("MJ_REAL_MOUSE_JITTER_PX", 2.0))
        self.real_mouse_click_offset_px = max(0.0, self._read_env_float("MJ_REAL_MOUSE_CLICK_OFFSET_PX", 2.0))
        self.real_mouse_min_move_ms = max(30, self._read_env_int("MJ_REAL_MOUSE_MIN_MOVE_MS", 100))
        self.real_mouse_max_move_ms = max(
            self.real_mouse_min_move_ms,
            self._read_env_int("MJ_REAL_MOUSE_MAX_MOVE_MS", 450)
        )
        self.browser_profile_dir = self._get_profile_dir()
        self._action_queue = queue.Queue()       # thread safe queue for actions
        self._stop_event = threading.Event()    # set this event to stop processing actions
        self._browser_thread = None

        self.init_vars()

    @staticmethod
    def _read_env_int(name:str, default:int=0) -> int:
        """ Read integer env var with fallback."""
        try:
            return int(os.environ.get(name, str(default)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _read_env_float(name:str, default:float=0.0) -> float:
        """ Read float env var with fallback."""
        try:
            return float(os.environ.get(name, str(default)))
        except (TypeError, ValueError):
            return default

    def _get_profile_dir(self, stable:bool=False) -> str:
        """Return browser user data directory path.

        stable=True keeps cache/profile between launches (used by mac high-quality mode).
        stable=False isolates profile per process.
        """
        base_dir = pathlib.Path(utils.sub_folder(Folder.BROWSER_DATA))
        if stable:
            profile_dir = base_dir / "profile_default"
        else:
            pid = os.getpid()
            profile_dir = base_dir / f"instance_{pid}"
        profile_dir.mkdir(parents=True, exist_ok=True)
        return str(profile_dir.resolve())

    @staticmethod
    def _is_profile_dir_error(error:Exception) -> bool:
        """Return True if launch error likely caused by locked/invalid profile directory."""
        msg = str(error).lower()
        keywords = (
            "singleton",
            "profile",
            "user data directory",
            "lock",
            "in use",
            "access is denied",
        )
        return any(k in msg for k in keywords)

    def _launch_context_with_channel_fallback(self, chromium, launch_kwargs:dict) -> BrowserContext:
        """Launch Chromium context, with optional system-channel fallback for missing binaries."""
        try:
            return chromium.launch_persistent_context(**launch_kwargs)
        except Exception as e:
            msg = str(e)
            if "Executable doesn't exist" not in msg and "playwright install" not in msg:
                raise
            for channel in ("msedge", "chrome"):
                try:
                    LOGGER.warning(
                        "Playwright Chromium executable missing; falling back to channel=%s",
                        channel
                    )
                    return chromium.launch_persistent_context(channel=channel, **launch_kwargs)
                except Exception:
                    continue
            raise

    @staticmethod
    def _playwright_driver_package_dir() -> pathlib.Path | None:
        """Locate Playwright driver 'package' directory.

        In PyInstaller one-dir builds, it's typically under:
          <app>/_internal/playwright/driver/package

        In normal Python runs, it's under the installed playwright package:
          <site-packages>/playwright/driver/package
        """
        # PyInstaller: sys._MEIPASS points to the unpacked/bundled internal dir.
        try:
            meipass = getattr(sys, "_MEIPASS", None)  # pylint: disable=protected-access
        except Exception:
            meipass = None
        if meipass:
            bundled = pathlib.Path(meipass) / "playwright" / "driver" / "package"
            if bundled.exists():
                return bundled

        # Regular Python: locate via playwright module path.
        try:
            import playwright  # pylint: disable=import-outside-toplevel
            pkg_dir = pathlib.Path(playwright.__file__).resolve().parent / "driver" / "package"
            if pkg_dir.exists():
                return pkg_dir
        except Exception:
            return None

        return None

    @staticmethod
    def _read_playwright_chromium_revision(driver_pkg_dir:pathlib.Path) -> str | None:
        """Read expected Chromium revision from Playwright's browsers.json."""
        browsers_json = driver_pkg_dir / "browsers.json"
        if not browsers_json.exists():
            return None
        try:
            with browsers_json.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for browser in data.get("browsers", []):
                if browser.get("name") == "chromium":
                    rev = browser.get("revision")
                    return str(rev) if rev else None
        except Exception:
            return None
        return None

    @staticmethod
    def _chromium_executable_relpath() -> pathlib.Path:
        """Chromium executable relative path inside a browser revision folder."""
        if os.name == "nt":
            return pathlib.Path("chrome-win") / "chrome.exe"
        if sys.platform == "darwin":
            return pathlib.Path("chrome-mac") / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
        return pathlib.Path("chrome-linux") / "chrome"

    def _chromium_executable_exists(self, browsers_root:str, revision:str,
        driver_pkg_dir:pathlib.Path) -> bool:
        """Return True if chromium exe exists for given browsers root.

        browsers_root can be:
          - "0": Playwright special value meaning driver_pkg_dir/.local-browsers
          - an absolute path to the cache root (containing chromium-<rev>/...)
          - an absolute path to the '.local-browsers' directory itself
        """
        try:
            if browsers_root == "0":
                root = driver_pkg_dir / ".local-browsers"
            else:
                root = pathlib.Path(browsers_root)
            exe = root / f"chromium-{revision}" / self._chromium_executable_relpath()
            return exe.exists() and exe.is_file()
        except Exception:
            return False

    def _prepare_playwright_browsers_path(self):
        """Best-effort fix for packaged builds missing bundled Playwright browsers.

        Playwright sometimes resolves browsers under driver_pkg_dir/.local-browsers in frozen apps.
        If the bundled browsers are missing, we fall back to the default Playwright cache
        (e.g. %LOCALAPPDATA%\\ms-playwright on Windows) when available.
        """
        driver_pkg_dir = self._playwright_driver_package_dir()
        if driver_pkg_dir is None:
            return

        revision = self._read_playwright_chromium_revision(driver_pkg_dir)
        if not revision:
            return

        env_val = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        if env_val and self._chromium_executable_exists(env_val, revision, driver_pkg_dir):
            return

        # Prefer bundled browsers when present (keeps exe self-contained).
        bundled_roots = [
            driver_pkg_dir / "ms-playwright",   # mac packaging path (codesign-friendly)
            driver_pkg_dir / ".local-browsers", # legacy path
        ]
        for bundled_root in bundled_roots:
            if self._chromium_executable_exists(str(bundled_root), revision, driver_pkg_dir):
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_root)
                return

        # Fallback to default cache (common when playwright install was run without PLAYWRIGHT_BROWSERS_PATH=0).
        if os.name == "nt":
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                cache_root = pathlib.Path(local_app_data) / "ms-playwright"
                if self._chromium_executable_exists(str(cache_root), revision, driver_pkg_dir):
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(cache_root)
                    return

    def init_vars(self):
        """ initialize internal variables"""
        self.context:BrowserContext = None
        self.page:Page = None        # playwright page, only used by thread
        self.fps_counter = FPSCounter()

        # for tracking page info
        self._page_title:str = None
        self._last_update_time:float = 0
        self.zoomlevel_check:float = None
        self.nonfatal_nav_error_count:int = 0
        self.runtime_inner_width:float = float(self.width)
        self.runtime_inner_height:float = float(self.height)
        self.runtime_game_rect:tuple[float, float, float, float] = (0.0, 0.0, float(self.width), float(self.height))
        self._fullscreen_runtime:bool = False
        self._overlay_start_pending:bool = False

        # overlay info
        self._canvas_id = None              # for overlay
        self._last_botleft_text = None
        self._last_guide = None
        self._real_mouse_hwnd:int | None = None

    def __del__(self):
        self.stop()

    def start(self, url:str, proxy:str=None, width:int=None, height:int=None,
        enable_chrome_ext:bool=False, fullscreen:bool=False, high_quality:bool=False):
        """ Launch the browser in a thread, and start processing action queue
        params:
            url(str): url of the page to open upon browser launch
            proxy(str): proxy server to use. e.g. http://1.2.3.4:555"
            width, height: viewport width and height
            enable_ext: True to enable chrome extensions
            fullscreen: start browser in fullscreen (mac only)
            high_quality: use higher quality render args and stable profile cache (mac only)
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
            args=(url, proxy, enable_chrome_ext, fullscreen, high_quality),
            name="BrowserThread",
            daemon=True)
        self._browser_thread.start()


    def _run_browser_and_action_queue(self, url:str, proxy:str, enable_chrome_ext:bool=False,
        fullscreen:bool=False, high_quality:bool=False):
        """ run browser and keep processing action queue (blocking)"""
        
        if proxy:
            proxy_object = {"server": proxy}
        else:
            proxy_object = None
        self._fullscreen_runtime = bool(sys.platform == "darwin" and fullscreen)
        self.nonfatal_nav_error_count = 0

        # In mac fullscreen/high-quality mode, use a persistent profile to reuse browser cache/resources.
        profile_is_stable = bool(sys.platform == "darwin" and (high_quality or fullscreen))
        self.browser_profile_dir = self._get_profile_dir(stable=profile_is_stable)
        if profile_is_stable:
            LOGGER.info("Using persistent browser profile cache: %s", self.browser_profile_dir)

        # read all subfolder names from Folder.CRX and form extension list
        if enable_chrome_ext:
            extensions_list = list_children(Folder.CHROME_EXT, True, False, True)
            # extensions_list = []
            # for root, dirs, files in os.walk(utils.sub_folder(Folder.CHROME_EXT)):
            #     for extension_dir in dirs:
            #         extensions_list.append(os.path.join(root, extension_dir))
            LOGGER.info('Extensions loaded: %s', extensions_list)
            disable_extensions_except_args = "--disable-extensions-except=" + ",".join(extensions_list)
            load_extension_args = "--load-extension=" + ",".join(extensions_list)

        # In packaged builds, ensure Playwright can find a browser binary (or fallback to system cache).
        self._prepare_playwright_browsers_path()

        launch_args = ["--noerrdialogs", "--no-sandbox"]
        if sys.platform == "darwin" and fullscreen:
            launch_args.append("--start-fullscreen")
        if sys.platform == "darwin" and high_quality:
            launch_args.extend([
                "--enable-gpu-rasterization",
                "--force-color-profile=srgb",
            ])
        if enable_chrome_ext:
            launch_args.extend([disable_extensions_except_args, load_extension_args])

        LOGGER.info(
            "Starting Chromium, viewport=%dx%d, proxy=%s, profile=%s, fullscreen=%s, high_quality=%s",
            self.width, self.height, proxy, self.browser_profile_dir, fullscreen, high_quality
        )
        with sync_playwright() as playwright:
            chromium = playwright.chromium
            launch_kwargs = {
                "user_data_dir": self.browser_profile_dir,
                "headless": False,
                "proxy": proxy_object,
                "ignore_https_errors": True,
                "ignore_default_args": ["--enable-automation"],
                "args": launch_args,
            }
            if self._fullscreen_runtime:
                launch_kwargs["no_viewport"] = True
            else:
                launch_kwargs["viewport"] = {"width": self.width, "height": self.height}
            try:
                self.context = self._launch_context_with_channel_fallback(chromium, launch_kwargs)
            except Exception as e:
                if profile_is_stable and self._is_profile_dir_error(e):
                    fallback_profile = self._get_profile_dir(stable=False)
                    LOGGER.warning(
                        "Stable browser profile failed (%s). Retrying with isolated profile: %s",
                        e, fallback_profile
                    )
                    self.browser_profile_dir = fallback_profile
                    launch_kwargs["user_data_dir"] = self.browser_profile_dir
                    try:
                        self.context = self._launch_context_with_channel_fallback(chromium, launch_kwargs)
                    except Exception as fallback_error:
                        LOGGER.error("Error launching browser with fallback profile: %s", fallback_error, exc_info=True)
                        return
                else:
                    LOGGER.error('Error launching the browser: %s', e, exc_info=True)
                    return

            try:
                pages = []
                for p in self.context.pages:
                    try:
                        if not p.is_closed():
                            pages.append(p)
                    except Exception:  # pylint: disable=broad-except
                        continue
                if pages:
                    non_extension_pages = []
                    for p in pages:
                        try:
                            page_url = str(p.url or "")
                        except Exception:  # pylint: disable=broad-except
                            page_url = ""
                        if not page_url.startswith("chrome-extension://"):
                            non_extension_pages.append(p)
                    self.page = non_extension_pages[0] if non_extension_pages else pages[0]
                    for extra_page in pages:
                        if extra_page is self.page:
                            continue
                        try:
                            extra_url = str(extra_page.url or "")
                            if extra_url in ("", "about:blank"):
                                extra_page.close()
                        except Exception:  # pylint: disable=broad-except
                            pass
                else:
                    self.page = self.context.new_page()
                self.page.goto(url, wait_until="domcontentloaded")
                self._refresh_runtime_view_metrics()
            except Exception as e:
                LOGGER.error('Error opening page. Check if certificate is installed. \n%s',e)

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
                if self._is_page_closed():
                    LOGGER.warning("Page closed. exiting browser loop.")
                    break
                if time.time() - self._last_update_time > 1:
                    try:
                        self._refresh_runtime_view_metrics()
                        self.nonfatal_nav_error_count = 0
                        self._last_update_time = time.time()
                    except Exception as e:
                        if self._is_transient_page_exception(e):
                            self.nonfatal_nav_error_count += 1
                            if self.nonfatal_nav_error_count in (1, 10, 50):
                                LOGGER.warning(
                                    "Transient page navigation error (count=%d): %s",
                                    self.nonfatal_nav_error_count, e
                                )
                            time.sleep(0.01)
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
                if not self._is_page_closed():
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

    def _clear_action_queue(self):
        """ Clear the action queue"""
        while True:
            try:
                self._action_queue.get_nowait()
            except queue.Empty:
                break

    def stop(self, join_thread:bool=False):
        """ Shutdown browser thread"""
        if self.is_running():
            self._stop_event.set()
            if join_thread:
                self._browser_thread.join()
            self._browser_thread = None

    def is_running(self):
        """ return True if browser thread is still running"""
        if self._browser_thread and self._browser_thread.is_alive():
            return True
        else:
            return False

    def _is_page_closed(self) -> bool:
        """Return True when page is unavailable or already closed."""
        if self.page is None:
            return True
        try:
            return self.page.is_closed()
        except Exception:  # pylint: disable=broad-except
            return True

    @staticmethod
    def _is_transient_page_exception(error:Exception) -> bool:
        """Return True for navigation-time JS context errors that should not stop browser loop."""
        msg = str(error).lower()
        transient_markers = (
            "execution context was destroyed",
            "cannot find context with specified id",
            "most likely because of a navigation",
            "navigated",
        )
        return any(marker in msg for marker in transient_markers)

    @staticmethod
    def _compute_runtime_game_rect(inner_width:float, inner_height:float) -> tuple[float, float, float, float]:
        """Compute 16:9 game area fitted inside current browser inner viewport."""
        inner_width = max(1.0, float(inner_width))
        inner_height = max(1.0, float(inner_height))
        target_ratio = 16 / 9
        current_ratio = inner_width / inner_height
        if current_ratio >= target_ratio:
            game_height = inner_height
            game_width = game_height * target_ratio
            offset_x = (inner_width - game_width) / 2
            offset_y = 0.0
        else:
            game_width = inner_width
            game_height = game_width / target_ratio
            offset_x = 0.0
            offset_y = (inner_height - game_height) / 2
        return (offset_x, offset_y, game_width, game_height)

    def _refresh_runtime_view_metrics(self):
        """Sample runtime viewport metrics from page and update mapping/overlay states."""
        if self._is_page_closed():
            return
        info = self.page.evaluate("""() => ({
            title: document.title || "",
            zoomScale: (window.visualViewport && typeof window.visualViewport.scale === "number")
                ? window.visualViewport.scale : 1,
            innerWidth: window.innerWidth || document.documentElement.clientWidth || 0,
            innerHeight: window.innerHeight || document.documentElement.clientHeight || 0
        })""")
        title = str(info.get("title", "") or "")
        zoom_scale = info.get("zoomScale", 1)
        inner_w = float(info.get("innerWidth", self.width) or self.width)
        inner_h = float(info.get("innerHeight", self.height) or self.height)
        self._page_title = title
        self.zoomlevel_check = float(zoom_scale) if isinstance(zoom_scale, (int, float)) else 1.0

        prev_w = self.runtime_inner_width
        prev_h = self.runtime_inner_height
        prev_rect = self.runtime_game_rect
        self.runtime_inner_width = max(1.0, inner_w)
        self.runtime_inner_height = max(1.0, inner_h)
        self.runtime_game_rect = self._compute_runtime_game_rect(self.runtime_inner_width, self.runtime_inner_height)
        if (
            abs(prev_w - self.runtime_inner_width) > 1
            or abs(prev_h - self.runtime_inner_height) > 1
            or any(abs(a - b) > 1 for a, b in zip(prev_rect, self.runtime_game_rect))
        ):
            LOGGER.debug(
                "Runtime viewport updated: inner=%.0fx%.0f game_rect=(x=%.1f,y=%.1f,w=%.1f,h=%.1f)",
                self.runtime_inner_width,
                self.runtime_inner_height,
                self.runtime_game_rect[0],
                self.runtime_game_rect[1],
                self.runtime_game_rect[2],
                self.runtime_game_rect[3],
            )

    def _runtime_overlay_size(self) -> tuple[int, int]:
        """Overlay canvas target size. Prefer runtime viewport when available."""
        width = int(round(self.runtime_inner_width)) if self.runtime_inner_width > 0 else int(self.width)
        height = int(round(self.runtime_inner_height)) if self.runtime_inner_height > 0 else int(self.height)
        return (max(1, width), max(1, height))

    def _translate_runtime_viewport_point(self, x:float, y:float) -> tuple[float, float]:
        """Map legacy fixed-viewport points into runtime fullscreen viewport."""
        if not self._fullscreen_runtime:
            return (x, y)
        base_w = max(1.0, float(self.width))
        base_h = max(1.0, float(self.height))
        nx = min(max(float(x) / base_w, 0.0), 1.0)
        ny = min(max(float(y) / base_h, 0.0), 1.0)
        offset_x, offset_y, game_w, game_h = self.runtime_game_rect
        mapped_x = offset_x + nx * game_w
        mapped_y = offset_y + ny * game_h
        return (mapped_x, mapped_y)

    def is_page_normal(self):
        """ return True if page is loaded """
        return not self._is_page_closed()

    def is_overlay_working(self):
        """ return True if overlay is on and working"""
        if self._is_page_closed():
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
        if self._overlay_start_pending:
            return
        self._last_botleft_text = None
        self._last_guide = None
        self._overlay_start_pending = True
        self._action_queue.put(self._action_start_overlay)

    def stop_overlay(self):
        """ Queue action: Stop showing the overlay"""
        self._overlay_start_pending = False
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
        target_x, target_y = self._translate_runtime_viewport_point(x, y)
        self.page.mouse.move(x=target_x, y=target_y, steps=steps)
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
            self._overlay_start_pending = False
            return
        canvas_w, canvas_h = self._runtime_overlay_size()
        self._canvas_id = utils.random_str(8) # random 8-byte alpha-numeric string
        js_code = f"""(() => {{
            // Create a canvas element and add it to the document body
            const canvas = document.createElement('canvas');
            canvas.id = '{self._canvas_id}';
            const syncSize = () => {{
                canvas.width = window.innerWidth || {canvas_w};
                canvas.height = window.innerHeight || {canvas_h};
            }};
            syncSize();
            canvas.__syncSize = syncSize;
            window.addEventListener('resize', syncSize);
            
            // Set styles to ensure the canvas is on top
            canvas.style.position = 'fixed'; // Use 'fixed' or 'absolute' positioning
            canvas.style.left = '0'; // Position at the top-left corner of the viewport
            canvas.style.top = '0';
            canvas.style.zIndex = '9999999'; // High z-index to ensure it is on top
            canvas.style.pointerEvents = 'none'; // Make the canvas click-through
            document.body.appendChild(canvas);            
            }})()"""
        self.page.evaluate(js_code)
        self._overlay_start_pending = False

    def _action_stop_overlay(self):
        """ Remove overlay from page"""

        self._overlay_start_pending = False
        if self.is_overlay_working() is False:
            return
        js_code = f"""(() => {{
            const canvas = document.getElementById('{self._canvas_id}');
            if (canvas) {{
                if (canvas.__syncSize) {{
                    window.removeEventListener('resize', canvas.__syncSize);
                }}
                canvas.remove();
            }}
            }})()"""
        self.page.evaluate(js_code)
        self._canvas_id = None
        self._last_botleft_text = None
        self._last_guide = None

    def _overlay_text_params(self):
        canvas_w, canvas_h = self._runtime_overlay_size()
        font_size = max(10, int(canvas_h/45))  # e.g., 22
        line_space = max(4, int(canvas_h/45/2))
        min_box_width = font_size * 15  # Minimum box width
        initial_box_height = line_space * 2 + (font_size + line_space) * 6  # based on number of lines
        box_top = int(canvas_h * 0.44)  # Distance from the top
        box_left = int(canvas_w * 0.14)  # Distance from the left
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
            ctx.clearRect({box_left}, {box_top}, canvas.width-{box_left}, {initial_box_height});            
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
            ctx.clearRect({box_left}, {box_top}, canvas.width-{box_left}, {initial_box_height});
        }});"""
        self.page.evaluate(js_code)
        self._last_guide = None

    def _action_overlay_update_botleft(self, text:str=None):
        if self.is_overlay_working() is False:
            return

        _canvas_w, canvas_h = self._runtime_overlay_size()
        font_size = max(10, int(canvas_h/48))
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


    def _read_window_geometry(self) -> dict | None:
        """Read window geometry from browser JS context."""
        if not self.is_page_normal():
            return None
        result = {}
        finish_event = threading.Event()
        def action():
            try:
                info = self.page.evaluate("""() => {
                    return {
                        screenX: window.screenX,
                        screenY: window.screenY,
                        outerWidth: window.outerWidth,
                        outerHeight: window.outerHeight,
                        innerWidth: window.innerWidth,
                        innerHeight: window.innerHeight,
                        dpr: window.devicePixelRatio || 1
                    };
                }""")
                result['info'] = info
            except Exception as e:
                LOGGER.error("Error getting viewport origin: %s", e)
            finish_event.set()
        self._action_queue.put(action)
        finish_event.wait(timeout=3)
        return result.get('info')

    def _get_hwnd_class_name(self, hwnd:int) -> str:
        """Get Win32 class name for a window handle."""
        if os.name != "nt" or not hwnd:
            return ""
        user32 = ctypes.windll.user32
        if not user32.IsWindow(hwnd):
            return ""
        cls_buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, cls_buf, 64)
        return cls_buf.value

    def _is_chrome_hwnd(self, hwnd:int) -> bool:
        """Return true for Chromium top-level windows."""
        cls_name = self._get_hwnd_class_name(hwnd)
        return cls_name.startswith("Chrome_WidgetWin")

    def _get_hwnd_metrics(self, hwnd:int) -> dict | None:
        """Get window/client geometry in screen pixels for given hwnd."""
        if os.name != "nt" or not hwnd:
            return None

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32 = ctypes.windll.user32
        if not user32.IsWindow(hwnd):
            return None
        if not user32.IsWindowVisible(hwnd):
            return None

        win_rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(win_rect)):
            return None

        client_rect = RECT()
        if not user32.GetClientRect(hwnd, ctypes.byref(client_rect)):
            return None
        client_w = client_rect.right - client_rect.left
        client_h = client_rect.bottom - client_rect.top
        if client_w <= 0 or client_h <= 0:
            return None

        client_origin = POINT(0, 0)
        if not user32.ClientToScreen(hwnd, ctypes.byref(client_origin)):
            return None

        return {
            "win_left": float(win_rect.left),
            "win_top": float(win_rect.top),
            "win_w": float(win_rect.right - win_rect.left),
            "win_h": float(win_rect.bottom - win_rect.top),
            "client_left": float(client_origin.x),
            "client_top": float(client_origin.y),
            "client_w": float(client_w),
            "client_h": float(client_h),
        }

    def _hwnd_match_score(self, hwnd:int, js_info:dict) -> float | None:
        """Score how well hwnd matches current page window geometry."""
        metrics = self._get_hwnd_metrics(hwnd)
        if metrics is None:
            return None
        try:
            screen_x = float(js_info.get("screenX", 0) or 0)
            screen_y = float(js_info.get("screenY", 0) or 0)
            outer_w = float(js_info.get("outerWidth", 0) or 0)
            outer_h = float(js_info.get("outerHeight", 0) or 0)
            inner_w = float(js_info.get("innerWidth", 0) or 0)
            inner_h = float(js_info.get("innerHeight", 0) or 0)
            dpr = float(js_info.get("dpr", 1.0) or 1.0)
        except Exception:
            return None
        if outer_w <= 0 or outer_h <= 0 or inner_w <= 0 or inner_h <= 0:
            return None

        scales = [1.0]
        if abs(dpr - 1.0) > 0.01:
            scales.append(dpr)
        # Dynamic scale inferred from actual window size helps cross-DPI matching.
        scales.append(max(0.5, min(4.0, metrics["win_w"] / outer_w)))
        scales.append(max(0.5, min(4.0, metrics["client_w"] / inner_w)))

        best = None
        for scale in scales:
            score = (
                abs(metrics["win_left"] - screen_x * scale) +
                abs(metrics["win_top"] - screen_y * scale) +
                abs(metrics["win_w"] - outer_w * scale) +
                abs(metrics["win_h"] - outer_h * scale) +
                abs(metrics["client_w"] - inner_w * scale) +
                abs(metrics["client_h"] - inner_h * scale)
            )
            if best is None or score < best:
                best = score
        return best

    def _get_foreground_chrome_hwnd(self, js_info:dict) -> int | None:
        """Use current foreground window when it is clearly the game browser."""
        if os.name != "nt":
            return None
        user32 = ctypes.windll.user32
        hwnd = int(user32.GetForegroundWindow() or 0)
        if not hwnd:
            return None
        GA_ROOT = 2
        hwnd = int(user32.GetAncestor(hwnd, GA_ROOT) or hwnd)
        if not self._is_chrome_hwnd(hwnd):
            return None
        score = self._hwnd_match_score(hwnd, js_info)
        if score is None:
            return None
        return hwnd if score < 1800 else None

    def _find_hwnd_by_probe_point(self, js_info:dict) -> int | None:
        """Probe a few points derived from JS geometry and resolve their root hwnd."""
        if os.name != "nt":
            return None

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        try:
            screen_x = float(js_info.get("screenX", 0) or 0)
            screen_y = float(js_info.get("screenY", 0) or 0)
            outer_w = float(js_info.get("outerWidth", 0) or 0)
            outer_h = float(js_info.get("outerHeight", 0) or 0)
            inner_w = float(js_info.get("innerWidth", 0) or 0)
            inner_h = float(js_info.get("innerHeight", 0) or 0)
            dpr = float(js_info.get("dpr", 1.0) or 1.0)
        except Exception:
            return None
        if outer_w <= 0 or outer_h <= 0 or inner_w <= 0 or inner_h <= 0:
            return None

        border_x = (outer_w - inner_w) / 2
        title_bar_y = outer_h - inner_h - border_x
        origin_x_css = screen_x + border_x
        origin_y_css = screen_y + title_bar_y

        probe_css_points = [
            (origin_x_css + 20, origin_y_css + 20),
            (screen_x + outer_w * 0.5, screen_y + min(outer_h * 0.5, 120)),
        ]
        scales = [1.0]
        if abs(dpr - 1.0) > 0.01:
            scales.append(dpr)

        user32 = ctypes.windll.user32
        GA_ROOT = 2
        best_hwnd = None
        best_score = None
        for px_css, py_css in probe_css_points:
            for scale in scales:
                point = POINT(round(px_css * scale), round(py_css * scale))
                hwnd = int(user32.WindowFromPoint(point) or 0)
                if not hwnd:
                    continue
                hwnd = int(user32.GetAncestor(hwnd, GA_ROOT) or hwnd)
                if not self._is_chrome_hwnd(hwnd):
                    continue
                score = self._hwnd_match_score(hwnd, js_info)
                if score is None:
                    continue
                if best_score is None or score < best_score:
                    best_score = score
                    best_hwnd = hwnd

        if best_hwnd is not None and best_score is not None and best_score < 2200:
            return best_hwnd
        return None

    def _find_matching_chrome_hwnd(self, js_info:dict) -> int | None:
        """Find best matching Chromium hwnd by global enumeration."""
        if os.name != "nt":
            return None
        user32 = ctypes.windll.user32
        hwnd_scores:list[tuple[float, int]] = []
        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def _enum_cb(hwnd, _lparam):
            hwnd = int(hwnd)
            if not self._is_chrome_hwnd(hwnd):
                return True
            score = self._hwnd_match_score(hwnd, js_info)
            if score is not None:
                hwnd_scores.append((float(score), hwnd))
            return True

        cb = enum_proc(_enum_cb)
        user32.EnumWindows(cb, 0)
        if not hwnd_scores:
            return None
        hwnd_scores.sort(key=lambda item: item[0])
        return hwnd_scores[0][1]

    def _resolve_browser_hwnd(self, js_info:dict) -> int | None:
        """Resolve browser hwnd using cache, foreground, probe and enumeration."""
        if os.name != "nt":
            return None

        if self._real_mouse_hwnd:
            score = self._hwnd_match_score(self._real_mouse_hwnd, js_info)
            if score is not None and score < 2200:
                return self._real_mouse_hwnd

        for resolver in (
            self._get_foreground_chrome_hwnd,
            self._find_hwnd_by_probe_point,
            self._find_matching_chrome_hwnd,
        ):
            hwnd = resolver(js_info)
            if hwnd:
                self._real_mouse_hwnd = hwnd
                return hwnd
        return None

    def _get_client_origin_and_scale(self, hwnd:int, js_info:dict) -> tuple[float, float, float, float] | None:
        """Get client-area screen origin and viewport scale from HWND."""
        if os.name != "nt":
            return None

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32 = ctypes.windll.user32
        h = ctypes.c_void_p(hwnd)

        rect = RECT()
        if not user32.GetClientRect(h, ctypes.byref(rect)):
            return None
        client_w = rect.right - rect.left
        client_h = rect.bottom - rect.top
        if client_w <= 0 or client_h <= 0:
            return None

        pt = POINT(0, 0)
        if not user32.ClientToScreen(h, ctypes.byref(pt)):
            return None

        inner_w = float(js_info.get('innerWidth', 0) or 0)
        inner_h = float(js_info.get('innerHeight', 0) or 0)
        dpr = float(js_info.get('dpr', 1.0) or 1.0)
        scale_x = (client_w / inner_w) if inner_w > 0 else dpr
        scale_y = (client_h / inner_h) if inner_h > 0 else dpr
        return (float(pt.x), float(pt.y), float(scale_x), float(scale_y))

    def _get_viewport_geometry(self) -> tuple[float, float, float, float] | None:
        """Get viewport mapping as (origin_x, origin_y, scale_x, scale_y) in screen coords."""
        info = self._read_window_geometry()
        if info is None:
            return None

        hwnd = self._resolve_browser_hwnd(info)
        if hwnd is not None:
            mapped = self._get_client_origin_and_scale(hwnd, info)
            if mapped is not None:
                return mapped

        # Fallback: estimate via JS outer/inner metrics.
        border_x = (info['outerWidth'] - info['innerWidth']) / 2
        title_bar_y = info['outerHeight'] - info['innerHeight'] - border_x
        origin_x_css = info['screenX'] + border_x
        origin_y_css = info['screenY'] + title_bar_y
        dpr = float(info.get('dpr', 1.0) or 1.0)
        return (float(origin_x_css * dpr), float(origin_y_css * dpr), dpr, dpr)

    def get_viewport_screen_origin(self) -> tuple[int, int]:
        """ Get browser viewport top-left in screen pixels (for real mouse)."""
        geometry = self._get_viewport_geometry()
        if geometry is None:
            return (0, 0)
        origin_x, origin_y, _scale_x, _scale_y = geometry
        return (round(origin_x), round(origin_y))

    def viewport_to_screen(self, viewport_x:float, viewport_y:float) -> tuple[int, int]:
        """ Convert viewport CSS coordinates to screen coordinates for SetCursorPos."""
        geometry = self._get_viewport_geometry()
        if geometry is None:
            return (int(viewport_x), int(viewport_y))
        origin_x, origin_y, scale_x, scale_y = geometry
        screen_x = round(origin_x + viewport_x * scale_x) + self.real_mouse_offset_x
        screen_y = round(origin_y + viewport_y * scale_y) + self.real_mouse_offset_y
        return (screen_x, screen_y)

    def _get_cursor_pos(self) -> tuple[int, int]:
        """Get current real cursor position in screen coordinates."""
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return int(pt.x), int(pt.y)

    def real_mouse_move(self, screen_x:int, screen_y:int,
        speed_pps:float|None=None, jitter_px:float|None=None):
        """Move real mouse with smooth human-like path instead of teleporting."""
        target_x = int(screen_x)
        target_y = int(screen_y)
        user32 = ctypes.windll.user32
        start_x, start_y = self._get_cursor_pos()
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy)
        speed_pps = max(300.0, float(speed_pps if speed_pps is not None else self.real_mouse_speed_pps))
        jitter_px = max(0.0, float(jitter_px if jitter_px is not None else self.real_mouse_jitter_px))
        if dist < 1.0:
            user32.SetCursorPos(target_x, target_y)
            return

        # Duration from travel speed; clamp to keep movement visible but responsive.
        move_sec = dist / speed_pps
        min_sec = self.real_mouse_min_move_ms / 1000.0
        max_sec = self.real_mouse_max_move_ms / 1000.0
        move_sec = max(min_sec, min(max_sec, move_sec + random.uniform(0.00, 0.03)))

        # Use a curved path + small fading jitter to avoid a dead-straight trajectory.
        nx = dx / dist
        ny = dy / dist
        px = -ny
        py = nx
        bend = min(22.0, max(4.0, dist * 0.06))
        bend *= random.choice((-1.0, 1.0))
        mid_t = random.uniform(0.35, 0.65)
        cx = start_x + dx * mid_t + px * bend
        cy = start_y + dy * mid_t + py * bend

        steps = int(max(14, min(80, move_sec / 0.008)))
        start_ts = time.perf_counter()
        for i in range(1, steps + 1):
            t = i / steps
            # cubic ease-in-out
            eased = 3 * t * t - 2 * t * t * t
            omt = 1.0 - eased
            bx = (omt * omt * start_x) + (2 * omt * eased * cx) + (eased * eased * target_x)
            by = (omt * omt * start_y) + (2 * omt * eased * cy) + (eased * eased * target_y)

            if i < steps:
                jitter = jitter_px * (1.0 - eased)
                bx += random.uniform(-jitter, jitter)
                by += random.uniform(-jitter, jitter)

            user32.SetCursorPos(int(round(bx)), int(round(by)))
            expected = start_ts + move_sec * t
            sleep_sec = expected - time.perf_counter()
            if sleep_sec > 0:
                time.sleep(sleep_sec)

        user32.SetCursorPos(target_x, target_y)

    def _random_offset_point(self, radius_px:float) -> tuple[int, int]:
        """Sample a random point within a circle around current cursor."""
        base_x, base_y = self._get_cursor_pos()
        if radius_px <= 0:
            return (base_x, base_y)
        theta = random.uniform(0.0, math.tau)
        # sqrt keeps points uniformly distributed in circle area
        r = math.sqrt(random.random()) * radius_px
        return (int(round(base_x + math.cos(theta) * r)),
                int(round(base_y + math.sin(theta) * r)))

    def real_mouse_click(self, delay:float=0.08,
        click_offset_px:float|None=None, speed_pps:float|None=None, jitter_px:float|None=None):
        """ Simulate a real mouse click (left button down + delay + up)
        params:
            delay: delay in seconds between down and up"""
        offset = self.real_mouse_click_offset_px if click_offset_px is None else click_offset_px
        offset = max(0.0, float(offset))
        if offset > 0:
            ox, oy = self._random_offset_point(offset)
            self.real_mouse_move(ox, oy, speed_pps=speed_pps, jitter_px=jitter_px)
        self.real_mouse_down()
        time.sleep(delay)
        self.real_mouse_up()

    def real_mouse_down(self):
        """ Real mouse left button down"""
        MOUSEEVENTF_LEFTDOWN = 0x0002
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)

    def real_mouse_up(self):
        """ Real mouse left button up"""
        MOUSEEVENTF_LEFTUP = 0x0004
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def real_mouse_wheel(self, dx:float, dy:float):
        """ Real mouse wheel scroll
        params:
            dx: horizontal scroll (not used on Windows)
            dy: vertical scroll amount"""
        MOUSEEVENTF_WHEEL = 0x0800
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(dy), 0)

    def _action_screen_shot(self, res_queue:queue.Queue, time_ms:int=5000):
        """ take screen shot from browser page
        Params:
            res_queue: queue for saving the image buff data"""
        if self.is_page_normal():
            try:
                # Use CSS-pixel screenshot to avoid Retina/device-pixel blowup in fullscreen.
                ss_bytes:BytesIO = self.page.screenshot(timeout=time_ms, scale="css")
                res_queue.put(ss_bytes)
            except Exception as e:
                LOGGER.error("Error taking screenshot: %s", e, exc_info=True)
                res_queue.put(None)
        else:
            res_queue.put(None)
            LOGGER.debug("Page not loaded, no screenshot")
