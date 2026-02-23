""" Logging helper functions """
import datetime
import logging
import os
import queue
from .utils import Folder, sub_file

DEFAULT_LOGGER_NAME = 'majsoul_copilot'
LOGGER = logging.getLogger(DEFAULT_LOGGER_NAME)
class LogHelper:
    """ Log helper"""
    log_file_name:str = None
    initialized:bool = False
    @staticmethod
    def config_logging(file_prefix:str=DEFAULT_LOGGER_NAME, console=True, file=True):
        """ Initialize logging format/output. Run once.
        params:
            file_prefix(str): prefix of the log file name
            console (bool): if output to console
            file (bool): if output to file
        """
        if LogHelper.initialized:
            LOGGER.warning("Logger %s already initialized", LOGGER.name)
            return

        logger = LOGGER
        level_name = os.environ.get("MJ_LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, level_name, logging.INFO)
        logger.setLevel(log_level)
        formatter = log_formatter()
        
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        if file:
            file_name = file_prefix + '_' + dt_string() + '.log'
            LogHelper.log_file_name = sub_file(Folder.LOG, file_name)
            file_handler = logging.FileHandler(LogHelper.log_file_name, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        LogHelper.initialized = True

def log_formatter() -> str:
    """ return the default log formatter"""
    return logging.Formatter('%(asctime)s %(levelname)s [%(threadName)s]%(filename)s:%(lineno)d | %(message)s')

def dt_string() -> str:
    """ return datetime string"""
    return datetime.datetime.now().strftime(r'%Y-%m-%d_%H-%M-%S')

class QueueHandler(logging.Handler):
    """ Log handler to send logging records to a thread-safe queue """
    def __init__(self, log_queue:queue.Queue):
        super().__init__()
        self.log_queue = log_queue 
        formatter = log_formatter()
        level_name = os.environ.get("MJ_LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, level_name, logging.INFO)
        self.setLevel(log_level)
        self.setFormatter(formatter)
        
    def emit(self, record):
        self.log_queue.put(record)
