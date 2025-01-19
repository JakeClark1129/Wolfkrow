from builtins import object
import copy
import os
import platform
import re
import string
import yaml
from ..core import tasks
from ..core.engine.task_graph import TaskGraph
from ..core.engine.resolver import Resolver

class LoaderException(Exception):
    """ Exception for generic Task errors
    """
    pass

class Loader(object):
    """ Responsible for loading the configuration files and 
        creating a task graph from a given workflow_name inside 
        present inside of the config file.

        Note: Duplicate entries found in more than 1 config file are overwritten by config files found later in the list

        Args:
            config_file_paths (list): List of file paths to parse for the configured 
                work_flows. If not specified, it deafaults to the "WOLFKROW_CONFIG_SEARCH_PATHS" 
                environment variable.
    """
    def __init__(self, config_file_paths=None, replacements=None, sgtk=None, temp_dir=None):
        if config_file_paths is None:
            config_file_paths = os.environ.get('WOLFKROW_CONFIG_SEARCH_PATHS')
            config_file_paths = os.path.expandvars(config_file_paths)
            if config_file_paths:
                config_file_paths = config_file_paths.split(",")

        if config_file_paths is None:
            raise LoaderException("Configuration file not specified and 'WOLFKROW_CONFIG_SEARCH_PATHS' not set.")

        self._config_file_paths = config_file_paths
        self.__config = None
        self.replacements = replacements or {}
        self._sgtk = sgtk
        self.temp_dir = temp_dir

    @property
    def config(self):
        if self.__config is None:
            self.__config = self._load_configs(self._config_file_paths)
        
        return self.__config

    def _update_config(self, current_dict, new_dict):
        
        # # Generic solution:
        # for key, value in new_dict.items():
        #     if key in current_dict:
        #         if type(value) != type(current_dict[key]):
        #             current_dict[key] = value
        #         elif isinstance(dict, value):
        #             self._update_config(current_dict[key], value)
        #         elif isinstance(list, value) or isinstance(set, value):
        #             for item in value:
        #                 pass

        # Custom solution:
        # Top level of the config. IE: task_attribute_defaults, replacements, tasks
        workflow_dict = new_dict.get("workflows")
        if workflow_dict:
            if "workflows" not in current_dict:
                current_dict["workflows"] = workflow_dict
            else:
                current_dict["workflows"].update(workflow_dict)

        tasks_dict = new_dict.get("tasks")
        if tasks_dict:
            if "tasks" not in current_dict:
                current_dict["tasks"] = tasks_dict
            else:
                current_dict["tasks"].update(tasks_dict)

        replacements_dict = new_dict.get("replacements")
        if replacements_dict:
            if "replacements" not in current_dict:
                current_dict["replacements"] = replacements_dict
            else:
                current_dict["replacements"].update(replacements_dict)

        resolver_search_paths = new_dict.get("resolver_search_paths")
        if resolver_search_paths:
            # resolver search paths completely override any previously specified search paths.
            current_dict["resolver_search_paths"] = resolver_search_paths

        task_attribute_defaults = new_dict.get("task_attribute_defaults")
        if task_attribute_defaults:
            if "task_attribute_defaults" not in current_dict:
                current_dict["task_attribute_defaults"] = task_attribute_defaults
            else:
                current_dict["task_attribute_defaults"].update(task_attribute_defaults)

        executables = new_dict.get("executables")
        if executables:
            if "executables" not in current_dict:
                current_dict["executables"] = executables
            else:
                current_dict["executables"].update(executables)

        path_swap = new_dict.get("path_swap")
        if path_swap:
            if "path_swap" not in current_dict:
                current_dict["path_swap"] = path_swap
            else:
                current_dict["path_swap"].update(path_swap)

    def _load_configs(self, config_file_paths):
        config = {}
        for config_file in config_file_paths:

            # Replace any replacements in the config file paths.
            resolver = Resolver(self.replacements, sgtk=self._sgtk)
            config_file = resolver.resolve(config_file)

            # Check that the config file exists before loading it.
            if not os.path.exists(config_file):
                print("Warning: Wolfkrow config file {} was not found.".format(config_file))
                continue

            with open(config_file, "r") as handle:
                file_contents = handle.read()

            config_snippet = yaml.load(file_contents, Loader=yaml.Loader)
            self._update_config(config, config_snippet)

        # replace replacements
        # TODO: Should configured replacements overwrite replacements that are passed 
        # into the tool, or viceversa?
        self.replacements.update(config.get('replacements', {}))

        return config

    def _create_task(self, task_name):
        configured_task_data = self.config['tasks'].get(task_name)
        if configured_task_data is None:
            return None

        default_task_data = self.get_default_task_data(configured_task_data['task_type'])
        task_data = copy.deepcopy(default_task_data)
        task_data.update(configured_task_data)

        task_type = task_data['task_type']
        task_obj = tasks.all_tasks.get(task_type)
        if task_obj is None:
            print("Warning: Task type '{task_type}' is undefined. Ignoring...".format(task_type=task_type))
            return None

        # The way path swap is configured is not really optimal for performing 
        # the actual path swaps. Lets format this into a lookup dictionary keyed 
        # on all different root paths possible.
        path_swap = self.config.get("path_swap", {})
        path_swap_lookup = {}
        for swap in path_swap:
            for os in path_swap[swap]:
                # We support a list of root paths for each OS because some OS's 
                # may have multiple root paths which point to the same location. 
                # Ex: Windows UNC paths vs drive letters.
                if isinstance(path_swap[swap][os], list):
                    for path in path_swap[swap][os]:
                        path_swap_lookup[path] = path_swap[swap]
                else:
                    # The resolver expects a list of OS paths, rather than a 
                    # single string, so convert this to a list.
                    path_swap[swap][os] = [path_swap[swap][os]]

                    path_swap_lookup[path_swap[swap][os][0]] = path_swap[swap]

        task_data['name'] = task_name
        task_data['config'] = self.config
        task = task_obj.from_dict(
            task_data, 
            replacements=self.replacements,
            resolver_search_paths=self.config.get("resolver_search_paths", []),
            path_swap_lookup=path_swap_lookup,
            config_files=self._config_file_paths, 
            temp_dir=self.temp_dir,
            sgtk=self._sgtk
        )
        return task

    def tasks_from_task_names_list(self, task_names):
        """ Parses list of task names, to find in the configuration files. Then 
            constructs the corresponding list of tasks.

            Note: Task names not found in the configuration file will be ignored.

            Args: 
                task_names (list): List containing the names of tasks to look up 
                    in the configuration file.
            Returns:
                List: List of constructed tasks.
        """
        tasks_list = []
        for task_name in task_names:

            task = self._create_task(task_name)
            if task is None:
                continue

            tasks_list.append(task)

        return tasks_list

    def get_default_task_data(self, task_name):
        if task_name in self.config.get('task_attribute_defaults', []):
            return self.config['task_attribute_defaults'][task_name]
        return {}

    def parse_workflow(self, workflow_name, prefix=None):

        task_graph = TaskGraph(
            workflow_name, 
            replacements=self.replacements, 
            temp_dir=self.temp_dir,
        )
        workflow_tasks = self.config['workflows'].get(workflow_name)

        if workflow_tasks is None:
            raise Exception("Unable to find workflow '{}'".format(workflow_name))

        for task_name in workflow_tasks:
            task = self._create_task(task_name)
            if task is None:
                continue

            task_graph.add_task(task)

        return task_graph
