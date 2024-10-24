import logging
import traceback
import math
import os
import shutil
import stat

import unittest

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks import task, sequence_task, task_exceptions
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.test_tasks import *

from .wolfkrow_testcase import WolfkrowTestCase

class TestSequenceTask(WolfkrowTestCase):

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

    def test_taskSequenceExecuteSuccess_command_line_normal(self):
        """ Tests that the SequenceTask is able to export its tasks to a shell 
        command correctly without deadline enabled.
        """
        # logging.info("===========================================")
        # logging.info("RUNNING TEST 'test_taskSequenceExecuteSuccess_command_line_normal'")
        # logging.info("===========================================")

        t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test")

        exported = t1.export_to_command_line("Test")

        # Count the amount of tasks there should be
        expected_export_count = int(math.ceil(float(t1.end_frame - t1.start_frame) / t1.chunk_size))
        if len(exported) != expected_export_count:
            error = True
            print("Received an unexpected amount of tasks exported: received: {}, expected: {}".format(
                len(exported),
                expected_export_count,
            ))

    def test_taskSequenceExecuteSuccess_command_line_deadline(self):
        """ Tests that the SequenceTask is able to export its tasks to a shell 
        command correctly with deadline enabled.
        """
        t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test")

        error = False
        exported = t1.export_to_command_line(deadline=True)

        # Count the amount of tasks there should be
        expected_export_count = 1
        if len(exported) != expected_export_count:
            error = True

    def test_taskSequenceExecuteSuccess_bash_script_deadline(self):
        """ Tests that the SequenceTask is able to export its tasks to a bash 
        script correctly with deadline enabled.
        """
        t1 = TestSequence(
            name="Task1", 
            start_frame=10, 
            end_frame=25, 
            dependencies=[], 
            replacements={}, 
            command_line_executable="test",
            temp_dir="./test_temp"
        )

        exported = t1.export(export_type="BashScript", deadline=True)

        # Count the amount of tasks there should be
        expected_export_count = 1
        if len(exported) != expected_export_count:
            print("Received an unexpected amount of tasks exported: received: {}, expected: {}".format(
                len(exported),
                expected_export_count,
            ))

        if not exported[0][1].endswith("<STARTFRAME> <ENDFRAME>"):
            print("Misformed bash script command for deadline. No frame range args passed in (Expected <STARTFRAME> <ENDFRAME>): {}".format(
                exported[0][1],
            ))

    def test_taskSequenceExportSuccess_python_script(self):
        """ Tests that the SequenceTask is able to export its tasks to a python script correctly.
        """
        t1 = TestSequence(
            name="Task1", 
            start_frame=10, 
            end_frame=25, 
            dependencies=[], 
            replacements={}, 
            python_script_executable="python",
            temp_dir="./test_temp"
        )

        exported = t1.export_to_python_script("test_export")

        expected_export_count = int(math.ceil(float(t1.end_frame - t1.start_frame) / t1.chunk_size))
        # Count the amount of tasks there should be
        if len(exported) != expected_export_count:
            error = True
            print("Received an unexpected amount of tasks exported: received: {}, expected: {}".format(
                len(exported),
                expected_export_count,
            ))

if __name__ == "__main__":
    unittest.main()
