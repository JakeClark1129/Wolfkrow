
name = "wolfkrow"

description = ""

version = "<version>"

requires = [
    "deadline",
    "misc",
    "networkx",
#    "six",
    "yaml"
]

variants = [["python-2.7"]]


def commands():
    import os

    root_path = expandvars("{root}")
    bin_path = os.path.join(root_path, "bin")
    python_path = os.path.join(root_path, "python")

    env.PATH.append(bin_path)
    env.PYTHONPATH.append(python_path)

    env.WOLFKROW_CONFIG_SEARCH_PATHS = os.path.join(python_path, "wolfkrow", "builder", "config_file.yaml")
    env.WOLFKROW_DEFAULT_PYTHON_SCRIPT_EXECUTABLE = "wolfkrow"
    env.WOLFKROW_DEFAULT_COMMAND_LINE_EXECUTABLE = "wolfkrow_run_task"
    env.WOLFKROW_RUN_TASK_EXECUTABLE = os.path.join(bin_path, "wolfkrow_run_task.py")

