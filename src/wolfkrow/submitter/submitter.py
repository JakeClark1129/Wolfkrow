#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QWidget, QComboBox

import sys

from wolfkrow.builder.workflow_builder import Loader
from wolfkrow.submitter.utils import settings

class Submitter(QWidget):
    def __init__(self):
        super(Submitter, self).__init__()
        # Initialize our config file.
        # TODO: read from sys.argv to see if they passed in a custom config file.
        config = settings.SubmitterConfig()
        
        # First, we need to initialize the wolfkrow loader
        self.loader = Loader(config_file_paths=config.wolfkrow_config_file_paths)


    def setup_ui(self):
        workflows = self.loader.get_workflow_names()
        
        workflow_selector = QComboBox(self)
        workflow_selector.addItems(workflows)


def main():
    app = QApplication(sys.argv)
    submitter = Submitter()
    submitter.setup_ui()
    submitter.show()

    app.exec()
    return 0

if __name__ == "__main__":
    sys.exit(main())