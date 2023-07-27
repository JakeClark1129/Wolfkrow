import logging
import traceback
import os
import shutil
import stat

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks import task, sequence_task, task_exceptions
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.test_tasks import *
from wolfkrow.core.tasks.nuke_render import NukeRender


import unittest

from .wolfkrow_testcase import WolfkrowTestCase

class TestTaskExport(WolfkrowTestCase):

    def setUp(self):
        if not os.path.exists("./test_temp"):
            os.makedirs("./test_temp")

    def tearDown(self):
        def on_rm_error( func, path, exc_info):
            # path contains the path of the file that couldn't be removed
            # let's just assume that it's read-only and unlink it.
            # NOTE: This code is only needed on Windows. Does this cause issues on Linux?
            os.chmod( path, stat.S_IWRITE )
            os.unlink( path )

        # Clean up the temp dir if it exists.
        if os.path.exists("./test_temp"):
            shutil.rmtree("./test_temp", onerror=on_rm_error)

    def test_BashScript_export(self):
        """ Tests the standard Task export and execute local method. This test is 
        meant to be a basic integration test to ensure that you are able to initialize
        a Task Object, add it to a task graph, and the execute the task graph.

        Tests BashScript export type.
        """
        job = task_graph.TaskGraph("test_BashScript_export")
        t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test")

        job.add_task(t1)

        word = "abcddeba"
        word_len = len(word) - 1
        for i in range(word_len):
            if word[i] == word[word_len - i]:
                a = i

        if a == i:
            print("Yay!")
        else:
            print("Nay")

        job.execute_local(export_type="BashScript")

    def test_BashScript_export_deadline(self):
        """ Tests the standard Task export and execute local method. This test is 
        meant to be a basic integration test to ensure that you are able to initialize
        a Task Object, add it to a task graph, and the execute the task graph.

        Tests BashScript export type.
        """

        temp_dir = self.get_test_temp_dir()

        job = task_graph.TaskGraph("test_BashScript_export")
        t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test", temp_dir=temp_dir)

        job.add_task(t1)

        exports = job.export_tasks(export_type="BashScript", deadline=True)

        script = exports["Task1"]["script"]
        script_name = os.path.basename(script)
        script_name = script_name[:-7] # Strip the last 7 characters. <QUOTE>

        test_script_path = os.path.join(temp_dir, script_name)
        test_script_path = "<QUOTE>{}<QUOTE>".format(test_script_path)

        self.assertTrue(test_script_path == script, "Deadline export script did not end as expected.")

    def test_BashScript_export_subtasks(self):
        """ Tests the export method for a Task which contains subtasks.
        """
        t1 = NukeRender(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test", temp_dir="./test_temp")

        t1.export(export_type="BashScript")

if __name__ == "__main__":
    unittest.main()
