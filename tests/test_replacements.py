from __future__ import print_function
import unittest
import os

from wolfkrow.builder import workflow_builder

from .wolfkrow_testcase import WolfkrowTestCase

class TestReplacements(WolfkrowTestCase):
    def test_replacements(self):

        loader = self.get_default_test_loader()

        task_graph = loader.parse_workflow("test_replacements")
        test_task = task_graph._tasks['test_replacements_task']

        self.assertEqual(test_task.source, "bar")

        test_data_folder = self.get_test_data_file("resolver_test_dir/nested/test_resolver.txt")
        self.assertEqual(os.path.normpath(test_task.destination), os.path.normpath(test_data_folder))

if __name__ == "__main__":
    unittest.main()
