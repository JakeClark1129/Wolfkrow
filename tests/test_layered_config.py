""" Tests for layered (context based) wolfkrow configs. """
import copy
import os
import shutil
import tempfile
import unittest

import yaml

from wolfkrow.config import LayeredConfig, Schema, SchemaException, merge, naming
from wolfkrow.config.merge import MISSING, NoteKind, ORIGINAL, UPDATED, REMOVED

SCHEMA = {
    "groups": [
        {"name": "Show", "layers": ["SHOW", "SEQUENCE", "SHOT"]},
        {"name": "App", "layers": ["APP", "STEP"]},
        {"name": "Override", "layers": ["OVERRIDE"]},
        {"name": "User", "layers": ["USER"]},
    ]
}

BASE_CONFIG = {
    "replacements": {"show_root": "/shows"},
    "tasks": {
        "dailies_quicktime": {
            "task_type": "NukeRender",
            "source": "{input_path}",
            "destination": "{publish_path}",
            "file_type": "mov",
            "scripts": ["slate.nk", "burnin.nk", "reformat.nk"],
        },
        "copy_to_publish": {
            "task_type": "FileCopy",
            "source": "{input_path}",
            "destination": "{publish_path}",
        },
    },
    "workflows": {
        "dailies": ["copy_to_publish", "dailies_quicktime"],
    },
}


class TestSchema(unittest.TestCase):

    def setUp(self):
        self.schema = Schema.from_dict(SCHEMA)

    def test_context_requires_previous_layers(self):
        with self.assertRaises(SchemaException):
            self.schema.context(SHOT="RND_999")
        context = self.schema.context(SHOW="AVG", SEQUENCE="RND", SHOT="RND_999", APP="Nuke")
        self.assertEqual(context.selection("Show"), ("AVG", "RND", "RND_999"))
        self.assertEqual(context.selection("App"), ("Nuke",))

    def test_invalid_values(self):
        for value in ["a,b", "a+b", "a=b", "a/b", " a", ".hidden"]:
            with self.assertRaises(SchemaException, msg=value):
                self.schema.context(SHOW=value)
        # An empty value means the layer is not selected.
        self.assertTrue(self.schema.context(SHOW="").is_base)

    def test_resolution_order(self):
        context = self.schema.context(SHOW="AVG", SEQUENCE="RND", SHOT="RND_999", APP="Nuke")
        names = [naming.file_name(c) for c in context.applicable_contexts()]
        self.assertEqual(names, [
            "base.wolfkrow.yml",
            "Show=AVG.wolfkrow.yml",
            "Show=AVG,RND.wolfkrow.yml",
            "Show=AVG,RND,RND_999.wolfkrow.yml",
            "App=Nuke.wolfkrow.yml",
            "Show=AVG+App=Nuke.wolfkrow.yml",
            "Show=AVG,RND+App=Nuke.wolfkrow.yml",
            "Show=AVG,RND,RND_999+App=Nuke.wolfkrow.yml",
        ])

    def test_user_beats_everything(self):
        context = self.schema.context(SHOW="AVG", APP="Nuke", USER="jacob")
        names = [naming.file_name(c) for c in context.applicable_contexts()]
        self.assertEqual(names[-1], "Show=AVG+App=Nuke+User=jacob.wolfkrow.yml")
        self.assertLess(names.index("Show=AVG+App=Nuke.wolfkrow.yml"), names.index("User=jacob.wolfkrow.yml"))

    def test_file_names_round_trip(self):
        context = self.schema.context(SHOW="AVG", SEQUENCE="RND", APP="Nuke", USER="jacob")
        name = naming.file_name(context)
        self.assertEqual(name, "Show=AVG,RND+App=Nuke+User=jacob.wolfkrow.yml")
        self.assertEqual(naming.parse_file_name(self.schema, name), context)
        self.assertEqual(naming.parse_file_name(self.schema, "base.wolfkrow.yml"), self.schema.base_context())
        self.assertIsNone(naming.parse_file_name(self.schema, "wolfkrow_schema.yml"))
        with self.assertRaises(SchemaException):
            # Not in schema order.
            naming.parse_file_name(self.schema, "App=Nuke+Show=AVG.wolfkrow.yml")

    def test_context_from_environment(self):
        context = self.schema.context_from_environment({"SHOW": "AVG", "SHOT": "X", "APP": "Nuke"})
        # SHOT is ignored because SEQUENCE is not set.
        self.assertEqual(context, self.schema.context(SHOW="AVG", APP="Nuke"))


