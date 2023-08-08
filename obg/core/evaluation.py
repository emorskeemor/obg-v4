import copy
from typing import Any, Dict, List, Tuple, Iterable

from obg.core import pathways, statistics, exceptions
from obg.core.blocks import OptionBlocks
from obg.utils import config, logging

import signal


def initializer():
    """Ignore CTRL+C in the worker process."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
# evaluation will use multiprocessing when there are more than
# this many states
MULTIPROCESS_THRESHOLD = 50
FAILED_OPTION_PRIORITY = config.Config.getint(
    "failed_option_priority", fallback=2
)


class EvaluatedObject:
    '''
    An evaluation of set of a option blocks
    '''
    creation_count = 0
    
    __slots__ = (
        "failed_options", "successful_options", "blocks", "total_students",
        "evaluated", "success_percentage", "paths_enabled", "id", "unhandled_students"
    )
    
    def __init__(self) -> None:
        self.failed_options: Dict[str, Dict] = dict()
        self.successful_options: Dict[str, Student] = dict()
        self.blocks: OptionBlocks = None
        self.total_students = 0
    
        self.evaluated = False
        self.success_percentage:float = 0
        self.paths_enabled = True
        self.id = EvaluatedObject.creation_count
        self.unhandled_students = {}
        EvaluatedObject.creation_count += 1
        
    def __hash__(self) -> int:
        return hash(tuple(map(tuple, self.blocks)))
    
    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, self.__class__):
            raise TypeError(
                "can only compare evaluated objects together"
            )
        return __value.blocks == self.blocks
        

    def pprint(self, full_repr=False):
        """
        pretty print evaluation to stdout
        """
        print(f"\nTotal generation statistics ID[{EvaluatedObject.creation_count}]:")
        print("\nTotal options : %i" % self.total_students)
        print("Successful options : %i" % len(self.successful_options))
        print("Failed options : %i" % len(self.failed_options))
        print("Success percentage : %f %%" % self.success_percentage)
        
        if self.blocks:
            print("\nblocks generated :")
            self.blocks.pprint(full_repr)
        else:
            print("no blocks generated")
        
                    
    def _set_success_percentage(self):
        # assert to avoid a zero error
        assert self.total_students, "total students must not equal to 0"
        success = len(self.successful_options)
        self.success_percentage = round(success/self.total_students*100, 2)
        
    def calculate_students(self, sentinel=None):
        '''
        calculates the number of students per class in this given set of option blocks
        '''
        for student_id, student in self.successful_options.items():
            for code, block in student.options:
                klass = self.blocks.retrieve(block-1, code)
                if sentinel and klass.students - 1 >= sentinel:
                    self.unhandled_students[student_id] = student
                    klass.students = sentinel
                else:
                    klass.increment_students()
                
        return self
    
from multiprocessing import Pool
from dataclasses import dataclass

@dataclass
class Student:
    
    options: list
    pathway: pathways.BasePathway
    
    priorties: list = None
    exceptions: List[Exception] = None
    
@dataclass
class FailedStudent:
    options: list
    pathway: pathways.BasePathway
    priorities: list = None

    
    
class EvaluationUtility:
    '''
    Evaluation utility to evalute a set of data against a set of blocks
    '''    
    # the order in which we check these paths matter as people on path four
    # did not follow any of the paths
    default_pathways = pathways.DEFAULT_PATHWAYS
    
    def __init__(self, cache: statistics.Cache, **options: object) -> None:
        # copy data and blocks 
        klass = self.__class__
        self.cache = cache
        self.options: Dict = options
        
        # evaluation options
        # pathways disabled for now during testing
        self.calculate_pathways = False
        self.default_pathways = klass.default_pathways
        
                
    def try_against_blocks(
        self,  
        blocks:List[List[str]],
        options:List, 
        order=True,
        raise_exceptions=True, 
        prioritise:int=None
        ) -> List[Tuple[str,int]]:
        '''
        try a set of options against the given set of blocks. set order
        to false to prioritise the initial order instead of automatically ordering.
        '''
        # deep copy blocks and options as we are going to be manipulating them
        # but we need to make sure we still have an untouched version for other options
        blocks = copy.deepcopy(blocks)
        options = copy.copy(options)
        # order blocks by number of available subjects
        required_iters = len(options)
        current_iters = 0
        handled = []
        # iterate until the length of subjects have been dealt with
        while current_iters < required_iters:
            counts = statistics.subject_block_count(options, blocks)
            # decide whether to order the counts or not. We want to do this
            # when prioritising a level of choices by original order
            if order:
                subject, count = [
                    (subj,occ) for subj, occ in sorted(counts.items(), key=lambda x:x[1])
                    ][0]
            else:
                subject, count = list(counts.items())[0]
            if count == 0:
                # if the count is 0, it means that the option could not be found in
                # the option blocks. This could be due to another subject already
                # taking up an option block.
                if prioritise is not None:
                    assert type(prioritise) is int, "prioritise must be an integer"
                    if prioritise > len(handled):
                        raise exceptions.PriorityFailed(
                            "unable to match options against priority level")
                if raise_exceptions:
                    raise exceptions.EvaluationFailed(
                        "%s could not be evaluated" % subject,
                    )
            # iterate through each block and try and insert the subject
            for block, subjects in enumerate(blocks):
                # check that the block has not already been dealt with
                if subjects is not None and type(subjects) is list:
                    if subject in subjects:
                        # if the subject is found, we have dealt with a subject
                        # and we need to set the block we found it in to be unusable
                        # and get detail about what we did with the subject
                        handled.append((
                            subject,
                            block+1
                        ))
                        blocks[block] = None
                        break

            options.remove(subject)
            current_iters += 1

        if raise_exceptions:
            # saftey net
            assert len(handled) == required_iters, "unmatched handled subjcts"
        return handled

    def get_pathway(self, options:List[str]):
        '''
        returns the pathway a set of options follow
        '''
        if self.calculate_pathways is False:
            return None
        paths:List[pathways.BasePathway] = self.options.get("pathways", self.default_pathways)
        for possible_path in paths:
            try:
                path = possible_path(self.cache.Ebacc)
                return path(*options)
            except exceptions.PathwayFailed:
                pass
        # raise an error meaning that the path ways we provided resulted in no
        # fallback pathway to be found
        raise exceptions.ImproperlyConfigured("could not find a general pathway for this object")

    def prioritise_failed(self, blocks:List[List[str]], options:List[str], level=FAILED_OPTION_PRIORITY):
        '''
        evaluate failed options by prioritising their original order
        '''
        # we know that these options will not evaluate sucessfully but we
        # can at least priorities a certain number of subjects that are in
        # order
        try:
            return self.try_against_blocks(
                blocks=blocks,
                options=options, 
                order=False, 
                raise_exceptions=False,
                prioritise=level
                )
        except exceptions.PriorityFailed as failed:
            # if this occurs, it means that we could not priories the level
            # of options specified which can be a raise for concern to the end
            # user
            return failed
        
    def evaluate_blocks(self, blocks:List[List[str]]):
        # create a new evaluation instance to store results
        if self.calculate_pathways is True and self.cache.Ebacc is None:
            raise exceptions.ImproperlyConfigured(
                "evaluating pathways requires EBACC subjects to be provided "
                "or set .evaluate_pathways to False "
                )
        
        evaluation = EvaluatedObject()
        evaluation.total_students = len(self.cache.data)
        evaluation.paths_enabled = self.calculate_pathways
        # iterate through each set of student options
        for key, student_options in self.cache.data.items():
            try:
                opts = self.try_against_blocks(blocks, student_options)
                pathway = self.get_pathway(student_options) 
                
                evaluation.successful_options.update({
                    key: Student(opts, pathway)
                })
            except exceptions.EvaluationFailed as failure:
                # if the evaluation failed, log why it failed
                errors = [failure]
                prioritised = self.prioritise_failed(
                    blocks, 
                    student_options,
                    level=self.options.get("failed_priority")
                    )

                if isinstance(prioritised, exceptions.EvaluationFailed):
                    errors.append(prioritised)
                    prioritised = None
                evaluation.failed_options.update({ 
                    key: Student(
                        options=student_options,
                        pathway=self.get_pathway(student_options),
                        priorties=prioritised,
                        exceptions=errors
                    )}
                )
        evaluation._set_success_percentage()
        evaluation.blocks = OptionBlocks(blocks, self.cache)
        # set evaluated flag to true to ensure all processes have been completed
        evaluation.evaluated = True
        self.cache.logger.output(
            "evaluation finished for '%s' with success rate '%f'" % (evaluation.id, evaluation.success_percentage),
            level="debug",
            grouping="evaluation"
            )
        return evaluation
    
    def multiprocess_states(self, states: Iterable[statistics.State]) -> Iterable[EvaluatedObject]:
        '''
        multiprocess states if the length of states passes a given threshold and is enabled. It will use
           .process_states() if it does not need to use multiprocessing.        
        '''
        if (
            len(states) > config.Config.getint("evaluation-threshold", fallback=MULTIPROCESS_THRESHOLD) 
            and self.cache.within_deamon is False 
            and config.Config.getbool("evaluation-multiprocessing", fallback=True)
            ):
            
            with Pool(initializer=initializer) as pool:
                self.cache.within_deamon = True
                try:
                    self.cache.logger.output("using multiprocessing", level="fatal")
                    return pool.map(self.evaluate_state, self.cache.generated_states)  
                except KeyboardInterrupt:
                    pool.terminate()
                    pool.join()
                    logging.logger.fatal("multiprocessing states was manually terminated")
                    return []
        else:
            return self.process_states(states)

    
    def process_states(self, states: Iterable[statistics.State]):
        '''default way to evaluate states'''
        for state in states:
            yield self.evaluate_blocks(state.blocks)
            
            
    def evaluate_state(self, state: statistics.State):
        return self.evaluate_blocks(state.blocks)
        
        
        

    def __str__(self) -> str:
        return "<EvaluationUtility>"

    def __repr__(self) -> str:
        return "<EvaluationUtility>"

        
    def get_student_pathways(self, data:Dict[Any, List]):
        for item, options in data.items():
            yield item, self.get_pathway(options)
                
   
    