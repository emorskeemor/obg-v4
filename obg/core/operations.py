from __future__ import annotations
from obg.core.blocks import OptionBlocks
from obg.core import exceptions
from obg.utils.config import Config

from typing import Dict, Iterable, List

MAIN_BRANCH_NAME = Config.get("main-branch-name", fallback="MAIN_BRNCH")

'''
WARNING: these are for testing and not recommeneded for use
'''
            
class LinearBranch:
    '''
    represents a set of operations to be executed in a linear fashion
    '''
    def __init__(self, nodes: List[Operation]) -> None:
        self.nodes = nodes
        self.branch_id = None
        
        self._applied_states = []
        
    def __str__(self) -> str:
        return "%s[%i]" % (self.branch_id, len(self.nodes))
        
    def apply(self, blocks: OptionBlocks):
        '''
        apply the set of operations on a given set of blocks
        '''
        if blocks is None:
            raise TypeError("cannot except non-type")
        changes = []
        for operation in self.nodes:
            blocks = operation.forwards(blocks)
            changes.append(blocks)
        self._applied_states = changes
    
        
    def get_final_state(self) -> OptionBlocks:
        '''
        get completed state after all operations have been applied
        '''
        assert len(self._applied_states) > 0, ".apply() must be called"
        return self._applied_states[-1]
    
    def pprint(self):
        '''pretty print all nodes to execute in order'''
        for node in self.nodes:
            print(node)
                    
    def merge(self, branch: LinearBranch, target):
        '''
        merge a given branch with the current branch
        '''
        start = branch.nodes[0]
        start_index = self.nodes.index(start)
        if target not in self.nodes:
            raise exceptions.OperationNotFound(
                "target operation '%s' was not found in branch '%s'" % (target.operation_name, branch.branch_id)
            )
        end_index = self.nodes.index(target)
        starting_op = self.nodes[start_index]
        merged = starting_op.merge(branch.branch_id, MAIN_BRANCH_NAME)
        self.nodes[end_index].dependency = merged[-1]
        self.nodes = self.nodes[:start_index+1] + merged + self.nodes[end_index:]
        self.check_merge()
        
    def check_merge(self):
        '''
        checks if merge was completed correctly
        '''
        node = self.nodes[-1]
        seen = []
        while node.dependency != None:
            if node in seen:
                raise exceptions.CyclicalDepdencyConflict(
                    (
                        "merge caused a cyclical depdency with '%s'=>'%s' . "
                        "This is likely caused by the linking operation you provided being before "
                        "the initial branch operation that is being merged"
                    ) % (node.operation_name, node.dependency.operation_name))
            seen.append(node)
            node = node.dependency
        if not isinstance(node, _InitialOperation):
            raise exceptions.MergeConflict(
                "merge did not lead back to initial operation")
        elif len(seen) != len(self.nodes) - 1:
            raise exceptions.MergeConflict(
                "missing nodes detected in merge")    
        
        
class Operation:
    '''
    represents a change to the option blocks
    '''
    operation_type:str
    
    def __init__(self) -> None:
        self.connections: Dict[str, Operation] = {}
        self.operation_name: str = None
        self.branch_id = None
        self.dependency: Operation = None
        
    def __str__(self) -> str:
        return "%s(desc='%s',conn=%i,brn='%s',dep='%s')" % (
            self.operation_type.upper(), 
            self.operation_name, 
            len(self.connections),
            self.branch_id,
            self.dependency.operation_name if self.dependency else 'N/A'
            )

    def __repr__(self) -> str:
        return self.__str__()

    def forwards(self, blocks: OptionBlocks) -> OptionBlocks:
        '''
        represents a change to the option blocks
        '''
        return blocks

    def backwards(self, blocks: OptionBlocks) -> OptionBlocks:
        '''
        undo a change to the option block. Essentially, the reverse operation.
        '''
        return blocks
    
    def add_connection(self, operation: Operation, branch):
        operation.dependency = self
        self.connections[branch] = operation
    
    @property
    def description(self):
        return "initial"
        
    def get_branch(self, name:str) -> Iterable[Operation]:
        '''
        get operations of a specific branch connected to this operation
        '''
        operation = self.connections.get(name)
        if operation is None:
            return []
        return [operation] + operation.get_branch(name)            
        
    def merge(self, name:str, new_branch:str):
        '''
        set all operations with the given branch 'name' to a 'new_branch'.
        '''
        operation = self.connections.get(name)
        if operation is None:
            return []
        operation.branch_id = new_branch
        self.connections.pop(name)
        self.connections[new_branch] = operation
        return [operation] + operation.merge(name, new_branch)            

    
class _InitialOperation(Operation):
    
    operation_type = "initial"
    
    @property
    def description(self):
        return "initial"
    
# OPERATIONS
    
class AddOperation(Operation):
    
    operation_type = "add"
    
    def __init__(self, subject, block) -> None:
        super().__init__()
        self.subject = subject
        self.block = block
    
    @property
    def description(self):
        return "add_%s_to_block_%i" % (self.subject, self.block)
    
    def forwards(self, blocks: OptionBlocks) -> OptionBlocks:
        blocks.add_class(self.block, self.subject)
        return blocks
    
    def backwards(self, blocks: OptionBlocks) -> OptionBlocks:
        blocks.remove_class(self.block, self.subject)
        return blocks

