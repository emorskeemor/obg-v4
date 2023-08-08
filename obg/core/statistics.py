# methods for matching and subject clashing

from itertools import combinations, chain
from typing import Any, Dict, Iterable, List, Tuple, Callable, Set

import copy

from obg.core import exceptions
from obg.utils.logging import logger

# clash methods

def clash_count(subjects:Iterable, data:Dict[Any,List]):
    '''
    returns a count of the number of times an arbitrary number of subjects
    exist in student's choices. e.g. checking Fr, Ge will return a count where
    Fr and Ge BOTH exist in a student's choices
    '''
    count = 0
    for student_options in data.values():
        matched = sum([1 for subj in set(subjects) if subj in student_options])
        if matched == len(subjects):
            count += 1
    return count
        

def clash_matrix(option_codes:List):
    '''
    generates a clash matrix
    '''
    clashes = list()
    for comparission in combinations(option_codes, 2):
        clashes.append(tuple(sorted(comparission)))
    return clashes

def evalute_clashes(clashes:set, data:Dict[Any, List]):
    '''
    returns a dictionary of clashes and their counts
    '''
    # essentially, we go through each clash from a set of clashes
    # and check each students option's to see how often it clashes
    return {clash:clash_count(clash, data) for clash in clashes}

def order_clashes(clashes:Dict[Tuple, int], reverse=True):
    '''
    order a dictionary of clashes by the number of clashes
    '''
    return {clashes:value for clashes, value in sorted(clashes.items(), key=lambda x:x[1], reverse=reverse)}

def filter_clashes(clashes:Dict[Tuple, int], predicate:Callable=None):
    '''
    return clashes filtered by a given conditional function. E.g.
    lambda x:x[1] > 1 returns all clashes greater than 1
    '''
    return dict(filter(predicate, clashes.items()))

def subject_popularity(data:Dict[str, List], option_codes:List[str]):
    '''
    gets the popularity counts of each subject from a dataset
    '''
    counts = dict.fromkeys(option_codes, 0)

    for student_opts in data.values():
        for option in student_opts:
            current_value = counts.get(option, None)  
            if current_value is None:
                raise exceptions.SubjectNotFound(
                    "subject '%s' was not found in the available options" % option
                )
            counts[option] = current_value + 1
            
    return counts

def subject_block_count(option_codes:List[str], blocks:List[List[str]]):
    '''
    count the occurances of options in a given set of blocks
    '''
    counts = dict.fromkeys(option_codes, 0)

    for option in option_codes:
        value = counts.get(option, None)
        occurances = 0
        for block in blocks:
            if block is None:
                continue
            if option in block:
                occurances += 1
        counts[option] = value + occurances
    return counts

