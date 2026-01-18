from builtins import str
import logging
import os
import unittest

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks.test_tasks import *
from wolfkrow import Loader

from .wolfkrow_testcase import WolfkrowTestCase

import sys

class TestTaskIO(WolfkrowTestCase):

    def test_TaskIO(self):
        """ Tests that the group task is exported correctly.
        """

        config_path = self.get_test_config_file("test_task_io.yaml")
        loader = Loader(
            config_file_paths=[config_path]
        )

        task_graph = loader.parse_workflow("task_io")

        results = task_graph.execute_local()

if __name__ == "__main__":
    unittest.main()
