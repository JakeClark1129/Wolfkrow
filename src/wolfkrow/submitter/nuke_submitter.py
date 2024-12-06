

from datetime import datetime
import os
import sys
import wolfkrow

import nuke
import re
import pyseq 

from PySide2 import QtGui, QtCore, QtWidgets

from ..core import utils
from .source import SourceItem
from .ui.source_item_model import SourceItemModel


wolfkrow_search_paths = [
    "X:/__pipeline/quick_publish_config/wolfkrow.yaml",
    "X:/$TK_PROJECT_NAME/_pipeline/quick_publish_config/wolfkrow.yaml",
]

# Monkey patch the TurnoverItemRole into the QtCore.Qt namespace
QtCore.Qt.SourceItemRole = 71

class WorkflowSelectorDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, workflows, parent=None):
        super().__init__(parent)
        self.workflows = workflows

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)

        editor.addItems(self.workflows)
        return editor

    def setEditorData(self, editor, index):
        data = index.data()
        if isinstance(data, int):
            editor.setCurrentIndex(data)
        elif isinstance(data, str):
            editor.setCurrentText(data)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentIndex(), QtCore.Qt.EditRole)

class NukeUI(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        loader = wolfkrow.Loader(
            config_file_paths=wolfkrow_search_paths,
        )
        self.workflows = list(loader.config["workflows"].keys())

        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.setup_ui()

        self.resize(1200, 600)

    def setup_ui(self):

        read_nodes = []
        for node in nuke.selectedNodes():
            if node.Class() == "Read":
                read_nodes.append(node)

        self.source_items = []
        for read_node in read_nodes:
            source_item = SourceItem(read_node["file"].getValue())
            self.source_items.append(source_item)

        source_item_model = SourceItemModel(self.source_items, workflows=self.workflows)

        source_item_view = QtWidgets.QTableView(self)
        source_item_view.setItemDelegateForColumn(
            0, 
            WorkflowSelectorDelegate(self.workflows, parent=source_item_view),
        )

        source_item_view.setModel(source_item_model)
        self.main_layout.addWidget(source_item_view)
        
        bottom_button_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(bottom_button_layout)
        bottom_button_layout.addStretch()
        start_button = QtWidgets.QPushButton("Start")
        start_button.clicked.connect(self.start)
        bottom_button_layout.addWidget(start_button)

    def start(self):
        # The first thing we need to do is to save the data from the UI back to the TurnoverItems
        for source_item in self.source_items:
            # Ignore items which are not enabled
            if source_item.enabled != 2:
                continue

        report_data = {
            "total_source_items": {},
            "successful_source_items": {},
            "deadline_jobs": [],
        }

        counter = 1

        task_graphs = []
        for source_item in self.source_items: 
            # Ignore items which are not enabled
            if source_item.enabled != 2:
                continue

            if source_item.name not in report_data["total_source_items"]:
                report_data["total_source_items"][source_item.name] = 0
            if source_item.name not in report_data["successful_source_items"]:
                report_data["successful_source_items"][source_item.name] = 0

            # Add this as a source item
            report_data["total_source_items"][source_item.name] += 1

            loader = wolfkrow.Loader(
                config_file_paths=wolfkrow_search_paths,
                replacements=source_item.replacements,
            )
            workflow_name = self.workflows[source_item.selected_workflow]
            item_task_graph = loader.parse_workflow(workflow_name)
            task_graphs.append((source_item, item_task_graph))
            # if not task_graph:
            #     task_graph = item_task_graph
            # else:
            #     task_graph.add_tasks(item_task_graph._tasks)

            date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

            # Set the batchname once per root file. So Things like a Plate and Grade 
            # are batched together on Deadline. This makes a lot of sense for artist 
            # publishes as well, since there will be many files per publish for an artist.
            # All of which will likely exist under a single scene file.
            report_data["successful_source_items"][source_item.name] += 1


        # Get the settings:
        settings_manager = utils.WolfkrowSettings()
        settings = settings_manager.settings

        for source_item, task_graph in task_graphs:
            batch_name = source_item.replacements["basename"] + " " + date

            deadline_jobs = task_graph.execute_deadline(
                batch_name=batch_name,
                inherit_environment=True,
                export_type="Json",
                temp_dir=settings.get("nuke_submitter", {}).get("temp_dir"),
            )
            report_data["deadline_jobs"].extend(deadline_jobs)
            counter += 1

        self.show_report(report_data)
        self.close()

    def close(self):
        super().close()

    def show_report(self, report_data):
        report = ReportDialog(report_data, parent=self)
        report.exec()

class ReportDialog(QtWidgets.QDialog):
    def __init__(self, report_data, parent=None):
        super().__init__(parent=parent)

        #self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)

        self.report_data = report_data

        layout = QtWidgets.QVBoxLayout(self)

        grid_layout = QtWidgets.QGridLayout()
        layout.addLayout(grid_layout)

        grid_layout.addWidget(QtWidgets.QLabel("Type"), 0, 0)
        grid_layout.addWidget(QtWidgets.QLabel("Total"), 0, 1)
        grid_layout.addWidget(QtWidgets.QLabel("Published"), 0, 2)

        for index, source_item_name in enumerate(report_data["total_source_items"]):
            grid_layout.addWidget(QtWidgets.QLabel(source_item_name), index + 1, 0)
            grid_layout.addWidget(QtWidgets.QLabel(str(report_data["total_source_items"][source_item_name])), index + 1, 1)
            grid_layout.addWidget(QtWidgets.QLabel(str(report_data["successful_source_items"][source_item_name])), index + 1, 2)
        
        deadline_job_layout = QtWidgets.QLabel("Deadline Jobs: {}".format(len(report_data.get("deadline_jobs", []))))
        layout.addWidget(deadline_job_layout)

        hlayout = QtWidgets.QHBoxLayout()
        layout.addLayout(hlayout)
        hlayout.addStretch()
        done_button = QtWidgets.QPushButton("Done")
        done_button.clicked.connect(self.close)
        hlayout.addWidget(done_button)

        self.adjustSize()

ui = None
def main():
    global ui
    #app = QtWidgets.QApplication.instance()
    ui = NukeUI()
    ui.show()
    #app.exec_()