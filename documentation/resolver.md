# Resolver

Wolfkrow has a powerful string substitution capability through the Resolver. It's primarily set up via a replacements dictionary.

# What are replacements?

The replacements dictionary is a large collection of key/value pairs which are used to perform string substitutions in the wolfkrow environment.

They are configured in many ways. As a technical user, the main way you can add new replacements is via adding them to the wolfkrow.yml files in the replacements. 

Otherwise, replacements get passed into the Loader when initializing wolfkrow. If using a custom submitter, then you have control over which replacements are added to the environment. 

The provided submitters provide a base level of replacements, which are gathered from the current environment, such as the current user, or they are gathered from the sources passed into Wolfkrow. For image sequences, we use a number of different inspection tools to gather information about the image, and include all of it as replacements. See individual documentation pages of the submitters for more information about which replacements are available in each. 

(Coming soon) Additionally, you are able to use the additional replacements hook, which allows you to inject your own replacements into replacements dictionary. This happens at the last stage of resolving, which should allow you to completely control all replacements used.


The following are the style of text substitutions available:
1. Replacements
2. Environment variables
3. Path prefix resolver
4. SGTK Template substitution
5. Dates

## Replacements

Replacements follow the following pattern "{replacement_name}", and can be present anywhere. 
NOTE: Depending on the stage that the replacement is used, the available replacements will change.
    ex: Replacements defined in the wolfkrow.yml file will not be available when resolving the settings file. TODO: Confirm this is true...

## Environment variables

This is basic environment variable substitution. if `$environment_var` string tokens are found, then the Resolver will search the environment for the given variable, and substitute its value.

## #Resolver

The #resolve token is used to resolve path prefixes. This token can be used before any file path which is specified. 
The #resolve token is configured by the resolver_search_paths key in the wolfkrow.yml files.
It works by cycling through each prefix in the resolver_search_paths, and combining it with the text following the token. If that file exists on disk, then it will be resolved. The paths are resolved in order, and the first found will be the path used.

For example, with the following configuration:

resolver_search_paths:
   - /shows/$SHOW/$SEQUENCE/$SHOT/config
   - /shows/$SHOW/$SEQUENCE/config
   - /shows/$SHOW/config

You could use:
\#resolver/nuke_snippets/apply_color.nk

This would typically resolve to the `/shows/Foo/config/nuke_snippets/apply_color.nk` script. However, some Shots may need a different color treatment, so you could create a `/shows/Foo/Bar/Baz/config/nuke_snippets/apply_color.nk` script which overrides the color process only for the Bar/Baz shot.

## SGTK Template

This is only enabled if you have passed in a SGTK configuration instance to the Loader. Or if using one of the submitters, it should be available automatically as long as SGTK is loaded in your current DCC.

It enables you to use SGTKTEMPLATE<template_name> style replacements. This works by grabbing the template from the SGTK configuration, and then using the replacements dictionary to fill the fields.

## Dates

https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes