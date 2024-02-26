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

        job.execute_local(export_type="BashScript")

    def test_BashScript_export_already_exists(self):
        """ Test that the bash script creation logic correctly handles cases where 
        a script already exists by ensuring that the script path generated is unique.
        """
        temp_dir = self.get_test_temp_dir()
        
        t1 = TestSequence(name="TestExportExists", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test")
        
        exported_a = t1.export(temp_dir=temp_dir, export_type="BashScript")
        exported_b = t1.export(temp_dir=temp_dir, export_type="BashScript")

        # Add the 4 exported paths to a set so that duplicates are not added.
        # NOTE: These paths include a time-stamp down to the second. It's possible
        #   that the generation logic for the path's run at a different second, 
        #   giving us a false negative. Though this is incredibly rare given how
        #   quickly this code runs.
        script_paths = set([])
        script_paths.add(exported_a[0][1])
        script_paths.add(exported_a[1][1])
        script_paths.add(exported_b[0][1])
        script_paths.add(exported_b[1][1])

        # Now ensure that 4 different scripts were added to the set.
        self.assertTrue(len(script_paths) == 4)

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
