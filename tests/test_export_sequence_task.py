import logging
import traceback
import math
import os
import shutil

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks import task, sequence_task, task_exceptions
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.test_tasks import *


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

# Clean up the temp dir if it exists.
if os.path.exists("./test_temp"):
    shutil.rmtree("./test_temp")

os.makedirs("./test_temp")

#TODO: Turn these into real unit tests.
def test_taskSequenceExecuteSuccess_command_line_normal():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_taskSequenceExecuteSuccess_command_line_normal'")
    logging.info("===========================================")

    t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test")

    error = False
    try: 
        exported = t1.export_to_command_line()

        # Count the amount of tasks there should be
        expected_export_count = int(math.ceil(float(t1.end_frame - t1.start_frame) / t1.chunk_size))
        if len(exported) != expected_export_count:
            error = True
            print("Received an unexpected amount of tasks exported: received: {}, expected: {}".format(
                len(exported),
                expected_export_count,
            ))
    except Exception:
        traceback.print_exc()
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_taskSequenceExecuteSuccess_command_line_normal' SUCCESSFUL")
        else:
            logging.info("TEST 'test_taskSequenceExecuteSuccess_command_line_normal' FAILED")
    logging.info("===========================================\n\n")

#TODO: Turn these into real unit tests.
def test_taskSequenceExecuteSuccess_command_line_deadline():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_taskSequenceExecuteSuccess_command_line_deadline'")
    logging.info("===========================================")

    t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test")

    error = False
    try: 
        exported = t1.export_to_command_line(deadline=True)

        # Count the amount of tasks there should be
        expected_export_count = 1
        if len(exported) != expected_export_count:
            error = True
            print("Received an unexpected amount of tasks exported: received: {}, expected: {}".format(
                len(exported),
                expected_export_count,
            ))
    except Exception:
        traceback.print_exc()
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_taskSequenceExecuteSuccess_command_line_deadline' SUCCESSFUL")
        else:
            logging.info("TEST 'test_taskSequenceExecuteSuccess_command_line_deadline' FAILED")
    logging.info("===========================================\n\n")

#TODO: Turn these into real unit tests.
def test_taskSequenceExecuteSuccess_bash_script_deadline():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_taskSequenceExecuteSuccess_command_line_deadline'")
    logging.info("===========================================")

    t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test",
        temp_dir="./test_temp")

    error = False
    try: 
        exported = t1.export(export_type="BashScript", deadline=True)

        # Count the amount of tasks there should be
        expected_export_count = 1
        if len(exported) != expected_export_count:
            error = True
            print("Received an unexpected amount of tasks exported: received: {}, expected: {}".format(
                len(exported),
                expected_export_count,
            ))

        if not exported[0][1].endswith("<STARTFRAME> <ENDFRAME>"):
            error = True
            print("Misformed bash script command for deadline. No frame range args passed in (Expected <STARTFRAME> <ENDFRAME>): {}".format(
                exported[0][1],
            ))
    except Exception:
        traceback.print_exc()
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_taskSequenceExecuteSuccess_command_line_deadline' SUCCESSFUL")
        else:
            logging.info("TEST 'test_taskSequenceExecuteSuccess_command_line_deadline' FAILED")
    logging.info("===========================================\n\n")

#TODO: Turn these into real unit tests.
def test_taskSequenceExecuteSuccess_python_script():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_taskSequenceExecuteSuccess_python_script'")
    logging.info("===========================================")

    t1 = TestSequence(
        name="Task1", 
        start_frame=10, 
        end_frame=25, 
        dependencies=[], 
        replacements={}, 
        python_script_executable="python",
        temp_dir="./test_temp"
    )

    error = False
    try: 
        exported = t1.export_to_python_script("test_export")

        # Count the amount of tasks there should be
        expected_export_count = int(math.ceil(float(t1.end_frame - t1.start_frame) / t1.chunk_size))
        if len(exported) != expected_export_count:
            error = True
            print("Received an unexpected amount of tasks exported: received: {}, expected: {}".format(
                len(exported),
                expected_export_count,
            ))
    except Exception:
        traceback.print_exc()
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_taskSequenceExecuteSuccess_python_script' SUCCESSFUL")
        else:
            logging.info("TEST 'test_taskSequenceExecuteSuccess_python_script' FAILED")
    logging.info("===========================================\n\n")



test_taskSequenceExecuteSuccess_command_line_normal()
test_taskSequenceExecuteSuccess_command_line_deadline()
test_taskSequenceExecuteSuccess_bash_script_deadline()
test_taskSequenceExecuteSuccess_python_script()