from __future__ import print_function
from builtins import str
from builtins import range
from builtins import object
from past.builtins import basestring
import os
import re
import string
import yaml

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
