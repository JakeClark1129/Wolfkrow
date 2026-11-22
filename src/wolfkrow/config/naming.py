""" File naming convention for layered wolfkrow config files.

The file name *is* the identifier of the context a config file belongs to, so
that the files can be navigated (And debugged) directly on the file system.

All files live flat in the config root:

    wolfkrow_schema.yml
    base.wolfkrow.yml
    App=Nuke.wolfkrow.yml
    Show=AVG.wolfkrow.yml
    Show=AVG,RND,RND_999.wolfkrow.yml
    Show=AVG,RND,RND_999+App=Nuke.wolfkrow.yml
    User=jacob.wolfkrow.yml

- Groups are written in schema order, separated by "+".
- Each group is written as <GroupName>=<value>,<value>,... in layer order.
- Groups with no selection are omitted.

A flat structure means every override that exists is visible in one place, and
a simple wildcard finds every file for a context. Ex: "*App=Nuke*"
"""

import os

from .schema import Context, SchemaException

SUFFIX = ".wolfkrow.yml"
BASE_FILE_NAME = "base" + SUFFIX
SCHEMA_FILE_NAME = "wolfkrow_schema.yml"


def file_name(context):
    """ Returns the file name for the context. """
    if context.is_base:
        return BASE_FILE_NAME

    parts = []
    for group, values in context.selections.items():
        parts.append("{}={}".format(group, ",".join(values)))
    return "+".join(parts) + SUFFIX


def parse_file_name(schema, name):
    """ Parses a file name back into a Context.

    Returns:
        Context | None: None if the name is not a layered config file name.

    Raises:
        SchemaException: The name looks like a config file, but does not match
            the schema.
    """
    name = os.path.basename(name)
    if not name.endswith(SUFFIX):
        return None
    if name == BASE_FILE_NAME:
        return schema.base_context()

    stem = name[:-len(SUFFIX)]
    selections = {}
    for part in stem.split("+"):
        if "=" not in part:
            raise SchemaException("Invalid config file name '{}'. Expected <Group>=<value>,...".format(name))
        group_name, values = part.split("=", 1)
        group = schema.group(group_name)
        if group.name in selections:
            raise SchemaException("Group '{}' is specified twice in '{}'".format(group.name, name))
        selections[group.name] = tuple(values.split(","))

    context = Context(schema, selections)
    if file_name(context) != name:
        raise SchemaException("Config file name '{}' is not in the canonical form '{}'".format(
            name, file_name(context)))
    return context
