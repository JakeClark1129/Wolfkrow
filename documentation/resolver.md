# Resolver

Wolfkrow has powerful string substitution capabilities through the Resolver. It allows you to place special tokens through the wolfkrow environment which will get resolved at run-time allowing more dynamic configuration.

These tokens can be present anywhere within the Wolfkrow environment. Including even within Nuke Scripts passed into NukeRender tasks. 

The following are the style of string substitutions available:
1. Replacements
2. Environment variables
3. Path prefix resolver
4. SGTK Template substitution
5. Dates


# Replacements

Replacements follow the following pattern "{replacement_name}" and results in a simple key --> value substitution from the replacements dictionary

(Coming soon) You can also do operations within the replacements, such as addition and subtraction, dictionary lookups, list indexing etc... (Similar to how f-strings work.)

NOTE: Depending on the stage that the replacement is used, the available replacements will change.
    Ex: Replacements defined in the wolfkrow.yml file will not be available when resolving the settings file.

## What are Replacements?

The replacements dictionary is a large collection of key/value pairs which are used to perform string substitutions in the wolfkrow environment.

They are configured in many ways. As a technical user, the main way you can add new replacements is via adding them to the wolfkrow.yml files in the replacements section.

Otherwise, replacements get passed into the Loader when initializing wolfkrow. If using a custom submitter, then you have control over which replacements are added to the environment. 

When defining replacements, it's possible to include other replacements in your value, allowing you to build complex recursive replacement definitions.
Ex: 
Replacements:
  show_root: "/shows/{show}"
  shot_root: "{show_root}/shots/{sequence}/{shot}"

  plate_publish_path: "{shot_root}/publishes/Plate/..."

Where show, sequence, and shot are all replacements which are calculated in the submitter and passed into the Wolfkrow Loader

(Coming soon) The provided submitters provide a base level of replacements, which are gathered from the current environment, such as the current user, or they are gathered from the sources passed into Wolfkrow. For image sequences, we use a number of different inspection tools to gather information about the image, and include all of it as replacements. See individual documentation pages of the submitters for more information about which replacements are available in each. 

(Coming soon) Additionally, you are able to use the additional replacements hook, which allows you to inject your own replacements into replacements dictionary. This happens at the last stage of resolving, which should allow you to completely control all replacements used.

## Environment variables

This is basic environment variable substitution. if `$environment_var` string tokens are found, then the Resolver will search the environment for the given variable, and substitute its value.

## Path prefix resolver

The #resolve token is used to resolve path prefixes. This token can be used before any file path which is specified. 
The #resolve token is configured by the resolver_search_paths key in the wolfkrow.yml files.
It works by cycling through each prefix in the resolver_search_paths, and combining it with the text following the token. If that file exists on disk, then it will be resolved. The paths are resolved in order, and the first found will be the path used.

For example, with the following configuration:

resolver_search_paths:
   - /shows/{show}/{sequence}/{shot}/config
   - /shows/{show}/{sequence}/config
   - /shows/{show}/config

You could use:
\#resolver/nuke_snippets/apply_color.nk

This would typically resolve to the `/shows/Foo/config/nuke_snippets/apply_color.nk` script. However, some Shots may need a different color treatment, so you could create a `/shows/Foo/Bar/Baz/config/nuke_snippets/apply_color.nk` script which overrides the color process only for the Bar/Baz shot.

## SGTK Template

This is only enabled if you have passed in a SGTK configuration instance to the Loader. Or if using one of the submitters, it should be available automatically as long as SGTK is loaded in your current DCC.

It enables you to use SGTKTEMPLATE<template_name> style replacements. This works by grabbing the template from the SGTK configuration, and then using the replacements dictionary to fill the fields.

## Dates

Date Substitutions are simply a wrapper around datetime strings. Read the docs on how to format these here:
https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes

To trigger date substitutions, you must use this format: DATE<strftime_format> where "strftime_format" is the format you want from the datetime documentation.

NOTE: The dates use datetime.now() as the current time, and this value is grabbed once on initialization of the individual task, and re-used.
    Meaning that all DATE<> tokens share a datetime ensuring the time is synced.
    This also means that if you re-run a Task, then the date is re-calculated, and therefore changes if you run the same task multiple times. Perhaps the task