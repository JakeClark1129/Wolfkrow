""" Input/Output connection logic for TaskAttributes.

A TaskAttribute can be flagged as an INPUT, an OUTPUT, or BOTH via its `io`
argument. Connectable attributes also declare a list of `types`, ordered from
the most generic to the most specific. Ex:

    input_start_frame = TaskAttribute(
        attribute_type=int,
        io=IO.INPUT,
        types=["int", "frame_number", "start_frame"],
    )

An output can be connected to an input when they share at least one type. The
more specific the shared type is (from the input's point of view), the better
the match. This allows the node editor to highlight every input an output *can*
be connected to, while emphasizing the inputs it *should* be connected to.

Connections are stored in the wolfkrow.yml files as regular TaskAttribute values
using an IO token:

    input_task:
        source: IO<upstream_task:destination>

Because a connection is just an attribute value, it is inherited, overridden and
diffed exactly like every other value in the config.

This module has no dependency on any other part of Wolfkrow, so it can be used
by external tools (Such as the Wolfkrow Editor) without side effects.
"""

import re


class IO(object):
    """ Bit flags describing the direction of a TaskAttribute's connection. """
    NONE = 0
    INPUT = 1
    OUTPUT = 1 << 1
    BOTH = INPUT | OUTPUT

    @classmethod
    def to_list(cls, flags):
        names = []
        if flags & cls.INPUT:
            names.append("input")
        if flags & cls.OUTPUT:
            names.append("output")
        return names


# A full value connection token. Ex: IO<task_name:attribute_name>
IO_TOKEN_REGEX = re.compile(r"^\s*IO<\s*([^:<>]+?)\s*:\s*([^:<>]+?)\s*>\s*$")


def parse_io_token(value):
    """ Parses an IO<task:attribute> token.

    Args:
        value (any): The (unresolved) TaskAttribute value.

    Returns:
        tuple(str, str) | None: (task_name, attribute_name) if the value is a
            connection token, otherwise None.
    """
    if not isinstance(value, str):
        return None

    match = IO_TOKEN_REGEX.match(value)
    if match is None:
        return None

    return match.group(1), match.group(2)


def make_io_token(task_name, attribute_name):
    """ Builds an IO<task:attribute> connection token. """
    return "IO<{}:{}>".format(task_name, attribute_name)


def is_io_token(value):
    return parse_io_token(value) is not None


def match_score(output_types, input_types):
    """ Scores how well an output matches an input.

    The score is based on the most specific type that the two share, measured
    from the input's perspective (Since the input is the one that knows what it
    needs).

    Args:
        output_types (list[str]): The types of the output attribute.
        input_types (list[str]): The types of the input attribute.

    Returns:
        int: 0 if the attributes are incompatible. Otherwise 1..len(input_types)
            where len(input_types) means the input's most specific type is
            satisfied (An "exact" match).
    """
    if not output_types or not input_types:
        return 0

    output_types = set(output_types)
    score = 0
    for index, input_type in enumerate(input_types):
        if input_type in output_types:
            score = index + 1
    return score


def is_exact_match(output_types, input_types):
    return bool(input_types) and match_score(output_types, input_types) == len(input_types)


def _name_tokens(name):
    return set(token for token in name.lower().split("_") if token)


def _tie_break_key(output_name, output_types, input_name, input_types):
    """ Secondary ranking used when multiple outputs score the same. """
    output_set = set(output_types)
    input_set = set(input_types)
    shared = len(output_set & input_set)
    unshared = len(output_set - input_set)
    same_name = 1 if output_name == input_name else 0
    shared_name_tokens = len(_name_tokens(output_name) & _name_tokens(input_name))
    return (same_name, shared, -unshared, shared_name_tokens)


def connect_all(outputs, inputs, existing_connections=None):
    """ Calculates the connections for a "Connect All" operation.

    Every input picks the single best output for it. Only "exact" matches (Where
    the input's most specific type is satisfied) are considered. If two or more
    outputs are equally good, the input is reported as ambiguous and left
    unconnected rather than guessing.

    Args:
        outputs (dict[str, list[str]]): output attribute name -> types
        inputs (dict[str, list[str]]): input attribute name -> types
        existing_connections (iterable[str]): Input attribute names that are
            already connected, and should not be touched.

    Returns:
        tuple(list[tuple[str, str]], list[str]): ([(output_name, input_name)], [ambiguous input names])
    """
    existing_connections = set(existing_connections or [])
    connections = []
    ambiguous = []

    for input_name, input_types in inputs.items():
        if input_name in existing_connections:
            continue

        candidates = []
        for output_name, output_types in outputs.items():
            if is_exact_match(output_types, input_types):
                key = _tie_break_key(output_name, output_types, input_name, input_types)
                candidates.append((key, output_name))

        if not candidates:
            continue

        candidates.sort(key=lambda candidate: candidate[0], reverse=True)
        if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
            ambiguous.append(input_name)
            continue

        connections.append((candidates[0][1], input_name))

    return connections, ambiguous


# =========================== #
# Common type definitions.    #
# =========================== #
# These are only conveniences to keep the built-in Tasks consistent. Custom tasks
# are free to invent their own types.
class Types(object):
    INT = ["int"]
    FRAME = ["int", "frame_number"]
    START_FRAME = ["int", "frame_number", "start_frame"]
    END_FRAME = ["int", "frame_number", "end_frame"]

    PATH = ["str", "path"]
    FILE = ["str", "path", "file"]
    DIRECTORY = ["str", "path", "directory"]
    IMAGE_SEQUENCE = ["str", "path", "file", "image_sequence"]
    MOVIE = ["str", "path", "file", "movie"]
    NUKE_SCRIPT = ["str", "path", "nuke_script"]

    SG_ENTITY_TYPE = ["str", "sg_entity_type"]
    SG_ID = ["int", "sg_id"]
