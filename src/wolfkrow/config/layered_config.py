""" Layered (context based) wolfkrow configs.

See schema.py for how contexts are resolved, naming.py for how the config files
are named, and merge.py for how each layer's changes are stored and applied.

Example:

    layered = LayeredConfig("/pipeline/wolfkrow_config")
    context = layered.schema.context(SHOW="AVG", SEQUENCE="RND", SHOT="RND_999", APP="Nuke")

    resolution = layered.resolve(context)
    resolution.config           # The fully resolved config dictionary.
    resolution.report           # Where every value came from. (See MergeReport)

    # Save edits for exactly this context. Only the differences to what is
    # inherited from the lower layers are written to the context's file.
    layered.save(context, edited_config)

    # Build a Loader to create TaskGraphs from the resolved config.
    loader = layered.create_loader(context, replacements={...})
"""

import collections
import copy
import os

import yaml

from . import merge, naming
from .schema import Schema, SchemaException


class LayeredConfigException(Exception):
    pass


class Resolution(object):
    """ The result of resolving a context.

    Attributes:
        context (Context): The context that was resolved.
        config (dict): The resolved config.
        report (merge.MergeReport): Provenance, removed values and notes. Layers
            are identified by their file name.
        layers (list[Context]): Contexts of the config files that were applied,
            in order. (Only those which exist)
        paths (list[str]): The paths of the config files that were applied.
    """

    def __init__(self, context, config, report, layers, paths):
        self.context = context
        self.config = config
        self.report = report
        self.layers = layers
        self.paths = paths


def _dump_yaml(data, handle):
    class _Dumper(yaml.SafeDumper):
        pass

    def _represent_ordered_dict(dumper, value):
        return dumper.represent_dict(value.items())

    _Dumper.add_representer(collections.OrderedDict, _represent_ordered_dict)
    yaml.dump(data, handle, Dumper=_Dumper, default_flow_style=False, sort_keys=False, allow_unicode=True)


