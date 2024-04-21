from __future__ import print_function
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
from wolfkrow.builder import workflow_builder
from wolfkrow.core.tasks import task
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.file_copy import FileCopy
from wolfkrow.core.tasks import task_exceptions
from wolfkrow.core.tasks.test_tasks import *

#TODO: Turn these into real unit tests.


from .wolfkrow_testcase import WolfkrowTestCase


# TODO: These tests rely on deadline API. We should try and get API stubs in place
# so we don't need to actually submit jobs to the farm.
class TestTaskGraph(WolfkrowTestCase):

    def test_taskGraphExecuteSuccess(self):
        logging.info("===========================================")
        logging.info("RUNNING TEST 'test_taskGraphExecuteSuccess'")
        logging.info("===========================================")

        loader = self.get_default_test_loader()

        job = loader.parse_workflow("test_taskGraphExecuteSuccess")

        job.execute_local()

    def test_taskGraphExecuteFailed_validation(self):
        logging.info("=====================================================")
        logging.info("RUNNING TEST 'test_taskGraphExecuteFailed_validation'")
        logging.info("=====================================================")
        job = task_graph.TaskGraph("taskGraphExecuteFailed_validation")
        t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
        t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
        t3 = TestTask_Failed_Validate(name="Task3", dependencies=["Task2", "Task1"], replacements={})
        t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
        t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})

        job.add_task(t1)
        job.add_task(t2)
        job.add_task(t3)
        job.add_task(t4)
        job.add_task(t5)

        try:
            job.execute_local()
            error = False
        except Exception:
            error = True
        finally:
            self.assertTrue(error)

    def test_taskGraphExecuteFailed_run(self):
        job = task_graph.TaskGraph("taskGraphExecuteFailed_run")
        t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
        t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
        t3 = TestTask_Failed_Run(name="Task3", dependencies=["Task2", "Task1"], replacements={})
        t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
        t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})

        job.add_task(t1)
        job.add_task(t2)
        job.add_task(t3)
        job.add_task(t4)
        job.add_task(t5)

        job.execute_local()

