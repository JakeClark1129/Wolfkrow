import logging
import os

import unittest

logging.basicConfig(level=logging.DEBUG)
from wolfkrow.core.tasks import task
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.file_copy import FileCopy
from wolfkrow.core.tasks import task_exceptions
from wolfkrow.core.tasks.test_tasks import *
from wolfkrow.core import utils

# TODO: These tests rely on deadline API. We should try and get API stubs in place
# so we don't need to actually submit jobs to the farm.
class TestExecuteDeadline(unittest.TestCase):
    def test_taskGraphExecuteSuccess(self):
        job = task_graph.TaskGraph("taskGraphExecuteSuccess")
        t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
        t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
        t3 = TestTask_Successful(name="Task3", dependencies=["Task2", "Task1"], replacements={})
        t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
        t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})
        job.add_task(t1)
        job.add_task(t2)
        job.add_task(t3)
        job.add_task(t4)
        job.add_task(t5)

        job.execute_deadline()

    def test_get_additional_job_attrs(self):
        settings_file = os.path.join(os.path.dirname(__file__), "test_settings.yaml")
        job = task_graph.TaskGraph(
            "taskGraphExecuteSuccess",
            settings_file=settings_file
        )
        # Set the environment variables required in the test_setting.yaml file.
        os.environ["SHOW"] = "foobar"
        os.environ["WORKSPACE"] = "Show"
        os.environ["WORKSPACE_PATH"] = "/shows/foobar"
        replacements = {
            "user": "test_user"
        }
        test_attrs = job._get_additional_job_attrs(replacements=replacements)

        sample_attrs = {
            "ExtraInfo0": "foobar",
            "ExtraInfo1": "Show",
            "ExtraInfo2": "/shows/foobar",
            "UserName": "test_user",
        }

        for attr_key, attr_value in list(sample_attrs.items()):
            self.assertIn(attr_key, test_attrs)

            self.assertEqual(attr_value, test_attrs[attr_key])

if __name__ == "__main__":
    unittest.main()

