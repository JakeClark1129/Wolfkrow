""" Tests for Task inputs/outputs and the connections between them. """
import json
import os
import tempfile
import unittest

from wolfkrow.builder import workflow_builder
from wolfkrow.core import connections
from wolfkrow.core.connections import IO, Types
from wolfkrow.core.tasks import all_tasks, describe_all_tasks
from wolfkrow.core.tasks.test_tasks import TestTask_Inputs, TestTask_Outputs

from .wolfkrow_testcase import WolfkrowTestCase


class TestConnections(unittest.TestCase):

    def test_io_token(self):
        self.assertEqual(connections.parse_io_token("IO<a_task:destination>"), ("a_task", "destination"))
        self.assertEqual(connections.parse_io_token(" IO< a : b > "), ("a", "b"))
        self.assertIsNone(connections.parse_io_token("/some/path"))
        self.assertIsNone(connections.parse_io_token("prefix IO<a:b>"))
        self.assertIsNone(connections.parse_io_token(5))
        self.assertEqual(connections.make_io_token("a", "b"), "IO<a:b>")

    def test_match_score(self):
        # Exact match.
        self.assertEqual(connections.match_score(Types.START_FRAME, Types.START_FRAME), 3)
        self.assertTrue(connections.is_exact_match(Types.START_FRAME, Types.START_FRAME))
        # Compatible, but not exact. (start frame -> end frame)
        self.assertEqual(connections.match_score(Types.START_FRAME, Types.END_FRAME), 2)
        self.assertFalse(connections.is_exact_match(Types.START_FRAME, Types.END_FRAME))
        # Incompatible.
        self.assertEqual(connections.match_score(Types.START_FRAME, Types.FILE), 0)
        # A more specific output satisfies a more generic input.
        self.assertTrue(connections.is_exact_match(Types.IMAGE_SEQUENCE, Types.FILE))

    def test_connect_all(self):
        outputs = {name: attr.types for name, attr in all_tasks["NukeRender"].io_attributes["outputs"].items()}
        inputs = {name: attr.types for name, attr in all_tasks["FileCopy"].io_attributes["inputs"].items()}
        result, ambiguous = connections.connect_all(outputs, inputs)
        self.assertEqual(sorted(result), sorted([
            ("destination", "source"),
            ("render_start_frame", "start_frame"),
            ("render_end_frame", "end_frame"),
            ("render_start_frame", "renumbered_start_frame"),
        ]))
        self.assertEqual(ambiguous, [])

        # Already connected inputs are left alone.
        result, _ = connections.connect_all(outputs, inputs, existing_connections=["source"])
        self.assertNotIn(("destination", "source"), result)

    def test_connect_all_ambiguous(self):
        outputs = {"a": Types.FILE, "b": Types.FILE}
        inputs = {"source": Types.FILE}
        result, ambiguous = connections.connect_all(outputs, inputs)
        self.assertEqual(result, [])
        self.assertEqual(ambiguous, ["source"])

        # Same name wins a tie.
        outputs = {"source": Types.FILE, "b": Types.FILE}
        result, ambiguous = connections.connect_all(outputs, inputs)
        self.assertEqual(result, [("source", "source")])

    def test_describe(self):
        descriptions = describe_all_tasks()
        self.assertIn("NukeRender", descriptions)
        # Abstract base tasks are hidden.
        self.assertNotIn("FileOperation", descriptions)
        self.assertNotIn("SequenceTask", descriptions)

        nuke_render = descriptions["NukeRender"]
        self.assertEqual(nuke_render["inputs"], ["source", "input_start_frame", "input_end_frame"])
        self.assertIn("nuke_script", nuke_render["outputs"])
        attributes = {attr["name"]: attr for attr in nuke_render["attributes"]}
        self.assertEqual(attributes["input_start_frame"]["types"], ["int", "frame_number", "start_frame"])
        self.assertEqual(attributes["input_start_frame"]["io"], ["input"])
        self.assertFalse(attributes["replacements"]["display_in_ui"])
        json.dumps(descriptions)


class TestTaskIO(WolfkrowTestCase):

    def setUp(self):
        super(TestTaskIO, self).setUp()
        self.temp = tempfile.mkdtemp()

    def _loader(self):
        return workflow_builder.Loader(
            config_file_paths=[self.get_test_config_file("test_task_io.yaml")],
            replacements={"temp": self.temp},
            temp_dir=self.temp,
        )

    def test_connections_add_dependencies(self):
        task_graph = self._loader().parse_workflow("task_io")
        input_task = task_graph._tasks["input_task"]
        self.assertEqual(input_task.dependencies, ["output_task"])
        self.assertEqual(input_task.get_connections()["source"], ("output_task", "destination"))

    def test_export_time_resolution(self):
        task_graph = self._loader().parse_workflow("task_io")
        task_graph.export_tasks(temp_dir=self.temp)

        input_task = task_graph._tasks["input_task"]
        output_task = task_graph._tasks["output_task"]

        self.assertEqual(input_task.source, self.temp + "/render.%04d.exr")
        self.assertEqual(input_task.start_frame, 1001)
        self.assertEqual(input_task.end_frame, 1010)
        # Not known until runtime.
        self.assertIsNone(input_task.runtime_value)

        self.assertTrue(output_task.outputs_file.endswith("output_task.outputs.json"))
        self.assertEqual(input_task.input_sources["runtime_value"], {
            "task": "output_task",
            "attribute": "runtime_value",
            "outputs_file": output_task.outputs_file,
        })

    def test_execute_local_runtime_outputs(self):
        task_graph = self._loader().parse_workflow("task_io")
        results = task_graph.execute_local(temp_dir=self.temp)
        self.assertEqual(results, {"output_task": True, "input_task": True})

        with open(os.path.join(self.temp, "report.json")) as handle:
            report = json.load(handle)

        self.assertEqual(report, {
            "source": self.temp + "/render.%04d.exr",
            "start_frame": 1001,
            "end_frame": 1010,
            # Picked up from the outputs.json file at runtime.
            "runtime_value": 42,
        })

    def test_runtime_value_overrides_export_value(self):
        outputs_file = os.path.join(self.temp, "upstream.outputs.json")
        with open(outputs_file, "w") as handle:
            json.dump({"start_frame": 2001}, handle)

        task = TestTask_Inputs(
            name="downstream",
            start_frame=1001,
            input_sources={"start_frame": {"task": "upstream", "attribute": "start_frame", "outputs_file": outputs_file}},
        )
        with self.assertLogs(level="WARNING") as logs:
            task.load_runtime_inputs()
        self.assertEqual(task.start_frame, 2001)
        self.assertIn("Using the runtime value", logs.output[0])

    def test_missing_upstream_attribute(self):
        from wolfkrow.core.engine.task_graph import TaskGraph, TaskGraphException
        task_graph = TaskGraph("bad")
        task_graph.add_task(TestTask_Outputs(name="up"))
        task_graph.add_task(TestTask_Inputs(name="down", source="IO<up:not_an_output>"))
        with self.assertRaises(TaskGraphException):
            task_graph.export_tasks(temp_dir=self.temp)


if __name__ == "__main__":
    unittest.main()
