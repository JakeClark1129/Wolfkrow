from __future__ import print_function
import logging
import shutil
import traceback

logging.basicConfig(level=logging.DEBUG)

from wolfkrow.core.tasks import file_copy

#TODO: Turn these into real unit tests.
def test_file_copy_sequence():
    logging.info("======================================")
    logging.info("RUNNING TEST 'test_file_copy_sequence'")
    logging.info("======================================")
    
    try:
        shutil.rmtree("./test_data/sequences/dest/")
    except Exception as e:
        pass

    task = file_copy.FileCopy(source="./test_data/sequences/test.%04d.tst", destination="./test_data/sequences/dest/test_renamed.%06d_postfix.tst", start_frame=5, end_frame=7, renumbered_start_frame=1001)

    try: 
        task.setup()
        ret = task.run()
        error = False
    except Exception:
        traceback.print_exc()
        error = True
    finally:
        if not error:
            logging.info("TEST 'test_taskGraphExecuteSuccess' SUCCESSFUL")
        else:
            logging.info("TEST 'test_taskGraphExecuteSuccess' FAILED")
    logging.info("======================================\n\n")

test_file_copy_sequence()