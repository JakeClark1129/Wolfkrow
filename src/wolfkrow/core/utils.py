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
