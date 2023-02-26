import logging
import traceback
import os
import shutil

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks import task, sequence_task, task_exceptions
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.test_tasks import *
from wolfkrow.core.tasks.nuke_render import NukeRender


# Clean up the temp dir if it exists.
if os.path.exists("./test_temp"):
    shutil.rmtree("./test_temp")

os.makedirs("./test_temp")

#TODO: Turn these into real unit tests.
def test_BashScript_export():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_BashScript_export'")
    logging.info("===========================================")
    job = task_graph.TaskGraph("test_BashScript_export")
    t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test")

    job.add_task(t1)

    # # ======================================================
    # # ==================== ENABLE PTVSD ====================
    # # ======================================================
    # import ptvsd
    # ptvsd.enable_attach()
    # print("Waiting for attach...")
    # ptvsd.wait_for_attach()
    # # ptvsd.break_into_debugger()
    # # ======================================================
    # # ======================================================
    # # ======================================================
    try: 
        job.execute_local(export_type="BashScript")
        error = False
    except Exception:
        traceback.print_exc()
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_BashScript_export' SUCCESSFUL")
        else:
            logging.info("TEST 'test_BashScript_export' FAILED")
    logging.info("===========================================\n\n")



#TODO: Turn these into real unit tests.
def test_BashScript_export_subtasks():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_BashScript_export_subtasks'")
    logging.info("===========================================")
    job = task_graph.TaskGraph("test_BashScript_export")
    t1 = NukeRender(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={}, command_line_executable="test", temp_dir="./test_temp")

    # # ======================================================
    # # ==================== ENABLE PTVSD ====================
    # # ======================================================
    # import ptvsd
    # ptvsd.enable_attach()
    # print("Waiting for attach...")
    # ptvsd.wait_for_attach()
    # # ptvsd.break_into_debugger()
    # # ======================================================
    # # ======================================================
    # # ======================================================
    error = False
    try: 
        exported = t1.export(export_type="BashScript")
        print(exported)
    except Exception:
        traceback.print_exc()
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_BashScript_export_subtasks' SUCCESSFUL")
        else:
            logging.info("TEST 'test_BashScript_export_subtasks' FAILED")
    logging.info("===========================================\n\n")

test_BashScript_export()
test_BashScript_export_subtasks()