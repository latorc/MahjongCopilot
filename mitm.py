""" Mitm proxy server for intercepting data to/from the game server"""
import threading
import asyncio
import queue
import json
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
from mitmproxy.http import HTTPFlow
from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster
import common.utils as utils
from common.utils import Folder
from common.log_helper import LOGGER

class WsType:
    """ websocket msg type"""
    START = 1
    END = 2
    MESSAGE = 3

@dataclass
class WSMessage:        
    """ Websocket message"""
    flow_id:str
    timestamp:float = None
    content:bytes = None
    type:int = WsType.MESSAGE

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
        
    def allow_url(self, url:str) -> bool:
        """ return true if url is allowed"""
        if not self.allowed_domains:
            # no filtering if None/empty
            return True
        
        if any(d in url for d in self.allowed_domains):
            # allowed
            return True
        
        return False

    def websocket_start(self, flow:HTTPFlow):
        """ ws start handler"""
        if self.allow_url(flow.request.pretty_url):
            self.message_queue.put(WSMessage(flow.id, flow.timestamp_start, None, WsType.START))
        else:
            flow.kill()
            LOGGER.info("Killing flow since it is not in allowed domains: %s", flow.request.pretty_url)            
        
    def websocket_message(self, flow:HTTPFlow):
        """ ws message handler"""
        msg = flow.websocket.messages[-1]
        if self.allow_url(flow.request.pretty_url):
            self.message_queue.put(WSMessage(flow.id, msg.timestamp, msg.content))
        
    def websocket_end(self, flow:HTTPFlow):
        """ ws flow end handler"""
        if self.allow_url(flow.request.pretty_url):
            self.message_queue.put(WSMessage(flow.id, flow.timestamp_start, None, WsType.END))        

    def replace_next_msg(self):
        pass
    
    def request(self, flow: HTTPFlow):
        """ handler for request"""
        parsed_url = urlparse(flow.request.url)
        if parsed_url.hostname == "majsoul-hk-client.cn-hongkong.log.aliyuncs.com":
            qs = parse_qs(parsed_url.query)
            try:
                content = json.loads(qs["content"][0])
                if content["type"] == "re_err":
                    LOGGER.warning("Majsoul Aliyun Error (killed): %s", str(qs))
                    flow.kill()
                else:
                    # LOGGER.debug("Majsoul Aliyun Log detected, len = %d", len(str(qs)))
                    LOGGER.debug("Majsoul Aliyun Log: %s", qs)
            except:
                return
    
SOCKS5 = "socks5"
HTTP = "http"
    
class MitmController:
    """ Controlling mitm proxy server interactions and managing threads
    mitm proxy server intercepts data to/from the game server"""
    
    def __init__(self, allowed_domains:list=None) -> None:
        """
        params:
            proxy_port(int): proxy server port to open
            allowed_domains(list): Intercept data only from allowed domains. Other websocket traffic will be blocked.
                filtering turned off if None/empty"""
        self.mitm_config_folder = utils.sub_folder(Folder.MITM_CONF)
        self.cert_file = utils.sub_file(Folder.MITM_CONF, 'mitmproxy-ca-cert.cer')
        
        self.mitm_thread = None
        self.dump_master = None
        self.proxy_port = None
        self.mode = None
        self.upstream_proxy = None
        self.proxy_str:str = None
        
        self.ws_data_addon = WSDataInterceptor(allowed_domains)
        
    def start(self, port:int, mode=HTTP, upstream_proxy:str=None):
        """ Start mitm server thread
        params:
            port(int): port to open
            upstream_proxy(str): upstream proxy server to forward data to. Format: http://ip:port"""
        self.proxy_port = port
        self.upstream_proxy = upstream_proxy
        self.mode = mode
        # Start thread
        self.mitm_thread = threading.Thread(
            name="MitmThread",
            target=self._run_mitm_task,
            daemon=True
        )
        self.mitm_thread.start()
    
    def _run_mitm_task(self):
        """Thread target: this runs the event loop for the async part."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run_mitm_async())

    
    async def _run_mitm_async(self):
        """ async run mitm proxy server"""
        ip_port = f"127.0.0.1:{self.proxy_port}"
        up_log_str = ""
        if self.mode==HTTP:
            if self.upstream_proxy:
                opts = options.Options(
                    listen_port=self.proxy_port,
                    confdir=str(self.mitm_config_folder),
                    mode=[f"upstream:{self.upstream_proxy}"],
                )
                up_log_str = f" (upstream_proxy={self.upstream_proxy})"
            else:
                opts = options.Options(
                    listen_port=self.proxy_port,
                    confdir=str(self.mitm_config_folder),
                )
            self.proxy_str = f"{HTTP}://{ip_port}"
        elif self.mode==SOCKS5:
            opts = options.Options(
                listen_port=self.proxy_port,
                confdir=str(self.mitm_config_folder),
                mode=[SOCKS5],
            )
            self.proxy_str = f"{SOCKS5}://{ip_port}"           
        else:
            raise ValueError(f"Unsupported mitm mode: {self.mode}")
            
        self.dump_master = DumpMaster(
            opts,
            with_termlog=False,
            with_dumper=False,
        )
        try:
            LOGGER.info("Starting mitm server%s, proxy=%s", up_log_str, self.proxy_str)
            self.dump_master.addons.add(self.ws_data_addon)
            await self.dump_master.run()
        except Exception as e:
            LOGGER.error("Exception in starting MITM server: %s", e, exc_info=True)
        except BaseException as e:
            LOGGER.error("Exception in starting MITM server: %s", e, exc_info=True)
        finally:
            self.proxy_str = None
        LOGGER.debug("mitm thread exiting")
    
    def stop(self):
        """ shutdown mitm proxy server and join thread"""        
        if self.mitm_thread and self.mitm_thread.is_alive():
            self.dump_master.shutdown()
            del self.dump_master
            self.dump_master = None
            self.mitm_thread.join()
    
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
        """Check MITM cert, and install if needed
        Return:
            bool: True if cert installed already or successfully. False if failed or timeout"""
        if not utils.wait_for_file(self.cert_file, timeout):
            LOGGER.error("MITM certificate not found: %s", self.cert_file)
            return False
        res, text = utils.is_certificate_installed(self.cert_file)
        if res:
            LOGGER.info("MITM certificate already installed: %s", self.cert_file)
            return True
        else:
            LOGGER.info("MITM cert not installed:\n%s", text)

        LOGGER.info("Installing MITM certificate: %s", self.cert_file)
        install_success, msg = utils.install_root_cert(self.cert_file)
        if install_success:
            LOGGER.info("Installed MITM certificate successfully. Output:\n%s",msg)
            return True
        else:
            LOGGER.error("Failed to install MITM certificate. Please install manually. Output:\n%s",msg)
            return False

            
if __name__ == '__main__':
    # Test code
    utils.initialize_logging('MITM_TEST')    
    mitm = MitmController(8999)
    LOGGER.info("Starting MITM")
    mitm.start()
    LOGGER.info("Installing certificate")
    res = mitm.install_mitm_cert()    
    LOGGER.info("MITM on:%s", mitm.is_running())
    LOGGER.info("Shutting down mitm")
    mitm.stop()
    LOGGER.info("MITM on:%s", mitm.is_running())
    import time
    time.sleep(1)
    LOGGER.info("MITM on:%s", mitm.is_running())