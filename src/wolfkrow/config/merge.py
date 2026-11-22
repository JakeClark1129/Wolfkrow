""" Three-way merge logic for layered wolfkrow configs.

Every config file above the base config only stores the parts of the config it
changes. Each change is stored as a "change record" which keeps the value the
change was made against right next to the new value:

    tasks:
      dailies_quicktime:
        scripts:
          $original: [slate.nk, burnin.nk, reformat.nk]
          $updated: [slate.nk, reformat.nk]
        file_type:
          $original: exr
          $updated: mov
      old_task:
        $original: {...}
        $removed: true

Storing the original value allows the *intent* of a change to be re-applied to
an inherited value that has since been changed by a lower layer. This is the
same idea as a git three-way merge, where:

    original  == the merge base (What the change was made against)
    updated   == "ours"         (The change made in this layer)
    inherited == "theirs"       (What the lower layers currently resolve to)

For example, if the base config later adds a "lut.nk" snippet to the scripts
list, the record above still only removes "burnin.nk", resulting in
[slate.nk, reformat.nk, lut.nk].

Unlike git, a conflict never stops the resolve: the layer being applied always
wins ("Last change wins"). Instead, every situation where the inherited value
has changed since the record was made is reported as a MergeNote, so that the
Wolfkrow Editor can flag it for review.

Plain values (Without $original/$updated) are also supported, which keeps the
files easy to write by hand:
  - A plain dict is deep merged into the inherited dict.
  - Any other plain value replaces the inherited value.

List items are matched by identity, not position. See `item_identity`.
"""

import copy
import json


ORIGINAL = "$original"
UPDATED = "$updated"
REMOVED = "$removed"
RECORD_KEYS = frozenset([ORIGINAL, UPDATED, REMOVED])


class _Missing(object):
    """ Sentinel for a value that does not exist. (As opposed to a None value) """
    def __repr__(self):
        return "MISSING"

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __deepcopy__(self, memo):
        return self


MISSING = _Missing()


class NoteKind(object):
    # The inherited value changed since this change was made. The change was
    # still applied, but might no longer be what the user intended.
    OUTDATED = "outdated"
    # The inherited value now matches the change. The change is redundant and
    # could be removed.
    REDUNDANT = "redundant"
    # The change refers to something that no longer exists in the inherited
    # value. (Ex: Removing a list item that is no longer there)
    ORPHANED = "orphaned"


class MergeNote(object):
    """ Something about a merge that a user may need to review. """

    def __init__(self, kind, path, layer, message):
        self.kind = kind
        self.path = tuple(path)
        self.layer = layer
        self.message = message

    def __repr__(self):
        return "MergeNote({}, {}, {}: {})".format(self.kind, "/".join(self.path), self.layer, self.message)


class MergeReport(object):
    """ Tracks where every value in a resolved config came from.

    Paths are tuples of path elements. Dict keys are used as-is. List items are
    represented as "[identity]". (See `item_path_element`)

    Attributes:
        provenance (dict): path -> layer that last set the value at that path.
        removed (dict): path -> {"value": removed value, "layer": layer}
            Values (dict keys or list items) removed by a layer above the base.
            Used by the editor to display removed values so they can be restored.
        notes (list[MergeNote]): Things that might need reviewing.
    """

    def __init__(self):
        self.provenance = {}
        self.removed = {}
        self.notes = []

    def set(self, path, layer):
        """ Marks a value (and everything under it) as being set by the layer. """
        self.clear(path)
        self.provenance[tuple(path)] = layer

    def clear(self, path):
        """ Clears all provenance and removal info at and below the path. """
        path = tuple(path)
        length = len(path)
        for store in (self.provenance, self.removed):
            for key in [key for key in store if key[:length] == path]:
                del store[key]

    def remove(self, path, value, layer):
        self.clear(path)
        self.removed[tuple(path)] = {"value": value, "layer": layer}

    def restore(self, path):
        self.removed.pop(tuple(path), None)

    def note(self, kind, path, layer, message):
        self.notes.append(MergeNote(kind, path, layer, message))

    def layer_for(self, path):
        """ Returns the layer which set the value at the path. Takes parent
        paths into account. (Ex: A layer that replaced a whole dict also set all
        of the dicts values)
        """
        path = tuple(path)
        for length in range(len(path), -1, -1):
            layer = self.provenance.get(path[:length])
            if layer is not None:
                return layer
        return None

    def layers_below(self, path):
        """ Returns all the layers which changed something at, or under, the path. """
        path = tuple(path)
        length = len(path)
        layers = set()
        for key, layer in self.provenance.items():
            if key[:length] == path:
                layers.add(layer)
        return layers


