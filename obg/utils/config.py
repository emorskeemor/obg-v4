from pathlib import Path
import os
import configparser

from functools import partial

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_ROOT = os.path.join(BASE_DIR, "static")

SETTINGS_LOOKUP = "settings.conf"

_GENERATION_SECTION = "GenerationSettings"



config = configparser.ConfigParser()
config.read(SETTINGS_LOOKUP)

class Config:
    '''generation settings config'''
    get = partial(config.get, _GENERATION_SECTION)
    getbool = partial(config.getboolean, _GENERATION_SECTION)
    getfloat = partial(config.getfloat, _GENERATION_SECTION)
    getint = partial(config.getint, _GENERATION_SECTION)