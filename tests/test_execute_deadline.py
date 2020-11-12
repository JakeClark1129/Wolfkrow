import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
from wolfkrow.core.tasks import task
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.file_copy import FileCopy
from wolfkrow.core.tasks import task_exceptions
from wolfkrow.core.tasks.test_tasks import *

#TODO: Turn these into real unit tests.
def test_taskGraphExecuteSuccess():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_taskGraphExecuteSuccess'")
    logging.info("===========================================")
    job = task_graph.TaskGraph("taskGraphExecuteSuccess")
    t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
    t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
    t3 = TestTask_Successful(name="Task3", dependencies=["Task2", "Task1"], replacements={})
    t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
    t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})

    job.add_task(t1)
    job.add_task(t2)
    job.add_task(t3)
    job.add_task(t4)
    job.add_task(t5)
    
    try: 
        job.execute_deadline()
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