class _NullReport(MergeReport):
    """ A report which discards everything. Used for internal comparisons. """

    def set(self, path, layer):
        pass

    def clear(self, path):
        pass

    def remove(self, path, value, layer):
        pass

    def restore(self, path):
        pass

    def note(self, kind, path, layer, message):
        pass


# ============= #
# Identity      #
# ============= #
def item_identity(item):
    """ Returns the identity of a list item. Used to match list items between
    the original, updated and inherited versions of a list.

    - Strings, numbers, and other simple values are their own identity.
    - A dict with a single key (Ex: a named nuke snippet {"burnin": {...}}) is
        identified by that key.
    - A dict with a "name" key is identified by that name.
    - Anything else is identified by its contents.
    """
    if isinstance(item, dict):
        if len(item) == 1:
            return "{}".format(next(iter(item)))
        if "name" in item and isinstance(item["name"], (str, int, float)):
            return "{}".format(item["name"])
    elif isinstance(item, (str, int, float, bool)) or item is None:
        return "{}".format(item)

    try:
        return json.dumps(item, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return repr(item)


def item_path_element(item):
    return "[{}]".format(item_identity(item))


def _identities(items):
    """ Returns the list of identities, or None if they are not unique. """
    ids = [item_identity(item) for item in items]
    if len(set(ids)) != len(ids):
        return None
    return ids


# ============= #
# Records       #
# ============= #
def is_record(node):
    """ Whether the node is a change record. """
    if not isinstance(node, dict) or not node:
        return False
    keys = set(node.keys())
    if not keys.issubset(RECORD_KEYS):
        return False
    return UPDATED in keys or node.get(REMOVED) is True


def make_change(original, updated):
    """ Creates a change record. Either value may be MISSING. """
    if updated is MISSING:
        record = {REMOVED: True}
        if original is not MISSING:
            record = {ORIGINAL: copy.deepcopy(original), REMOVED: True}
        return record

    record = {}
    if original is not MISSING:
        record[ORIGINAL] = copy.deepcopy(original)
    record[UPDATED] = copy.deepcopy(updated)
    return record


# ============= #
# Apply         #
# ============= #
def apply_patch(inherited, patch, layer=None, report=None, path=()):
    """ Applies a layer's patch to the inherited value.

    Args:
        inherited (any): The value resolved from all lower layers. May be MISSING.
        patch (any): The layer's patch. (Plain values, plain dicts, or change records)
        layer (str): Identifier of the layer being applied. Used for provenance.
        report (MergeReport): Report to record provenance and notes into.
        path (tuple): Path of the inherited value within the config.

    Returns:
        The merged value. Or MISSING if the value was removed.
    """
    if report is None:
        report = _NullReport()

    if is_record(patch):
        return _apply_record(inherited, patch, layer, report, tuple(path))

    if isinstance(patch, dict):
        if isinstance(inherited, dict):
            result = copy.copy(inherited)
        else:
            if inherited is not MISSING and inherited is not None:
                report.note(NoteKind.OUTDATED, path, layer,
                    "Expected a dictionary to merge into, but found {!r}. It was replaced.".format(inherited))
            result = {}
            report.set(path, layer)

        for key, value in patch.items():
            key_path = tuple(path) + (key,)
            merged = apply_patch(result.get(key, MISSING), value, layer, report, key_path)
            if merged is MISSING:
                result.pop(key, None)
            else:
                result[key] = merged
        return result

    # Plain values replace the inherited value.
    report.set(path, layer)
    return copy.deepcopy(patch)


def _apply_record(inherited, record, layer, report, path):
    original = record.get(ORIGINAL, MISSING)
    has_original = ORIGINAL in record

    # Removal.
    if record.get(REMOVED) is True and UPDATED not in record:
        if inherited is MISSING:
            report.note(NoteKind.ORPHANED, path, layer, "Removes a value which no longer exists.")
            return MISSING
        if has_original and inherited != original:
            report.note(NoteKind.OUTDATED, path, layer,
                "The removed value has changed since it was removed. (Was {!r}, now {!r})".format(original, inherited))
        report.remove(path, copy.deepcopy(inherited), layer)
        return MISSING

    updated = record[UPDATED]

    # Without an original value, there is nothing to merge against. The
    # updated value is used as-is.
    if not has_original:
        if inherited is not MISSING and inherited == updated:
            report.note(NoteKind.REDUNDANT, path, layer, "The inherited value already matches this change.")
        report.restore(path)
        report.set(path, layer)
        return copy.deepcopy(updated)

    if inherited is MISSING:
        if original is not MISSING:
            report.note(NoteKind.OUTDATED, path, layer,
                "This changed {!r}, which is no longer inherited. Applied anyway.".format(original))
        report.restore(path)
        report.set(path, layer)
        return copy.deepcopy(updated)

    # The inherited value hasn't changed since the change was made. (Fast path)
    if inherited == original:
        if isinstance(original, list) and isinstance(updated, list):
            return _merge_lists(original, updated, inherited, layer, report, path)
        if isinstance(original, dict) and isinstance(updated, dict):
            return apply_patch(inherited, diff(original, updated), layer, report, path)
        report.set(path, layer)
        return copy.deepcopy(updated)

    # The inherited value has changed. Re-apply the intent of the change.
    if isinstance(original, list) and isinstance(updated, list) and isinstance(inherited, list):
        return _merge_lists(original, updated, inherited, layer, report, path)

    if isinstance(original, dict) and isinstance(updated, dict) and isinstance(inherited, dict):
        return apply_patch(inherited, diff(original, updated), layer, report, path)

    if inherited == updated:
        report.note(NoteKind.REDUNDANT, path, layer, "The inherited value already matches this change.")
    else:
        report.note(NoteKind.OUTDATED, path, layer,
            "The inherited value changed from {!r} to {!r} since this change was made.".format(original, inherited))
    report.set(path, layer)
    return copy.deepcopy(updated)


def _merge_lists(original, updated, inherited, layer, report, path):
    """ Re-applies the change original -> updated onto the inherited list.
    List items are matched by identity. (See item_identity)
    """
    original_ids = _identities(original)
    updated_ids = _identities(updated)
    inherited_ids = _identities(inherited)

    # Items can't be matched reliably. Fall back to replacing the whole list.
    if original_ids is None or updated_ids is None or inherited_ids is None:
        if inherited != original:
            report.note(NoteKind.OUTDATED, path, layer,
                "The inherited list changed since this change was made, and could "
                "not be merged because it contains duplicate items. It was replaced.")
        report.set(path, layer)
        return copy.deepcopy(updated)

    original_lookup = dict(zip(original_ids, original))
    updated_lookup = dict(zip(updated_ids, updated))

    original_set = set(original_ids)
    updated_set = set(updated_ids)

    result = [copy.deepcopy(item) for item in inherited]
    result_ids = list(inherited_ids)

    def index_of(identity):
        try:
            return result_ids.index(identity)
        except ValueError:
            return None

    # 1. Removals
    for identity in original_ids:
        if identity in updated_set:
            continue
        index = index_of(identity)
        item_path = path + ("[{}]".format(identity),)
        if index is None:
            report.note(NoteKind.ORPHANED, item_path, layer, "Removes an item which is no longer inherited.")
            continue
        if result[index] != original_lookup[identity]:
            report.note(NoteKind.OUTDATED, item_path, layer, "The removed item has changed since it was removed.")
        report.remove(item_path, result[index], layer)
        del result[index]
        del result_ids[index]

    # 2. Modified items.
    for identity in updated_ids:
        if identity not in original_set or original_lookup[identity] == updated_lookup[identity]:
            continue
        index = index_of(identity)
        item_path = path + ("[{}]".format(identity),)
        if index is None:
            report.note(NoteKind.ORPHANED, item_path, layer, "Changes an item which is no longer inherited.")
            continue
        merged = _apply_record(
            result[index],
            make_change(original_lookup[identity], updated_lookup[identity]),
            layer, report, item_path,
        )
        result[index] = merged

    # 3. Re-ordering of the items which exist in both the original and updated lists.
    original_common = [identity for identity in original_ids if identity in updated_set]
    updated_common = [identity for identity in updated_ids if identity in original_set]
    if original_common != updated_common:
        present = [identity for identity in updated_common if identity in result_ids]
        slots = sorted(result_ids.index(identity) for identity in present)
        items = dict(zip(result_ids, result))
        for slot, identity in zip(slots, present):
            result[slot] = items[identity]
            result_ids[slot] = identity
        report.set(path + ("$order",), layer)

    # 4. Additions. Inserted relative to their neighbours in the updated list.
    for position, identity in enumerate(updated_ids):
        if identity in original_set:
            continue

        item = copy.deepcopy(updated_lookup[identity])
        item_path = path + ("[{}]".format(identity),)

        existing = index_of(identity)
        if existing is not None:
            if result[existing] == item:
                report.note(NoteKind.REDUNDANT, item_path, layer, "The inherited list already contains this item.")
            else:
                report.note(NoteKind.OUTDATED, item_path, layer, "The inherited list already contains a different version of this item. It was replaced.")
                result[existing] = item
            report.restore(item_path)
            report.set(item_path, layer)
            continue

        insert_at = None
        # Insert after the closest previous neighbour that still exists.
        for previous in reversed(updated_ids[:position]):
            index = index_of(previous)
            if index is not None:
                insert_at = index + 1
                break
        else:
            if position == 0:
                insert_at = 0

        # Otherwise, before the closest next neighbour.
        if insert_at is None:
            for following in updated_ids[position + 1:]:
                index = index_of(following)
                if index is not None:
                    insert_at = index
                    break

        if insert_at is None:
            insert_at = len(result)
            if updated_ids[:position]:
                report.note(NoteKind.OUTDATED, item_path, layer,
                    "The items this was added next to no longer exist. It was added to the end.")

        result.insert(insert_at, item)
        result_ids.insert(insert_at, identity)
        report.restore(item_path)
        report.set(item_path, layer)

    return result


# ============= #
# Diff          #
# ============= #
def diff(inherited, edited, previous=MISSING):
    """ Creates the patch which turns the inherited value into the edited value.

    Args:
        inherited (any): The value resolved from all lower layers. May be MISSING.
        edited (any): The value after the user's edits. May be MISSING.
        previous (any): The layer's existing patch. Parts of the existing patch
            which still produce the edited value are kept as they are, so their
            original values (and any outdated notes) are preserved, rather than
            silently re-recorded against the new inherited value.

    Returns:
        The patch. Or MISSING if there are no changes.
    """
    if previous is not MISSING:
        if apply_patch(inherited, previous) == edited:
            return copy.deepcopy(previous)

    if inherited == edited:
        return MISSING

    if isinstance(inherited, dict) and isinstance(edited, dict):
        previous_children = previous if (isinstance(previous, dict) and not is_record(previous)) else {}
        patch = {}
        keys = list(edited.keys()) + [key for key in inherited.keys() if key not in edited]
        for key in keys:
            child = diff(
                inherited.get(key, MISSING),
                edited.get(key, MISSING),
                previous_children.get(key, MISSING),
            )
            if child is not MISSING:
                patch[key] = child
        return patch or MISSING

    return make_change(inherited, edited)


def strip_records(patch):
    """ Converts a patch to plain values. (Useful for displaying a layer on its own) """
    if is_record(patch):
        return MISSING if UPDATED not in patch else copy.deepcopy(patch[UPDATED])
    if isinstance(patch, dict):
        result = {}
        for key, value in patch.items():
            value = strip_records(value)
            if value is not MISSING:
                result[key] = value
        return result
    return copy.deepcopy(patch)
