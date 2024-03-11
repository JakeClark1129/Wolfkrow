#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QWidget, QComboBox, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QFrame, QSizePolicy

from PyQt5.QtCore import Qt

import sys

from wolfkrow.builder.workflow_builder import Loader
from wolfkrow.submitter.utils import settings

class Submitter(QWidget):
    def __init__(self):
        super(Submitter, self).__init__()
        # Initialize our config file.
        # TODO: read from sys.argv to see if they passed in a custom config file.
        config = settings.SubmitterConfig()
        
        self.required_replacements_layout = None
        # First, we need to initialize the wolfkrow loader
        self.loader = Loader(config_file_paths=config.wolfkrow_config_file_paths)


    def setup_ui(self):
        workflows = self.loader.get_workflow_names()
        
        self.workflow_selector = QComboBox(self)
        self.workflow_selector.addItems(workflows)
        self.workflow_selector.currentIndexChanged.connect(self.workflow_selected)

    def workflow_selected(self, index):
        selected_workflow = self.workflow_selector.currentText()

        required_replacements = self.loader.get_required_workflow_replacements(selected_workflow)

        self.setup_required_replacements(required_replacements)
        # for replacement in required_replacements:
        #     replacement_text_edit = ReplacementTextEdit()
        #     replacement_text_edit.setup(self, replacement, options=None, strict=False)
        #     self.required_replacements_layout.addWidget(replacement_text_edit)

    def setup_required_replacements(self, required_replacements):

        # First, clear out all existing widgets. (TODO: Does this properly work recursively for children of children?)
        if self.required_replacements_layout is not None:
            for i in reversed(range(self.required_replacements_layout.count())): 
                widget = self.required_replacements_layout.takeAt(i).widget()
                if widget:
                    widget.deleteLater()
        else:
            self.required_replacements_layout = QHBoxLayout(self)

        # Now add vertical columns to the layout.
        replacement_names_layout = QVBoxLayout()
        self.required_replacements_layout.addLayout(replacement_names_layout)

        # Add a spacer line
        separador = QFrame()
        separador.setFrameShape(QFrame.VLine)
        #separador.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        #separador.setLineWidth(3)
        self.required_replacements_layout.addWidget(separador)

        # Add user input fields
        replacement_input_fields_layout = QVBoxLayout()
        self.required_replacements_layout.addLayout(replacement_input_fields_layout)

        # Now create all the required replacements widgets
        for replacement in required_replacements:
            display_label = QLabel(replacement.replacement_name)
            display_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            replacement_names_layout.addWidget(display_label)

            options_dropdown = None
            value_text_edit = None 
            # If in strict mode, and options are passed in, then we only provide a dropdown box to select from.
            if replacement.options:
                options_dropdown = QComboBox()
                options_dropdown.addItems(replacement.options)
                if not replacement.strict:
                    options_dropdown.setEditable(True)
                #self.dropdown.currentIndexChanged.connect(self.replacement_changed)
                replacement_input_fields_layout.addWidget(options_dropdown)
            else:
                value_text_edit = QLineEdit()
                #self.value_text_edit.textChanged.connect(self.replacement_changed)
                replacement_input_fields_layout.addWidget(value_text_edit)


def main():
    app = QApplication(sys.argv)
    submitter = Submitter()
    submitter.setup_ui()
    submitter.show()

    app.exec()
    return 0

if __name__ == "__main__":
    sys.exit(main())