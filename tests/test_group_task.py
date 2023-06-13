from builtins import str
import logging
import os
import unittest

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks.test_tasks import *
from wolfkrow import Loader

from .wolfkrow_testcase import WolfkrowTestCase

class TestGroupTask(WolfkrowTestCase):

    def test_GroupTask_export_command_line(self):
        """ Tests that the group task is exported correctly.
        """

        config_path = self.get_test_config_file("test_group_task.wolfkrow.yaml")
        loader = Loader(
            config_file_paths=[config_path]
        )
        task_graph = loader.parse_workflow("Group_Test")

        exported_tasks = task_graph.export_tasks("CommandLine")

        with open(exported_tasks["Group_Test"]["executable_args"][0], 'r') as fh:
            contents = fh.read()
        
        # TODO: assert that the contents equals what we expected it to. 
        # logging.info("Group Task file contents:")
        # logging.info(contents)

    def test_GroupTask_export_python_script(self):

        
        # TODO: We need a better way of setting this in the settings.
        os.environ["WOLFKROW_DEFAULT_PYTHON_SCRIPT_EXECUTABLE"] = "python"

        config_path = self.get_test_config_file("test_group_task.wolfkrow.yaml")
        loader = Loader(
            config_file_paths=[config_path]
        )
        task_graph = loader.parse_workflow("Group_Test")

        exported_tasks = task_graph.export_tasks("PythonScript")

        logging.info("Exported Tasks: " + str(exported_tasks))

        with open(exported_tasks["Group_Test"]["script"], 'r') as fh:
            contents = fh.read()

        # TODO: assert that the contents equals what we expected it to.
        # logging.info("Group Task file contents:")
        # logging.info(contents)

if __name__ == "__main__":
    unittest.main()
