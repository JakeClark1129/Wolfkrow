""" Schema and Context definitions for layered (context based) wolfkrow configs.

A schema is defined by a `wolfkrow_schema.yml` file in the root of a layered
config directory:

    groups:
      - name: Show
        layers: [SHOW, SEQUENCE, SHOT]
      - name: App
        layers: [APP, STEP]
      - name: Override
        layers: [OVERRIDE]
      - name: User
        layers: [USER]

- The base config (base.wolfkrow.yml) is always used.
- Each group is a flat chain of layers. A layer can only be selected if all the
  layers before it in the group are selected. (A Shot requires a Sequence)
- A context selects a prefix of every group. Ex:
      Show: AVG / RND / RND_999,  App: Nuke
- Every combination of selections has its own config file. (See naming.py)

Resolution order:

All config files whose selections are equal to, or a prefix of, the selected
context apply. They are applied in order, with later groups always winning over
earlier groups, and deeper layers winning over shallower layers within a group.
("Left -> right, then top -> down". Last change wins)

The sort key is the depth of every group, starting from the LAST group. Ex:
for the schema above, and the context "Show: AVG/RND/RND_999, App: Nuke":

    base                           (User 0, Override 0, App 0, Show 0)
    Show=AVG                       (0, 0, 0, 1)
    Show=AVG,RND                   (0, 0, 0, 2)
    Show=AVG,RND,RND_999           (0, 0, 0, 3)
    App=Nuke                       (0, 0, 1, 0)
    Show=AVG+App=Nuke              (0, 0, 1, 1)
    Show=AVG,RND+App=Nuke          (0, 0, 1, 2)
    Show=AVG,RND,RND_999+App=Nuke  (0, 0, 1, 3)

The file for the selected context is always applied last, so what is shown in
the editor for a context is exactly what will be resolved for that context.
"""

import collections
import itertools
import os
import re

import yaml


class SchemaException(Exception):
    pass


# Characters which are not allowed in context values, as they are either
# reserved by the file naming convention, or not allowed in file names.
INVALID_VALUE_CHARACTERS = '=,+/\\:*?"<>|'
_INVALID_VALUE_REGEX = re.compile("[{}]".format(re.escape(INVALID_VALUE_CHARACTERS)))


def validate_value(value):
    """ Raises a SchemaException if the value can't be used as a context value. """
    if not isinstance(value, str):
        raise SchemaException("Context values must be strings. Received: {!r}".format(value))
    if not value or value != value.strip():
        raise SchemaException("Context values must not be empty or start/end with whitespace: {!r}".format(value))
    if value.startswith(".") or value.endswith("."):
        raise SchemaException("Context values must not start or end with '.': {!r}".format(value))
    if _INVALID_VALUE_REGEX.search(value):
        raise SchemaException("Context value {!r} contains one of the reserved characters: {}".format(
            value, INVALID_VALUE_CHARACTERS))


class Layer(object):
    def __init__(self, key, label=None):
        self.key = key
        self.label = label or key.replace("_", " ").title()

    def __repr__(self):
        return "Layer({})".format(self.key)


class Group(object):
    """ A flat chain of layers. Ex: Show -> Sequence -> Shot """

    def __init__(self, name, layers, color=None):
        validate_value(name)
        self.name = name
        self.layers = layers
        self.color = color

    @property
    def keys(self):
        return [layer.key for layer in self.layers]

    def __repr__(self):
        return "Group({}: {})".format(self.name, " -> ".join(self.keys))


