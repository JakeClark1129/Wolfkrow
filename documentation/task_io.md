# Task Inputs and Outputs

TaskAttributes can be flagged as inputs and/or outputs. These are what get
connected together in the Wolfkrow Editor.

```python
from wolfkrow.core.connections import IO, Types

class MyTask(Task):
    source = TaskAttribute(attribute_type=str, io=IO.INPUT, types=Types.FILE)
    input_start_frame = TaskAttribute(attribute_type=int, io=IO.INPUT,
        types=["int", "frame_number", "start_frame"])
    destination = TaskAttribute(attribute_type=str, io=IO.OUTPUT, types=Types.FILE)
```

## Types

`types` is ordered from the most generic to the most specific. The first type is
usually a primitive (`int`, `str`).

* An output can be connected to an input when they share a type other than the
  primitive. (Every string isn't compatible with every other string.) An input
  whose only type is the primitive (Ex: `["int"]`) accepts anything of that type.
* The more specific the shared type is, the better the match. When the input's
  most specific type is shared, it is an exact match.
* While dragging a connection in the editor, compatible inputs are highlighted,
  exact matches are emphasized, and everything else is dimmed.
* "Connect all" only connects exact matches, and skips any input with more than
  one equally good output.

The `Types` class contains the types used by the built-in tasks. Custom tasks
are free to invent their own types.

## Connections

Connections are stored as values using an IO token:

```yaml
tasks:
  render:
    task_type: NukeRender
    destination: /renders/shot.%04d.exr
  copy:
    task_type: FileCopy
    source: IO<render:destination>
    start_frame: IO<render:render_start_frame>
```

* A connection makes the task depend on the upstream task automatically.
* Values are resolved during export: the input receives the upstream task's
  output value after the upstream task has been validated.
* After running, each task writes its output values to its own
  `<time>_<job>_<task>.outputs.json` in the temp directory. When a task starts,
  it reads the outputs files of the tasks it is connected to. If a value there
  differs from the export time value, the runtime value is used, and a warning
  is printed. This allows outputs which are only known at runtime (Ex: the id of
  a created SG entity) to be passed on.

## Other UI attributes

* `display_in_ui`: Whether the attribute is shown on the node in the Wolfkrow Editor.
* `ui_widget`: Hint for the editor widget. One of `line`, `multiline`, `int`,
  `float`, `bool`, `options`, `list`, `dict`, `path`. Defaults based on the
  attribute_type.
* `ui_position` (On every Task): The node's position in the editor. It is
  stored in the config like any other attribute, so it is inherited and
  overridden like everything else.

`wolfkrow_describe_tasks` prints a JSON description of every task type. This is
what the Wolfkrow Editor uses to build its nodes.
