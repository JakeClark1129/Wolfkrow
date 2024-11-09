## Wolfkrow.yml

The Wolfkrow.yml files are the main interface for the technical users of Wolfkrow. This file is where you configure the tasks and workflows which are used by artists submitting jobs.

## The anatomy of the wolfkrow.yml file

# Executables:

# task_attribute_defaults

Here you can set default attribute for all task configuration instances in the `tasks` section.

Ex: 
```
task_attribute_defaults:
    NukeRender: # The type of the task
        executable: wolfkrow_nuke # The attribute name, and default value. 

```

# Replacements 

Here is where you can set up additional replacements. 

These can be combinations of other replacements, and environment variables. You can also hard-code values between them. 

Ex:
publish_path: "$PROJECTS_ROOT/{show}/sequences/{sequence}/{shot}/publishes/{publish_name}/{publish_version}

# Resolver search paths

This is where you can tell the resolver which paths to search for when using the resolver token. See Resolver (TODO:  Link HERE).

You can also use environment variables and other replacements in these paths.

# Tasks

Here is where you configure tasks which get used in workflows. See Tasks for more information.

Every Task attribute for the Task definition, can be configured here.

# Workflows

Here is where you string the tasks together to build a workflow