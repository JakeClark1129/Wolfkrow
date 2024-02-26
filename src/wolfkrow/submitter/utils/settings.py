

import os
import yaml

class WolfkrowSubmitterSettingsException(Exception):
    pass

class SubmitterConfig():
    def __init__(self, config_file_path=None):
        if config_file_path is None:
            config_file_path = os.getenv('WOLFKROW_SUBMITTER_CONFIG_FILE')
            if config_file_path is not None:
                config_file_path = os.path.expandvars(config_file_path)

        # Default to the default configuration which ships with wolfkrow.
        # TODO: This probably isn't useful in a practical setup... (But is convenient for testing)
        if config_file_path is None:
            curr_dir = os.path.dirname(os.path.realpath(__file__))
            config_file_path = os.path.join(curr_dir, "../submitter_settings.yaml")

        self._config_file_path = config_file_path

        self.__config = None
        
    @property
    def config(self):
        if self.__config is None:
            self.__config = self._load_configs(self._config_file_path)

            # Raise an exception if the config file is invalid.
            if self.__config is None:
                raise WolfkrowSubmitterSettingsException("Unable to load config file")
        return self.__config

    def _load_configs(self, config_file_path):
        config = {}

        if config_file_path is None:
            print("Warning: No Submitter config file found. Please ensure you set WOLFKROW_SUBMITTER_CONFIG_FILE")
            return None

        # Check that the config file exists before loading it.
        if not os.path.exists(config_file_path):
            print("Warning: Wolfkrow Submitter config file {} was not found.".format(config_file_path))
            return None

        with open(config_file_path, "r") as handle:
            file_contents = handle.read()

        config = yaml.load(file_contents, Loader=yaml.Loader)

        return config

    @property
    def wolfkrow_config_file_paths(self):
        return self.config["wolfkrow_config_file_paths"]