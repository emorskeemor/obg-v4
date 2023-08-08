from typing import Iterable

class SubjectError(Exception):
    '''
    Error when dealing with a subject
    '''
    pass

class SubjectNotFound(SubjectError):
    '''
    subject was not found
    '''
    pass

class SubjectAlreadyExists(SubjectError):
    '''
    subject already exists
    '''
    pass

class BranchRequired(Exception):
    '''
    Interrupt to signal a branch is required. This is used when multiple options need to be tested.
    '''
    def __init__(self,*, state, options:list, subject_code:str, override_state=False, insert=True) -> None:
        super().__init__()
        self.state = state
        self.options = options
        self.subject_code = subject_code
        self.override_state = override_state
        self.insert = insert
                
    def __str__(self) -> str:
        return "[code:%s][opts:%s]" % (
            self.subject_code, 
            ",".join(map(str, self.options))
            )
        
    def __repr__(self) -> str:
        return "[code:%s][opts:%s]" % (
            self.subject_code, 
            ",".join(map(str, self.options))
            )
        
class MultipleBranchesRequired(Exception):
    '''
    Iterrupt to signal multiple branches are required.
    '''
    def __init__(self, branches: Iterable[BranchRequired], *args: object) -> None:
        super().__init__(*args)
        self.branches = branches
        
class ImproperlyConfigured(Exception):
    '''
    system was not configured correctly
    '''
    pass

class PathwayFailed(Exception):
    '''
    options did not meet a pathway criteria
    '''
    
class EvaluationFailed(Exception):
    '''
    evaluation was unsuccessful
    '''
    
class ValidationError(Exception):
    '''
    validation check was not passed
    '''
    
class OperationNotFound(Exception):
    '''
    operation was not found
    '''
    pass

class PriorityFailed(Exception):
    pass

class TerminateGeneration(Exception):
    '''
    stops generation process
    '''
    def __init__(self, reason, *args: object) -> None:
        super().__init__(*args)
        self.reason = reason
        
class OperationError(Exception):
    '''
    error with operation commiting
    '''

class BranchNotFound(Exception):
    '''
    operation branch not found
    '''

class MergeConflict(Exception):
    '''
    conflict found when merging two branches together
    '''

class CyclicalDepdencyConflict(Exception):
    '''
    merge cause cyclical depdencies
    '''