class TestMerge(unittest.TestCase):

    def test_scalar(self):
        report = merge.MergeReport()
        patch = {"file_type": {ORIGINAL: "exr", UPDATED: "mov"}}
        result = merge.apply_patch({"file_type": "exr", "a": 1}, patch, "L1", report)
        self.assertEqual(result, {"file_type": "mov", "a": 1})
        self.assertEqual(report.layer_for(("file_type",)), "L1")
        self.assertEqual(report.notes, [])

    def test_scalar_outdated(self):
        report = merge.MergeReport()
        patch = {"file_type": {ORIGINAL: "exr", UPDATED: "mov"}}
        result = merge.apply_patch({"file_type": "dpx"}, patch, "L1", report)
        # The layer still wins.
        self.assertEqual(result, {"file_type": "mov"})
        self.assertEqual([note.kind for note in report.notes], [NoteKind.OUTDATED])

    def test_scalar_redundant(self):
        report = merge.MergeReport()
        patch = {"file_type": {ORIGINAL: "exr", UPDATED: "mov"}}
        merge.apply_patch({"file_type": "mov"}, patch, "L1", report)
        self.assertEqual([note.kind for note in report.notes], [NoteKind.REDUNDANT])

    def test_list_removal_survives_inherited_changes(self):
        patch = {ORIGINAL: ["slate.nk", "burnin.nk", "reformat.nk"], UPDATED: ["slate.nk", "reformat.nk"]}
        # The base has since added a snippet, and re-ordered the list.
        inherited = ["lut.nk", "reformat.nk", "slate.nk", "burnin.nk"]
        report = merge.MergeReport()
        result = merge.apply_patch(inherited, patch, "L1", report)
        self.assertEqual(result, ["lut.nk", "reformat.nk", "slate.nk"])
        self.assertIn(("[burnin.nk]",), report.removed)

    def test_list_addition_anchored(self):
        patch = {ORIGINAL: ["a", "c"], UPDATED: ["a", "b", "c"]}
        self.assertEqual(merge.apply_patch(["x", "a", "c", "y"], patch), ["x", "a", "b", "c", "y"])
        # Previous neighbour is gone, so it goes before the next neighbour.
        self.assertEqual(merge.apply_patch(["c", "y"], patch), ["b", "c", "y"])
        # Both neighbours are gone.
        report = merge.MergeReport()
        self.assertEqual(merge.apply_patch(["y"], patch, "L1", report), ["y", "b"])
        self.assertTrue(any(note.kind == NoteKind.OUTDATED for note in report.notes))

    def test_list_orphaned_removal(self):
        patch = {ORIGINAL: ["a", "b"], UPDATED: ["a"]}
        report = merge.MergeReport()
        self.assertEqual(merge.apply_patch(["a", "c"], patch, "L1", report), ["a", "c"])
        self.assertEqual([note.kind for note in report.notes], [NoteKind.ORPHANED])

    def test_list_of_named_snippets(self):
        original = [{"slate": {"node_type": "Slate"}}, {"reformat": {"node_type": "Reformat", "width": 1920}}]
        updated = [{"slate": {"node_type": "Slate"}}, {"reformat": {"node_type": "Reformat", "width": 3840}}]
        # A lower layer has since changed another knob on the same snippet.
        inherited = [{"slate": {"node_type": "Slate"}}, {"reformat": {"node_type": "Reformat", "width": 1920, "height": 1080}}]
        result = merge.apply_patch(inherited, {ORIGINAL: original, UPDATED: updated})
        self.assertEqual(result[1], {"reformat": {"node_type": "Reformat", "width": 3840, "height": 1080}})

    def test_list_reorder(self):
        patch = {ORIGINAL: ["a", "b", "c"], UPDATED: ["c", "a", "b"]}
        self.assertEqual(merge.apply_patch(["a", "b", "c", "d"], patch), ["c", "a", "b", "d"])

    def test_remove_key(self):
        report = merge.MergeReport()
        patch = {"tasks": {"old": {ORIGINAL: {"task_type": "FileCopy"}, REMOVED: True}}}
        result = merge.apply_patch({"tasks": {"old": {"task_type": "FileCopy"}, "keep": {}}}, patch, "L1", report)
        self.assertEqual(result, {"tasks": {"keep": {}}})
        self.assertIn(("tasks", "old"), report.removed)

    def test_plain_values(self):
        # Hand written files: plain dicts merge, plain values replace.
        result = merge.apply_patch(
            {"tasks": {"a": {"x": 1, "y": [1, 2]}}},
            {"tasks": {"a": {"y": [3]}, "b": {"x": 2}}},
        )
        self.assertEqual(result, {"tasks": {"a": {"x": 1, "y": [3]}, "b": {"x": 2}}})

    def test_diff_round_trip(self):
        inherited = copy.deepcopy(BASE_CONFIG)
        edited = copy.deepcopy(BASE_CONFIG)
        edited["tasks"]["dailies_quicktime"]["scripts"].remove("burnin.nk")
        edited["tasks"]["dailies_quicktime"]["file_type"] = "mp4"
        del edited["tasks"]["copy_to_publish"]
        edited["tasks"]["new_task"] = {"task_type": "FileCopy"}

        patch = merge.diff(inherited, edited)
        self.assertEqual(merge.apply_patch(inherited, patch), edited)
        # Only the changes are stored.
        self.assertEqual(set(patch), {"tasks"})
        self.assertEqual(set(patch["tasks"]["dailies_quicktime"]), {"scripts", "file_type"})
        self.assertEqual(patch["tasks"]["new_task"], {UPDATED: {"task_type": "FileCopy"}})
        self.assertTrue(patch["tasks"]["copy_to_publish"][REMOVED])
        self.assertIs(merge.diff(inherited, copy.deepcopy(inherited)), MISSING)

    def test_diff_keeps_previous_records(self):
        # A change was made when the base was "exr". The base has since changed to "dpx".
        previous = {"file_type": {ORIGINAL: "exr", UPDATED: "mov"}, "other": {ORIGINAL: 1, UPDATED: 2}}
        inherited = {"file_type": "dpx", "other": 1}
        edited = {"file_type": "mov", "other": 3}
        patch = merge.diff(inherited, edited, previous)
        # The unchanged record keeps its original value, so it is still flagged as outdated.
        self.assertEqual(patch["file_type"], {ORIGINAL: "exr", UPDATED: "mov"})
        self.assertEqual(patch["other"], {ORIGINAL: 1, UPDATED: 3})


