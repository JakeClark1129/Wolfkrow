
import os

import yaml
import copy

from ..core.engine import resolver
from ..core import tasks
from ..core.engine.task_graph import TaskGraph

from .schema import WolfkrowConfigSchema

class WolfkrowConfigNode():
    def __init__(self, schema_node, context, parent=None):
        self._schema_node = schema_node

        self._parent = parent
        self.children = {}

        self._path = schema_node.resolve_path(context)
        self._key = schema_node.resolve_key(context)

        if self._parent:
            self._parent.add_child(self)
            
        self._config = WolfkrowConfig(self._path)

    def add_child(self, child_node):
        self.children[child_node._key] = child_node

class WolfkrowConfig():
    def __init__(self, path=None, replacements=None):
        """
        Initializes a WolfkrowConfig instance.

        Args:
            path (str, optional): The path to the configuration file. If not provided, 
                an empty config is initialized.
        """
        self._path = path

        self.additional_replacements = replacements or {}

        self._config = {}
        if self._path:
            self._parse_config(self._path)

    def _parse_config(self, path):
        # The path has been resolved correctly, but the file doesn't exist. This
        # is a valid state, as the config file is optional, so we just set the 
        # config to an empty dictionary.
        if not os.path.isfile(path):
            self._config = {}
            return

        with open(path, "r") as handle:
            file_contents = handle.read()

        self._config = yaml.load(file_contents, Loader=yaml.Loader)

    def add_config(self, other_config):
        """ Merges the other config into this config. 
        
        When handling conflicts between the two configs, we typically override 
        individual units, rather than entire sections. 
        Ex: If specifying a Task section in the config, only the specific tasks 
            that are specified in the new config will be overridden, and the rest
            of the tasks will be left unchanged.
        We also do not want to override specific attributes of a Task, so it's not
        possible to only override a single attribute of a Task configuration. 
        Instead, you must override the entire Task.
        
        Args:
            other_config (WolfkrowConfig): The other config to merge into this config.
        """

        # If this config was originally loaded from a path, clear the path, as 
        # the config is now a combination of multiple configs, and doesn't 
        # correspond to a single file anymore.
        if self._path:
            self._path = None

        # Top level of the config. IE: task_attribute_defaults, replacements, tasks
        workflow_dict = other_config._config.get("workflows")
        if workflow_dict:
            if "workflows" not in self._config:
                self._config["workflows"] = workflow_dict
            else:
                self._config["workflows"].update(workflow_dict)

        tasks_dict = other_config._config.get("tasks")
        if tasks_dict:
            if "tasks" not in self._config:
                self._config["tasks"] = tasks_dict
            else:
                self._config["tasks"].update(tasks_dict)

        replacements_dict = other_config._config.get("replacements")
        if replacements_dict:
            if "replacements" not in self._config:
                self._config["replacements"] = replacements_dict
            else:
                self._config["replacements"].update(replacements_dict)

        resolver_search_paths = other_config._config.get("resolver_search_paths")
        if resolver_search_paths:
            # resolver search paths completely override any previously specified search paths.
            self._config["resolver_search_paths"] = resolver_search_paths

        task_attribute_defaults = other_config._config.get("task_attribute_defaults")
        if task_attribute_defaults:
            if "task_attribute_defaults" not in self._config:
                self._config["task_attribute_defaults"] = task_attribute_defaults
            else:
                self._config["task_attribute_defaults"].update(task_attribute_defaults)

        executables = other_config._config.get("executables")
        if executables:
            if "executables" not in self._config:
                self._config["executables"] = executables
            else:
                self._config["executables"].update(executables)

        path_swap = other_config._config.get("path_swap")
        if path_swap:
            if "path_swap" not in self._config:
                self._config["path_swap"] = path_swap
            else:
                self._config["path_swap"].update(path_swap)

    
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
            replacements=self.additional_replacements,
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

    def get_workflow_names(self):
        return self.config["workflows"].keys()


    def get_required_task_replacements(self, task_name):
        tasks_lookup = self.config["tasks"]

        task_data = self.get_task_data(task_name)
        if task_data is None:
            return None

        required_task_replacements = []

        for attribute, value in task_data.items():
            found_replacements = resolver.Resolver.check_for_replacements(value)
            if found_replacements:
                required_task_replacements.extend(found_replacements)

        return required_task_replacements


    def get_required_workflow_replacements(self, workflow_name):
        workflow = self.config["workflows"].get(workflow_name)

        if workflow is None:
            return None
        
        required_workflow_replacements = []

        for task_name in workflow:
            task_required_replacements = self.get_required_task_replacements(task_name)
            if task_required_replacements:
                required_workflow_replacements.extend(task_required_replacements)

        # Convert all the replacements to data objects
        # NOTE: This is a stop gap hack. We need to add configuration to the workflow definitions which allow techinical users to define required replacements.
        required_workflow_replacement_data_objects = []
        for replacement in required_workflow_replacements:
            replacement_data_object = RequiredReplacementData(replacement, options=None, strict=False)
            required_workflow_replacement_data_objects.append(replacement_data_object)

        return required_workflow_replacement_data_objects

class RequiredReplacementData():
    def __init__(self,replacement_name, default=None, options=None, strict=False):
        self.replacement_name = replacement_name
        self.default = default
        self.options = options
        self.strict = strict

class WolfkrowConfigManager():
    def __init__(self, wolfkrow_config_search_paths):
        self.schema = WolfkrowConfigSchema(
            wolfkrow_config_search_paths=wolfkrow_config_search_paths
        )

    def resolve_complete_wolfkrow_config(self, context):
        # Start at the root of the schema, and resolve down the schema based on the context, until we reach a leaf node. Along the way, we will build up the complete config by merging the configs at each node in the schema.
        current_schema_node = self.schema._schema_root_node

        config_nodes = []


        # We resolve down the schema tree depth first, to build a linear heritage.
        # NOTE: We resolve depth first as a work-around to resolve ambiguous 
        # schemas for the given context. The result is that the first valid path 
        # down the schema will always be the one that is resolved, and any other 
        # valid paths will be ignored. 
        parent_config_node = None
        while current_schema_node.children:
            found_valid_child = False
            for schema_node in current_schema_node.children.values():
                if not schema_node.validate(context):
                    continue

                # If we got here, then the current schema node is valid for the context.
                current_schema_node = schema_node
                config_node = WolfkrowConfigNode(schema_node, context, parent_config_node)
                config_nodes.append(config_node)
                parent_config_node = config_node
                found_valid_child = True
                break
            
            # If we went through all the children and didn't find a valid one,
            # then there are no more valid paths down the schema, and we can 
            # stop resolving.
            if not found_valid_child:
                break

        # Once we have a linear heritage of config nodes, we can merge their 
        # configs to get the complete config.
        wolfkrow_config = WolfkrowConfig()
        for config_node in config_nodes:
            wolfkrow_config.add_config(config_node._config)

        return wolfkrow_config
