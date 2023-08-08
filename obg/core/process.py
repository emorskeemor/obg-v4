from obg.core import statistics, protocols
from obg.utils.config import Config
from obg.utils.logging import logger

DEFAULT_PRIORITY_QUARTILE = 0.75

class Process:
    
    PROCESS_ID = None
    
    def __init__(
        self, 
        state: statistics.State, 
        cache: statistics.Cache,
        ) -> None:
        self.state = state
        self.cache = cache
        
    def __new__(cls, *args, **kwargs):
        
        if cls.PROCESS_ID is None:
            cls.PROCESS_ID = cls.__name__
        
        return super().__new__(cls)    

    def before_process(self):
        pass
    
    def run_process(self):
        '''
        executes the process
        '''
        raise NotImplementedError()
    
    def after_process(self):
        self.cache.logger.output(
            "proccess %s [%s] successful" % (hash(self.state.id), self.__class__.__name__),
            level="info",
            grouping="process_completion"
            )
    
    @property
    def process_id(self):
        return self.__class__.PROCESS_ID
    
    @property
    def process_cache(self):
        '''retrive cache for this specific process'''
        return self.cache.process_cache.get(self.process_id)
    
    @process_cache.setter
    def process_cache(self, value):
        self.cache.process_cache[self.process_id] = value
        
    def ready_cache(self):
        '''
        use to set the cached value if it does not already exist
        
        if self.process_cache is None:
            ... 
            self.process_cache = ...
        '''
    
    def execute(self):
        '''
        executes the process
        '''
        self.ready_cache()
        self.before_process()
        self.run_process()
        self.after_process()
        
class PriorityPairs(Process):
    
    def ready_cache(self):
        if self.process_cache is None:
            singles = statistics.filter_classes(self.state.classes, value=1)
            matrix = statistics.evalute_clashes(
                statistics.clash_matrix(singles.keys()),
                self.cache.data
                )
            unique = list(set(matrix.values()))
            if len(unique) >= 1:
                quartile = unique[
                    int(Config.getfloat(
                        "priority_quartile", fallback=DEFAULT_PRIORITY_QUARTILE
                        ) * (len(unique)))
                    ]
            
                priority = statistics.filter_clashes(
                    matrix, predicate=lambda x:x[1] >= quartile
                    )
            else:
                self.cache.logger.output("no priority pairs", level="fatal")
                priority = {}
            self.process_cache = priority
        
    
    def run_process(self):
        for first, second in self.process_cache:
           self.state.auto_populate(subject=first, iterations=1)
           self.state.auto_populate(subject=second, iterations=1)
        
           
class RemainingPairs(Process):
    
    def ready_cache(self):
        if self.process_cache is None:
            singles = statistics.filter_classes(self.state.classes, value=1)
            remaining = set(self.state.used).symmetric_difference(singles.keys())
            if self.cache.protocol.is_using(protocols.OrderSetProtocol):
                remaining = sorted(remaining)
                
            self.process_cache = remaining
            
    
    def run_process(self):

        for subject in self.process_cache:
            self.state.auto_populate(subject=subject, iterations=1)
            
class MainProcess(Process):
    
    def ready_cache(self):
        if self.process_cache is None:
            self.process_cache = dict()
            
    def run_process(self):
        # do not repeat the proccess for single classes or negligible
        for use in reversed(range(1, len(self.state.blocks))):

            for subject in statistics.filter_classes(self.state.classes, use):
                self.state.auto_populate(
                    subject=subject,
                    iterations=use
                )
               
            
import operator

class Negligible(Process):

    def run_process(self):
        for subject in statistics.filter_classes(
            self.state.classes,
            value=len(self.state.blocks),
            operation=operator.ge,
            ):
            self.state.populate_all_blocks(subject=subject)
    
   

        
PROCESSES = [PriorityPairs, RemainingPairs, MainProcess, Negligible]