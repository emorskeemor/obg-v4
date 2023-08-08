from typing import List
from obg.core import statistics, evaluation, exceptions

import operator
from itertools import chain

from dataclasses import dataclass

import copy

class OptionBlocks:
    '''
    set of generated option blocks
    '''
    def __init__(self, blocks: List[List[str]], _cache: statistics.Cache) -> None:
        self.blocks: List[List[ClassOption]] = [
            [ClassOption(subject) if not isinstance(
                subject, ClassOption) 
            else subject for subject in block] for block in blocks
        ]                    
                    
        self._cache = _cache
        
    def __len__(self):
        return len(self.blocks)
    
    def __iter__(self):
        return iter(self.blocks)
    
    def __getitem__(self, pos):
        return self.blocks[pos]
    
    def __setitem__(self, __pos, __value):
        raise NotImplementedError(
            "cannot support scripting. Instead use .add_class to add a new subject")
        
    def add_class(self, block:int, subject:str):
        '''
        add a class to the block
        '''
        subject = self.normalise(subject)
        
        if subject in self.blocks[block]:
            raise exceptions.SubjectAlreadyExists(
                "subject '%s' already exists in block '%i'" % (subject.code, block))
        
        self.blocks[block].append(subject)
        
    def remove_class(self, block:int, subject:str):
        '''
        remove a class from the block
        '''
        subject = self.normalise(subject)
        
        if subject not in self.blocks[block]:
            raise exceptions.SubjectNotFound("subject '%s' not found in block '%i'" % (subject, block))
        
        self.blocks[block].remove(subject)
        
    def move_class(self, target:int, to:int, subject:str):
        '''
        move a class from 'target' to another block 'to'
        '''
        if subject not in self.blocks[target]:
            raise exceptions.SubjectNotFound("subject '%s' not found in block '%i'" % (subject, target))
        if subject in self.blocks[to]:
            raise exceptions.SubjectAlreadyExists(
                "subject '%s' already exists in block '%i'" % (subject.code, to)
                )
        self.remove_class(target, subject)
        self.add_class(to, subject)

        
    def normalise(self, subject:str):
        '''convert a subject to an object'''
        if not isinstance(subject, ClassOption):
            if not isinstance(subject, str):
                raise TypeError("item to add must be a string")
            subject = ClassOption(subject)
        return subject
    
    def copy(self):
        blocks = copy.deepcopy(self.blocks)
        return self.__class__(blocks, self._cache)
    
    def raw(self):
        return [[subject.code for subject in block] for block in self.blocks]
    
    def _subject_popularity(self):
        return statistics.subject_popularity(
            self._cache.data,
            self._cache.option_codes
            )

    def retrieve(self, block:int, subject:str):
        for klass in self.blocks[block]:
            if klass.code == subject:
                return klass
        raise exceptions.SubjectNotFound(
            "subject '%s' was not found in block '%s'" % (subject, block)
        )
        
                    
    def discard_small_classes(self, minimum:int=0):
        '''
        remove classes which have a number of subjects less than the minimum. If not provided,
        classes with 0 students will be discarded.
        '''
        populated_blocks = [[] for _ in range(len(self.blocks))]
        for index, block in enumerate(self.blocks):
            for subject in block:
                if subject.students > minimum:
                    populated_blocks[index].append(subject)
        return self.__class__(populated_blocks, self._cache)
    
    def get_classes(self, students:int, operation=operator.lt, minimum=0, maximum=40):
        '''
        returns a tuple of classes which have less than a given number of students. 
        allow_max = False will leave out classes equal or greater than the number of blocks
        '''
        # if not allow_max:
        #     return tuple(chain(
        #         *[[subject for subject in block if operation(subject.students, students) and subject.students < len(self.blocks)] 
        #           for block in self.blocks]
                
            
        return tuple(
            chain(*[[subject for subject in block if operation(subject.students, students) and subject.students > minimum and subject.students < maximum
                     ] for block in self.blocks
                    ]))

    
    def collate_student_options(self):
        '''return sum of all students in the option blocks'''
        return sum([sum([subject.students for subject in block]) for block in self.blocks])
    
    def collate_number_of_options(self):
        '''returns the total number of options from the cache data'''
        return sum([len(options) for options in self._cache.data.values()])

    def check(self):
        '''
        [DEBUG ONLY] run checks on this set of blocks
        '''
        diff = self.collate_number_of_options() - self.collate_student_options()
        if diff != 0:
            self._cache.logger.output(
                msg="'%s' options were lost" % (diff),
                level="fatal"
            )
            
    def evaluate(self, **opts):
        '''
        evaluate this set of option blocks. Note, students calculated will be discarded
        '''
        util = evaluation.EvaluationUtility(self._cache, **opts)
        return util.evaluate_blocks(self.raw())
        
    def pprint(self, full_repr=False):
        '''
        pretty print blocks to stdout
        '''
        for block in self.blocks:
            if full_repr:
                print(block)
            else:
                print(", ".join(map(str, block)))
                
    
    
@dataclass(slots=True)
class ClassOption:
    '''
    represents a class in the option blocks
    '''
    code: str
    students: int = 0
    
    def __str__(self) -> str:
        return "%s(%i)" % (self.code, self.students)    
    
    def __eq__(self, __value: object) -> bool:
        return __value == self.code

    def increment_students(self, value=1):
        self.students += value
        
