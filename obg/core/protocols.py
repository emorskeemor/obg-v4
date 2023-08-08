
class Protocol:
    
    name:str = None
    
    def __init__(self) -> None:
        self.description = self.__class__.__doc__
    
    def __new__(cls, *args, **kwargs):
        if cls.name is None:
            cls.name = cls.__name__
        return super().__new__(cls)
    
    def __str__(self) -> str:
        return "%s object" % self.__class__.name
        
    def is_using(self, protocol):
        if isinstance(self, protocol):
            return self
        return None
        
    def __and__(self, __o):
        if isinstance(__o, chain_protocols):
            return __o & self
        elif isinstance(__o, Protocol):
            return chain_protocols(self, __o)
        raise TypeError("can only add protocol objects")
    
    def __or__(self, __o):
        return self.__and__(__o)
    

class DefaultProtcol(Protocol):
    '''Default generation protocol'''
    name = "protocol_a"
    
class ImmediateEvaluation(Protocol):
    '''Evaluate on creation'''
    name = "protocol_b"
    def __init__(self, threshold:float=None) -> None:
        super().__init__()
        assert threshold <= 100, "threshold cannot have a large value than 100"
        self.threshold = threshold
        
class OrderingProtocol(Protocol):
    '''ordering options protocol'''
    name = "protocol_c"

class LimitProtocol(Protocol):
    '''stops generation after a certain amount of nodes have been created'''
    name = "protocol_d"
    def __init__(self, maximum:int) -> None:
        super().__init__()
        self.maximum = maximum
        
class OrderSetProtocol(Protocol):
    name = "protocol_e"
    


class chain_protocols:
    '''
    object which allows multiple protocols to be used
    '''
    def __init__(self, *protocols) -> None:
        self.protocols = list(protocols)
        for protocol in self.protocols:
            if not isinstance(protocol, Protocol):
                raise TypeError("invalid protocol '%s'" % protocol)
            setattr(self, protocol.name, protocol)
        
    def is_using(self, protocol: Protocol):
        for i in self.protocols:
            if isinstance(i, protocol):
                return i
        return None
    
    def __and__(self, __o):
        if isinstance(__o, chain_protocols):
            self.protocols.extend(__o.protocols)
            return self
        elif isinstance(__o, Protocol):
            self.protocols.append(__o)
            return self
        raise TypeError("can only add protocol objects")