class RemoveOperation(Operation):
    
    operation_type = "remove"
    
    def __init__(self, subject, block) -> None:
        super().__init__()
        self.subject = subject
        self.block = block
    
    @property
    def description(self):
        return "remove_%s_from_block_%i" % (self.subject, self.block)
    
    def forwards(self, blocks: OptionBlocks) -> OptionBlocks:
        blocks.remove_class(self.block, self.subject)
        return blocks
    
    def backwards(self, blocks: OptionBlocks) -> OptionBlocks:
        blocks.add_class(self.block, self.subject)
        return blocks
    
class MoveOperation(Operation):
    
    operation_type = "move"
    
    def __init__(self, target:int, to:int, subject:str) -> None:
        super().__init__()
        self.target = target
        self.to = to
        self.subject = subject
    
    @property
    def description(self):
        return "move_%s_from_block_%i_to_block_%i" % (self.subject, self.target, self.to)
    
    def forwards(self, blocks: OptionBlocks) -> OptionBlocks:
        blocks.move_class(self.target, self.to, self.subject)
        return blocks
    
    def backwards(self, blocks: OptionBlocks) -> OptionBlocks:
        blocks.move_class(self.to, self.target, self.subject)
        return blocks
    
class EmptyOperation(Operation):
    
    operation_type = "empty"
    
    def __init__(self) -> None:
        super().__init__()
        
    @property
    def description(self):
        return "empty_operation"
    
    
    
class BranchManager:
    '''add operations without having to specify the branch'''
    def __init__(self, branch_id:str, graph: OperationGraph) -> None:
        self.branch_id = branch_id
        self.operations = []
        self.graph = graph
        
    def __enter__(self):
        return self 
    
    def __exit__(self, *args, **kwargs):
        pass
    
    def add_operation(self, operation: Operation, target:str=None, name:str=None):
        '''proxy to OperationGraph.add_operation()'''
        return self.graph.add_operation(operation, target, name, branch=self.branch_id)
        
    
class OperationGraph:
    '''
    data structure to hold all operations
    '''
    ADD = AddOperation
    REMOVE = RemoveOperation
    MOVE = MoveOperation
    EMPTY = EmptyOperation
    
    branch_manager = BranchManager
    
    def __init__(self) -> None:
        self.operation_count = 0
        self.operations: Dict[str, Operation] = {}
        self._branches: Dict[str, Operation] = {}
        self._recent_branches: Dict[str, Operation] = {}
        
        self._initial = _InitialOperation()
        # register the initial operation as the main branch
        self.register_branch(MAIN_BRANCH_NAME, self._initial)
        self.register_operation(self._initial, branch=MAIN_BRANCH_NAME)
        
    def __getitem__(self, key) -> Operation:
        return self.operations[key]            
        
    
    def register_operation(self, operation: Operation, name=None, branch=None):
        '''
        add operation to the graph.
        '''
        if operation.operation_name is None:
            name = self.create_operation_name(operation)
        self.operations[name] = operation
        operation.operation_id = self.operation_count
        operation.operation_name = name
        operation.branch_id = branch
        self.operation_count += 1
        self._recent_branches[branch] = operation
        return operation
        
    def add_operation(self, operation: Operation, target:str=None, name:str=None, branch:str=None):
        '''
        add an operation to the graph. Providing a 'target' will automatically add the given operation to
        the target's connections. 'Name' specifies the operation's name. 'Branch' defines which branch to add the given
        operation. By default uses the alias for the main branch.
        '''
        branch = branch or MAIN_BRANCH_NAME
        if target is None:
            target_operation = self._recent_branches.get(branch)
        elif target not in self.operations:
            raise exceptions.OperationNotFound("operation to target '%s' was not found" % target)
        if target_operation is None:
            raise exceptions.BranchNotFound("invalid branch '%s' provided" % branch)
        operation = self.register_operation(operation, name, branch)
        self._recent_branches[branch] = operation
        self.operations[operation.operation_name] = operation
        self.operations[target_operation.operation_name].add_connection(operation, branch)
        return operation.operation_name
        
    def register_branch(self, branch_name:str, starting_node: str|Operation):
        '''
        Creates a branch. A branch is a set of operations that stems away from the main branch.
        Starting node can be specified as a string.
        '''
        if isinstance(starting_node, str):
            starting_node = self.get_operation(starting_node)
        self._branches[branch_name] = starting_node
        self._recent_branches[branch_name] = starting_node
        return self.branch_manager(branch_name, self)
    
    def merge(self, branch:str|BranchManager, linking:str):
        '''
        merge a given branch to a main node on the main branch
        '''
        if isinstance(branch, BranchManager):
            branch = branch.branch_id
            
        target = self.get_operation(linking)
        if target.branch_id != MAIN_BRANCH_NAME:
            raise exceptions.MergeConflict(
                "cannot merge as linking node '%s' is not on the main branch '%s'" % (linking, MAIN_BRANCH_NAME)
            )
        main = self.get_branch(MAIN_BRANCH_NAME)
        to_merge = self.get_branch(branch)
        main.merge(to_merge, target)       
        return main
                
    def get_operation(self, name:str):
        op = self.operations.get(name)
        if op is None:
            raise exceptions.OperationNotFound(
                "operation with id '%s' was not found" % name
            )
        return op
    
    def create_operation_name(self, operation: Operation):
        # id_description
        return "%s_%s" % (str(self.operation_count).zfill(4), operation.description)
    
    def pprint_operations(self):
        for operation in self.operations.values():
            print(operation)
            
    def get_branch(self, name:str=MAIN_BRANCH_NAME):
        '''
        return a Branch object which contains a set of operations
        '''
        start = self._branches.get(name)
        if start is None:
            raise exceptions.BranchNotFound("invalid branch '%s' provided" % name)
        
        branch = LinearBranch([start] + start.get_branch(name))
        branch.branch_id = name
        return branch
    
