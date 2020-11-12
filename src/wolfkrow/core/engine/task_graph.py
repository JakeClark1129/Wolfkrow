""" taskGraph Module for building a task graph and executing it as a job.

    Author: Jacob Clark
"""

import logging
import networkx
import subprocess
import tempfile

from wolfkrow.core import utils

logging.basicConfig(level=logging.WARNING)

class TaskGraphException(Exception):
    """ Exception for generic TaskGraph errors
    """
    pass

class TaskGraphValidationException(TaskGraphException):
    """ Exception for TaskGraph validation errors
    """
    pass


class TaskGraph(object):
    """ Provides an interface to build, and execute a series of tasks.
    """

    def __init__(self, name, replacements=None):
        """ Initializes TaskGraph object.

            Args: 
                name (str): The name of the task graph. This is purely cosmetic and has no impact on task graph execution.
            
            Kwargs:
                replacements (dict): A dictionary of string replacements used by tasks.
        """
        self._graph = networkx.DiGraph()
        self._settings = utils.settings
        self._tasks = {}
        self.name = name
        self.replacements = replacements or {}

    def add_task(self, task):
        """ Adds a task to the task dictionary, and to the graph network.

            Note: When adding a task to the task graph, we will also add all the tasks dependencies to the graph regardless of whether or not
            the Task Object exists.

            Args:
                task (Task): Task Object to add.

            Raises:
                TaskGraphException: Task Name in Graph is not Unique.
        """

        if self._tasks.get(task.name) is None:
            self._tasks[task.name] = task
        else:
            raise TaskGraphException("Task Name is not Unique: %s." % task.name)

        self._graph.add_node(task.name)

        # Edges are added such that when the task graph is built it goes from "depended on task => dependent task". This results in the most 
        # depended on tasks being at the top of the tree when sorting Topologically. which will result in the correct order of task execution
        edges = [(dependency, task.name) for dependency in task.dependencies]
        self._graph.add_edges_from(edges)

    def validate_task_graph(self):
        """ Validates the current Task graph.

            Raises:
                TaskGraphValidationException: Invalid Task Graph
        """

        if not networkx.is_directed_acyclic_graph(self._graph):
            raise TaskGraphValidationException("Task Graph contains circular dependencies.")

    def export_tasks(self):
        """ Exports each individual task to its standalone state for execution.
        """

        exported_tasks = {}

        tempdir = tempfile.mkdtemp()
        logging.info("TEMPDIR: " + tempdir)

        for task_name, task in self._tasks.items():

            # Export scripts for task.
            exported = task.export(tempdir, self.name)
            if not isinstance(exported, list):
                exported = [exported]

            for exported_task in exported:
                exported_tasks[exported_task[0].name] = {
                    "executable": task.executable,
                    "script": exported_task[1],
                    "obj": exported_task[0],
                }

        return exported_tasks

    def execute_local(self):

        exported_tasks = self.export_tasks()

        results = {}
        taskExecutionOrder = networkx.topological_sort(self._graph)
        for task_name in taskExecutionOrder:
            task = exported_tasks.get(task_name)
            if task is None:
                logging.debug("Skipping Task '%s' because it was added as a dependency, but was never added to the TaskGraph." % task_name)
                continue

            ready = True
            for dependencyName in task['obj'].dependencies:
                # If the dependency has no entry, it means it was never actually added it to the task graph.
                if results.get(dependencyName) is False:
                    ready = False
                    break

            if not ready:
                logging.warning("This task's dependencies failed to execute. Skipping task: '%s'" % task.name)
                continue

            #TODO: The python script being executed here can be a security liability 
            # since they can be modified between being written out, and being executed 
            # here. Either add a mechanism for ensuring they have not been modified 
            # or prevent them from being modified.
            process = subprocess.Popen(
                [task["executable"], task["script"]],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                logging.info("Task '%s' Successfully completed" % task['obj'].name)
                results[task['obj'].name] = True
            else:
                logging.error("Task '%s' Failed. Will skip all dependant tasks." % task['obj'].name)
                results[task['obj'].name] = False

        #TODO: Cleanup the tempdir from exported_tasks.

    def execute_deadline(self):
        #import Deadline.DeadlineConnect as Connect
        #deadline = Connect.DeadlineCon(self._settings["deadline_server"], self._settings["deadline_port"])
        deadline = None

        def submit_task_to_deadline(task, deadline, dependencies):
            dependencies_str = ",".join(dependencies)
            job_attrs = {
				"Name": task['obj'].name,
				"Plugin": "CommandLine",
				"Executable": task['executable'], 
				"Args": task['script'], 
				"JobDependencies": dependencies_str
			}

            plugin_attrs = {

            }

            job_id = task['obj'].name
            #job_id = deadline.Jobs.SubmitJob(job_attrs, plugin_attrs)
            print("Job: {}".format(job_id))
            return job_id

        exported_tasks = self.export_tasks()

        results = {}
        taskExecutionOrder = networkx.topological_sort(self._graph)
        for task_name in taskExecutionOrder:
            task = exported_tasks.get(task_name)
            if task is None:
                logging.debug("Skipping Task '%s' because it was added as a dependency, but was never added to the TaskGraph." % task_name)
                continue

            job_dependencies = []
            for dependencyName in task['obj'].dependencies:
                # If the dependency has no deadline_id, it means it was never actually added it to the task graph.
                dependency = exported_tasks.get(dependencyName)
                if dependency and "deadline_id" in dependency:
                    job_dependencies.append(dependency['deadline_id'])

            deadline_id = submit_task_to_deadline(task, deadline, job_dependencies)
            task['deadline_id'] = deadline_id

    def execute_legacy(self):
        """ Executes the task graph.

            Note: Executes tasks in Topological order based on their dependencies. 
                This means the order of execution may vary for tasks not dependent 
                on one another.

            Note: This is a simple implementation of execute which results in asynchronous
                task execution on a single machine. Ideally there would be an implementation
                that will export each task, then dispatch the tasks to a render 
                farm for synchronous task execution where possible.

            Note: Marked as legacy because it naively assumes all tasks are capable 
                of being run in the same environment. Some tasks will require unique 
                execution environments. Such as a nuke render task might require 
                nuke to be importable. (Therefore needs to be run with "nuke -t ..."
                instead of "python ...")
        """

        self.validate_task_graph()
        
        results = {}
        taskExecutionOrder = networkx.topological_sort(self._graph)
        for task_name in taskExecutionOrder:
            task = self._tasks.get(task_name)
            # Due to how we handle dependencies it is possible that we have tasks in our task graph that never actually existed.
            if task is None:
                logging.debug("Skipping Task '%s' because it was added as a dependency, but was never added to the TaskGraph." % task_name)
                continue
            
            logging.info("Running task: %s" % task_name)

            #Determine if this task's dependencies have successfully completed. Otherwise skip it
            ready = True
            for dependencyName in task.dependencies:
                # If the dependency has no entry, it means it was never actually added it to the task graph.
                if results.get(dependencyName) is False:
                    ready = False
                    break
            
            if not ready:
                logging.warning("This task's dependencies failed to execute. Skipping task: '%s'" % task.name)
                continue

            #Run the task
            result = task()
            results[task.name] = result
            if result is False:
                logging.error("Task '%s' Failed. Will skip all dependant tasks." % task.name)
            else:
                logging.info("Task '%s' Successfully completed" % task.name)

