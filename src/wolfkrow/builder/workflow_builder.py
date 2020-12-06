
import os
import re
import string
import yaml
import wolfkrow.core.tasks as tasks
from wolfkrow.core.engine.task_graph import TaskGraph
from wolfkrow.core import utils

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
    def __init__(self, config_file_paths=None, replacements=None, sgtk=None):
        if config_file_paths is None:
            config_file_paths = os.environ.get('WOLFKROW_CONFIG_SEARCH_PATHS')
            if config_file_paths:
                config_file_paths = config_file_paths.split(",")

        if config_file_paths is None:
            raise LoaderException("Configuration file not specified and 'WOLFKROW_CONFIG_SEARCH_PATHS' not set.")
        self._config_file_paths = config_file_paths
        self.__config = None
        self._sgtk = sgtk
        self.replacements = replacements or {}
        # Ensure that the replacements dictionary is an instance of ReplacementsDict
        if not isinstance(self.replacements, utils.ReplacementsDict):
            self.replacements = utils.ReplacementsDict(self.replacements)

    @property
    def config(self):
        if self.__config is None:
            self.__config = self._load_configs(self._config_file_paths)
        
        return self.__config

    def _get_sgtk_template_value(self, template_name):
        """ Will attempt to find the given template name in the sgtk instace, and 
            then use the replacements dict as the fields to get the substituted
            template.
        """

        if self._sgtk is None:
            # TODO: ERROR: Workflow builder initialized without sgtk instance, BUT sgtk templates found in workflow.
            return None

        template = self._sgtk.templates.get(template_name)
        if template is None:
            return None

        value = template.apply_fields(self.replacements)
        return value

    def _replace_replacements(self, value):
         # Check for SGTK templates defined in the template.
        regexp = "(SGTKTEMPLATE{)(.*)(})"
        replace_str = "SGTKTEMPLATE{{{}}}"
        matches = re.findall(regexp, value)
        for match in matches:
            template_name = match.group(2)
            template_value = self._get_sgtk_template_value(template_name)
            if template_value:
                sub = replace_str.format(match.group(2))
                value = value.replace(sub, template_value)

        # Replace the remaining replacements.
        value = string.Formatter().vformat(value, (), self.replacements)
        return value

    def _load_configs(self, config_file_paths):
        config = {}
        for config_file in config_file_paths:
            with open(config_file, "r") as handle:
                file_contents = handle.read()

            config_snippet = yaml.load(file_contents, Loader=yaml.
            FullLoader)
            config.update(config_snippet)

        # replace replacements
        for replacement in config['replacements']:
            # Should configured replacements overwrite replacements that are passed 
            # into the tool, or viceversa?
            self.replacements.update(replacement)

        def replace_replacements_dict_crawler(dictionary, replacements):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    replace_replacements_dict_crawler(value, replacements)
                elif isinstance(value, list):
                    for index in range(len(value)):
                        if isinstance(value[index], dict):
                            replace_replacements_dict_crawler(value[index], replacements)
                        elif isinstance(value[index], str):
                            value[index] = string.Formatter().vformat(value[index], (), replacements)
                elif isinstance(value, str):                    
                    # Replace any replacements in the string.
                    dictionary[key] = self._replace_replacements(value)

        replace_replacements_dict_crawler(config, self.replacements)

        return config

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

        tasks_lookup = {}
        for task in self.config['tasks']:
            for task_name in task.keys():
                tasks_lookup[task_name] = task[task_name]

        tasks_list = []
        for task_name in task_names:

            task_data = tasks_lookup.get(task_name)
            if task_data is None:
                continue

            task_obj = tasks.all_tasks.get(task_data['task_type'])
            if task_obj is None:
                #TODO: Warn about missing task definition but still continue without the task.
                continue

            task_data['name'] = task_name
            task = task_obj.from_dict(task_data)
            tasks_list.append(task)

        return tasks_list

    def parse_workflow(self, workflow_name):

        task_graph = TaskGraph("workflow", replacements=self.replacements)
        workflow_tasks = None
        for workflow in self.config['workflows']:
            if workflow_name in workflow.keys():
                workflow_tasks = workflow[workflow_name]
                break
        
        if workflow_tasks is None:
            raise Exception("Unable to find workflow '{}'".format(workflow_name))

        tasks_lookup = {}
        for task in self.config['tasks']:
            for task_name in task.keys():
                tasks_lookup[task_name] = task[task_name]

        #TODO: Add extra validation for the config file. (ensure tasks requested 
        # in the workflow section are defined in the tasks section)
        for task_name in workflow_tasks:

            task_data = tasks_lookup.get(task_name)

            task_obj = tasks.all_tasks.get(task_data['task_type'])
            if task_obj is None:
                #TODO: Warn about missing task definition but still continue without the task.
                continue
            
            task_data['name'] = task_name
            task = task_obj.from_dict(task_data)
            task_graph.add_task(task)

        task_graph.execute_local()


if __name__ == "__main__":
    loader = Loader([r"C:\Projects\Wolfkrow\src\wolfkrow\builder\config_file.yaml"])
    loader.parse_workflow("Convert to Tiff")