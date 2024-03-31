import threading
import asyncio
import queue
from pathlib import Path
from mitmproxy.http import HTTPFlow
from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster
import utils
from log_helper import LOGGER

MITM_CONFDIR = 'mitm_config'
WS_START = 1
WS_END = 2
WS_MESSAGE = 3
class WSMessage:    
    """ Websocket message"""
    def __init__(self, flow_id: str, timestamp: float = None, content: bytes = None, msg_type:int=WS_MESSAGE) -> None:
        self.flow_id = flow_id
        self.timestamp = timestamp
        self.content = content
        self.type = msg_type


class WSDataInterceptor:
    """ mitm websocket addon that intercepts data"""

    def __init__(self, allowed_domains:list=None):
        """ pass flow_message_dict for storing intercepted flow data
        params:
            allowed_domains: list of allowed domains to intercept. websocket connection for other websites will be killed"""
        if allowed_domains:
            self.allowed_domains = allowed_domains
        else:
            self.allowed_domains = None
        self.message_queue = queue.Queue()      
        """Queue for unretrieved messages
        each element is: WSMessage"""

    def websocket_start(self, flow:HTTPFlow):
        if any(allowed_domain in flow.request.pretty_url for allowed_domain in self.allowed_domains):
            self.message_queue.put(WSMessage(flow.id, flow.timestamp_start, None, WS_START))
        else:
            flow.kill()
            LOGGER.info("Killing flow since it is not in allowed domains: %s", flow.request.pretty_url)            
        
    def websocket_message(self, flow:HTTPFlow):
        if any(allowed_domain in flow.request.pretty_url for allowed_domain in self.allowed_domains):
            self.message_queue.put(WSMessage(flow.id, flow.websocket.messages[-1].timestamp, flow.websocket.messages[-1].content))
        
    def websocket_end(self, flow:HTTPFlow):
        if not any(allowed_domain in flow.request.pretty_url for allowed_domain in self.allowed_domains):
            self.message_queue.put(WSMessage(flow.id, flow.timestamp_start, None, WS_END))        

class MitmController:
    """ Controlling mitm proxy server interactions and managing threads
    mitm proxy server intercepts data to/from the game server"""
    
    def __init__(self, proxy_port:int, allowed_domains:list=None) -> None:
        """
        params:
            proxy_port(int): proxy server port to open
            allowed_domains(list): Intercept data only from allowed domains. Other websocket traffic will be blocked."""
        
        self.proxy_port = proxy_port
        self.mitm_config_folder = utils.get_sub_folder(MITM_CONFDIR)

        self.mitm_thread = None
        self.dump_master = None
        
        self.flow_message_dict:dict[str, queue.Queue] = {}
        """ Used for exchanging flow data between mitm(thread) and interface.
        {flow_id: msg_queue, ...}"""
        self.ws_data_addon = WSDataInterceptor(allowed_domains)
        
    def start(self):
        """ Start mitm server thread"""
       
        # Start thread
        self.mitm_thread = threading.Thread(
            name="MitmThread",
            target=lambda: asyncio.run(self._run_mitm_async()),
            daemon=True
        )
        self.mitm_thread.start()
        
    
    async def _run_mitm_async(self):
        """ async run mitm proxy server"""
        opts = options.Options(
            listen_port=self.proxy_port,
            confdir=str(self.mitm_config_folder)
        )
        self.dump_master = DumpMaster(
            opts,
            with_termlog=False,
            with_dumper=False,
        )
        self.dump_master.addons.add(self.ws_data_addon)
        await self.dump_master.run()
    
    def stop(self):
        """ shutdown mitm proxy server and join thread"""        
        if self.dump_master:
            self.dump_master.shutdown()
            self.dump_master = None
    
    def is_running(self) -> bool:
        """ return True if mitm proxy server is running"""
        if self.mitm_thread and self.mitm_thread.is_alive():
            return True
        else:
            return False
    
    def get_message(self, block:bool=False, timeout:float=None) -> WSMessage:
        """ pop ws message from the queue. raise queue.Empty if timeout or non-blocked"""
        msg = self.ws_data_addon.message_queue.get(block, timeout)
        return msg
    
    def install_mitm_cert(self, timeout:float=5):
        """Install mitm certificate onto the system
        Return:
            bool: True if installed successfully. False if failed or timeout"""
        cert_file = Path(self.mitm_config_folder) / 'mitmproxy-ca-cert.cer'
        if not utils.wait_for_file(cert_file, timeout):
            LOGGER.error(f"MITM certificate not found: {cert_file}")
            return False
        else:
            LOGGER.debug(f"Certificate file: {cert_file}")
            install_success = utils.install_root_cert(cert_file)
            if install_success:
                return True
            else:
                LOGGER.error("Failed to install MITM certificate. Please install manually.")
                return False

            
if __name__ == '__main__':
    # Test code
    utils.initialize_logging('MITM_TEST')    
    mitm = MitmController(8999)
    LOGGER.info("Starting MITM")
    mitm.start()
    LOGGER.info("Installing certificate")
    mitm.install_mitm_cert()
    
    LOGGER.info("MITM on:%s", mitm.is_running())
    LOGGER.info("Shutting down mitm")
    mitm.stop()
    LOGGER.info("MITM on:%s", mitm.is_running())
    import time
    time.sleep(1)
    LOGGER.info("MITM on:%s", mitm.is_running())