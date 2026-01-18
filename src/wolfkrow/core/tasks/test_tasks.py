from __future__ import print_function
from wolfkrow.core.tasks import task, sequence_task
from wolfkrow.core.engine import task_graph

from . import task_exceptions
from ..connections.connection import ConnectionTypes, ConnectionDirection, Connection

class TestTask_Successful(task.Task):
    def __init__(self, **kwargs):
        super(TestTask_Successful, self).__init__(**kwargs)

    def validate(self):
        return True

    def setup(self):
        return True

    def run(self):
        return 0


class TestTask_Failed_Validate(task.Task):
    def __init__(self, **kwargs):
        super(TestTask_Failed_Validate, self).__init__(**kwargs)

    def validate(self):
        raise task_exceptions.TaskValidationException("Task is rigged to fail")

    def setup(self):
        return True

    def run(self):
        return 0


class TestTask_Failed_Run(task.Task):
    def __init__(self, **kwargs):
        super(TestTask_Failed_Run, self).__init__(**kwargs)

    def validate(self):
        return True

    def setup(self):
        return True

    def run(self):
        #logging.info("'%s' was unsuccessfully run because it is rigged to fail" % self.name)
        raise task_graph.TaskGraphException("Rigged to fail")


class TestSequence(sequence_task.SequenceTask):
    def validate(self):
        return True

    def setup(self):
        pass
    
    def run(self, frame):
        print(frame)
        return 0
    
class TestTask_MultiOutput(task.Task):
    output_file = task.TaskAttribute(
        default_value="", 
        configurable=True, 
        attribute_type=str, 
        connection_flags=ConnectionTypes.FILE_SEQUENCE | ConnectionTypes.FILE, 
        connection_direction=ConnectionDirection.OUTPUT,
    )
    
    start_frame = task.TaskAttribute(
        default_value="", 
        configurable=True, 
        attribute_type=str, 
        connection_flags=ConnectionTypes.START_FRAME,
        connection_direction=ConnectionDirection.OUTPUT | ConnectionDirection.INPUT,
    )
    
    end_frame = task.TaskAttribute(
        default_value="", 
        configurable=True, 
        attribute_type=str, 
        connection_flags=ConnectionTypes.END_FRAME,
        connection_direction=ConnectionDirection.OUTPUT | ConnectionDirection.INPUT,
    )    
    
    def setup(self):
        pass
    
    def run(self):
        print("Output File: " + str(self.output_file))
        print("Start Frame: " + str(self.start_frame))
        print("End Frame: " + str(self.end_frame))
        return 0
class TestTask_MultiInput(task.Task):
    input_file = task.TaskAttribute(
        default_value="", 
        configurable=True, 
        attribute_type=str, 
        connection_flags=ConnectionTypes.FILE_SEQUENCE | ConnectionTypes.FILE, 
        connection_direction=ConnectionDirection.INPUT,
    )
    
    start_frame = task.TaskAttribute(
        default_value="", 
        configurable=True, 
        attribute_type=str, 
        connection_flags=ConnectionTypes.START_FRAME,
        connection_direction=ConnectionDirection.OUTPUT | ConnectionDirection.INPUT,
    )
    
    end_frame = task.TaskAttribute(
        default_value="", 
        configurable=True, 
        attribute_type=str, 
        connection_flags=ConnectionTypes.END_FRAME,
        connection_direction=ConnectionDirection.OUTPUT | ConnectionDirection.INPUT,
    )
    
    def setup(self):
        pass
    
    def run(self):
        print("Input File: " + str(self.input_file))
        print("Start Frame: " + str(self.start_frame))
        print("End Frame: " + str(self.end_frame))
        return 0