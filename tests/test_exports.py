import logging
import traceback

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks import task, sequence_task, task_exceptions
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.test_tasks import *

#TODO: Turn these into real unit tests.
def test_BashScript_export():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_BashScript_export'")
    logging.info("===========================================")
    job = task_graph.TaskGraph("test_BashScript_export")
    t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={})

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

test_BashScript_export()