""" Inject socks5 proxy into windows process using proxinjector-cli.exe"""

import threading
import subprocess
import pathlib
import time
import sys
from common.utils import Folder, sub_run_args
from common.log_helper import LOGGER

class ProxyInjector:
    """ Inject socks5 proxy into windows process"""
    def __init__(self):
        self.p_name:str = None
        self.proxy_ip:str = None
        self.proxy_port:int = None
        
        self._thread:threading.Thread = None
        self._stop_event = threading.Event()

    def start(self, process_name:str, proxy_ip:str, proxy_port:int):
        """ Start injecting socks5 proxy into the process
        params:
            process_name(str): name of the process to inject
            proxy_ip(str): ip address of the proxy server
            proxy_port(int): port of the proxy server"""
        if sys.platform != 'win32':
            LOGGER.warning("Proxy inject only supports windows. skip start")
            return
        if self.is_running():
            LOGGER.debug("Already running. skip start")
            return
        self.p_name = process_name
        self.proxy_ip = proxy_ip
        self.proxy_port = proxy_port
        self._stop_event.clear()
        self._thread = threading.Thread(
            name="ProxyInjectThread",
            target=self.run,
            daemon=True,
        )
        self._thread.start()
    
    def is_running(self) -> bool:
        """ return True if the injection thread is running"""
        if self._thread and self._thread.is_alive():
            return True
        else:
            return False
        
    def stop(self, join_thread:bool=False):
        """ stop thread"""
        if self.is_running():
            self._stop_event.set()
            if join_thread:
                self._thread.join()
            self._thread = None
        
    def run(self):
        """ run the injection process"""
        try:            
            proxy = f'{self.proxy_ip}:{self.proxy_port}'
            LOGGER.info("Start injecting, process=%s, proxy=%s", self.p_name, proxy)
            pi_path = pathlib.Path(Folder.PROXINJECT) / 'proxinjector-cli.exe'
            if not pi_path.is_file():
                raise FileNotFoundError(f"Not found: {pi_path}")    
            
            cmds = [
                str(pi_path),
                '-n', self.p_name,
                '-p', proxy,
            ]
            # Set up the startup info to hide the window
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = subprocess.SW_HIDE
            process = None
            while not self._stop_event.is_set():
                if process is None or process.poll() is not None:
                    if process is not None:
                        process.terminate()  # Politely ask the process to terminate
                        process.wait()  # Wait for process to terminate
                    args = sub_run_args()
                    process = subprocess.Popen(
                        cmds, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        startupinfo=startup_info)
                time.sleep(0.5)
                
            if process and process.poll() is None:
                process.kill()
            LOGGER.info("Proxy injection stopped.")
        except Exception as e:
            LOGGER.error("ProxyInjector Error: %s", e, exc_info=True)
        