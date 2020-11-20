import os
import yaml


def load_settings(settings_file):
    with open(settings_file, "r") as handle:
        file_contents = handle.read()
    settings = yaml.load(file_contents, Loader=yaml.FullLoader)
    return settings

settings = None
default_settings_file = os.path.join(os.path.dirname(__file__), "settings.yaml")
load_settings(default_settings_file)


class ReplacementsDict(dict):
    """ Implement the __missing__ method for dictionary so that it returns '{<key>}' 
        when the value is not present so that when it is passed to the str.format 
        function, missing keys do not raise an exception.
    """

    def __missing__(self, key):
        return "{" + key + "}"
