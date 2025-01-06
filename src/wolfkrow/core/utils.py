from builtins import object

import os
import sys
import yaml

from importlib import reload
from types import ModuleType

class WolfkrowSettings(object):
    """ Simple helper class to simplify getting the settings for wolfkrow. 

    NOTE: The settings are a different file than the wolfkrow.yaml file.
    """
    def __init__(self, settings_file=None):

        self.settings_file = None

        # If a settings file was passed into the init method, then use that
        if settings_file:
            self.settings_file = settings_file
        
        # Otherwise try and fallback to the environment variable
        if not self.settings_file:
            environ_settings_file = os.environ.get("WOLFKROW_SETTINGS_FILE")
            self.settings_file = environ_settings_file

        # And finally look in this current directory for the default one.
        if not self.settings_file:
            default_settings_file = os.path.join(os.path.dirname(__file__), "settings.yaml")
            self.settings_file = default_settings_file

        # Now load whatever settings file we found.
        self._load_settings()

    def _load_settings(self):
        with open(self.settings_file, "r") as handle:
            file_contents = handle.read()
        settings = yaml.load(file_contents, Loader=yaml.Loader)
        self.settings = settings

    def set_settings_file(self, settings_file):
        self.settings_file = settings_file
        # Now reload the config
        self._load_settings()


def wolfkrow_reload(module):
    """ Recursively reload all wolfkrow modules. Intended to be used in development, 
    when making changes and you don't want to restart the interpreter. (Typically
    when testing in a DCC like Nuke.)

    NOTE: Only recurses into submodules of the module passed in. Will not reload
        any other dependencies that the module may have.
    """
    reload(module)
    modules = list(sys.modules.values())
    for module_ in modules:
        if module_ is None:
            continue
        if module_.__name__ == module.__name__:
            continue
        if not isinstance(module_, ModuleType):
            continue
        if module_.__name__.startswith(module.__name__ + "."):
            # This shouldn't really be recursive, but without the recursion call, 
            # we end up reloading the task module after loading all the individual 
            # tasks. This means that the task module sets the all_tasks dictionary 
            # to an empty dictionary, and removes all the tasks that were loaded 
            # (Tasks add them selves to this dictionary as they are imported).
            # Recursive here doesn't "solve" this problem, but it does just happen
            # to load things in the correct order, so lets just leave it for now.
            wolfkrow_reload(module_)
