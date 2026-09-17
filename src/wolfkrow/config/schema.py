""" NOTE: Currently this is a highly simplified version of the schema. It currently
only supports a linear chain of nodes, and does not support branching. 

The future plan, is to completely rewrite the Wolfkrow config resolving system
to support multiple different linear config chains, and then each config
chain will have relationships to the other config chains. 
This will result in potentially hundreds/thousands of different possible config
nodes of all the different combinations possible.
Ex, the following set up would allow us to have different configs between any
    combination of projects, sequences, shots, apps, pipe steps, tasks, and users.
    ROOT NODE:
    - $PROJECT -> $SEQ -> $SHOT
    - $APP -> $PIPE_STEP -> $TASK
    - $USER
    
Would result in 4 * 4 * 2 - 3 possible different combinations of config nodes.
Ex: 
    We could have a config node wolfkrow-<PROJECT>-<SEQ>-<APP>-<PIPE_STEP>.yaml
    OR
    We could have a config node wolfkrow-<PROJECT>-<SEQ>-<SHOT>-<APP>-<PIPE_STEP>-<USER>.yaml
    
Then of course, the actual wolfkrow config files on disk would need to resolve 
the context vars. So the actual file on disk would need to be something like this:
Ex:
    wolfkrow_AVENGERS-SEQ01-SHOT001-MAYA-ANIMATION.yaml
    
Which means the total config files would be approximately:
4(projects * sequences * shots) * 4(apps * pipe_steps * tasks) * 2(users)
which very quickly becomes an astronomical number of possible config files.
This gives the user complete flexibility to have different config for highly
specific contexts, but still allows for very simple generic configs.

NOTE: The actual math here is much more complicated and nuanced, but you get the point.


The actual resolution of the config files will need to be rewritten as well. Currently,
the config resolution is s simple override, where a task definition in will simply
override a task definition in a parent config. Instead, we will need to have a more
nuanced resolution system which will allow for overriding of individual attributes 
of a task.
Ex: Nuke users, might always want UHD quicktimes to be generated. And a specific show might not want Slates.
    This is 2 different attributes of the same task, for 2 different contexts. 
    So, if were rendering a quicktime for a Nuke user, on the no-slate show, we 
    would want to use the UHD quicktime attribute from the Nuke user config, and
    the no-slate attribute from the show config.
To achieve this, the idea is to use a diffing system, where each config file 
instead of being a complete config, is instead a diff of the config from the 
parent node.
This will then allow us to merge all the diffs together after the context is complete.
In the case of conflicting diffs, we will need a conflict resolution system. I
propose that we use a simple "last one wins" system, where the last config file 
in the resolution chain wins. The chain will be resolved Left -> right, Top -> Bottom.
Ex: 
    In the above example, a conflict between $PROJECT and $SHOT, the $SHOT will 
        win because it is more RIGHT than $PROJECT,
    Also a conflict between $APP, and $SHOT, the $APP will win because it is more 
        BOTTOM than $SHOT.
With the complication here, it's also incredibly important that there are UI elements
to visualize where each attribute is coming from, and to highlight any conflicts.

This methodology of config resolution, will also greatly simplify the total config files. 
Instead of multiplicative, it will be additive. So in the above example, we would
only need 1 + 3 + 3 + 1 = 8 config combinations.
"""

from email.policy import default
import re

from collections import deque
class WolfkrowConfigSchemaNode():
    # Regex to match $ENV, ${ENV}, %ENV%, and $env:ENV style environment variable references.
    env_var_regex = re.compile(r"\${?([a-zA-Z0-9_]+)}?|%([a-zA-Z0-9_]+)%|\$env:([a-zA-Z0-9_]+)")

    def __init__(self, path, parent=None):
        self.path = path

        self.context_keys = self._get_environment_variables_from_path(path)
        self.key = "-".join(self.context_keys)

        self.child = None
        self.parent = parent
        if self.parent:
            self.parent.add_child(self)

    def add_child(self, child_node):
        self.child = child_node

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
    
    def _substitute_environment_variables_in_path(self, path, env_var_values, default_value=None):
        def replacement(match):
            env_var_name = match.group(1) or match.group(2) or match.group(3)
            
            # If the env var is not found in the provided values, return the 
            # original match (leave it unchanged)
            env_var_value = env_var_values.get(
                env_var_name, 
                default_value if default_value is not None else match.group(0)
            )

            return env_var_value
        
        return self.env_var_regex.sub(replacement, path)

    def resolve_path(self, context, default_value=None):
        """ Resolves the environment variables in the path for this schema node.

        Args:
            context (dict): A dictionary of environment variable values to use for substitution.
            default_value (str, optional): The value to use if an environment 
                variable is not provided in the context. 
                Default behavior is to leave the environment variable unchanged 
                if it is not found in the context.

        Returns:
            str: The resolved path with environment variables substituted.
        """
        resolved_path = self._substitute_environment_variables_in_path(self.path, context, default_value=default_value)
        return resolved_path
    
    def resolve_key(self, context, default_value=None):
        """ Resolves the environment variables in the key for this schema node.

        Args:
            context (dict): A dictionary of environment variable values to use for substitution.
            default_value (str, optional): The value to use if an environment 
                variable is not provided in the context. 
                Default behavior is to leave the environment variable unchanged 
                if it is not found in the context.

        Returns:
            str: The resolved key with environment variables substituted.
        """
        resolved_key = self._substitute_environment_variables_in_path(self.key, context, default_value=default_value)
        return resolved_key

class WolfkrowConfigSchema():
    
    def __init__(self, wolfkrow_config_search_paths):
        
        if not isinstance(wolfkrow_config_search_paths, list):
            raise ValueError("wolfkrow_config_search_paths must be a list of paths.")

        self.wolfkrow_config_search_paths = wolfkrow_config_search_paths

        self.schema_nodes = []
        self._schema_root_node = None
        self.context_keys = set()
        self._build_schema(wolfkrow_config_search_paths)

    def _build_schema(self, wolfkrow_config_search_paths):

        # Reset the schema nodes and root node before building the schema.
        self.schema_nodes = []
        self._schema_root_node = None
        self.context_keys = set()


        # Create a empty root node for the base of the schema
        schema_root_node = WolfkrowConfigSchemaNode(
            path="",
            parent=None
        )

        # Start a queue, and add all the top level search paths to it. We will 
        # use this queue to do a breadth first traversal of the search paths, 
        # and build the schema nodes as we go.
        parent_schema_node = schema_root_node
        for search_path in wolfkrow_config_search_paths:

            schema_node = WolfkrowConfigSchemaNode(
                path=search_path,
                parent=parent_schema_node
            )

            self.context_keys.update(schema_node.context_keys)
            parent_schema_node = schema_node

            self.schema_nodes.append(schema_node)

        self._schema_root_node = schema_root_node