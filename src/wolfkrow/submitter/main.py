
from datetime import datetime
import os
import wolfkrow
import sys

from PySide2 import QtCore, QtGui


def main(app):
    # # start ui # TODO: Why use this show_dialog function? rather than starting our own QApplication/Main Window?
    #widget = app.engine.show_dialog("Ingest", app, IngestUI)
    # Ahhh we need to be using an engine which has the "show_dialog" method implemented. This allows us to use a DCCs native solution for UI code.
    # This is a standalone App and so our engine is tk-shell which does not have a show_dialog method implemented. Instead we should be using the standard Qt methods (a QApplication and a QWidget) to show our UI.
    # Also, there is a style.qss file at the root of this app. How/where does it get used?


    app = QtGui.QApplication(sys.argv)

    # contents = open("X:/__pipeline/sandbox/jacob.clark/GitHub/ts-ingest/style.qss", "r").read()

    # app.setStyleSheet(contents)

    # Attempt to get SGTK config instance. Do nothing if it's not available.
    try:
        import sgtk
        engine = sgtk.platform.current_bundle()
        #engine.engine._initialize_dark_look_and_feel()

        # Ensure our path cache is up to date with what's on disk.
        engine.sgtk.synchronize_filesystem_structure()
        tk = engine.sgtk
    except:
        tk = None
        pass

    ui = IngestUI(
        engine.sgtk, 
        engine,
        engine.shotgun, 
        engine.context.project,  
    )
    ui.show()
    #ui.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.
    # QSizePolicy.Expanding)
    #size = ui.sizeHint()
    ui.resize(1400, 600)
    app.exec_()

    if not ui._publish:
        sys.exit(0)

    # sg_user = engine.shotgun.find_one("HumanUser", [["id", "is", engine.context.user["id"]]], ["login"])
    # user_name = sg_user["login"]

    # # For some reason, some users in SG have their login as their full emails, and
    # # other have just their user name. Splitting on "@" to get the user name.
    # user_name = user_name.split("@")[0]

    # base_replacements = {
    #     # "shot": turnover_item.shot,
    #     # "task": turnover_item.task,
    #     "user_name": user_name,
    # }

    # counter = 1
    # top_level_turnover_items = {}
    # for turnover_item in turnover_items: 
    #     publish_template = engine.sgtk.templates["turnover_shot_plate"]
    #     plate_backup_template = engine.sgtk.templates["turnover_shot_plate_backup"]
    #     item_replacements = {**base_replacements, **turnover_item.replacements}
    #     item_replacements["input_path"] = turnover_item.path

    #     # TODO:
    #     # publish_path = plate_publish_template.apply_fields(item_replacements)
    #     # backup_path = plate_backup_template.apply_fields(item_replacements)
    #     # item_replacements["publish_path"] = publish_path
    #     # item_replacements["backup_path"] = backup_path

    #     item_replacements["publish_path"] = "X:\\__pipeline\\sandbox\\jacob.clark\\IngestPrototype/plates/publish/rnd_999_acescg_v001.%04d.exr"
    #     item_replacements["backup_path"] = "X:\\__pipeline\\sandbox\\jacob.clark\\IngestPrototype/plates/backup/{}.%04d.exr".format(
    #         item_replacements["basename"]
    #     )

    #     loader = wolfkrow.Loader(
    #         config_file_paths=[r"X:\__pipeline\sandbox\jacob.clark\IngestPrototype\wolfkrow.yaml"],
    #         replacements=item_replacements,
    #         sgtk=engine.sgtk,
    #         temp_dir=r"X:\__pipeline\sandbox\jacob.clark\temp"
    #     )
    #     workflow_name = turnover_item.replacements["workflow"]
    #     item_task_graph = loader.parse_workflow(workflow_name, prefix=turnover_item.publish_name)
    #     # if not task_graph:
    #     #     task_graph = item_task_graph
    #     # else:
    #     #     task_graph.add_tasks(item_task_graph._tasks)

    #     date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    #     # Set the batchname once per root file. So Things like a Plate and Grade 
    #     # are batched together on Deadline. This makes a lot of sense for artist 
    #     # publishes as well, since there will be many files per publish for an artist.
    #     # All of which will likely exist under a single scene file.
        
    #     # Get the top level turnover_item
    #     top_level_parent = turnover_item
    #     while top_level_parent.parent is not None:
    #         top_level_parent = top_level_parent.parent

    #     if top_level_parent.publish_name not in top_level_turnover_items:
    #         top_level_turnover_items[top_level_parent.publish_name] = (top_level_parent, item_task_graph)

    #     # Merge the new task graph into the top level task graph
    #     if top_level_parent is not turnover_item:
    #         top_level_task_graph = top_level_turnover_items[top_level_parent.publish_name][1]
    #         top_level_task_graph.merge_task_graph(item_task_graph)

    # for top_level_turnover_item, top_level_task_graph in top_level_turnover_items.values():
    #     batch_name = top_level_turnover_item.publish_name + " " + date

    #     env_pass_through_list = [
    #         "PYTHONPATH",
    #         "PATH",
    #         "OCIO",
    #         "WOLFKROW_DEFAULT_COMMAND_LINE_EXECUTABLE",
    #         "WOLFKROW_SETTINGS_FILE",
    #     ]
    #     environment = {key: os.environ[key] for key in env_pass_through_list if key in os.environ}

    #     # TODO: Get OCIO env var from sgtk or something...
    #     environment["OCIO"] = "X:\HBO003_Hidden\_pipeline\OCIO\HBO003_consolidated.ocio"

    #     import time

    #     top_level_task_graph.execute_deadline(
    #         batch_name=batch_name,
    #         inherit_environment=False,
    #         environment=environment,
    #         export_type="CommandLine",
    #         temp_dir=r"X:\__pipeline\sandbox\jacob.clark\temp\{}".format(str(int(time.time()))),
    #         shell="cmd",
    #     )
    #     counter += 1