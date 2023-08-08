from obg.core import statistics, process, exceptions, evaluation, protocols
from obg.utils.logging import logger

import itertools
import copy

from functools import partial

class Node:
    
    processes = process.PROCESSES
    creation_counter = 0
    
    def __init__(self, parent=None) -> None:
        self.parent = parent
        self.children = []
        self.state: statistics.State = None
        self.cache: statistics.Cache = None
        
        self.id = self.__class__.creation_counter
        self.__class__.creation_counter = self.id + 1
        
        self.util: evaluation.EvaluationUtility = None
        self.protocol: protocols.Protocol = None
        
        
    def copy(self):
        new = self.__class__(parent=self)
        self.children.append(new)
        new.state = self.state.copy()
        new.cache = self.cache
        new.util = self.util
        new.protocol = new.cache.protocol
        return new
    
    def __str__(self) -> str:
        parent = self.parent
        if parent is None:
            parent = "init"
        return "Node[%i]/%s" % (self.id, parent)
    
    def __hash__(self) -> int:
        # how 'unique' a node will depend on the blocks it currently has
        return hash(self.state)
    
    def run(self):
        try:
            # load the next process and execute it. If there is another process after exection,
            # recursively call to restart.
            self.load_next_process().execute()
            if self.continue_process() is True:
                self.run()
            else:
                if self.cache._options.get("check_finished", False):
                    self.is_finished()
                    
                self.cache.logger.output("Node complete! %s" % self.id, level="info", grouping="completion")
                self.cache.generated_states.add(self.state)
                
                # handling evaluation on the fly.
                if protocol := self.protocol.is_using(protocols.ImmediateEvaluation):
                    result = self.util.evaluate_state(self.state)
                    if result.success_percentage >= protocol.threshold:
                        raise exceptions.TerminateGeneration(
                            "state '%s' satisfied threshold" % self.state.id
                        )
                # limit the number of nodes that is allowed to be created.
                if protocol:= self.protocol.is_using(protocols.LimitProtocol):
                    if self.id + 1 > protocol.maximum:
                        raise exceptions.TerminateGeneration(
                            '"generation teriminated as it generated too many nodes'
                        )
                    
        except (exceptions.BranchRequired) as branch:
            # process may require branch, create a new node to handle this
            self.branch(branch)
        
        
    def branch(self, branch: exceptions.BranchRequired):
        # creates a new set of branches where needed
        if branch.insert:
            log_branch = partial(self.cache.logger.output, level="debug", grouping="branching")
            log_branch("creating '%i' new branches %s" % (len(branch.options), branch))
            for choice in branch.options:
                log_branch("branch executing %s [%s]" % (branch, choice))
                new_node = self.copy()
                if new_node.state.populate_block(
                    subject=branch.subject_code,
                    index=choice
                ):
                    new_node.run()
                else:
                    logger.warn("branch '%s' was prevented from running" % choice)
        else:
            # does not insert but the state can be changed and used
            new_node = self.copy()
            if branch.override_state:
                new_node.state = branch.state
            new_node.run()
            
    def load_next_process(self) -> process.Process:
        # instansiate the current process
        return self.state.current_process(
            state=self.state,
            cache=self.cache
        ) 
        
    def continue_process(self):
        # check if there is another process to run and update the state
        # with the current process to execute.
        klass = self.__class__
        self.state.process_index = self.state.process_index + 1
        if self.state.process_index >= len(klass.processes):
            return False
        self.state.current_process = klass.processes[
            self.state.process_index
            ]
        return True
    
    def is_finished(self):
        '''
        raises validation error if not all classes have been fully dealt with
        '''
        for subject, classes in self.state.classes.items():
            if classes > 0:
                raise exceptions.ValidationError(
                    "node '%s' failed to populate fully."
                    " Error raised from subject '%s'" % (self.id, subject)
                )
        return True