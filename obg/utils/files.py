
import csv
import os
import copy

from obg.utils.config import STATIC_ROOT, Config

DATA_FILE_LOOKUP = "data-file"
OPTIONS_FILE = "options-file"

def read_csv(path:str):
    with open(os.path.join(STATIC_ROOT, path), "r") as file:
        reader = csv.reader(file)
        return list(reader)
    
def get_data(using=None):
    return read_csv(Config.get(using or DATA_FILE_LOOKUP))

def get_options(using=None):
    return read_csv(Config.get(using or OPTIONS_FILE))

def options_from_data(data:dict):
    seen = set()
    for student in data.values():
        for opt in student:
            seen.add(opt)
    return seen

def reformat_data(data:dict):
    
    opts = options_from_data(data)
    mapping = dict.fromkeys(opts, None)
    for opt in opts:
        auto = str(opt[:2]).capitalize()
        code = input("designate new code for '%s' [%s] : " % (opt, auto))
        if not code:
            code = auto
        mapping[opt] = code
    copied = copy.deepcopy(data)
    for uid, opts in data.items():
        
        copied[uid] = [mapping.get(opt) for opt in opts]
    return copied, list(mapping.values())
            
def dump_reformated_data(data:dict, options:list):
    
    name = input("save DATA as : ")
    with open(os.path.join(STATIC_ROOT, name), "w", newline='') as f:
        writer = csv.writer(f)
        for student in data.values():
            writer.writerow(student)
            
    name = input("save OPTIONS as : ")
    with open(os.path.join(STATIC_ROOT, name), "w", newline='') as f:
        writer = csv.writer(f)
        for _ in range(len(options)):
            writer.writerow(options)
    