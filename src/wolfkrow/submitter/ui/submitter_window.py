

from datetime import datetime
import os
import sys
import wolfkrow

import sgtk
from sgtk.platform.qt import QtCore, QtGui

from ..turnover import TurnoverFactory

from .turnover_model import TurnoverModel, TurnoverModelProxy, BoolDelegate, ListDelegate, ContextDelegate
from .turnover_model_tree import TurnoverTreeModel, TreeViewDelegate
from .turnover_table_view import TurnoverTableView

class IngestUI(QtGui.QWidget):
    def __init__(self, sgtk, engine, shotgun, project, parent=None):
        super().__init__(parent=parent)
        self.sgtk = sgtk
        self.engine = engine
        self.project = project

        self.main_layout = QtGui.QVBoxLayout(self)
        self.drop_widget = self.create_initial_drop_ui()
        self.drop_widget.dragEnterEvent = self.drop_widget_dragEnterEvent
        self.drop_widget.dropEvent = self.drop_widget_dropEvent

        self.main_layout.addWidget(self.drop_widget)
        self.data_widget = None

        # self.parse_directory()
        #self.setup_ui()

        self._publish = False

    def drop_widget_dragEnterEvent(self, event):

        self.setBackgroundRole(QtGui.QPalette.Highlight)
        event.acceptProposedAction()

    def drop_widget_dropEvent(self, event):

        data = event.mimeData()

        urls = data.urls()

        if urls:
            path = urls[0].toLocalFile()
            self.text_box.setText(path)
            self.start_job()
            event.acceptProposedAction()
        else:
            return

    def create_initial_drop_ui(self):
        main_widget = QtGui.QWidget(self)

        main_widget.setAcceptDrops(True)

        main_layout = QtGui.QVBoxLayout()
        main_widget.setLayout(main_layout)

        hlayout = QtGui.QHBoxLayout()

        main_layout.addStretch()
        main_layout.addLayout(hlayout)
        main_layout.addStretch()

        hlayout.addStretch()
        self.text_box = QtGui.QLineEdit()
        self.text_box.setFixedWidth(600)
        hlayout.addWidget(self.text_box)

        open_folder_button = QtGui.QPushButton()
        open_folder_button.clicked.connect(self.create_file_dialog)
        pixmapi = QtGui.QStyle.SP_FileDialogStart
        icon = open_folder_button.style().standardIcon(pixmapi)
        open_folder_button.setIcon(icon)

        hlayout.addWidget(open_folder_button)

        go = QtGui.QPushButton("Go")
        go.clicked.connect(self.start_job)
        hlayout.addWidget(go)
        hlayout.addStretch()
        return main_widget

    def get_default_folder_path(self):
        # First, we check if there is a settings entry already
        settings = QtCore.QSettings("Wolfkrow", "Submitter")
        previous_path = settings.value("submitter_last_directory")

        if previous_path and os.path.exists(previous_path):
            return previous_path

        return ""


    def create_file_dialog(self):
        self.file_dialog = QtGui.QFileDialog()
        file_dialog = self.file_dialog
        file_dialog.setFileMode(QtGui.QFileDialog.Directory)
        file_dialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
        file_dialog.setAcceptMode(QtGui.QFileDialog.AcceptOpen)


        default_directory = self.get_default_folder_path()
        file_dialog.setDirectory(default_directory)

        file_dialog.fileSelected.connect(lambda text: self.text_box.setText(text))

        file_dialog.show()
        return file_dialog

    def start_job(self):
        #QtGui.DeleteLater(self.drop_widget)
        self.drop_widget.hide()

        project = os.environ.get("TK_PROJECT_NAME")


        settings = QtCore.QSettings("Wolfkrow", "Submitter")
        settings.setValue("submitter_last_directory", self.text_box.text())


        directory = self.text_box.text()

        turnover_items, turnover_definitions = self.parse_path(directory)

        self.data_widget = self.create_data_widget(turnover_items, turnover_definitions)
        self.main_layout.addWidget(self.data_widget)

    def parse_directory(self, directory):
        engine = sgtk.platform.current_bundle()

        # TODO: This need to happen as part of the UI. Should probably just accept drag + drop.
        # A file browser button is also required
        #directory = r"X:\BLR001_Ballerina\data_io\in\client\24_08\240801"
        #directory = self.file_dialog.selectedFiles()[0]
        #directory = r"X:\JUP007_Scorpio\data_io\in\client\24_07\240704\_DLL17702_ SCORPIO_PULL_ORDER_00081_20240703\SCORPIO_PULL_ORDER_00081_20240703"
        #directory = r"X:\JUP007_Scorpio\data_io\in\client"
        #directory = r"X:\JUP007_Scorpio\data_io\in\client\24_07\240704\_DLL17702_ SCORPIO_PULL_ORDER_00081_20240703\delete_me_later_20240927"

        context_manager = ContextManager(engine.sgtk, engine.context.project)
        context_manager.populate("Sequence")
        context_manager.populate("Shot", ["sg_sequence"])

        # Instantiate the TurnoverFactory and create TurnoverItems from the root directory passed in
        # TODO: This code needs to be moved to the UI code which accepts the root directory from the user
        turnover_factory = TurnoverFactory(engine.sgtk, context_manager)
        turnover_items = turnover_factory.create_turnover_items(directory)
        for turnover_item in turnover_items:
            print(turnover_item)


        self.turnover_items = turnover_items
        self.context_manager = context_manager

        return turnover_items, turnover_factory.config_manager.turnover_definitions

    def create_data_widget(self, turnover_items, turnover_definitions):


        # # Clear the existing UI first
        # def clear_layout(layout):
        #     for i in reversed(range(layout.count())): 
        #         if layout.itemAt(i).widget():
        #             layout.itemAt(i).widget().deleteLater()

        # clear_layout(self.main_layout)

        main_widget = QtGui.QWidget(self)
        main_widget.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

        main_layout = QtGui.QVBoxLayout()
        main_widget.setLayout(main_layout)
        splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        splitter.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        #horizontal_layout = QtGui.QHBoxLayout()
        main_layout.addWidget(splitter)
        bottom_button_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(bottom_button_layout)
        bottom_button_layout.addStretch()
        # cancel_button = QtGui.QPushButton("Cancel")
        # cancel_button.clicked.connect(self.close)
        # bottom_button_layout.addWidget(cancel_button)
        publish_button = QtGui.QPushButton("Publish")
        publish_button.clicked.connect(self.publish)
        bottom_button_layout.addWidget(publish_button)

        # Create and set up the models for the different Views
        # NOTE: I am not happy about this. The "correct" QT model/view architecture
        #   should allow me to create a single `TurnoverTreeModel` and then create
        #   multiple proxy objects to filter the data for each view.
        #   However, the dataChanged/parent/indexing logic is not working as expected.
        #   when trying to use a filter proxy model on the tree model on a table view.
        #   Instead, lets just create 2 separate models over the same raw data. 
        #   This means that changes to the data in one model will not be reflected 
        #   in the other, but there is no other way around this currently...
        #   Perhaps we can make the 2 models communicate with eachother... and 
        #   emit signals on eachothers behalf...
        #   Here is a stackoverflow post which suggested I do it this way:
        #   https://stackoverflow.com/questions/37588408/how-to-display-sub-rows-of-qabstractitemmodel-in-qtableview?lq=1
        turnover_model_table = TurnoverModel(turnover_items)
        turnover_model_tree = TurnoverTreeModel(turnover_items)
        
        # tree_proxy = TurnoverModelTreeProxy()
        # tree_proxy.setSourceModel(turnover_model)
        tree_view = QtGui.QTreeView()
        #tree_view.setStyleSheet("TreeViewEditWidget {border: 1px solid red }")
        tree_view.setModel(turnover_model_tree)

        delegate = TreeViewDelegate(tree_view)
        tree_view.setItemDelegateForColumn(0, delegate)

        for row in range(12):
            index = tree_view.model().index(row, 0, QtCore.QModelIndex())
            tree_view.openPersistentEditor(index)

            tree_view.openPersistentEditor(tree_view.model().index(0, 0, index))

            tree_view.expand(index)

        # for row in range(8):
        #     tree_view.openPersistentEditor(tree_view.model().index(row, 0))

        splitter.addWidget(tree_view)
        #main_layout.addWidget(tree_view)

        proxy_models = {}
        for turnover_type in turnover_definitions:
            turnover_model_proxy = TurnoverModelProxy(turnover_definitions[turnover_type])
            turnover_model_proxy.setSourceModel(turnover_model_table)

            proxy_models[turnover_type] = turnover_model_proxy

        # Create a QTabWidget, and add a page for each turnover model proxy.

        tab_widget = QtGui.QTabWidget()
        splitter.addWidget(tab_widget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

        for proxy_model_name in proxy_models:
            table_view = TurnoverTableView(
            #table_view = QtGui.QTableView(
                parent=self,
            )
            proxy_model = proxy_models[proxy_model_name]
            table_view.setModel(proxy_model)

            #table_view.horizontalHeader().setStretchLastSection(True)
            #table_view.horizontalHeader().setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
            table_view.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

            user_fields = proxy_model.user_fields

            #delegate = ContextDelegate(table_view)
            #table_view.setItemDelegateForColumn(shot_index, delegate)
            #table_view.setItemDelegateForColumn(sequence_index, delegate)
            # for row in range(table_view.model().rowCount()):
            #     table_view.openPersistentEditor(table_view.model().index(row, shot_index))
            #     table_view.openPersistentEditor(table_view.model().index(row, sequence_index))


            for user_field in user_fields.values():
                if user_field.type == "bool":
                    delegate_type = BoolDelegate
                elif user_field.type == "list":
                    delegate_type = ListDelegate
                elif user_field.type == "context":
                    delegate_type = ContextDelegate
                else:
                    continue
            
                column_number = user_fields.index_of(user_field.name)
                delegate = delegate_type(table_view)
                table_view.setItemDelegateForColumn(
                    column_number + 1, 
                    delegate
                )

                for row in range(table_view.model().rowCount()):
                    table_view.openPersistentEditor(table_view.model().index(row, column_number + 1))

            tab_widget.addTab(table_view, proxy_model_name)

        return main_widget

    def publish(self):

        # The first thing we need to do is to save the data from the UI back to the TurnoverItems
        for turnover_item in self.turnover_items:
            # Ignore items which are not enabled
            if turnover_item.enabled != 2:
                continue

            turnover_item.save()


        sg_batch = []

        from ..publish import Publisher

        # publisher = Publisher(self.shotgun)

        # latest_versions = publisher.get_latest_versions(self.turnover_items)

        # # Ensure that this version does not already exist
        # exists = []
        # for turnover_item in self.turnover_items:
        #     if turnover_item.publish_name in latest_versions:
        #         version = turnover_item.replacements.get("version")
        #         if version is None:
        #             raise ValueError("Version is not set for turnover item: {}".format(turnover_item.publish_name))
        #         if latest_versions[turnover_item.publish_name] >= turnover_item.replacements["version"]:
        #             exists.append(turnover_item)

        # existing_published_files = {}
        # existing_versions = {}

        # if exists:
        #     message = "The following files already exist in Shotgun:\n"
        #     for turnover_item in exists:
        #         message += "{}\n".format(turnover_item.publish_name)
        #     message += "\n"
        #     message += "They will be overwritten.\n\n"
        #     message += "Do you want to continue?"
        #     reply = QtGui.QMessageBox.question(self, "Version Exists", message, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        #     if reply == QtGui.QMessageBox.No:
        #         return
            
        #     existing_published_files = publisher.get_published_files(exists)

        #     existing_versions = publisher.get_published_versions(exists)

        # for turnover_item in self.turnover_items:
        #     # Ignore items which are not enabled
        #     if turnover_item.enabled != 2:
        #         continue

        #     if turnover_item.publish_name in existing_published_files:
        #         file_request_mode = "update"
        #     else:
        #         file_request_mode = "create"

        #     turnover_item_code = publisher.get_publish_code(turnover_item)
        #     turnover_item.replacements["publish_code"] = turnover_item_code

        #     request = {
        #         "request_type": file_request_mode,
        #         "entity_type": "PublishedFile",
        #         "data": {
        #             "code": turnover_item_code,
        #             "sg_publish_name": turnover_item.publish_name,
        #             "project": self.project,
        #             "entity": turnover_item.context.entity,
        #             "sg_publishing_status": "ips",
        #             "version_number": turnover_item.replacements["version"],
        #         }
        #     }
        
        #     # Add the required entity_id field if we are updating an existing PublishedFile
        #     if file_request_mode == "update":
        #         request["entity_id"] = existing_published_files[turnover_item.publish_name]["id"]

        #     sg_batch.append(request)


        #     # Versions don't know about the publish name, instead they need to 
        #     # be checked for based on the code
        #     if turnover_item_code in existing_versions:
        #         version_request_mode = "update"
        #     else:
        #         version_request_mode = "create"


        #     # TODO: We should ensure we add the PublishedFile to this Version...
        #     if turnover_item.replacements.get("create_version"):
        #         request = {
        #             "request_type": version_request_mode,
        #             "entity_type": "Version",
        #             "data": {
        #                 "code": turnover_item_code,
        #                 "project": self.project,
        #                 "entity": turnover_item.context.entity,
        #             }
        #         }
        #         sg_batch.append(request)

        #         if version_request_mode == "update":
        #             request["entity_id"] = existing_versions[turnover_item_code]["id"]

        # results = self.shotgun.batch(sg_batch)
        # for result in results:
        #     print(result)

        # Build a lookup dictionary keyed on the publish code.
        # turnover_item_lookup = {}
        # for turnover_item in self.turnover_items:
        #     turnover_item_code = publisher.get_publish_code(turnover_item)
            
        #     turnover_item_lookup[turnover_item_code] = turnover_item

        # # Add the published_file_id and version_id to the turnover items
        # for result in results:
        #     if result["type"] == "PublishedFile":
        #         turnover_item_lookup[result["code"]].replacements["published_file_id"] = result["id"]
        #     elif result["type"] == "Version":
        #         turnover_item_lookup[result["code"]].replacements["version_id"] = result["id"]

        sg_user = self.shotgun.find_one("HumanUser", [["id", "is", self.engine.context.user["id"]]], ["login"])
        user_name = sg_user["login"]

        # For some reason, some users in SG have their login as their full emails, and
        # other have just their user name. Splitting on "@" to get the user name.
        user_name = user_name.split("@")[0]

        # TODO: Any other replacements to add here?
        base_replacements = {
            "user": user_name,
            "user_entity": sg_user,
            "auth_token": self.shotgun.config.session_token,
        }

        report_data = {
            "total_turnover_items": {},
            "published_turnover_items": {},
            "deadline_jobs": [],
        }

        counter = 1
        top_level_turnover_items = {}
        for turnover_item in self.turnover_items: 
            # Ignore items which are not enabled
            if turnover_item.enabled != 2:
                continue

            if turnover_item.name not in report_data["total_turnover_items"]:
                report_data["total_turnover_items"][turnover_item.name] = 0
            if turnover_item.name not in report_data["published_turnover_items"]:
                report_data["published_turnover_items"][turnover_item.name] = 0

            # Add this as a turnover item
            report_data["total_turnover_items"][turnover_item.name] += 1
            
            publish_template = self.sgtk.templates["turnover_shot_plate"]
            plate_backup_template = self.sgtk.templates["turnover_shot_plate_backup"]
            item_replacements = {**base_replacements, **turnover_item.replacements}
            item_replacements["input_path"] = turnover_item.path

            # TODO:
            # publish_path = plate_publish_template.apply_fields(item_replacements)
            # backup_path = plate_backup_template.apply_fields(item_replacements)
            # item_replacements["publish_path"] = publish_path
            # item_replacements["backup_path"] = backup_path

            wolfkrow_search_paths = [
                "X:/__pipeline/publish_config/wolfkrow.yaml",
                "X:/{project}/_pipeline/publish_config/wolfkrow.yaml",
            ]

            loader = wolfkrow.Loader(
                config_file_paths=wolfkrow_search_paths,
                replacements=item_replacements,
                sgtk=self.sgtk,
            )
            workflow_name = turnover_item.replacements["workflow"]
            item_task_graph = loader.parse_workflow(workflow_name, prefix=turnover_item.publish_name)
            # if not task_graph:
            #     task_graph = item_task_graph
            # else:
            #     task_graph.add_tasks(item_task_graph._tasks)

            date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

            # Set the batchname once per root file. So Things like a Plate and Grade 
            # are batched together on Deadline. This makes a lot of sense for artist 
            # publishes as well, since there will be many files per publish for an artist.
            # All of which will likely exist under a single scene file.
            
            # Get the top level turnover_item
            top_level_parent = turnover_item
            while top_level_parent.parent is not None:
                top_level_parent = top_level_parent.parent

            if top_level_parent.publish_name not in top_level_turnover_items:
                top_level_turnover_items[top_level_parent.publish_name] = (top_level_parent, item_task_graph)

            # Merge the new task graph into the top level task graph
            if top_level_parent is not turnover_item:
                top_level_task_graph = top_level_turnover_items[top_level_parent.publish_name][1]
                top_level_task_graph.merge_task_graph(item_task_graph)

            report_data["published_turnover_items"][turnover_item.name] += 1

        for top_level_turnover_item, top_level_task_graph in top_level_turnover_items.values():
            batch_name = top_level_turnover_item.publish_name + " " + date

            env_pass_through_list = [
                "OCIO",
                "PYTHONPATH",
                "PATH",
                "WOLFKROW_DEFAULT_COMMAND_LINE_EXECUTABLE",
                "WOLFKROW_SETTINGS_FILE",
            ]

            environment = {key: os.environ[key] for key in env_pass_through_list if key in os.environ}

            deadline_jobs = top_level_task_graph.execute_deadline(
                batch_name=batch_name,
                inherit_environment=False,
                environment=environment,
                export_type="CommandLine",
                temp_dir=r"X:\__pipeline\sandbox\jacob.clark\temp",
                shell="cmd",
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

class ReportDialog(QtGui.QDialog):
    def __init__(self, report_data, parent=None):
        super().__init__(parent=parent)

        #self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)

        self.report_data = report_data

        layout = QtGui.QVBoxLayout(self)

        grid_layout = QtGui.QGridLayout()
        layout.addLayout(grid_layout)

        
        #grid_layout.setColumnCount(3)
        #grid_layout.setRowCount(len(report_data["total_turnover_items"]))
        #grid_layout.setSizeAdjustPolicy(QtGui.QAbstractScrollArea.AdjustToContents)
        #table.setHorizontalHeaderLabels(["Type", "Total", "Published"])

        grid_layout.addWidget(QtGui.QLabel("Type"), 0, 0)
        grid_layout.addWidget(QtGui.QLabel("Total"), 0, 1)
        grid_layout.addWidget(QtGui.QLabel("Published"), 0, 2)

        for index, turnover_item_name in enumerate(report_data["total_turnover_items"]):
            grid_layout.addWidget(QtGui.QLabel(turnover_item_name), index + 1, 0)
            grid_layout.addWidget(QtGui.QLabel(str(report_data["total_turnover_items"][turnover_item_name])), index + 1, 1)
            grid_layout.addWidget(QtGui.QLabel(str(report_data["published_turnover_items"][turnover_item_name])), index + 1, 2)
        
        deadline_job_layout = QtGui.QLabel("Deadline Jobs: {}".format(len(report_data.get("deadline_jobs", []))))
        layout.addWidget(deadline_job_layout)

        hlayout = QtGui.QHBoxLayout()
        layout.addLayout(hlayout)
        hlayout.addStretch()
        done_button = QtGui.QPushButton("Done")
        done_button.clicked.connect(self.close)
        hlayout.addWidget(done_button)

        #grid_layout.resizeColumnsToContents()
        #grid_layout.resizeRowsToContents()
        #grid_layout.adjustSize()
        self.adjustSize()
        #table.horizontalHeader().setResizeMode(QtCore.QHeaderView.ResizeToContents)



        # for row in range(table_view.model().rowCount(None)):
        #     turnover_item = table_view.model().turnover_item(row)

            # shot_combo_box = QtGui.QComboBox(editable=True)

            # # Add an empty item to the combo box to allow for no selection. To publish to the sequence.
            # shot_combo_box.addItem("")

            # # TODO: Select the current shot of the turnover item in the combo box
            # # If it doesn't exist, set to error state.

            # # Now add all the shots to the combo box. 
            # # TODO: We should do some clever filtering/sorting here based on the sequence currently selected...
            # shots = self.context_manager.get_entities("Shot")
            # shot_names = [shot["code"] for shot in shots]
            # shot_combo_box.addItems(shot_names)

            # # Add the Shot context widget to the cell
            # table_view.setIndexWidget(table_view.model().index(row, shot_index), shot_combo_box)

            # sequence_combo_box = QtGui.QComboBox(editable=True)
            # # Add an empty item to the combo box to allow for no selection. To publish to the project.
            # sequence_combo_box.addItem("")

            # # Now add all the sequences to the combo box.
            # sequences = self.context_manager.get_entities("Sequence")
            # sequence_names = [sequence["code"] for sequence in sequences]
            # sequence_combo_box.addItems(sequence_names)
            
            # # Add the Sequence context widget to the cell
            # table_view.setIndexWidget(table_view.model().index(row, sequence_index), sequence_combo_box)

        #size = self.parent().size()
        #self.parent().setMinimumSize(size)
        #self.setMinimumSize(size)
        #table_view.setMinimumSize(size)
        
        # size = table_view.sizeHint()
        # table_view.setMinimumSize(size)

class ContextManager():

    def __init__(self, sgtk, project):
        # self._turnover_item = turnover_item
        self.sgtk = sgtk
        self.project = project

        # Entity lookup dictionary keyed by entity type
        self.entities = {}

    def populate(self, entity_type, fields=None):
        # return early if we already have the entities
        if entity_type in self.entities:
            return

        if fields is None:
            fields = []

        # Find all entities of the given type from Shotgun
        entities = self.sgtk.shotgun.find(entity_type, [["project", "is", self.project]], ["code"] + fields)
        self.entities[entity_type] = entities

    def get_entities(self, entity_type):
        return self.entities[entity_type]
    
    def discover_context(self, entity_name):
        # First try and find the entity in the sequences
        sequence = self.get_entity("Sequence", entity_name)
        if sequence:
            return self.context_from_entity(sequence)

        # If we can't fnind the etity in the sequences, try and find it in the shots
        shot = self.get_entity("Shot", entity_name)
        if shot:
            shot_context = self.context_from_entity(shot)
            return shot_context

        # If we can't find the entity in the shots, return None
        #TODO: Search Assets
        return None

    def get_entity(self, entity_type, entity_name):
        for entity in self.entities[entity_type]:
            if entity["code"] == entity_name:
                return entity

        # If we can't find the entity, return None
        return None

    def context_from_entity(self, entity):
        
        context = self.sgtk.context_from_entity(entity["type"], entity["id"])

        if entity["type"] == "Shot":
            context.additional_entities.append(entity.get("sg_sequence"))

        return context

# class ShotContext(ContextManager):
#     def __init__(self, turnover_item, sgtk, project):
#         super().__init__(turnover_item, sgtk, project, "Shot")

# class SequenceComboBox(ContextManager):
#     def __init__(self, turnover_item, sgtk, project):
#         super().__init__(turnover_item, sgtk, project, "Sequence")

# class ContextSelector(QtGui.QDialog):
#     def __init__(self, turnover_items, context_manager):
#         super(ContextSelector, self).__init__()

#         self.turnover_items = turnover_items

#         self.context_manager = context_manager
#         self.context_manager.populate("Sequence")
#         self.context_manager.populate("Shot", ["sg_sequence"])

#         self.vertical_layout = QtGui.QVBoxLayout(self)
#         self.entity_type_combo = QtGui.QComboBox()
#         self.entity_type_combo.addItems(["Shot", "Asset"])
#         self.entity_type_combo.currentIndexChanged.connect(self.entity_type_changed)
#         self.vertical_layout.addWidget(self.entity_type_combo)
#         self.entity_type_changed(self.entity_type_combo.currentIndex())

#         # Add Done button to bottom right of the UI
#         done_layout = QtGui.QHBoxLayout(self)
#         done_layout.addStretch()
#         done_button = QtGui.QPushButton("Done")
#         done_button.clicked.connect(self.close)
#         done_layout.addWidget(done_button)

#         self.vertical_layout.addStretch()
#         self.vertical_layout.addLayout(done_layout)

#     # def done(self):
#     #     self.close()

#     def entity_type_changed(self, index):
#         entity_type = self.entity_type_combo.itemText(index)
#         if entity_type == "Shot":
#             self.setup_shot_ui()
#         elif entity_type == "Asset":
#             self.setup_asset_ui()

#     def setup_shot_ui(self):
#         hlayout = QtGui.QHBoxLayout(self)
#         self.sequence_combo = QtGui.QComboBox(self)
#         self.sequence_combo.addItems([sequence["code"] for sequence in self.context_manager.get_entities("Sequence")])
#         self.sequence_combo.currentIndexChanged.connect(self.sequence_changed)
#         hlayout.addWidget(self.sequence_combo)


#         self.shot_combo = QtGui.QComboBox(self)
#         # self.shot_combo.addItems([shot["code"] for shot in self.context_manager.get_entities("Shot")])
#         self.shot_combo.currentIndexChanged.connect(self.shot_changed)
#         hlayout.addWidget(self.shot_combo)

#         self.vertical_layout.addLayout(hlayout)

#         # Now trigger the index changed logic to populate the default options.
#         self.sequence_changed(self.sequence_combo.currentIndex())
#         self.shot_changed(self.shot_combo.currentIndex())

#     def setup_asset_ui(self):
#         pass

#     def sequence_changed(self, index):
#         sequence_code = self.sequence_combo.itemText(index)
#         #sequence = [sequence for sequence in self.context_manager.get_entities("Sequence") if sequence["code"] == sequence_code][0]
        
#         self.shot_combo.clear()
#         for shot in self.context_manager.get_entities("Shot"):
#             if shot["sg_sequence"]["name"] == sequence_code:
#                 self.shot_combo.addItem(shot["code"])
#         #self.context_manager.set_turnover_item_context(sequence)

#     def shot_changed(self, index):
#         shot_code = self.shot_combo.itemText(index)
#         shot = [shot for shot in self.context_manager.get_entities("Shot") if shot["code"] == shot_code][0]
#         for turnover_item in self.turnover_items:
#             turnover_item.set_context(shot)


class TurnoverTableItem(QtGui.QTableWidgetItem):
    def __init__(self, turnover_item, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turnover_item = turnover_item

class TurnoverTable(QtGui.QTableView):
    def __init__(self, parent):
        super().__init__(parent=parent)

        # self.context_manager = ContextManager(sgtk, project)

        # self.setColumnCount(len(required_fields))
        # self.setRowCount(len(turnover_items) + 1)

        # for i, field in enumerate(required_fields):
        #     self.setItem(0, i, QtGui.QTableWidgetItem(field))

        # self.itemDoubleClicked.connect(self.shotItemDoubleClicked)

        # for i, turnover_item in enumerate(turnover_items):
        #     for j, field in enumerate(required_fields):
        #         item = TurnoverTableItem(turnover_item, turnover_item.given_fields.get(field, ""))
        #         if item.text() == "shot":
        #             pass
        #         else:
        #             item.setFlags(item.flags() | QtGui.Qt.ItemIsEditable)

        #         self.setItem(i + 1, j, item)

        # self.resizeColumnsToContents()
        # self.resize(800, 600)
        # self.show()

    # def shotItemDoubleClicked(self, item):
    #     # Get the column title
    #     title_item = self.item(0, item.column())
    #     title = title_item.text()

        
    #     if title == "shot":
    #         # TODO: Get a selection of the current turnover items.
    #         self.context_selector = ContextSelector([item.turnover_item], self.context_manager)
    #         self.context_selector.parent = self
    #         self.context_selector.show()