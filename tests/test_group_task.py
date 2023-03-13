from builtins import str
import logging
import os
import traceback

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks import task, sequence_task, task_exceptions
from wolfkrow.core.engine import task_graph
from wolfkrow.core.tasks.test_tasks import *
from wolfkrow import Loader

#TODO: Turn these into real unit tests.
def test_GroupTask_export_command_line():
    logging.info("=================================================")
    logging.info("RUNNING TEST 'test_GroupTask_export_command_line'")
    logging.info("=================================================")

    loader = Loader(
        config_file_paths=[r"C:\Projects\Wolfkrow\tests\test_group_task.wolfkrow.yaml"]
    )
    task_graph = loader.parse_workflow("Group_Test")

    exported_tasks = task_graph.export_tasks("CommandLine")

    logging.info("Exported Tasks: " + str(exported_tasks))

    with open(exported_tasks["Group_Test"]["executable_args"][0], 'r') as fh:
        contents = fh.read()
    
    logging.info("Group Task file contents:")
    logging.info(contents)

def test_GroupTask_export_python_script():
    logging.info("==================================================")
    logging.info("RUNNING TEST 'test_GroupTask_export_python_script'")
    logging.info("==================================================")

    # TODO: We need a better way of setting this in the settings.
    os.environ["WOLFKROW_DEFAULT_PYTHON_SCRIPT_EXECUTABLE"] = "python"

    loader = Loader(
        config_file_paths=[r"C:\Projects\Wolfkrow\tests\test_group_task.wolfkrow.yaml"]
    )
    task_graph = loader.parse_workflow("Group_Test")

    exported_tasks = task_graph.export_tasks("PythonScript")

    logging.info("Exported Tasks: " + str(exported_tasks))

    with open(exported_tasks["Group_Test"]["script"], 'r') as fh:
        contents = fh.read()

    logging.info("Group Task file contents:")
    logging.info(contents)

# test_GroupTask_export_command_line()
# test_GroupTask_export_python_script()