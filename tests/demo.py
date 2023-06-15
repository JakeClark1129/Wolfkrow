from __future__ import print_function



# ======================================================
# ==================== ENABLE PTVSD ====================
# ======================================================
import ptvsd
ptvsd.enable_attach()
print("Waiting for attach...")
ptvsd.wait_for_attach()
# ptvsd.break_into_debugger()
# ======================================================
# ======================================================
# ======================================================

from wolfkrow.builder import workflow_builder
import os
root = os.path.dirname(__file__)
config_file = os.path.join(root, "demo.yaml")
replacements = {
	"input_files": "C:\\Projects\\Wolfkrow\\tests\\test_data\\sequences\\test.%03d.tst",
	"input_files_basename": "test"
}
loader = workflow_builder.Loader(config_file_paths=[config_file], replacements=replacements)
task_graph = loader.parse_workflow("demo_workflow")
task_graph.execute_local()
