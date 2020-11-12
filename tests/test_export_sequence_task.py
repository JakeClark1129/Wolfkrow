import logging
import traceback

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks import task, sequence_task, task_exceptions
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.test_tasks import *

#TODO: Turn these into real unit tests.
def test_taskGraphExecuteSuccess():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_taskGraphExecuteSuccess'")
    logging.info("===========================================")
    job = task_graph.TaskGraph("taskGraphExecuteSuccess")
    t1 = TestSequence(name="Task1", start_frame=10, end_frame=25, dependencies=[], replacements={})

    job.add_task(t1)

    try: 
        job.execute_local()
        error = False
    except Exception:
        traceback.print_exc()
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_taskGraphExecuteSuccess' SUCCESSFUL")
        else:
            logging.info("TEST 'test_taskGraphExecuteSuccess' FAILED")
    logging.info("===========================================\n\n")

test_taskGraphExecuteSuccess()