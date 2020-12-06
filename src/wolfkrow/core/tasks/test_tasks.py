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