from __future__ import print_function
import unittest

from wolfkrow.builder import workflow_builder

from .wolfkrow_testcase import WolfkrowTestCase

class TestReplacements(WolfkrowTestCase):
    def test_replacements(self):

        loader = self.get_default_test_loader()

        task_graph = loader.parse_workflow("test_replacements")
        test_task = task_graph._tasks['test_replacements_task']

        self.assertEqual(test_task.source, "bar")

if __name__ == "__main__":
    unittest.main()
