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

if __name__ == "__main__":
    unittest.main()