class TestLayeredConfig(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.layered = LayeredConfig.create(self.root, Schema.from_dict(SCHEMA), BASE_CONFIG)
        self.schema = self.layered.schema

    def tearDown(self):
        shutil.rmtree(self.root)

    def _edit(self, context, function):
        config = copy.deepcopy(self.layered.resolve(context).config)
        function(config)
        return self.layered.save(context, config)

    def test_user_walkthrough(self):
        """ The example from the design discussion. """
        shot = self.schema.context(SHOW="AVG", SEQUENCE="RND", SHOT="RND_999")
        nuke = self.schema.context(APP="Nuke")
        both = self.schema.context(SHOW="AVG", SEQUENCE="RND", SHOT="RND_999", APP="Nuke")

        # 1. Remove the burnin for RND_999
        self._edit(shot, lambda c: c["tasks"]["dailies_quicktime"]["scripts"].remove("burnin.nk"))
        # 2. Remove the slate for Nuke
        self._edit(nuke, lambda c: c["tasks"]["dailies_quicktime"]["scripts"].remove("slate.nk"))

        # 3. Both removals apply to the combined context, and are attributed to their layers.
        resolution = self.layered.resolve(both)
        self.assertEqual(resolution.config["tasks"]["dailies_quicktime"]["scripts"], ["reformat.nk"])
        removed = resolution.report.removed
        scripts = ("tasks", "dailies_quicktime", "scripts")
        self.assertEqual(removed[scripts + ("[burnin.nk]",)]["layer"], "Show=AVG,RND,RND_999.wolfkrow.yml")
        self.assertEqual(removed[scripts + ("[slate.nk]",)]["layer"], "App=Nuke.wolfkrow.yml")

        # 4. Add a task for the combined context only.
        def add_task(config):
            config["tasks"]["notify"] = {"task_type": "CommandLine", "script": "echo", "args": ["done"]}
            config["workflows"]["dailies"].append("notify")
        self._edit(both, add_task)

        self.assertIn("notify", self.layered.resolve(both).config["tasks"])
        self.assertNotIn("notify", self.layered.resolve(shot).config["tasks"])
        self.assertNotIn("notify", self.layered.resolve(nuke).config["tasks"])
        self.assertEqual(self.layered.resolve(both).report.layer_for(("tasks", "notify", "script")),
            "Show=AVG,RND,RND_999+App=Nuke.wolfkrow.yml")

        # Only the shot and Nuke files exist for those contexts, and they only store the change.
        with open(self.layered.path_for(shot)) as handle:
            shot_patch = yaml.safe_load(handle)
        self.assertEqual(shot_patch, {"tasks": {"dailies_quicktime": {"scripts": {
            ORIGINAL: ["slate.nk", "burnin.nk", "reformat.nk"],
            UPDATED: ["slate.nk", "reformat.nk"],
        }}}})

        # 5. A later change to the base config is merged with the overrides.
        self._edit(self.schema.base_context(),
            lambda c: c["tasks"]["dailies_quicktime"]["scripts"].append("lut.nk"))
        self.assertEqual(
            self.layered.resolve(both).config["tasks"]["dailies_quicktime"]["scripts"],
            ["reformat.nk", "lut.nk"],
        )

    def test_last_change_wins(self):
        shot = self.schema.context(SHOW="AVG", SEQUENCE="RND", SHOT="RND_999")
        user = self.schema.context(USER="jacob")
        self._edit(shot, lambda c: c["tasks"]["dailies_quicktime"].update(file_type="mp4"))
        self._edit(user, lambda c: c["tasks"]["dailies_quicktime"].update(file_type="exr"))
        both = self.schema.context(SHOW="AVG", SEQUENCE="RND", SHOT="RND_999", USER="jacob")
        self.assertEqual(self.layered.resolve(both).config["tasks"]["dailies_quicktime"]["file_type"], "exr")

    def test_reverting_removes_file(self):
        nuke = self.schema.context(APP="Nuke")
        self._edit(nuke, lambda c: c["tasks"]["dailies_quicktime"].update(file_type="mp4"))
        self.assertTrue(self.layered.exists(nuke))
        self._edit(nuke, lambda c: c["tasks"]["dailies_quicktime"].update(file_type="mov"))
        self.assertFalse(self.layered.exists(nuke))

    def test_known_values(self):
        self._edit(self.schema.context(SHOW="AVG", SEQUENCE="RND"), lambda c: c["replacements"].update(a="1"))
        self._edit(self.schema.context(SHOW="AVG", SEQUENCE="ABC"), lambda c: c["replacements"].update(a="2"))
        self.assertEqual(self.layered.known_values("Show"), ["AVG"])
        self.assertEqual(self.layered.known_values("Show", ["AVG"]), ["ABC", "RND"])

    def test_loader(self):
        os.environ.setdefault("WOLFKROW_SETTINGS_FILE",
            os.path.join(os.path.dirname(__file__), "test_settings.yaml"))
        nuke = self.schema.context(APP="Nuke")
        self._edit(nuke, lambda c: c["tasks"]["dailies_quicktime"]["scripts"].remove("slate.nk"))

        loader = self.layered.create_loader(nuke, replacements={"input_path": "/in", "publish_path": "/out"})
        task_graph = loader.parse_workflow("dailies")
        task = task_graph._tasks["dailies_quicktime"]
        self.assertEqual(task.scripts, ["burnin.nk", "reformat.nk"])
        self.assertEqual(task.config_root, self.layered.root)
        self.assertEqual(task.config_context, {"APP": "Nuke"})


if __name__ == "__main__":
    unittest.main()
