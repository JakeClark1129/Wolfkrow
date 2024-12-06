## Wolfkrow

# About

Wolfkrow is a Task Execution engine that prioritizes 2D workflows to automate a repetitive series of tasks to allow bulk processing of Media*.
Its main goal is to allow technical artists or TDs to modify their workflows without needing to know how to code. This is accomplished by using the wolfkrow.yml files. These files allow you to create Tasks and assign them to workflows. 
NOTE: The Wolfkrow.yml files will soon be able to be created using a Node based Node editing tool. This will hopefully expand the scope of who is able to set up and use Wolfkrow.


\* Wolfkrow's current Task implementations are based around 2D Media processing, with custom Task implementations you could automate other things as well.


# Setup

Set-up for Wolfkrow is quite simple. 
1. Download the latest version from GitHub as a zip file.
2. Pip install the zip file.

Part of the pip installation process will create a wolfkrow_run_task executable. Ensure this is added to PATH 

After this is done, there are some environment variables which need to be set:

* WOLFKROW_CONFIG_SEARCH_PATHS (Optional): This controls where wolfkrow searches for wolfkrow.yml files. More on this later. (TODO: Link to other docs section) 
* WOLFKROW_SETTINGS_FILE (Required): This controls where wolfkrow looks for it's main settings file.
* WOLFKROW_TASK_SEARCH_PATHS (Optional): This controls where wolfkrow looks for additional custom Task definitions.

If submitting jobs to Deadline, you must ensure that the Deadline Python API is available on PYTHONPATH, and that the deadline web service is set up and running. TODO: Add a deadline page to the docs.

# Usage

*Incoming* A simple front-end application which allows a user to drag and drop a file in and choose a workflow to process it though.

Currently, the main interface for Wolfkrow is via python through the Loader. The loader loads and parses the wolfkrow.yml files, and then allows you to create Tasks and TaskGraphs from them.

Once you have a TaskGraph from the Loader, then you can execute that TaskGraph. There is a lot to TaskGraph execution, but here is the basics.

* execute_local: The simplest execution method, but not ideal for large TaskGraphs or for processing lots of files. This executes every task in the task graph sequentially.
* execute_deadline: This is the primary execution method. This exports the TaskGraph into standalone tasks, which are then sent to Deadline to execute concurrently (depending on dependencies defined in the wolfkrow.yml file).

Example:
```python
        config_paths = [
            "/example/config_a/wolfkrow.yml", 
            "/example/config_b/wolfkrow.yml"
        ]
        replacements = {
            "studio": "AwesomeVFXHouse",
            "show_width": 4350,
            "show_height": 1918,
        }
        tk = sgtk.platform.current_engine().sgtk
        loader = workflow_builder.Loader(
            config_file_paths=config_paths,
            replacements=replacements,
            sgtk=tk,
        )
        task_graph = loader.parse_workflow("sample_workflow_name")

        task_graph.execute_deadline()
```

# Definitions

* Task: A defined re-usable piece of work which is configured in the wolfkrow.yml file. Ex: `NukeRender` which allows you to define a custom render task using Nuke.
* Task Attribute: The configurable attributes on a Task. Ex: the NukeRender task allows you to specify the `destination`
* TaskGraph: A collection of initialized Task's which are ready to be executed.
* Loader: Reads the wolfkrow.yml files and creates Tasks and TaskGraphs
* Resolver: 
* Replacement
* wolfkrow.yml