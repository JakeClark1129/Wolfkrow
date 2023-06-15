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



class TestTaskExport(unittest.TestCase):

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


        # ======================================================
        # ==================== ENABLE PTVSD ====================
        # ======================================================
        import ptvsd
        ptvsd.enable_attach()
        print("Waiting for attach...")
        ptvsd.wait_for_attach()
        # ptvsd.break_into_debugger()
        # ======================================================
        # ======================================================
        # ======================================================
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

    def test_BashScript_export_subtasks(self):
        """ Tests the export method for a Task which contains subtasks.
        """
        t1 = NukeRender(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test", temp_dir="./test_temp")

        t1.export(export_type="BashScript")

if __name__ == "__main__":
    unittest.main()
