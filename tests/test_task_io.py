from builtins import str
import logging
import os
import unittest

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks.test_tasks import *
from wolfkrow.config.config import WolfkrowConfig

from .wolfkrow_testcase import WolfkrowTestCase

import sys
# # =================================================
# # ==================== debugpy ====================
# # =================================================
# sys.path.append("C:\\Users\\jacob.clark\\AppData\\Roaming\\Python\\Python39\\site-packages")
# sys.path.append("C:\\Users\\jacob.clark\\AppData\\Roaming\\Python\\Python39\\_site-packages")
# sys.path.append("X:\\__pipeline\\software\\__packages\\territory\\debugpy\\1.8.1\\e7b64aebe77c11047a71e73bebf05e90cbb6361d\\python")
# sys.path.append("/Volumes/projects-a/__pipeline/software/__packages/territory/debugpy/1.8.1/e7b64aebe77c11047a71e73bebf05e90cbb6361d/python")
# import debugpy
# debugpy.configure() 
# debugpy.listen(("localhost", 5678))

# print("Waiting for debugger attach")
# debugpy.wait_for_client()
# debugpy.breakpoint()
# # =================================================
# # =================================================
# # =================================================

class TestTaskIO(WolfkrowTestCase):

    def test_TaskIO(self):
        """ Tests that the group task is exported correctly.
        """

        config_path = self.get_test_config_file("test_task_io.yaml")
        config = WolfkrowConfig(
            path=config_path
        )

        task_graph = config.parse_workflow("task_io")

        results = task_graph.execute_local()

if __name__ == "__main__":
    unittest.main()
