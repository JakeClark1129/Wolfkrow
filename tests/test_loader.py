from __future__ import print_function
import unittest

from wolfkrow.builder import workflow_builder

from .wolfkrow_testcase import WolfkrowTestCase

class TestScene(WolfkrowTestCase):
    def test_scene(self):
        scene = self.get_default_test_scene()

        config = scene.config

        #TODO
        self.assertTrue(config)

    def test_default_task_attributes(self):
        scene = self.get_default_test_scene()

        task_graph = scene.parse_workflow("test_nuke_render")
        self.assertTrue(task_graph._tasks['test_nuke_render'].command_line_executable_args == ["-t"])
        self.assertTrue(task_graph._tasks['test_nuke_render'].python_script_executable_args == ["-t"])

if __name__ == "__main__":
    unittest.main()
