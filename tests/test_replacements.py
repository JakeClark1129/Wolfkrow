from __future__ import print_function
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
from wolfkrow.core.tasks import task
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.file_copy import FileCopy
from wolfkrow.core.tasks import task_exceptions
from wolfkrow.core.tasks.test_tasks import *

from wolfkrow.builder import workflow_builder

#TODO: Turn these into real unit tests.
def test_replacements():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_replacements'")
    logging.info("===========================================")

    loader = workflow_builder.Loader(config_file_paths=["./test_config_file.yaml", "./config/test_config_file2.yaml"])
    task_graph = loader.parse_workflow("test_replacements")
    test_task = task_graph._tasks['test_replacements_task']

    if test_task.source == "bar":
        logging.info("TEST 'test_taskGraphExecuteSuccess' SUCCESSFUL")
    else:
        logging.info("TEST 'test_taskGraphExecuteSuccess' FAILED")
    logging.info("===========================================\n\n")

#test_replacements()