class Schema(object):
    """ Describes the groups (And their layers) of a layered config. """

    def __init__(self, groups):
        self.groups = list(groups)

        names = [group.name for group in self.groups]
        if len(set(names)) != len(names):
            raise SchemaException("Group names must be unique: {}".format(names))

        keys = [layer.key for group in self.groups for layer in group.layers]
        if len(set(keys)) != len(keys):
            raise SchemaException("Layer keys must be unique across all groups: {}".format(keys))

        self._groups_by_name = collections.OrderedDict((group.name, group) for group in self.groups)

    @classmethod
    def from_dict(cls, data):
        groups = []
        for group_data in (data or {}).get("groups", []):
            layers = []
            for layer_data in group_data.get("layers", []):
                if isinstance(layer_data, dict):
                    layers.append(Layer(layer_data["key"], layer_data.get("label")))
                else:
                    layers.append(Layer(str(layer_data)))
            if not layers:
                raise SchemaException("Group '{}' has no layers.".format(group_data.get("name")))
            groups.append(Group(group_data["name"], layers, color=group_data.get("color")))
        return cls(groups)

    @classmethod
    def from_file(cls, path):
        with open(path, "r") as handle:
            return cls.from_dict(yaml.safe_load(handle))

    def to_dict(self):
        groups = []
        for group in self.groups:
            group_data = collections.OrderedDict()
            group_data["name"] = group.name
            group_data["layers"] = [
                layer.key if layer.label == Layer(layer.key).label else {"key": layer.key, "label": layer.label}
                for layer in group.layers
            ]
            if group.color:
                group_data["color"] = group.color
            groups.append(dict(group_data))
        return {"groups": groups}

    def group(self, name):
        try:
            return self._groups_by_name[name]
        except KeyError:
            raise SchemaException("Unknown group '{}'. Expected one of: {}".format(name, list(self._groups_by_name)))

    def base_context(self):
        return Context(self, {})

    def context(self, values=None, **kwargs):
        """ Creates a context from layer key -> value pairs. Ex:

            schema.context(SHOW="AVG", SEQUENCE="RND", APP="Nuke")

        Layers that are not set (or set to None/"") are not selected. Setting a
        layer without setting the layers before it in the group is an error.
        """
        values = dict(values or {}, **kwargs)
        known_keys = set(layer.key for group in self.groups for layer in group.layers)
        unknown = [key for key, value in values.items() if key not in known_keys and value]
        if unknown:
            raise SchemaException("Unknown context keys: {}".format(unknown))

        selections = {}
        for group in self.groups:
            selected = []
            missing = None
            for layer in group.layers:
                value = values.get(layer.key)
                if value in (None, ""):
                    missing = missing or layer.key
                    continue
                if missing:
                    raise SchemaException(
                        "'{}' can't be selected without selecting '{}'".format(layer.key, missing))
                selected.append(value)
            if selected:
                selections[group.name] = tuple(selected)
        return Context(self, selections)

    def context_from_environment(self, environ=None):
        """ Creates a context using environment variables named after each
        layer's key. Stops at the first unset layer in each group.
        """
        environ = os.environ if environ is None else environ
        values = {}
        for group in self.groups:
            for layer in group.layers:
                value = environ.get(layer.key)
                if not value:
                    break
                values[layer.key] = value
        return self.context(values)


class Context(object):
    """ An immutable selection of values for every group of a Schema.

    Args:
        schema (Schema): The schema this context belongs to.
        selections (dict): group name -> tuple of selected values. (In layer order)
    """

    def __init__(self, schema, selections):
        self.schema = schema
        normalized = collections.OrderedDict()
        for group in schema.groups:
            values = tuple(selections.get(group.name, ()) or ())
            if len(values) > len(group.layers):
                raise SchemaException("Group '{}' only has {} layers. Received: {}".format(
                    group.name, len(group.layers), values))
            for value in values:
                validate_value(value)
            if values:
                normalized[group.name] = values

        unknown = set(selections) - set(group.name for group in schema.groups)
        if unknown:
            raise SchemaException("Unknown groups: {}".format(sorted(unknown)))

        self._selections = normalized

    @property
    def selections(self):
        return collections.OrderedDict(self._selections)

    def selection(self, group_name):
        return self._selections.get(group_name, ())

    def depth(self, group_name):
        return len(self.selection(group_name))

    @property
    def is_base(self):
        return not self._selections

    def values(self):
        """ Returns the layer key -> value dict for this context. """
        values = collections.OrderedDict()
        for group in self.schema.groups:
            for layer, value in zip(group.layers, self.selection(group.name)):
                values[layer.key] = value
        return values

    def with_selection(self, group_name, values):
        selections = dict(self._selections)
        selections[group_name] = tuple(values or ())
        return Context(self.schema, selections)

    def sort_key(self):
        """ Key used to sort contexts into resolution order. (See module docs) """
        return tuple(self.depth(group.name) for group in reversed(self.schema.groups))

    def contains(self, other):
        """ Whether the other context applies when resolving this context. (Every
        one of the other context's selections is a prefix of ours)
        """
        for group in self.schema.groups:
            theirs = other.selection(group.name)
            if self.selection(group.name)[:len(theirs)] != theirs:
                return False
        return True

    def applicable_contexts(self):
        """ Returns every context which applies when resolving this context, in
        resolution order. Starts with the base context, ends with this context.
        """
        prefixes = []
        for group in self.schema.groups:
            selection = self.selection(group.name)
            prefixes.append([selection[:depth] for depth in range(len(selection) + 1)])

        contexts = []
        for combination in itertools.product(*prefixes):
            selections = {
                group.name: values for group, values in zip(self.schema.groups, combination) if values
            }
            contexts.append(Context(self.schema, selections))

        contexts.sort(key=lambda context: context.sort_key())
        return contexts

    def label(self):
        if self.is_base:
            return "Base"
        return " + ".join(
            "{}: {}".format(group, " / ".join(values)) for group, values in self._selections.items()
        )

    def __eq__(self, other):
        return isinstance(other, Context) and other._selections == self._selections

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(self._selections.items()))

    def __repr__(self):
        return "Context({})".format(self.label())
