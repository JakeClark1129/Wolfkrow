

class ConnectionTypes:
    FILE = 1
    FILE_SEQUENCE = 1 << 1
    START_FRAME = 1 << 2
    END_FRAME = 1 << 3
    NUKE_SCRIPT = 1 << 4

class ConnectionDirection:
    INPUT = 1
    OUTPUT = 1 << 1


class Connection:
    """ A Class representing a connection between two Tasks. 
    
    Every connection must either be a Input, or an Output, and the connection 
    must be between compatible types.
    """
    
    def __init__(self, name, connection_tags, direction):
        self.name = name
        self.connection_tags = connection_tags
        self.direction = direction

    def is_compatible(self, other_connection):
        """ Check if this connection is compatible with another connection. 
        
        Two connections are compatible if they share at least one connection tag.
        """
        return bool(self.connection_tags & other_connection.connection_tags)

class Input(Connection):
    """ A Class representing an Input connection for a Task. """
    
    def __init__(self, name, connection_tags):
        super().__init__(name, connection_tags, direction="input")

class Output(Connection):
    """ A Class representing an Output connection for a Task. """
    
    def __init__(self, name, connection_tags):
        super().__init__(name, connection_tags, direction="output")