from typing import List

from obg.core.evaluation import EvaluatedObject
from obg.core import exceptions

class Validator:
    def __init__(self) -> None:
        pass
    
    def check(self, evaluation: EvaluatedObject):
        raise NotImplementedError()
    
class SymmetricalAlignmentValidator(Validator):
    
    def check(self, evaluation: EvaluatedObject):
        lengths = {len(b) for b in evaluation.blocks}
        if lengths != len(evaluation.blocks):
            raise exceptions.ValidationError("blocks are not symmetrical")
    
class MaxSubjectsValidator(Validator):
    
    def __init__(self, max_value:int) -> None:
        super().__init__()
        self.max_value = max_value
    
    def check(self, evaluation: EvaluatedObject):
        for block in evaluation.blocks:
            if len(block) > self.max_value:
                raise exceptions.ValidationError("block has too many subjects")