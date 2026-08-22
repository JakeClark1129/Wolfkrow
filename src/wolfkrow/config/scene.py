

import os

import yaml
import re

from .config import WolfkrowConfigManager

# NOTE: Historically, wolfkrow was primarily driven by environment variables,
# which very heavily encouraged a single global configuration for all of Wolfkrow
# in a studio. 
# Instead, we are trying to move towards a more instanced design which encourages
# users to have many smaller configurations. Similar to what you'd do with Nuke 
# scripts.
# This new pattern should encourage users to have a single wolfkrow instance for
# ingestion, publishing, and client sends, rather than a single global configuration
# for all of wolfkrow.

class WolfkrowScene():
    """ This class is a wolfkrow scene file. It has all the settings and 
    configuration required to load, edit, and run a wolfkrow graph.
    """
    def __init__(self, wolfkrow_scene_file):

        self.wolfkrow_scene_file = wolfkrow_scene_file

        self._settings = {}

        # Load the settings file.
        self._load_settings()
        
        self.config_manager = WolfkrowConfigManager(self.wolfkrow_search_paths)

    def _load_settings(self):
        with open(self.wolfkrow_scene_file, "r") as handle:
            file_contents = handle.read()
        settings = yaml.load(file_contents, Loader=yaml.Loader)
        self._settings = settings

    @property
    def wolfkrow_search_paths(self):
        return self._settings.get("wolfkrow", {}).get("wolfkrow_config_search_paths", {})

    def default_context_from_env(self):
        """ This method generates a default context dictionary for this scene by
        looking at all the environment variables used in the paths of the schema
        nodes, and then pulling those values from the actual environment variables.
        """
        context = {}
        for key in self.config_manager.schema.context_keys:
            if key in os.environ:
                context[key] = os.environ[key]
        return context

    def resolve_complete_wolfkrow_config(self, context):
        return self.config_manager.resolve_complete_wolfkrow_config(context)

    def parse_workflow(self, workflow_name, prefix=None, context=None):
        if context is None:
            context = self.default_context_from_env()

        config = self.resolve_complete_wolfkrow_config(context)

        return config.parse_workflow(workflow_name, prefix=prefix)