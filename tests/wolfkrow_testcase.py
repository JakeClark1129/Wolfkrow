from __future__ import print_function
import unittest
import os

import shutil
import stat

from wolfkrow.builder import workflow_builder

class WolfkrowTestCase(unittest.TestCase):

    def setUp(self):
        if not os.path.exists("./test_temp"):
            os.makedirs("./test_temp")

    def tearDown(self):
        def on_rm_error( func, path, exc_info):
            # path contains the path of the file that couldn't be removed
            # let's just assume that it's read-only and unlink it.
            # NOTE: This code is only needed on Windows. Does this cause issues on Linux?
            os.chmod( path, stat.S_IWRITE )
            os.unlink( path )

        # Clean up the temp dir if it exists.
        if os.path.exists("./test_temp"):
            shutil.rmtree("./test_temp", onerror=on_rm_error)

    def get_default_test_loader(self):
        config_paths = [
            self.get_test_config_file("test_config_file.yaml"), 
            self.get_test_config_file("test_config_file2.yaml")
        ]
        loader = workflow_builder.Loader(config_file_paths=config_paths)
        return loader

    def get_test_config_file(self, config_file_name):
        root = self._get_test_root("config")
        config_file = os.path.join(root, config_file_name)
        return config_file

    def get_test_temp_file(self, temp_file_name):
        root = self._get_test_root("temp")
        temp_file = os.path.join(root, temp_file_name)
        return temp_file

    def get_test_data_file(self, test_data_file):
        root = self._get_test_root("data")
        temp_file = os.path.join(root, test_data_file)
        return temp_file

    def _get_test_root(self, root_type):
        current_file = os.path.realpath(__file__)
        test_root = os.path.dirname(current_file)
        test_root = os.path.join(test_root, "test_{}".format(root_type))
        return test_root