class LayeredConfig(object):
    """ A directory of layered wolfkrow config files. """

    def __init__(self, root, schema=None):
        self.root = os.path.abspath(os.path.expandvars(os.path.expanduser(root)))

        if schema is None:
            schema_path = os.path.join(self.root, naming.SCHEMA_FILE_NAME)
            if not os.path.isfile(schema_path):
                raise LayeredConfigException("No schema file found at '{}'".format(schema_path))
            schema = Schema.from_file(schema_path)
        self.schema = schema

        self._cache = {}

    @classmethod
    def create(cls, root, schema, base_config=None):
        """ Creates a new layered config directory. """
        if not os.path.isdir(root):
            os.makedirs(root)
        schema_path = os.path.join(root, naming.SCHEMA_FILE_NAME)
        if os.path.exists(schema_path):
            raise LayeredConfigException("A layered config already exists at '{}'".format(root))
        with open(schema_path, "w") as handle:
            _dump_yaml(schema.to_dict(), handle)

        layered = cls(root)
        layered.save(layered.schema.base_context(), base_config or {})
        return layered

    # ============ #
    # Files        #
    # ============ #
    def path_for(self, context):
        return os.path.join(self.root, naming.file_name(context))

    def exists(self, context):
        return os.path.isfile(self.path_for(context))

    def load_layer(self, context):
        """ Returns the raw contents (The patch) of a context's config file. """
        path = self.path_for(context)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            self._cache.pop(path, None)
            return {}

        cached = self._cache.get(path)
        if cached is None or cached[0] != mtime:
            with open(path, "r") as handle:
                data = yaml.safe_load(handle) or {}
            if not isinstance(data, dict):
                raise LayeredConfigException("Config file '{}' must contain a dictionary.".format(path))
            self._cache[path] = (mtime, data)
            cached = self._cache[path]

        return copy.deepcopy(cached[1])

    def existing_contexts(self):
        """ Returns the contexts of every config file in the root, plus any
        files that could not be parsed as (file_name, error) tuples.
        """
        contexts = []
        errors = []
        for name in sorted(os.listdir(self.root)):
            if not name.endswith(naming.SUFFIX):
                continue
            try:
                context = naming.parse_file_name(self.schema, name)
            except SchemaException as error:
                errors.append((name, str(error)))
                continue
            if context is not None:
                contexts.append(context)
        return contexts, errors

    def known_values(self, group_name, parent_values=()):
        """ Returns the values already used for the next layer of a group, given
        the values selected for the previous layers. Used to populate the
        context selector.
        """
        parent_values = tuple(parent_values)
        depth = len(parent_values)
        values = set()
        contexts, _ = self.existing_contexts()
        for context in contexts:
            selection = context.selection(group_name)
            if len(selection) > depth and selection[:depth] == parent_values:
                values.add(selection[depth])
        return sorted(values)

    # ============ #
    # Resolving    #
    # ============ #
    def resolve(self, context, include_self=True):
        """ Resolves the config for the context.

        Args:
            context (Context): The context to resolve.
            include_self (bool): Whether to apply the context's own file. When
                False, the result is what the context *inherits*.
        """
        report = merge.MergeReport()
        config = {}
        layers = []
        paths = []

        for layer_context in context.applicable_contexts():
            if not include_self and layer_context == context:
                continue
            if not self.exists(layer_context):
                continue

            layer_id = naming.file_name(layer_context)
            patch = self.load_layer(layer_context)
            config = merge.apply_patch(config, patch, layer=layer_id, report=report)
            layers.append(layer_context)
            paths.append(self.path_for(layer_context))

        if config is merge.MISSING:
            config = {}

        return Resolution(context, config, report, layers, paths)

    # ============ #
    # Saving       #
    # ============ #
    def make_patch(self, context, edited_config):
        """ Calculates the patch to store for the context, so that it resolves to
        the edited config.
        """
        if context.is_base:
            return copy.deepcopy(edited_config)

        inherited = self.resolve(context, include_self=False).config
        previous = self.load_layer(context) if self.exists(context) else merge.MISSING
        patch = merge.diff(inherited, edited_config, previous=previous)
        if patch is merge.MISSING:
            return {}
        return patch

    def save(self, context, edited_config):
        """ Saves the edited config for the context. Only the differences to the
        inherited config are written. If there are no differences, the context's
        file is removed. (The base file is always kept)

        Returns:
            str | None: The path written to, or None if the file was removed.
        """
        patch = self.make_patch(context, edited_config)
        path = self.path_for(context)

        if not patch and not context.is_base:
            if os.path.isfile(path):
                os.remove(path)
            self._cache.pop(path, None)
            return None

        self.write_layer(context, patch)
        return path

    def write_layer(self, context, patch):
        """ Writes the raw patch for a context to its file. """
        path = self.path_for(context)
        temp_path = path + ".tmp"
        with open(temp_path, "w") as handle:
            handle.write("# Wolfkrow config: {}\n".format(context.label()))
            if not context.is_base:
                handle.write(
                    "# Only changes to the inherited config are stored here. Each change\n"
                    "# keeps the value it was made against ($original) next to the new\n"
                    "# value ($updated), so it can be re-applied if the inherited value changes.\n"
                )
            handle.write("\n")
            _dump_yaml(patch, handle)
        os.replace(temp_path, path)
        self._cache.pop(path, None)
        return path

    # ============ #
    # Wolfkrow     #
    # ============ #
    def create_loader(self, context, replacements=None, sgtk=None, temp_dir=None):
        """ Creates a Loader for the resolved config of the context. """
        from wolfkrow.builder.workflow_builder import Loader
        return Loader(
            config_root=self.root,
            config_context=context.values(),
            replacements=replacements,
            sgtk=sgtk,
            temp_dir=temp_dir,
        )
