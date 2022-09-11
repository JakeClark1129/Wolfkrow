#!/usr/bin/env python

from builtins import zip
from builtins import range
import argparse
import sys

from wolfkrow.core.tasks import all_tasks

def parse_args():
    """ Parses the args passed into run_task.

        Expects --task_name to be provided, and then an arbitrary amount of follow 
        up arguments matching the form "--key value". Uses the additional arguments 
        to construct a dictionary which is later used to instantiate a Task Object.

        Returns:
            args, task_args: Namespace containing the expected arguments, then a 
                dictionary of all the additional arguments.
    """

    parser = argparse.ArgumentParser(prog='wolfkrow_run_task')
    parser.add_argument('--task_name', help="Class name of the task to run.")
    known, unknown = parser.parse_known_args()

    # Assumes args passed in like "--key1 value1 --key2 value2 etc..." 
    # Then strips the '--' from the keys to build a dictionary
    for index in range(len(unknown)):
        if index % 2 == 0:
            unknown[index] = unknown[index].lstrip('-')
    task_args = dict(list(zip(unknown[:-1:2],unknown[1::2])))
    return known, task_args

def main():
    args, task_args = parse_args()
    task_class = all_tasks.get(args.task_name)

    # Cannot continue if we do know know what task we are meant to be executing.
    if task_class is None:
        sys.exit(1)

    # Use the args passed in to construct a Task Object
    task = task_class.from_dict(task_args)
    
    # Execute the Task Object.
    ret = task()
    return ret

if __name__ == '__main__':
    ret = main()
    sys.exit(ret)