def calculate_classes(popularity:Dict[str, int],*, class_size:int, maximum=None) -> Dict[str, int]:
    '''
    returns a dict of {subject_code:classes_for_subject} for each of the subject counts.
    '''
    results = {}
    for subj_code, count in popularity.items():
        classes = 0
        if classes == class_size:
            classes = 1
        else:
            classes = (int(count) // class_size) + 1
        # set max if given
        if maximum and classes > maximum:
            classes = maximum
        results[subj_code] = classes
    return results

import operator

def filter_classes(classes:Dict[str, int], value:int, operation:Any=operator.eq):
    '''
    order the grouped counts.
    '''
    return dict(filter(lambda i:operation(i[1], value), classes.items()))

from obg.core.protocols import Protocol
from obg.utils.logging import Log
    
class ProcessCache(dict):
    
    pass


class Cache:
    '''
    generation cache for a specific generation instance. Only exists as long as the generation processing is active
    '''
    
    def __init__(self, data: Dict[Any, Iterable], option_codes: Iterable[str]) -> None:
        self.data = data
        self.option_codes = option_codes
        self.popularity = {}
        self.protocol: Protocol = None
        self.generated_states = set()
        self.process_cache = dict()
        self.within_deamon = False
        self.debug_options = {}
        self.logger: Log = None
        self.Ebacc = None
        
        # extra settings 
        self._options = {}
        
    def copy(self):
        data = copy.deepcopy(self.data)
        option_codes = copy.copy(self.option_codes)
        new = self.__class__(data, option_codes)
        new.popularity = self.popularity
        
        
                
class CachedStats:
    '''
    object that calculates clashes between subjects. 
    '''
    # an object is used to allow for caching 
    def __init__(self, cache: Cache) -> None:
        self.data = cache.data
        self._cache = {}

    def subject_block_clashes(self, subject_code:str, block:List) -> int:
        '''
        similar to 'subject_block_clashes' but caches using a given dictionary and returns the clash
        count and a dictionary that has not yet been cahed
        '''
        clashes = 0
        for subject in block:
            # sort the clash as, when we are using a clash matrix, the clashes will be ordered
            # by alphabetical order. We need to do this to cache properly and find the correct
            # cached value if it exists
            clash = tuple(sorted((subject, subject_code)))
            cached = self._cache.get(clash, None)
            if cached is None:
                count = clash_count(clash, self.data)
                self._cache.update({clash:count})
                clashes += count
            else:
                clashes += cached
        return clashes

    def total_block_count(self, subject_code:str, blocks:List[List]) -> List[int]:
        '''
        cached version of 'total_block_clashes' which looks up the clash in a cache dict before
        calculating the clash. Returns a list of clash counts and an an updated version of the cache
        with clashes that were not yet cached
        '''
        # clash_counts = [cached_subject_block_clashes(subject_code, block, data, cache) for block in blocks]
        # return clash_counts
        clash_counts = []
        for block in blocks:
            count = self.subject_block_clashes(subject_code, block)
            clash_counts.append(count)
        return clash_counts
    
    def clear_cache(self):
        self._cache = {}
        
    


# matching methods

def match_subjects(subjects: List[str], data:Dict[Any,List]):
    '''
    very similar to 'clash_count' but returns the matches students
    instead
    '''
    matched_subjects = dict()
    for key, student_options in data.items():
        matched = sum([1 for subj in subjects if subj in student_options])
        if matched == len(subjects):
            matched_subjects[key] = student_options
    return matched_subjects

_pred = lambda x: x

class clean:
    def __init__(self, predicate: Callable = _pred) -> None:
        self.predicate = predicate
        
    def __call__(self, value) -> Any:
        base = self.predicate(value)
        return [i for i in base if i]
        

def to_dict(data:List[List[str]], predicate: Callable=_pred):
    return {key: predicate(value) for key, value in enumerate(data)}

import uuid

def to_dict_uuid(data:List[List[str]], predicate: Callable=_pred):
    '''
    attaches uuid4 to each item
    '''
    return {uuid.uuid4(): predicate(value) for value in data}

def to_list(data:List[str], predicate: Callable=_pred):
    return [predicate(i) for i in data]


        
class State:
    
    creation_counter = 0
    
    __slots__ = (
        'blocks', 'classes', 'together', 'current_process', 'process_index',
        'cache', 'stats', 'id', 'allow_branching', 'used'
        )
    
    def __init__(self) -> None:
        self.blocks: List[List[str]] = list()
        # keeps track of the number of classes a subject still has 
        self.classes: Dict[str, int] = dict()
        self.together: Dict[str, Dict[str,int]] = dict()
        self.used: Set = set()
        
        # keeping track of processes
        self.current_process = None
        self.process_index: int = None
 
        self.cache: Cache = None
        self.stats: CachedStats = None
        
        self.allow_branching = True
        
        self.id = self.__class__.creation_counter
        self.__class__.creation_counter = self.id + 1
        
    def __hash__(self) -> int:
        # how 'unique' a node will depend on the blocks it currently has
        return hash(tuple(map(tuple, self.blocks)))
    
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, State):
            raise TypeError(
                "can only compare 'State' instances with each other"
            )
        return __o.blocks == self.blocks
        
                
    def __str__(self) -> str:
        return "StateObject[%i]" % State.creation_counter
    
    def copy(self):
        new = self.__class__()
        new.blocks = copy.deepcopy(self.blocks)
        new.classes = copy.deepcopy(self.classes)
        new.together = copy.deepcopy(self.together)
        new.used = self.used.copy()
        
        new.current_process = self.current_process
        new.process_index = self.process_index        
        
        new.cache = self.cache
        new.stats = self.stats
        
        new.allow_branching = self.allow_branching
        
        return new
    
    # insertion methods
    
    def raw_insert(self,*,subject:str, index:int):
        '''
        insert a subject into a given block
        '''
        assert index >= 0, "value must be greater than 0"
        assert index < len(self.blocks), "greater than number of blocks"
        block = self.blocks[index]
        usage = self.classes.get(subject, None)
        if usage is None:
            raise exceptions.SubjectNotFound(
                "unknown subject '%s' is trying to be inserted" % subject
            )
        if subject in block:
            raise exceptions.SubjectAlreadyExists(
                "'%s' already exists in block index '%s'" % (subject, block)
            )
        self.used.add(subject)
        self.blocks[index].append(subject)
        self.classes[subject] = usage - 1
        
    
    def raw_insert_many(self, subjects:Iterable,*,index:int):
        '''insert many subjects into a given block'''
        for subject in subjects:
            self.raw_insert(subject=subject, index=index)
    
    def populate_all_blocks(self,*,subject:str):
        ''' adds a given subject to all blocks'''
        for block_index in range(len(self.blocks)):
            self.populate_block(
                subject=subject,
                index=block_index
            )
    
    def populate_block(self,*,subject:str, index:int):
        '''
        proxy method to raw_insert()
        '''
        try:
            self.raw_insert(subject=subject, index=index)
            return True
            # handle double inserts
        except (exceptions.SubjectAlreadyExists, exceptions.SubjectNotFound) as e:
            return False
    
    def auto_populate(self, *, subject:str, iterations:int, raise_exceptions=True):
        '''
        uses heuristics to decide the best block to insert a subject into. It will repeat
        this n times. May raise a BranchRequired() interupt to signal there are multiple
        blocks the subject can be insert into.
        '''
        for _ in range(iterations):
            usage = self.classes.get(subject)
            
            if usage <= 0:
                return None
            clashes = list(enumerate(self.stats.total_block_count(
                subject_code=subject,
                blocks=self.blocks
            )))
            inserted = False
            while inserted is False and len(clashes) > 0:
                # get the block with the smallest clash count
                block_num, clash_count = min(clashes, key=lambda x:x[1])
                duplicates = self._find_duplicates(
                    block_clashes=clashes, 
                    matching=clash_count,
                    subject=subject
                    )
                if len(duplicates) > 1 and self.allow_branching and raise_exceptions:
            
                    raise exceptions.BranchRequired(
                        state=self, 
                        options=duplicates, 
                        subject_code=subject
                        )

                if self.populate_block(subject=subject, index=block_num) is False:
                    # if we weren't able to populate the given block, remove that
                    # block from the block clashes and move on
                    clashes.remove((block_num, clash_count))
                else:
                    inserted = True
            if inserted is False:
                raise exceptions.SubjectError(
                    "unable to insert subject '%s' into the given option blocks" % subject
                )
            
    def _find_duplicates(self, block_clashes, matching:int, subject:str):
        # return a list of indexes where we have multiple blocks matching the
        # same number of clashes. Blocks are ignore if they are empty or already
        # contain the subject
        indexes = []
        for block_num, count in block_clashes:
            block = self.blocks[block_num]
            if count == matching and len(block) > 0 and subject not in block:
                indexes.append(block_num)
        return indexes
    