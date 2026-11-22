# Layered (context based) configs

Layered configs let a small config file change part of a larger one, for any
combination of contexts. Ex: remove the burnin from the dailies quicktime for
one shot, and remove the slate for every Nuke user.

## Set up

A layered config is a single directory (Typically somewhere central, such as
`/pipeline/wolfkrow_config`). It contains a schema, a base config, and one file
per context that has changes.

```
wolfkrow_schema.yml
base.wolfkrow.yml
App=Nuke.wolfkrow.yml
Show=AVG,RND,RND_999.wolfkrow.yml
Show=AVG,RND,RND_999+App=Nuke.wolfkrow.yml
User=jacob.wolfkrow.yml
```

Point Wolfkrow at it with the `WOLFKROW_CONFIG_ROOT` environment variable, or
pass `config_root` to the `Loader`.

### The schema

`wolfkrow_schema.yml` defines the groups, and the layers of each group.

```yaml
groups:
  - name: Show
    layers: [SHOW, SEQUENCE, SHOT]
  - name: App
    layers: [APP, STEP]
  - name: Override
    layers: [OVERRIDE]
  - name: User
    layers: [USER]
```

* You can define as many groups as you want, each with as many layers as you want.
* A layer can only be selected when all the layers before it (In the same
  group) are selected. A Shot requires a Sequence.
* Layer keys double as environment variable names. When no context is given to
  the `Loader`, the context is read from the environment. (`$SHOW`, `$APP`, etc...)

### Contexts

A context is a selection of layers from every group. Ex: `Show: AVG / RND / RND_999`
and `App: Nuke`. Every combination has its own config file, and the file name is
the identifier of the context it belongs to:

* Groups are written in schema order, separated by `+`.
* Each group is written as `<Group>=<value>,<value>,...` in layer order.
* The characters `= , + / \ : * ? " < > |` are not allowed in context values.

Use a wildcard to find every file for something. Ex: `ls *App=Nuke*`

### Resolution order

Every file whose selections are equal to, or a prefix of, the selected context
is applied. Later groups always win over earlier groups, and deeper layers win
over shallower layers within a group. (Left -> right, then top -> down. Last
change wins.) For `Show: AVG / RND / RND_999, App: Nuke`:

```
base.wolfkrow.yml
Show=AVG.wolfkrow.yml
Show=AVG,RND.wolfkrow.yml
Show=AVG,RND,RND_999.wolfkrow.yml
App=Nuke.wolfkrow.yml
Show=AVG+App=Nuke.wolfkrow.yml
Show=AVG,RND+App=Nuke.wolfkrow.yml
Show=AVG,RND,RND_999+App=Nuke.wolfkrow.yml
```

The file for the selected context is always applied last, so what the Wolfkrow
Editor shows for a context is exactly what is resolved for that context.

## What is stored in each file

The base config is a normal wolfkrow.yml file. Every other file only stores what
it changes, and every change keeps the value it was made against (`$original`)
next to the new value (`$updated`):

```yaml
tasks:
  dailies_quicktime:
    scripts:
      $original: [slate.nk, burnin.nk, reformat.nk]
      $updated: [slate.nk, reformat.nk]
    file_type:
      $original: exr
      $updated: mov
  old_task:
    $original: {task_type: FileCopy, ...}
    $removed: true
  new_task:
    $updated: {task_type: FileCopy, ...}
```

Storing the original value allows the *intent* of the change to be re-applied
when the inherited value changes. If the base later adds `lut.nk` to the scripts
list, the change above still only removes `burnin.nk`. This is the same idea as
a git three-way merge, except that there are never conflicts: the layer being
applied always wins. Instead, these situations are reported (And shown in the
Wolfkrow Editor) so they can be reviewed:

* **outdated**: The inherited value changed since the change was made.
* **redundant**: The inherited value now matches the change.
* **orphaned**: The change refers to something that no longer exists.

List items are matched by identity rather than position: strings and numbers by
their value, named nuke snippets (`{burnin: {...}}`) by their name, and dicts
with a `name` key by that name.

Files can also be written by hand using plain values. A plain dict is merged
into the inherited dict, any other plain value replaces the inherited value.

> **Note:** Layered configs merge tasks key by key. The legacy
> `WOLFKROW_CONFIG_SEARCH_PATHS` configs still replace whole tasks.

## Version control (Recommended)

Wolfkrow does not require version control, but we recommend keeping the config
root in a git repository:

* History and blame for every context file.
* Easy rollbacks of bad config changes.
* Safe concurrent editing by multiple TDs. As each file only stores a few small
  changes, git's line based merging works well on them.

A simple policy that works well is to commit after every save from the Wolfkrow
Editor, and to review changes to `base.wolfkrow.yml` before they are pushed.
