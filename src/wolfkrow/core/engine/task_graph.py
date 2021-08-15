""" taskGraph Module for building a task graph and executing it as a job.

    Author: Jacob Clark
"""

import copy
import logging
import networkx
import os
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

    def __init__(self, name, replacements=None, temp_dir=None):
        """ Initializes TaskGraph object.

            Args: 
                name (str): The name of the task graph. This is purely cosmetic and has no impact on task graph execution.
            
            Kwargs:
                replacements (dict): A dictionary of string replacements used by tasks.
                temp_dir (str): Temp directory to use as each tasks temp_dir.
        """

        self._graph = networkx.DiGraph()
        self._settings = utils.settings
        self._tasks = {}
        self.name = name
        self.replacements = replacements or {}
        self.temp_dir = temp_dir

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

        # Edges are added such that when the task graph is built it goes from 
        # "depended on task => dependent task". This results in the most 
        # depended on tasks being at the top of the tree when sorting Topologically. 
        # which will result in the correct order of task execution
        edges = [(dependency, task.name) for dependency in task.dependencies]
        self._graph.add_edges_from(edges)

    def add_tasks(self, tasks):
        for task in tasks:
            self.add_task(task)

    def add_dependency(self, task, dependency):
        """ Adds an additional dependency to a task already in the task graph.
        """
        task.dependencies.append(dependency)
        self._graph.add_edge(dependency, task.name)

    def validate_task_graph(self):
        """ Validates the current Task graph.

            Raises:
                TaskGraphValidationException: Invalid Task Graph
        """

        if not networkx.is_directed_acyclic_graph(self._graph):
            raise TaskGraphValidationException("Task Graph contains circular dependencies.")

    def export_tasks(self, export_type="PythonScript", temp_dir=None, deadline=False):
        """ Exports each individual task to its standalone state for execution.

            Note: there is some weird logic here to handle tasks that expand into 
            other tasks. We need to come up with a cleaner solution. Perhaps we can 
            allow each task to store a copy of its own task graph only containing 
            all its dependents, and then each task can be responsible for exporting 
            its own dependents during execution?

            Kwargs:
                export_type (str): Either "PythonScript" or "CommandLine" and dictates 
                    the format that the Tasks get exported to.
                temp_dir (str): Path to use for temp files. Will default to the 
                    following values in order.
                    1) Value passed in to this argument
                    2) Value originally passed into the task graph.
                    3) Value pointed to by any of the temp dir environment 
                        variables as dictated by tempfile.mkdtemp()
                deadline (bool): Whether or not to submit
        """

        exported_tasks = {}

        temp_dir = temp_dir or self.temp_dir
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp()
        logging.info("TEMPDIR: " + temp_dir)

        # Create a copy of the tasks dictionary.
        tasks = copy.copy(self._tasks)
        for task in tasks.values():

            # Export scripts for task.
            exported = task.export(
                export_type=export_type, 
                temp_dir=temp_dir, 
                job_name=self.name,
                deadline=deadline,
            )

            # If the task export returns a list, that means it was a task which 
            # expanded into multiple other tasks. We need to add these new tasks 
            # to the task_graph.
            if isinstance(exported, list):
                for exported_task in exported:
                    self.add_task(exported_task[0])
                # Search the task graph for tasks which dependend on the original 
                # task, and update them to depend on the new tasks.
                for task2 in self._tasks.values():
                    if task.name in task2.dependencies:
                        for exported_task in exported:
                            self.add_dependency(task2, exported_task[0].name)
            else:
                exported = [exported]

            for exported_task in exported:
                if export_type == "CommandLine":
                    command_bits = exported_task[1].split()
                    executable = command_bits[0]
                    args = command_bits[1:]
                    exported_tasks[exported_task[0].name] = {
                        "executable": executable,
                        "executable_args": args,
                        "script": None,
                        "obj": exported_task[0],
                    }
                elif export_type == "PythonScript":
                    exported_tasks[exported_task[0].name] = {
                    "executable": task.python_script_executable,
                    "executable_args": task.python_script_executable_args,
                    "script": exported_task[1],
                    "obj": exported_task[0],
                }

        return exported_tasks

    def execute_local(
        self, 
        temp_dir=None,
        export_type="CommandLine",
    ):

        exported_tasks = self.export_tasks(export_type=export_type, temp_dir=temp_dir)

        results = {}
        taskExecutionOrder = networkx.topological_sort(self._graph)
        for task_name in taskExecutionOrder:
            task = exported_tasks.get(task_name)
            if task is None:
                logging.debug("Skipping Task '%s' because it was added as a "
                    "dependency, but was never added to the TaskGraph." % task_name)
                continue

            ready = True
            for dependencyName in task['obj'].dependencies:
                # If the dependency has no entry, it means it was never actually added it to the task graph.
                if results.get(dependencyName) is False:
                    ready = False
                    break

            if not ready:
                logging.warning("This task's dependencies failed to execute. Skipping task: '%s'" % task['obj'].name)
                continue

            args = []
            args.append(task['executable'])
            if task['executable_args']:
                args.extend(task['executable_args'])
            if task.get("script") and task['script'] is not None:
                script_args = filter(lambda x: bool(x), task['script'].split(' '))
                args.extend(script_args)

            #TODO: The python script being executed here can be a security liability 
            # since they can be modified between being written out, and being executed 
            # here. Either add a mechanism for ensuring they have not been modified 
            # or prevent them from being modified.
            process = subprocess.Popen(
                args,
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

    def get_job_attrs_for_tasktype(self, task_type):
        """ Reads the settings file to get the default Group, Limits, and Pool 
            for each deadline job, and then also does a lookup to see if there
            is any overrides defined for the task_type requested.

            Args:
                task_type (str): Name of the type of task. Ex: NukeRender
            
            Returns:
                Dict: Dictionary containing Group, Limits, and Pool. Intended for 
                    use when submitting a Task to Deadline.
        """

        job_attrs = {
            "Group": self._settings["deadline"]["default_group"],
            "Limits": self._settings["deadline"]["default_limits"],
            "Pool": self._settings["deadline"]["default_pool"],
        }

        # Now look up any task_type specific overrides
        overrides = self._settings["deadline"].get("task_overrides", {})
        task_overrides = overrides.get(task_type)
        if task_overrides:
            if "group" in task_overrides:
                job_attrs["Group"] = task_overrides["group"]
            if "limit" in task_overrides:
                job_attrs["Limits"] = task_overrides["limits"]
            if "pool" in task_overrides:
                job_attrs["Pool"] = task_overrides["pool"]

        return job_attrs 

    def execute_deadline(
        self, 
        batch_name=None, 
        inherit_environment=True, 
        temp_dir=None, 
        export_type="CommandLine"
    ):
        """ Executes a task graph on deadline. 

            Kwargs:
                batch_name (str): The batch name of the job on deadline.
                inherit_environment (bool): Passes the current environment on to 
                    the deadline job if true.
                temp_dir (str): Temp directory to use as each tasks temp_dir.
                export_type (str): The export format for tasks to use.
        """

        import Deadline.DeadlineConnect as Connect
        deadline = Connect.DeadlineCon(
            self._settings["deadline"]["host_name"],
            self._settings["deadline"]["port"])

        def submit_task_to_deadline(task, deadline, dependencies, batch_name=None, frames=None):
            dependencies_str = ",".join(dependencies)
            batch_name = batch_name or self.name
            job_attrs = {
                "Name": task['obj'].name,
                "BatchName": batch_name,
                "UserName": os.environ.get("USER"),
                "Plugin": "CommandLine",
                "JobDependencies": dependencies_str,
            }

            task_job_attrs = self.get_job_attrs_for_tasktype(self.__class__.__name__)
            job_attrs.update(task_job_attrs)

            # If the task has a start_frame, end_frame, and chunk_size, then add these attributes to the deadline job.
            if (hasattr(task["obj"], "start_frame") and 
                hasattr(task["obj"], "end_frame") and 
                hasattr(task["obj"], "chunk_size")
            ):
                job_attrs['Frames'] = "{}-{}".format(task["obj"].start_frame, task["obj"].end_frame)
                job_attrs['ChunkSize'] = task["obj"].chunk_size  
                # Override chunk size to the total frame count if it is 0 or None
                if task["obj"].chunk_size and task["obj"].chunk_size == 0:
                    job_attrs['ChunkSize'] = task["obj"].end_frame - task["obj"].start_frame + 1

            # Add Environment variables.
            if inherit_environment:
                var_index = 0
                for key, value in os.environ.items():
                    job_attrs['EnvironmentKeyValue%s' % var_index] = "%s=%s" % (key, value)
                    var_index += 1

            if task['executable_args']:
                arguments = " ".join(task['executable_args'])
                if task.get("script") is not None:
                    arguments = arguments + " " + task['script']
            elif task.get("script") is not None:
                arguments = " " + task['script']

            plugin_attrs = {
                "Executable":task['executable'],
                "Arguments":arguments,
            }

            job = deadline.Jobs.SubmitJob(job_attrs, plugin_attrs)
            print("Job: {} - {}".format(job["Name"], job["_id"]))
            return job


        exported_tasks = self.export_tasks(
            export_type=export_type, 
            temp_dir=temp_dir, 
            deadline=True, 
        )
        deadline_jobs = {}

        taskExecutionOrder = networkx.topological_sort(self._graph)
        for task_name in taskExecutionOrder:
            task = exported_tasks.get(task_name)
            if task is None:
                logging.debug("Skipping Task '%s' because it was added as a dependency, but was never added to the TaskGraph." % task_name)
                continue

            job_dependencies = []
            for dependency_name in task['obj'].dependencies:
                # If the dependency has no deadline_id, it means it was never actually added it to the task graph.
                dependency = exported_tasks.get(dependency_name)
                if dependency and "deadline_id" in dependency:
                    job_dependencies.append(dependency['deadline_id'])

            deadline_job = submit_task_to_deadline(
                task, 
                deadline, 
                job_dependencies, 
                batch_name=batch_name
            )
            deadline_jobs[task_name] = deadline_job
            task['deadline_id'] = deadline_job["_id"]
        return deadline_jobs

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

