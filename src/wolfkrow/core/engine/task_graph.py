""" taskGraph Module for building a task graph and executing it as a job.

    Author: Jacob Clark
"""
from __future__ import print_function

from builtins import object
import copy
import fnmatch
import logging
import networkx
import os
import subprocess
import tempfile

from wolfkrow.core import utils
from wolfkrow.core.engine.resolver import Resolver

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

    def __init__(self, name, replacements=None, temp_dir=None, settings_file=None, prefix=None):
        """ Initializes TaskGraph object.

            Args: 
                name (str): The name of the task graph. This is purely cosmetic and has no impact on task graph execution.
            
            Kwargs:
                replacements (dict): A dictionary of string replacements used by tasks.
                temp_dir (str): Temp directory to use as each tasks temp_dir.
                settings_file (str): Path to the settings file to use for wolfkrows settings.
        """

        self._graph = networkx.DiGraph()

        # Get the settings:
        settings_manager = utils.WolfkrowSettings(settings_file=settings_file)
        self._settings = settings_manager.settings
        self._tasks = {}
        self._prefix = prefix
        self.name = name
        self.replacements = replacements or {}
        self.temp_dir = temp_dir

    def add_task(self, task, prefix=None):
        """ Adds a task to the task dictionary, and to the graph network.

        Also tracks dependencies between tasks. Note on dependencies:

        There are 2 modes of dependency tracking, inheritance based, and non-inheritance based.
        The difference comes into play when tasks have pre-fixes assigned (Typically
        when merging task graphs). 
        *Non-Inheritance*: When a task has a prefix, it will only have dependencies 
            from tasks with the same prefix. 
        *Inheritance*: Prefixes are no longer relevant in this mode (For dependencies). 
            Tasks will inherit dependencies from all tasks in the graph, which
            share the same name.

        This dependency inheritance is handled later during the export process. 
        For now we only track the dependencies based on the based on the name, and
        not the prefix + name combo.

            Args:
                task (Task): Task Object to add.

            Raises:
                TaskGraphException: Task Name in Graph is not Unique.
        """
        if prefix:
            # If this task already has a prefix, then we need to add the new 
            # prefix to the existing prefix.
            if task.name_prefix:
                task.name_prefix = prefix + "_" + task.name_prefix
            else:
                task.name_prefix = prefix

        if self._tasks.get(task.full_name) is None:
            self._tasks[task.full_name] = task
        else:
            raise TaskGraphException("Task Name is not Unique: %s." % task.full_name)

        # Add the task to the graph.
        self._graph.add_node(task.name)

        # Edges are added such that when the task graph is built it goes from 
        # "depended on task => dependent task". This results in the most 
        # depended on tasks being at the top of the tree when sorting topologically. 
        # which will result in the correct order of task execution
        edges = []
        for dependency in task.dependencies:
            edges.append((dependency, task.name))

        # Add the edges to the graph.
        self._graph.add_edges_from(edges)

    def add_tasks(self, tasks, prefix=None):
        for task in tasks:
            self.add_task(task, prefix=prefix)

    def merge_task_graph(self, task_graph, prefix=None):
        self.add_tasks(task_graph._tasks.values(), prefix=prefix)

    def add_dependency(self, task, dependency):
        """ Adds an additional dependency to a task already in the task graph.
        """
        task.add_dependency(dependency)

        self._graph.add_edge(dependency, task.name)

    def validate_task_graph(self):
        """ Validates the current Task graph.

            Raises:
                TaskGraphValidationException: Invalid Task Graph
        """

        if not networkx.is_directed_acyclic_graph(self._graph):
            raise TaskGraphValidationException("Task Graph contains circular dependencies.")

    def export_tasks(self, export_type="Json", temp_dir=None, deadline=False):
        """ Exports each individual task to its standalone state for execution.

            Note: there is some weird logic here to handle tasks that expand into 
            other tasks. We need to come up with a cleaner solution. Perhaps we can 
            allow each task to store a copy of its own task graph only containing 
            all its dependents, and then each task can be responsible for exporting 
            its own dependents during execution?

            Kwargs:
                export_type (str): *Deprecated* Should be set to Json. All other export methods are deprecated.
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
        for task in list(tasks.values()):

            # Export scripts for task.
            exported = task.export(
                export_type=export_type, 
                temp_dir=temp_dir, 
                job_name=self.name,
                deadline=deadline,
            )

            exported_task_names = [export.task.full_name for export in exported]

            if len(exported) > 1:
                for exported_task in exported[1:]:
                    self.add_task(exported_task.task, prefix=self._prefix)
                    # Update the new tasks to depend on the original task.
                    self.add_dependency(exported_task.task, task.name)

                # Search the task graph for tasks which depended on the original 
                # task, and update them to depend on the new tasks.
                for task2 in list(self._tasks.values()):
                    # Do not add a dependency to yourself.
                    if task2.name == task.name:
                        continue

                    # Do not add dependencies to tasks that we just added to the task graph.
                    if task2.full_name in exported_task_names:
                        continue

                    if task.name in task2.dependencies:
                        for exported_task in exported[1:]:
                            self.add_dependency(task2, exported_task.task.name)

            for exported_task in exported:
                # Add this task to the exported tasks
                exported_tasks[exported_task.task.full_name] = exported_task

                # Deadline needs special tokens for quotes in order to work correctly.
                if deadline and export_type == "BashScript" :
                    executable = "<QUOTE>{}<QUOTE>".format(exported_task.executable)
                    exported_task.executable = executable

        return exported_tasks

    def execute_local(
        self, 
        temp_dir=None,
        export_type="Json",
    ):

        exported_tasks = self.export_tasks(export_type=export_type, temp_dir=temp_dir)

        results = {}
        taskExecutionOrder = networkx.topological_sort(self._graph)
        for task_name in taskExecutionOrder:
            task_export = exported_tasks.get(task_name)
            if task_export is None:
                logging.debug("Skipping Task '%s' because it was added as a "
                    "dependency, but was never added to the TaskGraph." % task_name)
                continue

            ready = True
            for dependencyName in task_export.task.dependencies:
                #TODO: Add dependency inheritance support + corrected logic around task name prefixes
                # If the dependency has no entry, it means it was never actually added it to the task graph.
                if results.get(dependencyName) is False:
                    ready = False
                    break

            if not ready:
                logging.warning("This task's dependencies failed to execute. Skipping task: '%s'" % task_export.task.full_name)
                continue

            args = task_export.as_list()

            #TODO: The python script being executed here can be a security liability 
            # since they can be modified between being written out, and being executed 
            # here. Either add a mechanism for ensuring they have not been modified 
            # or prevent them from being modified.
            process = subprocess.Popen(
                args,
                shell=False,
            )
            process.communicate()

            if process.returncode == 0:
                logging.info("Task '%s' Successfully completed" % task_export.task.full_name)
                results[task_export.task.full_name] = True
            else:
                logging.error("Task '%s' Failed. Will skip all dependant tasks." % task_export.task.full_name)
                results[task_export.task.full_name] = False

        #TODO: Cleanup the tempdir from exported_tasks.

    def _get_additional_job_attrs(self, replacements=None, sgtk=None, task_type=None):
        """ Reads the settings file to get the default Group, Limits, and Pool 
            for each deadline job, and then also does a lookup to see if there
            is any overrides defined for the task_type requested.

            Args:
                task_type (str): Name of the type of task. Ex: NukeRender
            
            Returns:
                Dict: Dictionary containing Group, Limits, and Pool. Intended for 
                    use when submitting a Task to Deadline.
        """
        # FIXME: there is no "resolver" key in the settings file. This lives in 
        #   the wolfkrow.yaml file, so we should be getting this value from there. 
        #   And while were at it, make sure to also grab the new swap paths value.
        # Get the search paths settings for the resolver prefix logic.
        resolver_search_paths = self._settings.get("resolver", {}).get("search_paths", [])

        resolver = Resolver(replacements, resolver_search_paths, sgtk=sgtk)

        job_attrs = {
            "Group": self._settings["deadline"].get("default_group"),
            "Limits": self._settings["deadline"].get("default_limits"),
            "LimitGroups": self._settings["deadline"].get("default_limit_groups"),
            "Pool": self._settings["deadline"].get("default_pool"),
        }

        # Iterate over and add the attributes from the extra job attributes setting.
        job_attributes_setting = self._settings["deadline"].get("extra_job_attributes", {})
        for attr_key, attr_value in list(job_attributes_setting.items()):
            # replace replacements in the attr value:
            attr_value_replaced = resolver.resolve(attr_value)
            job_attrs[attr_key] = attr_value_replaced

        # Now look up any task_type specific overrides
        overrides = self._settings["deadline"].get("task_overrides", {})
        task_overrides = overrides.get(task_type)
        if task_overrides:
            if "group" in task_overrides:
                job_attrs["Group"] = task_overrides["group"]
            if "limits" in task_overrides:
                job_attrs["Limits"] = task_overrides["limits"]
            if "pool" in task_overrides:
                job_attrs["Pool"] = task_overrides["pool"]
            if "limit_groups" in task_overrides:
                job_attrs["LimitGroups"] = task_overrides["limit_groups"]

        return job_attrs 

    def execute_deadline(
        self, 
        batch_name=None, 
        inherit_environment=True, 
        environment=None,
        additional_job_attributes=None,
        temp_dir=None,
        export_type="Json",
        dependency_inheritance=True,
    ):
        """ Executes a task graph on deadline. 

            Kwargs:
                batch_name (str): The batch name of the job on deadline.
                inherit_environment (bool): Passes the current environment on to 
                    the deadline job if true.
                environment (dict): The environment to submit the job with. 
                    (If inherit environment is true, then the 2 environments are 
                    merged and this one take priority)
                temp_dir (str): Temp directory to use as each tasks temp_dir.
                export_type (str): The export format for tasks to use.
                dependency_inheritance (bool): Whether or not to inherit dependencies 
                    from tasks with a different prefix. Typically only relevant when
                    Tasks from multiple TaskGraphs are merged into a single TaskGraph.
        """

        # Initialize the environment as an empty dict if nothing was passed in.
        if environment is None:
            environment = {}

        import Deadline.DeadlineConnect as Connect
        deadline = Connect.DeadlineCon(
            self._settings["deadline"]["host_name"],
            self._settings["deadline"]["port"])

        def submit_task_to_deadline(task_export, deadline, dependencies, batch_name=None, frames=None):
            dependencies_str = ",".join(dependencies)
            batch_name = batch_name or task_export.task.full_name

            # Initialize the base job_attrs for a CommandLine Deadline Job.
            job_attrs = {
                "Name": task_export.task.full_name,
                "BatchName": batch_name,
                "Plugin": "CommandLine",
                "JobDependencies": dependencies_str,
            }

            # Now add the additional job attributes passed in, which may be required
            # to run on the local deadline set up.
            if additional_job_attributes:
                job_attrs.update(additional_job_attributes)

            # Finally, add the additional job attributes from the configuration file.
            additional_job_attrs = self._get_additional_job_attrs(
                replacements=task.task.replacements,
                sgtk=task.task.sgtk,
                task_type=task.task.__class__.__name__
            )
            job_attrs.update(additional_job_attrs)

            # If the task has a start_frame, end_frame, and chunk_size, then add these attributes to the deadline job.
            if (hasattr(task.task, "start_frame") and task.task.start_frame is not None and
                hasattr(task.task, "end_frame") and task.task.end_frame is not None and
                hasattr(task.task, "chunk_size") and task.task.chunk_size is not None
            ):
                job_attrs['Frames'] = "{}-{}".format(task.task.start_frame, task.task.end_frame)
                job_attrs['ChunkSize'] = task.task.chunk_size  
                # Override chunk size to the total frame count if it is 0 or None
                if task.task.chunk_size and task.task.chunk_size == 0:
                    job_attrs['ChunkSize'] = task.task.end_frame - task.task.start_frame + 1

            environment_dict = {}
            if inherit_environment:
                # First we apply the filters from our settings.
                inclusion_filters = self._settings.get("deadline", {}).get("environment_inclusion_filters", [])
                exclusion_filters = self._settings.get("deadline", {}).get("environment_exclusion_filters", [])
                inclusion_list = self._settings.get("deadline", {}).get("environment_inclusion_list", [])
                exclusion_list = self._settings.get("deadline", {}).get("environment_exclusion_list", [])

                # Build the initial list of included keys. Includes all by default.
                filtered_environment_keys = []
                if inclusion_filters:
                    for inclusion_filter in inclusion_filters:
                        filtered = fnmatch.filter(os.environ.keys(), inclusion_filter)
                        filtered_environment_keys.extend(filtered)
                else:
                    filtered_environment_keys = os.environ.keys()

                # Now remove stuff which matches the exclusion filters
                excluded = set()
                if exclusion_filters:
                    for exclusion_filter in exclusion_filters:
                        filtered = fnmatch.filter(filtered_environment_keys, exclusion_filter)
                        excluded.union(set(filtered))

                # Also remove stuff which is explicitly excluded
                if exclusion_list:
                    excluded.union(set(exclusion_list))

                # Now add stuff which is explicitly included
                if inclusion_list:
                    filtered_environment_keys.extend(inclusion_list)

                # Now finally build the environment:
                environment_dict = { key: os.environ[key] for key in filtered_environment_keys if key not in excluded and key in os.environ }


            environment_dict.update(environment)

            # Add Environment variables.
            var_index = 0
            for key, value in list(environment_dict.items()):
                job_attrs['EnvironmentKeyValue%s' % var_index] = "%s=%s" % (key, value)
                var_index += 1

            plugin_attrs = {
                "Executable": task.executable,
                "Arguments": task.args,
            }

            job = deadline.Jobs.SubmitJob(job_attrs, plugin_attrs)
            if isinstance(job, str):
                print("Failed to submit job. {}".format(job))
                return None
            else:
                print("Job: {:<55} - {}".format(job.get("Props").get("Name"), job["_id"]))
                return job


        exported_tasks = self.export_tasks(
            export_type=export_type, 
            temp_dir=temp_dir, 
            deadline=True,
        )
        deadline_jobs = {}

        taskExecutionOrder = networkx.topological_sort(self._graph)
        for task_name in taskExecutionOrder:
            tasks = []
            # The task graph does not deal with prefixes, so we need to get all
            # task exports which have this task_name (without prefix).
            # We will correct the task dependencies later depending on whether or
            # not inheritance is enabled.
            for task_export in exported_tasks.values():
                if task_export.task.name == task_name:
                    tasks.append(task_export)

            if len(tasks) == 0:
                logging.debug("Skipping Task '%s' because it was added as a dependency, but was never added to the TaskGraph." % task_name)
                continue

            for task in tasks:
                job_dependencies = []
                def add_dependency(dependency_name):
                    # If the dependency has no deadline_id, it means it was never actually added it to the task graph.
                    dependency = exported_tasks.get(dependency_name)
                    if dependency and dependency.deadline_id is not None:
                        job_dependencies.append(dependency.deadline_id)

                for dependency_name in task.task.dependencies:
                    if dependency_inheritance:
                        # If dependency inheritance is turned on, then we must look
                        # at all the exported tasks to see if the tasks name matches
                        # our dependency. This is for when multiple task graphs have
                        # been merged into a single task graph. There may be cases
                        # where we want tasks in our original task graph to depend on
                        # tasks in the merged task graph.
                        # Ex: A Plate Publish TaskGraph is merged with a Grade Publish,
                        #   TaskGraph and we want the plate quicktime generation to 
                        #   depend on the grade publish.
                        for exported_task_name in exported_tasks:
                            exported_task = exported_tasks[exported_task_name]
                            if exported_task.task.name == dependency_name:
                                add_dependency(exported_task_name)
                    else:
                        # If dependency inheritance is turned off, then we only want 
                        # tasks to depend on tasks with the same prefix as themselves.
                        # This will be useful in cases where multiple TaskGraphs of 
                        # the same workflow have been merged. In these cases we want
                        # the tasks to ignore the tasks from the other merged TaskGraphs.
                        # Ex: A Plate Publish task Graph is merged with another Plate
                        #   Publish task graph. In this case, we want the plate quicktime
                        #   generation to depend on its own plate generation task, but no
                        #   other plate generation tasks.
                        dependency_name = task.task.name_prefix + "_" + dependency_name
                        add_dependency(dependency_name)

                # If there are any external dependency ID's, add them to the job_dependencies list as well.
                if task.task.external_dependencies:
                    external_dependencies = task.task.external_dependencies.split(",")
                    job_dependencies.extend(external_dependencies)

                deadline_job = submit_task_to_deadline(
                    task, 
                    deadline, 
                    job_dependencies, 
                    batch_name=batch_name
                )
                if deadline_job:
                    deadline_jobs[task_name] = deadline_job
                    task.deadline_id = deadline_job["_id"]

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
                logging.warning("This task's dependencies failed to execute. Skipping task: '%s'" % task.full_name)
                continue

            #Run the task
            result = task()
            results[task.full_name] = result
            if result is False:
                logging.error("Task '%s' Failed. Will skip all dependant tasks." % task.full_name)
            else:
                logging.info("Task '%s' Successfully completed" % task.full_name)

