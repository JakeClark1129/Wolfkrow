# Loader

The loader is wolfkrows main entry point. After initialization, it allows you to parse Workflows into TaskGraphs, which can then be combined with other TaskGraphs and executed. 

# Initialization

The loader has many optional initialization options.
* config_file_paths: The path to the wolfkrow.yml configuration files to use. This overrides the WOLFKROW_CONFIG_SEARCH_PATHS environment variable.
* replacements: The additional replacements to use to resolve the task definitions in the wolfkrow.yml files. (Allows the use of "{key_name}" style strings in the wolfkrow.yml file.)
* sgtk: Add a sgtk Configuration instance to add support for SGTK. (Allows the use of "SGTKTEMPLATE<template_name>" style strings in the woflkrow.yml file.)
* temp_dir: Override the systems default temp directory. Used for writing temporary files during export + execution.

# Usage:

There are a few way's to use the Loader. They all revolve around creating Tasks using the passed in values from initialization.

The following methods are the main methods:

* parse_workflow: This is the primary method which parses a single workflow definition, and returns a TaskGraph containing all the Tasks configured in the workflow.
* tasks_from_task_names_list: This is a secondary method which does a similar thing to the parse_workflow method, but it requires you to pass in the task names yourself rather than reading them from the configuration file.

