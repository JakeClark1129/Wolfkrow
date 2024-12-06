#!/usr/bin/env python
"""
Module providing the main way to run Wolfkrow jobs from the command line.
"""
from builtins import zip
from builtins import range
import argparse
import json
import sys
import os

from wolfkrow.core.tasks import all_tasks


class WolfkrowRunTaskException(Exception):
    """
    Exception for run task errors.
    """

    pass


def _print_and_raise(message):
    """
    Prints the given message and raises it as an exception.

    Args:
        message (str): The message to print + raise as an exception.
    """
    print("[ERROR] %s" % message)
    raise WolfkrowRunTaskException(message)


def parse_args():
    """
    Parses the args passed into run_task.

    Requires a "--task_name" argument to specify the name of the task to run.

    For preference, receives a "--json_args_file" argument specifying the path
    to a JSON file containing the arguments for the task.

    Alternatively supports receiving the task arguments as an arbitrary number
    of arguments in the form "--key value".

    In either case, these arguments are passed into a an instance of a Task
    object of the type specified by "--task_name".

    Returns:
        args, task_args: Namespace containing the expected arguments, and a
            dictionary of any other arguments.
    """
    parser = argparse.ArgumentParser(prog="wolfkrow_run_task")
    parser.add_argument("--task_name", help="Class name of the task to run.")

    parser.add_argument(
        "--json_args_file",
        help="JSON file containing all the args.",
        required=False
    )

    known, unknown = parser.parse_known_args()


    task_args = {}

    # Load args from a JSON file
    args_file_path = known.json_args_file
    if args_file_path is not None:
        print("Loading args from JSON file:")
        print(args_file_path)

        if not os.path.isfile(args_file_path):
            message = "No such JSON file: %s" % args_file_path
            _print_and_raise(message)

        try:
            with open(args_file_path) as json_file:
                task_args = json.load(json_file)

        except Exception as exception:
            message = (
                "Couldn't load JSON file: %s - %s"
                % (args_file_path, exception)
            )
            _print_and_raise(message)

        if not isinstance(task_args, dict):
            message = (
                "JSON data read from %s is not a dictionary" % args_file_path
            )
            _print_and_raise(message)

    # Overlay any extra args passed in like this:
    #
    #   "--key1 value1 --key2 value2 etc..."
    for index in range(len(unknown)):
        if index % 2 == 0 and index < len(unknown) - 1:
            key = unknown[index].lstrip("-")
            value = unknown[index + 1]
            task_args[key] = value

    return known, task_args


def main():
    """
    Main entry point for the script.

    Parses arguments, creates a Task instance + executes it.
    """
    args, task_args = parse_args()
    task_class = all_tasks.get(args.task_name)

    # Cannot continue if we do know know what task we are meant to be executing.
    if task_class is None:
        sys.exit(1)

    # Use the args passed in to construct a Task Object
    task = task_class.from_dict(task_args)

    # Execute the Task Object.
    result = task()

    return result


if __name__ == '__main__':
    ret = main()
    sys.exit(ret)
