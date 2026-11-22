from __future__ import print_function
from wolfkrow.core.tasks import task, sequence_task
from wolfkrow.core.engine import task_graph
from . import task_exceptions
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

# ============================= #
# Test tasks for Task I/O tests #
# ============================= #
from wolfkrow.core.connections import IO, Types


class TestTask_Outputs(task.Task):
    """ Test task with outputs. `runtime_value` is only known after it has run. """
    destination = task.TaskAttribute(io=IO.OUTPUT, types=Types.FILE, attribute_type=str)
    start_frame = task.TaskAttribute(io=IO.OUTPUT, types=Types.START_FRAME, attribute_type=int)
    end_frame = task.TaskAttribute(io=IO.OUTPUT, types=Types.END_FRAME, attribute_type=int)
    runtime_value = task.TaskAttribute(io=IO.OUTPUT, types=Types.INT, attribute_type=int)
    runtime_value_result = task.TaskAttribute(attribute_type=int,
        description="The value assigned to runtime_value when this task runs.")

    def setup(self):
        pass

    def run(self):
        if self.runtime_value_result is not None:
            self.runtime_value = self.runtime_value_result
        return 0


class TestTask_Inputs(task.Task):
    """ Test task with inputs. Writes the values it received to `report_file`. """
    source = task.TaskAttribute(io=IO.INPUT, types=Types.FILE, attribute_type=str)
    start_frame = task.TaskAttribute(io=IO.INPUT, types=Types.START_FRAME, attribute_type=int)
    end_frame = task.TaskAttribute(io=IO.INPUT, types=Types.END_FRAME, attribute_type=int)
    runtime_value = task.TaskAttribute(io=IO.INPUT, types=Types.INT, attribute_type=int)
    report_file = task.TaskAttribute(attribute_type=str)

    def setup(self):
        pass

    def run(self):
        import json
        with open(self.report_file, "w") as handle:
            json.dump({
                "source": self.source,
                "start_frame": self.start_frame,
                "end_frame": self.end_frame,
                "runtime_value": self.runtime_value,
            }, handle)
        return 0
