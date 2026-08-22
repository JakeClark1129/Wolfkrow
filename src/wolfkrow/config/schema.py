
import re

from collections import deque
class WolfkrowConfigSchemaNode():
    # Regex to match $ENV, ${ENV}, %ENV%, and $env:ENV style environment variable references.
    env_var_regex = re.compile(r"\${?([a-zA-Z0-9_]+)}?|%([a-zA-Z0-9_]+)%|\$env:([a-zA-Z0-9_]+)")

    def __init__(self, name, path, parent=None):
        self.name = name
        self.path = path

        self.context_keys = self._get_environment_variables_from_path(path)
        self.key = "-".join(self.context_keys)


        self.children = {}
        self.parent = parent
        if self.parent:
            self.parent.add_child(self)

    def add_child(self, child_node):
        self.children[child_node.name] = child_node

    def validate(self, context):
        for key in self.context_keys:
            if key not in context:
                return False
        return True

    def _get_environment_variables_from_path(self, path):
        env_vars = set()
        for match in self.env_var_regex.finditer(path):
            env_var_name = match.group(1) or match.group(2) or match.group(3)
            env_vars.add(env_var_name)
        return env_vars
    
    def _substitute_environment_variables_in_path(self, path, env_var_values):
        def replacement(match):
            env_var_name = match.group(1) or match.group(2) or match.group(3)
            
            # If the env var is not found in the provided values, return the 
            # original match (leave it unchanged)
            env_var_value = env_var_values.get(env_var_name, match.group(0))  

            return env_var_value
        
        return self.env_var_regex.sub(replacement, path)

    def resolve_path(self, context):
        resolved_path = self._substitute_environment_variables_in_path(self.path, context)
        return resolved_path
    
    def resolve_key(self, context):
        resolved_key = self._substitute_environment_variables_in_path(self.key, context)
        return resolved_key

class WolfkrowConfigSchema():
    
    def __init__(self, wolfkrow_config_search_paths):
        self.wolfkrow_config_search_paths = wolfkrow_config_search_paths

        self.schema_nodes = {}
        self._schema_root_node = None
        self.context_keys = set()
        self._build_schema(wolfkrow_config_search_paths)

    def _build_schema(self, wolfkrow_config_search_paths):

        # Reset the schema nodes and root node before building the schema.
        self.schema_nodes = {}
        self._schema_root_node = None
        self.context_keys = set()


        # Create a empty root node for the base of the schema
        schema_root_node = WolfkrowConfigSchemaNode(
            name="root",
            path="",
            parent=None
        )

        # Start a queue, and add all the top level search paths to it. We will 
        # use this queue to do a breadth first traversal of the search paths, 
        # and build the schema nodes as we go.
        queue = deque()
        for search_path_name, search_path_dict in wolfkrow_config_search_paths.items():
            queue.append((search_path_name, search_path_dict, 0, schema_root_node))

        # Now do do the breadth first traversal of the search paths.
        while queue:
            search_path_name, search_path_dict, depth, parent_schema_node = queue.popleft()

            schema_node = WolfkrowConfigSchemaNode(
                name=search_path_name,
                path=search_path_dict.get("path", ""),
                parent=parent_schema_node
            )

            self.context_keys.update(schema_node.context_keys)

            children = search_path_dict.get("children", {})
            for child_name, child_dict in children.items():
                queue.append((child_name, child_dict, depth + 1, schema_node))

        self._schema_root_node = schema_root_node