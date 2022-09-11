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
def test_loader():
    logging.info("===========================================")
    logging.info("RUNNING TEST 'test_config_loading'")
    logging.info("===========================================")

    loader = workflow_builder.Loader(config_file_paths=["./test_config_file.yaml", "./config/test_config_file2.yaml"])
    config = loader.config

    #TODO
    if not config:
        logging.info("TEST 'test_config_loading' FAILED")
    else:
        logging.info("TEST 'test_config_loading' SUCCESSFUL")
    logging.info("===========================================\n\n")

def test_default_task_attributes():
    logging.info("======================================")
    logging.info("RUNNING TEST 'default_task_attributes'")
    logging.info("======================================")

    loader = workflow_builder.Loader(config_file_paths=["./test_config_file.yaml", "./config/test_config_file2.yaml"])

    task_graph = loader.parse_workflow("test_nuke_render")
    if task_graph._tasks['test_nuke_render'].executable_args == "-t":
        logging.info("TEST 'default_task_attributes' SUCCESSFUL")
    else: 
        logging.info("TEST 'default_task_attributes' FAILED")

test_loader()
test_default_task_attributes()