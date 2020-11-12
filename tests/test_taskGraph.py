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

def test_taskGraphExecuteFailed_validation():
    logging.info("=====================================================")
    logging.info("RUNNING TEST 'test_taskGraphExecuteFailed_validation'")
    logging.info("=====================================================")
    job = task_graph.TaskGraph("taskGraphExecuteFailed_validation")
    t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
    t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
    t3 = TestTask_Failed_Validate(name="Task3", dependencies=["Task2", "Task1"], replacements={})
    t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
    t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})

    job.add_task(t1)
    job.add_task(t2)
    job.add_task(t3)
    job.add_task(t4)
    job.add_task(t5)

    try: 
        job.execute_local()
        error = False
    except Exception:
        error = True
    finally:
        if error:
            logging.info("TEST 'test_taskGraphExecuteFailed_validation' SUCCESSFUL")
        else:
            logging.info("TEST 'test_taskGraphExecuteFailed_validation' FAILED")
        

    

def test_taskGraphExecuteFailed_run():
    logging.info("==============================================")
    logging.info("RUNNING TEST 'test_taskGraphExecuteFailed_run'")
    logging.info("==============================================")
    job = task_graph.TaskGraph("taskGraphExecuteFailed_run")
    t1 = TestTask_Successful(name="Task1", dependencies=[], replacements={})
    t2 = TestTask_Successful(name="Task2", dependencies=["Task1"], replacements={})
    t3 = TestTask_Failed_Run(name="Task3", dependencies=["Task2", "Task1"], replacements={})
    t4 = TestTask_Successful(name="Task4", dependencies=["Task3"], replacements={})
    t5 = TestTask_Successful(name="Task5", dependencies=[], replacements={})

    job.add_task(t1)
    job.add_task(t2)
    job.add_task(t3)
    job.add_task(t4)
    job.add_task(t5)

    try: 
        job.execute_local()
        error = False
    except Exception:
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_taskGraphExecuteFailed_run' SUCCESSFUL")
        else:
            logging.info("TEST 'test_taskGraphExecuteFailed_run' FAILED")



test_taskGraphExecuteSuccess()
test_taskGraphExecuteFailed_validation()
test_taskGraphExecuteFailed_run()

fc = FileCopy(name="Create BackUp", source="C:/Projects/Wolfkrow/src/wolfkrow/core/engine/task_graph.py", destination="C:/backups/")
fc()
print(fc)
fc.export("C:/backups/exports/", "testing")