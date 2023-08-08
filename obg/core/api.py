
from typing import Dict, Iterable, Tuple, Any, List

from obg.core import protocols, statistics, tree, process, evaluation, exceptions, validators
from obg.utils.logging import logger, Log

import operator

from itertools import chain
import copy
import time

DEFAULT_PROTOCOL = protocols.DefaultProtcol()
STARTING_PROCESS = 0

class Generator:
    '''
    Object to generate a set of option blocks
    '''
    def __init__(
        self, 
        data:Dict[Any, Iterable[str]],
        options:Iterable[str],
        *,
        number_of_blocks: int,
        class_size:int, 
        protocol: protocols.Protocol | protocols.chain_protocols =None,
        validators: Iterable[validators.Validator] = None,
        debug = False,
        **opts
        ) -> None:
        
        self.data = data
        self.options = options
        self.number_of_blocks = number_of_blocks
        self.protocol = protocol or DEFAULT_PROTOCOL
        self.class_size = class_size
        self.validators = [] if not validators else validators
        self.debug = debug
        
        self.stats = {
            "generation_time": 0,
            "evaluation_time": 0,
            "nodes": 0,
            "generated_blocks": 0,
        }
        self.cache = None
        self._ready = False
        self.node = None
        self.best_evaluation = None
        self.matching_best = []
        
        self.opts = opts
        
    @property
    def ready(self):
        return self._ready
    
    @property
    def state(self):
        return self.node.state
        
    def setup(self, raise_exceptions=True):
        '''
        runs checks and setups the necessary components for generation. Must be run
        before .run() otherwise an error will be raised
        '''
        logger.debug("generator setup starting")
        # stage 1: initialise some variables
        self.check_protocols()
        statistics.State.creation_counter = 0
        evaluation.EvaluatedObject.creation_count = 0
        
        
        if self.protocol.is_using(protocols.OrderingProtocol):
            self.options = sorted(self.options)
        
        self.cache = statistics.Cache(self.data, self.options)
        self.cache.debug_options = self.opts.pop("debug_options", {})
        self.cache.logger = Log(**self.cache.debug_options)
        
        node = tree.Node()
        node.util = evaluation.EvaluationUtility(self.cache)
        node.opts = self.opts
        node.protocol = self.protocol
        # initialise state
        initial_state = statistics.State()
        initial_state.cache = self.cache
        initial_state.stats = statistics.CachedStats(self.cache)
        initial_state.blocks = [[] for _ in range(self.number_of_blocks)]
        initial_state.process_index = STARTING_PROCESS 
        initial_state.current_process = process.PROCESSES[STARTING_PROCESS]    
        
        # run checks
        try:
            self.check_data()  
        except exceptions.ValidationError as e:
            if raise_exceptions:
                raise e from None
            self.cache.logger.output(e, level="fatal")
            return False  
        
        # stage 2: calculate important statistics
        self.cache.popularity = statistics.subject_popularity(
            data=self.data,
            option_codes=self.options
        )
        initial_state.classes = statistics.calculate_classes(
            self.cache.popularity, 
            class_size=self.class_size, 
            maximum=self.number_of_blocks
        )
        
        
        self.cache.protocol = self.protocol
        node.state = initial_state
        node.cache = self.cache
        self.node = node
        
        logger.debug("generator setup finished")
        self._ready = True
        return True
        
    def get_subject_classes(self, subject:str):
        '''returns the number of classes this subject has '''
        count = self.node.state.classes.get(subject)
        if count is None:
            raise exceptions.SubjectNotFound(
                "'%s' is not a valid subject" % subject
            )
        return count
        
        
    def update_classes(self, **classes):
        '''
        update the number of classes a given subject gets
        '''
        for subject, klass in classes.items():
            self.get_subject_classes(subject)
            if klass > self.number_of_blocks:
                raise exceptions.ImproperlyConfigured(
                    "defining '%s' exceeds the maximum number of blocks '%s'" % (
                        subject, self.number_of_blocks
                    )
                )
        self.node.state.classes.update(**classes)
        
    def pre_run(self):
        # run all checks 
        if self._ready is False:
            raise exceptions.ImproperlyConfigured(
                "generation process is not ready to run. .setup() was not called or "
                "setup failed due to an unraised error"
            )
    
    def run(self):
        '''
        executes the generation process
        '''
        self.pre_run()
        start = time.perf_counter()
        try:
            self.node.run()
        except KeyboardInterrupt:
            logger.fatal("generation process MANUALLY terminated")
        except exceptions.TerminateGeneration as t:
            logger.error("[generation INTERALLY terminated] '%s'" % t.reason)
        
        end = time.perf_counter()
        self.stats["generation_time"] = end-start
        self._ready = False
        self.post_run()
        
    def post_run(self):
        # handle clean up or calculate stats
        self.stats["generated_blocks"] = len(self.cache.generated_states)
        
    def run_with_threshold(self, min_students:int=5, max_students:int=30):
        '''
        generate a set of option blocks where classes meet a given threshold of students.
        If a class does not meet the threshold, the number of classes it gets is decremented
        and the generation process repeats. 
        '''
        tracker = copy.deepcopy(self.node.state.classes)
        iteration = 0
            
        while True:
            self.node.state.classes = tracker.copy()
            self.run()
            iteration + 1

            evaluation = self.evaluate()
            self.cache.logger.output(
                "iteration '%i' has a success rate of '%f'" % (iteration, evaluation.success_percentage), level="fatal")
            if evaluation.success_percentage == 0:
                break
            with_students = evaluation.calculate_students(sentinel=max_students)
            smallest = list(with_students.blocks.get_classes(min_students))
            largest = list(with_students.blocks.get_classes(max_students, operation=operator.ge, maximum=max_students))
            
            if len(smallest) <= 0 and len(largest) <= 0:
                break
            # self.options = {"debug_options":{"branching":False, "process_completion":False, "evaluation": False}}
            self.setup()
            
            for subject in smallest:
                classes = tracker.get(subject.code)
                tracker[subject.code] = classes-1
                   
            
            for subject in largest:
                classes = tracker.get(subject.code)                
                tracker[subject.code] = classes+1        
            
    def evaluate(self, with_pathways=False):
        '''
        evaluate all the generated option blocks
        '''
        start = time.perf_counter()
        utility = evaluation.EvaluationUtility(self.node.cache)
        utility.calculate_pathways = with_pathways
        best = evaluation.EvaluatedObject()
        try:
            # multiprocess states if necessary
            for result in utility.multiprocess_states(utility.cache.generated_states):
                if not self.check_evaluation(result):
                    continue
                
                if best is None:
                    best = result
                elif result.success_percentage > best.success_percentage:
                    best = result
                elif result.success_percentage == best.success_percentage:
                    self.matching_best.append(result)
                    
        except KeyboardInterrupt:
            logger.fatal("evaluation process manually terminated")
            
        self.best_evaluation = best
        end = time.perf_counter()
        self.stats["evaluation_time"] = end-start
        return best
        
    def check_protocols(self):
        if not isinstance(
            self.protocol, (protocols.Protocol, protocols.chain_protocols)):
            raise TypeError(
                "protocol provided must inherit from 'Protocol' or use 'chain_protocols'"
            )
            
    def check_data(self):
        allowed_opts = set(self.options)
        for id, options in self.data.items():
            if len(options) > self.number_of_blocks:
                raise exceptions.ValidationError(
                    "'%s' has a number of options that exceeds the maximum number of blocks" % id
                )
            for opt in options:
                if opt not in allowed_opts:
                    raise exceptions.ValidationError(
                        "invalid option '%s'" % opt  
                    )
    
    def check_subjects(self, iterable: Iterable):
        
        for subject in iterable:
            if subject not in self.cache.option_codes:
                raise exceptions.SubjectNotFound(
                    "subject '%s' is not a valid subject code" % subject 
                )
        
    def check_evaluation(self, evaluation: evaluation.EvaluatedObject):
        try:
            for validator in self.validators:
                validator.check(evaluation)
            return True
        except exceptions.ValidationError:
            return False
          
    def pprint_statistics(self):
        
        for stat, result in self.stats.items():
            logger.debug("[%s] => (%s)" % (stat, result))
            
    def define_ebacc(self, 
                  humanities: List[str], 
                  science: List[str], 
                  languages: List[str], 
                  vocational: List[str]
                  ):
        '''
        define EBacc subjects which will be used for calculating pathways
        '''
        try:
            self.check_subjects(chain(humanities, science, languages, vocational))
        except (exceptions.SubjectNotFound) as e:
            raise exceptions.ImproperlyConfigured(
                'while defining EBacc subjects "%s"' % e
                )
        
        self.cache.Ebacc = {
            "humanities": humanities,
            "sciences": science,
            "languages": languages,
            "vocational": vocational
        }
        
