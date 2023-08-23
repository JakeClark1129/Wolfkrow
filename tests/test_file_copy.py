from __future__ import print_function
import logging
import os
import shutil
import stat

logging.basicConfig(level=logging.DEBUG)

import unittest

from wolfkrow.core.tasks import file_copy

from wolfkrow_testcase import WolfkrowTestCase

class TestFileCopy(WolfkrowTestCase):

    def test_file_copy_sequence(self):
        """ Simple test for the FileCopy Task which ensures that the files are 
        successfully copied to the destination.
        """

        source_path = self.get_test_data_file(
            os.path.join("sequences", "test.%04d.tst")
        )
        dest_path = self.get_test_temp_file(
            os.path.join("sequences", "dest", "test_renamed.%06d_postfix.tst")
        )
        task = file_copy.FileCopy(
            source=source_path, 
            destination=dest_path, 
            start_frame=5, 
            end_frame=7, 
            renumbered_start_frame=1001
        )

        task.setup()
        ret = task.run()
        if ret != 0:
            raise("FileCopy task returned non zero exit status.")

        # Now ensure that the files were successfully copied
        for i in range(1001, 1004):
            test_path = dest_path % i
            self.assertTrue(os.path.exists(test_path), "Copied files do not exist in expected location")

if __name__ == "__main__":
    unittest.main()
