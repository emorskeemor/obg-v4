import logging
from obg.utils.config import Config

class CustomFormatter(logging.Formatter):

    blue = "\x1b[34;20m"
    white = "\x1b[42;30m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: white + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
    
logger = logging.getLogger("obg")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

ch.setFormatter(CustomFormatter())

logger.addHandler(ch)
logger.disabled = not Config.getbool("debug")

class Log:
    '''
    object to log only when enabled to by a lookup dictionary
    '''
    def __init__(self, **opts) -> None:
        self.options = opts
        
    def output(self, msg:str, level:str="log", grouping:str=None):
        func = getattr(logger, level)
        if grouping is None:
            func(msg)
        elif self.options.get(grouping, True) is True:
            func(msg)

