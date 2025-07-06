""" Module implementing a nuke render task.
"""
from __future__ import print_function

from builtins import range
from past.builtins import basestring
import errno
import logging
import os
import re

from .task import Task, TaskAttribute
from .sequence_task import SequenceTask
from .task_exceptions import TaskValidationException

from wolfkrow.core.engine.resolver import Resolver

class RenderRange():
    """ Class to calculate the frame range for the read nodes.
    """
    def __init__(self, 
        start_frame=None, 
        end_frame=None, 
        input_start_frame=None, 
        input_end_frame=None, 
        render_start_frame=None, 
        render_end_frame=None
    ):
        self.start_frame = int(start_frame) if start_frame is not None else None
        self.end_frame = int(end_frame) if end_frame is not None else None
        self.input_start_frame = int(input_start_frame) if input_start_frame is not None else None
        self.input_end_frame = int(input_end_frame) if input_end_frame is not None else None
        self.render_start_frame = int(render_start_frame) if render_start_frame is not None else None
        self.render_end_frame = int(render_end_frame) if render_end_frame is not None else None

    def calculate(self):
        """ Calculates the frame range for the read nodes.
        """
        # Set up the default frame number values. 
        input_start_frame = self.start_frame
        render_start_frame = self.start_frame

        input_end_frame = self.end_frame
        render_end_frame = self.end_frame

        # Apply the frame number overrides
        if self.input_start_frame is not None:
            input_start_frame = self.input_start_frame

        if self.input_end_frame is not None:
            input_end_frame = self.input_end_frame

        if self.render_start_frame is not None:
            render_start_frame = self.render_start_frame

        if self.render_end_frame is not None:
            render_end_frame = self.render_end_frame

        # validate that the frame range is valid.
        if input_start_frame is None or input_end_frame is None:
            raise TaskValidationException("Input frame range must be set.")
        
        if render_start_frame is None or render_end_frame is None:
            raise TaskValidationException("Render frame range must be set.")

        return (input_start_frame, input_end_frame, render_start_frame, render_end_frame)


class NukeTask(Task):
    def export_to_command_line(self, job_name, temp_dir=None, deadline=False, export_json=False):
        """ Will generate a `wolfkrow_run_task` command line command to run in 
            order to re-construct and run this task via command line. 

            Appends a '$' to the end of the command because nuke will try to accept
            the last arguments as a frame number/range.
        """
        exported = super(NukeTask, self).export_to_command_line(
            job_name,
            temp_dir=temp_dir,
            deadline=deadline,
        )

        # Append a "$" to the end of the command so that nuke does not consume 
        # the last argument as a frame number/range.
        for export in exported:
            args = "{} $".format(export.task_args)
            export.task_args = args
        return exported

    def _command_line_sanitize_attribute(
        self, attribute_name, attribute_value, deadline=False
    ):
        """
        Processes the attribute value to prepare it for use on the command line.

        Default implementation just returns the given value.
        """
        # When setting a knob value in Nuke, it resolves the double backslashes 
        # to single backslashes, which then causes errors because it still treat's 
        # single slashes as an escape character. So we need to double up, so that 
        # the double backslashes are actually double backslashes once they are set 
        # on the knobs in Nuke.
        if isinstance(attribute_value, basestring) and "\\" in attribute_value:
            attribute_value = attribute_value.replace("\\", "\\\\")

        # Continue processing the attribute value.
        attribute_value = super(NukeTask, self)._command_line_sanitize_attribute(
            attribute_name, attribute_value, deadline=deadline
        )

        return attribute_value

class NukeRender(NukeTask):

    scripts = TaskAttribute(default_value=[], configurable=True, attribute_type=list, 
        description="list of nuke scripts to concatenate together. Python scripts will be executed."
    )

    # Attributes for read node
    source = TaskAttribute(default_value="", configurable=True, attribute_type=str)

    # Attributes for read node
    # TODO: How can we do validation on complex attributes like this?
    #   Should we build a schema system which allows us to write custom validators
    #   for complex attributes?
    additional_sources = TaskAttribute(default_value=None, configurable=True, attribute_type=dict)

    # Attributes for write node
    write_node_class = TaskAttribute(default_value="Write", configurable=True, attribute_type=str)
    write_node_name = TaskAttribute(default_value=None, configurable=False, attribute_type=str, 
        description="""
    Name of the wrtie node to create/render from. If left unset, will automatically 
    determine its own name (recommended)
        """
    )
    destination = TaskAttribute(default_value="", configurable=True, attribute_type=str)
    file_type = TaskAttribute(default_value="exr", configurable=True, attribute_type=str)
    bit_depth = TaskAttribute(default_value="16 bit half", configurable=True, attribute_type=str)
    codec = TaskAttribute(default_value=8, configurable=True, attribute_type=str, 
        description="""Which Codec to render the quicktime with.""")
    compression = TaskAttribute(default_value=None, attribute_type=int, description="""Which Compression to use when writing the file. This value is only used when 
writing exr, sgi, targa, or tiff files. Each file type has its own options. See below:
    EXR:
        0 - none
        1 - ZIP (1 scanlines)
        2 - ZIP (16 scanlines)
        3 - PIZ Wavelet (32 scanlines)
        4 - RLE
        5 - B44
        6 - B44a
        7 - DWAA
        8 - DWAB
    
    SGI:
        0 - none
        1 - RLE

    TARGA:
        0 - none
        1 - RLE

    TIFF:
        0 - none
        1 - PackBits
        2 - LZW
        3 - Deflate
    """)

    # Frame range to use for reading and writing.
    start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, 
        description="The start frame to use for the read node and render range.")
    end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int,
        description="The end frame to use for the read node and render range.")

    # Frame range overrides for the input
    input_start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, 
        description="The start frame set on the read node. Overrides the start_frame for Read node only.")
    input_end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int,
        description="The end frame set on the read node. Overrides the end_frame for Read node only.")

    # Frame range overrides for the output
    render_start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int, 
        description="The start frame to render from. Passed to the execute method when rendering. Overrides the start_frame for render range only.")
    render_end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int,
        description="The end frame to render to. Passed to the execute method when rendering. Overrides the end_frame for render range only.")
    
    render_increment = TaskAttribute(
        default_value=1, 
        configurable=True, 
        attribute_type=int, 
        description="The increments to use when rendering. Ex: 10 will render every 10th frame."
    )
    chunk_size = TaskAttribute(default_value=8, configurable=True, attribute_type=int, 
        description="Number of frames to split each task into for running on multiple machines. 0 to perform no chunking"
    )

    renumber = TaskAttribute(
        default_value=None, 
        configurable=True, 
        attribute_type=int,
        description="Add's a timeoffset node to the nuke script which will renumber the input_start_frame to the renumber specified."
    )
    
    generate_quicktimes_in_chunks = TaskAttribute(
        default_value=False, 
        configurable=True, 
        attribute_type=bool,
        description="Whether or not to generate quicktimes in chunks, or in a single "
            "render. Useful for long quicktimes which you want to concatenate back "
            "together after a distributed render on the farm."
    )
    additional_read_node_properties = TaskAttribute(
        default_value={}, 
        configurable=True, 
        attribute_type=dict, 
        description="Dictionary containing key value pairs as 'knob_name': 'knob_value'"
    )
    additional_write_node_properties = TaskAttribute(
        default_value={}, 
        configurable=True, 
        attribute_type=dict, 
        description="Dictionary containing key value pairs as 'knob_name': 'knob_value'"
    )

    font_path = TaskAttribute(
        default_value=None, 
        configurable=True, 
        attribute_type=str, 
        description="Root folder to font files to include in the nuke script."
    )

    root_node_properties = TaskAttribute(
        default_value={}, 
        configurable=True, 
        attribute_type=dict, 
        description="Dictionary containing key value pairs as 'knob_name': 'knob_value' "
            "for values to set on the root node."
    )


    def get_subtasks(self):
        """ Constructs a NukeRenderRun task which should get executed after this task.
        """

        # We have to come up with a predictable write node name so that the 
        # NukeRenderRun task knows which write node to execute.
        self.write_node_name = "{}_wolfkrow_write".format(self.write_node_class)

        # path to the generated nuke script.
        script_path = "{root_dir}/{task_name}.nk".format(
            root_dir=self.temp_dir,
            task_name=self.full_name,
        )

        chunk_size = self.chunk_size
        if self.file_type.lower() in ["mov"] and self.generate_quicktimes_in_chunks is False:
            chunk_size = self.render_end_frame - self.render_start_frame + 1

        # Create NukeRenderRun task.
        # TODO: We should just iterate over all the TaskAttributes and find the ones
        #   that they have in common and pass them through.
        nuke_render_run = NukeRenderRun(
            name=self.name + "_render",
            name_prefix=self.name_prefix,
            replacements=self.replacements,
            resolver_search_paths=self.resolver_search_paths,
            path_swap_lookup=self.path_swap_lookup,
            script=script_path, 
            write_node=self.write_node_name,
            start_frame=self.render_start_frame, 
            end_frame=self.render_end_frame, 
            increment=self.render_increment,
            chunk_size=chunk_size,
            command_line_executable=self.command_line_executable,
            command_line_executable_args=self.command_line_executable_args,
            python_script_executable=self.python_script_executable,
            python_script_executable_args=self.python_script_executable_args,
        )

        return [nuke_render_run]

    def validate(self):
        """ Preforms Validation checks for NukeRenderRun Task.

            Raises:
                TaskValidationException: NukeRenderRun task is not properly initialized
        """

        # Calculate the render range for the main read node.
        render_range = RenderRange(
            start_frame=self.start_frame,
            end_frame=self.end_frame,
            input_start_frame=self.input_start_frame,
            input_end_frame=self.input_end_frame,
            render_start_frame=self.render_start_frame,
            render_end_frame=self.render_end_frame,
        )
        input_start_frame, input_end_frame, render_start_frame, render_end_frame = render_range.calculate()
        
        # And finally set the values back on the task.
        self.input_start_frame = input_start_frame
        self.input_end_frame = input_end_frame

        # validate that the frame range is valid.
        if input_start_frame is None or input_end_frame is None:
            raise TaskValidationException("Input frame range must be set.")
        
        if render_start_frame is None or render_end_frame is None:
            raise TaskValidationException("Render frame range must be set.")

        super(NukeRender, self).validate()

        additional_sources = NukeRender.additional_sources.__get__(self, dont_resolve=True)
        for source, data in additional_sources.items():
            if "source" not in data:
                raise TaskValidationException("Additional source '{}' does not have a 'source' key.".format(source))
            
            # Every source can have it's own render range, but default to the parent's range.
            render_range = RenderRange(
                start_frame=data.get("start_frame", self.start_frame),
                end_frame=data.get("end_frame", self.end_frame),
                input_start_frame=data.get("input_start_frame", self.input_start_frame),
                input_end_frame=data.get("input_end_frame", self.input_end_frame),
                render_start_frame=data.get("render_start_frame", self.render_start_frame),
                render_end_frame=data.get("render_end_frame", self.render_end_frame),
            )
            input_start_frame, input_end_frame, render_start_frame, render_end_frame = render_range.calculate()
            # TODO: Test that this actually modifies the data dict. (I think we might only be getting a copy of the dict)
            data["input_start_frame"] = input_start_frame
            data["input_end_frame"] = input_end_frame
            data["render_start_frame"] = render_start_frame
            data["render_end_frame"] = render_end_frame

    def setup(self):
        """ Will create destination directory if it does not already exist.

            Raises: 
                OSError: Unable to create destination directory
        """
        directory = os.path.dirname(self.destination)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    def _find_bottom_node(self, node):
        """ Finds the bottom node of the node tree that the supplied node belongs to.

            Note: This function makes assumptions about the node tree.
                1) There is no downward branching. (Multiple outputs are not allowed.)
                2) The current node tree is not cyclic. (Not possible in nuke currently)

            Args:
                node (Node): node of a node tree to check against.
        """
            
        dependents = node.dependent()
        if len(dependents) == 0:
            return node

        # Nuke does not allow for cyclic node graphs, so we can assume that this will eventually return.
        return self._find_bottom_node(dependents[0])

    def _find_top_node(self, bottom_node):
        """ Finds the top node from the supplied nodes inputs. an acceptable top_node
            must not have anything connected.

            Will traverse up the node tree using depth-first traversal, and returns 
            the first acceptable node found.

            Note: This function makes assumptions about the node tree.
                1) There is no downward branching. (Multiple outputs are not allowed.)
                2) The current node tree is not cyclic. (Not possible in nuke currently)

            Args:
                bottom_node (Node): Node to get the top node of.
        """

        inputs = bottom_node.inputs()
        if inputs == 0:
            return bottom_node

        for i in range(0, inputs):
            input_node = bottom_node.input(i)
            # Nuke does not allow for cyclic node graphs, so we can assume that this will eventually return.
            top_node = self._find_top_node(input_node)
            if top_node is not None:
                return top_node
        
        # This node does not have any acceptable top_node nodes
        return None

    def _append_nuke_node(self, node_dict, current_bottom_node):
        """ Will attach the supplied nuke node to the current_bottom_node.

            Args: 
                node_dict (dict): Dictionary containing information about what 
                    node to create, and knob values to set.
                current_bottom_node (Node): The node to attach the script to. 
                    Should be the bottom of the current nuke script.
        """
        import nuke

        for node_name, node_dict_ in node_dict.items():
            node_type = node_dict_.get("node_type")

            # Remove the node_type so it doesn't get added to the tcl_list because it is not a valid knob name.
            del node_dict_["node_type"]
            if not node_type:
                print("Warning: attribute 'node_type' required. Received: {}".format(node_dict_))

            tcl_list = []
            for key, value in node_dict_.items():
                tcl_list.append(str(key))
                value = str(value)
                # If there is a space in the value, then we must wrap the value 
                # in quotes so it doesn't get confused as an extra knob name/value
                if " " in value:
                    value = '"' + value + '"'
                tcl_list.append(str(value))

            tcl_list_str = " ".join(tcl_list)


            nuke_node = nuke.createNode(node_type, tcl_list_str)
            nuke_node.setName(node_name)

            # Connect the current_bottom_node to the new scripts top_node. 
            # current_bottom_node will be None for an empty nuke script
            if current_bottom_node is not None:
                nuke_node.setInput(0, current_bottom_node)

            # We are receiving a dictionary with a single entry which is another 
            # dictionary which contains the node knob values we want. Breaking 
            # the iteration immediately to make it clear this dict should NEVER
            # contain more than one entry. (Especially since dict's are un-ordered)
            break

        # return the node we just created as the new bottom node
        return nuke_node


    def _append_nuke_script(self, script, current_bottom_node):
        """ Will attach the supplied nuke script to the current_bottom_node.

            Args: 
                script (str): The script to to attach to the current_bottom_node
                current_bottom_node (Node): The node to attach the script to. 
                    Should be the bottom of the current nuke script.
        """
        import nuke

        # Unselect all nodes in the script
        selected_nodes = nuke.selectedNodes()
        for node in selected_nodes:
            node.setSelected(False)

        if not os.path.exists(script):
            print("Supplied nuke script '{nuke_script}' does not exist. Skipping...".format(
                    nuke_script=script
                )
            )
            return current_bottom_node

        # Paste the nodes from the other nuke script into this one.
        nuke.nodePaste(script)
        pasted_nodes = nuke.selectedNodes()
        if len(pasted_nodes) == 0:
            # Empty nuke script.
            print("Supplied nuke script '{nuke_script}' is empty. Skipping...".format(
                    nuke_script=script
                )
            )
            return current_bottom_node

        # Check for the nodes indicating the top and bottom of the pasted nuke script.
        top_node = nuke.toNode("top")
        bottom_node = nuke.toNode("bottom")
        random_node = pasted_nodes[0]

        # Rename the nodes so that the 'top' and 'bottom' nodes can be found in the next script that gets pasted.
        if top_node is not None:
            top_node.setName("top_1")
        if bottom_node is not None:
            top_node.setName("bottom_1")

        # Node indicating the bottom node was not found. Use slightly more intelligent ways to determine the bottom_node
        if bottom_node is None:
            bottom_node = self._find_bottom_node(top_node or random_node)

        # Node indicating the top node was not found. Use slightly more intelligent ways to determine the top_node
        if top_node is None:
            top_node = self._find_top_node(bottom_node)

        # No acceptable top_node found. don't connect anything.
        if top_node is None:
            print("Supplied nuke script '{nuke_script}' contains no acceptable top node. Skipping.".format(
                nuke_script=script
            ))
            return current_bottom_node

        # Connect the current_bottom_node to the new scripts top_node. 
        # current_bottom_node will be None for an empty nuke script
        if current_bottom_node is not None:
            top_node.setInput(0, current_bottom_node)

        return bottom_node

    def _concatenate_nuke_scripts(self, scripts):
        current_bottom_node = None
        for script in scripts:
            if isinstance(script, dict):
                self._append_nuke_node(script, current_bottom_node)
            else:
                _, ext = os.path.splitext(script)
                if ext == ".py":
                    # TODO: execute python scripts (HOW???) Look into pyscript_knob
                    # https://learn.foundry.com/nuke/developers/70/pythonreference/
                    pass
                elif ext == ".nk":
                    current_bottom_node = self._append_nuke_script(script, current_bottom_node)
        return current_bottom_node

    def _init_read_node(self, read_node, read_data=None):
        """ Initializes the read node with the source, input and render frame ranges.

            Args:
                read_node (Node): The nuke read node to initialize.
        """
        import nuke

        read_node.knob("raw").setValue(True)
        read_node.knob("file").setValue(read_data.get("source"))
        read_node.knob("first").setValue(read_data.get("input_start_frame"))
        read_node.knob("last").setValue(read_data.get("input_end_frame"))

        if read_data.get("renumber"):
            # Unselect all nodes in the script
            selected_nodes = nuke.selectedNodes()
            for node in selected_nodes:
                node.setSelected(False)

            # Select the read node, so that the node we create next will be connected to it.
            read_node.setSelected(True)
            
            # Now create the time offset node
            time_offset = nuke.createNode("TimeOffset")
            time_offset.setSelected(False)
            time_offset.knob("time_offset").setValue(read_data["renumber"] - read_data.get("input_start_frame"))
            time_offset.setInput(0, read_node)

    def set_node_knob_values_from_dict(self, node, value_dict):
        """ Will iterate a given a dictionary of knob_name: value, and will assign 
            each value found to the corresponding knob on the node.

            Args:
                node: The Node object of a nuke node.
                value_dict (dict): Dictionary of knob names, and the value to set.
        """

        for key, value in list(value_dict.items()):
            if key in node.knobs():
                failed = False
                try:
                    knob = node.knob(key)
                    if not isinstance(value, int):
                        # Get the knob's data type, and attempt to cast value to that type.
                        knob_value_type = type(knob.getValue())
                        if knob_value_type != type(None):
                            try:
                                value = knob_value_type(value)
                            except:
                                pass
                    knob.setValue(value)
                except Exception as e:
                    print("Failed to set knob '{}' to {!r}".format(key, value))

    def run(self):
        # Import nuke here because the main engine which creates the tasks will not be run in a nuke process.
        import nuke

        # Concatenate all the nuke scripts in the self.scripts list into a single nuke script.
        bottom_node = self._concatenate_nuke_scripts(self.scripts)

        top_node = None
        # bottom_node will be None when there is no 'scripts' in self.scripts (or 
        # all scripts are empty/invalid)
        if bottom_node:
            # Determine the top node of the script, in order to attach a read node to it.
            top_node = self._find_top_node(bottom_node)

        # Create Read node for self.source
        print(f"wolfkrow_read: {self.source} {self.input_start_frame}-{self.input_end_frame}")
        read_node = nuke.createNode("Read")
        read_data = {
            "source": self.source,
            "input_start_frame": self.input_start_frame,
            "input_end_frame": self.input_end_frame,
            "renumber": self.renumber,
        }
        self._init_read_node(read_node, read_data)

        if self.additional_read_node_properties:
            self.set_node_knob_values_from_dict(read_node, self.additional_read_node_properties)

        # Set up all the additional sources.        
        for additional_source, data in self.additional_sources.items():
            additional_source_node = nuke.toNode(additional_source)
            if additional_source_node is None:
                print("Warning: Additional source '{}' does not exist. Skipping...".format(additional_source))
                continue

            self._init_read_node(additional_source_node, data)

        if self.additional_read_node_properties:
            self.set_node_knob_values_from_dict(read_node, self.additional_read_node_properties)

        time_offset = None
        if self.renumber:
            time_offset = nuke.createNode("TimeOffset")
            time_offset.setSelected(False)
            time_offset.knob("time_offset").setValue(self.renumber - self.input_start_frame)
            time_offset.setInput(0, read_node)

        if top_node:
            if time_offset:
                top_node.setInput(0, time_offset)
            else:
                top_node.setInput(0, read_node)

        # determine the destination file path:

        # If the destination is just a directory, calculate the output filename 
        # from the input name.
        if self.destination.endswith(os.sep) or self.destination.endswith("/"):
            source_basename = os.path.basename(self.source)
            base, ext = os.path.splitext(source_basename)
            dest_basename = "{}.{}".format(base, self.file_type)
            destination = os.path.join(self.destination, dest_basename)
        else:
            destination = self.destination

        # Select the bottom node so that the write node automatically gets connected to it.
        if bottom_node:
            read_node.setSelected(False)
            bottom_node.setSelected(True)

        # Create Write node for self.destination
        write_node = nuke.createNode(self.write_node_class)
        write_node.knob("name").setValue(self.write_node_name)
        write_node.knob("file").setValue(destination)
        write_node.knob("file_type").setValue(self.file_type)
        write_node.knob("raw").setValue(True)

        if self.file_type in ["exr", "dpx", "png", "tiff", "sgi"]:
            write_node.knob("datatype").setValue(self.bit_depth)
        elif self.file_type in ["mov"]:
            write_node.knob("mov64_codec").setValue(self.codec)

        if self.file_type in ["exr", "sgi", "targa", "tiff"]:
            if self.compression:
                write_node.knob("compression").setValue(self.compression)

        root_node = nuke.toNode("root")

        if self.font_path:
            root_node.knob("free_type_font_path").setValue(self.font_path)

        # Set values for arbitrary knobs and values.
        if self.additional_write_node_properties:
            self.set_node_knob_values_from_dict(write_node, self.additional_write_node_properties)

        if self.additional_write_node_properties:
            self.set_node_knob_values_from_dict(write_node, self.additional_write_node_properties)

        if self.root_node_properties:
            self.set_node_knob_values_from_dict(root_node, self.root_node_properties)

        # If there is no bottom node, set the read node as the bottom_node
        if not bottom_node:
            bottom_node = read_node

        write_node.setInput(0, bottom_node)

        # Save out the generated nuke script.
        script_path = "{root_dir}/{task_name}.nk".format(
            root_dir=self.temp_dir,
            task_name=self.full_name,
        )

        # Now that everything is concatenated, substitute all the replacements:
        import wolfkrow.core.utils as utils        
        all_nodes = nuke.allNodes()
        for node in all_nodes:
            for knob_name in node.knobs():
                knob = node[knob_name]
                knob_value = knob.value()
                if isinstance(knob_value, basestring):
                    new_knob_value = self.resolver.resolve(knob_value)
                    if knob_value != new_knob_value:
                        try:
                            knob.setValue(new_knob_value)
                        except Exception as exception:
                            import traceback
                            traceback.print_exc()
                            print("Warning: Unable to substitute knob '{}' on node '{}' with replacements. Old Value: {} vs. New Value {}".format(node, knob, knob_value, new_knob_value))

                index = 0
                if knob.hasExpression(index):
                    animations = knob.animations()
                    for index, animation in enumerate(animations):
                        expression = animation.expression()
                        expression = re.sub("\\\\{", "{", expression)
                        expression = re.sub("\\\\}", "}", expression)
                        new_expression = self.resolver.resolve(expression)
                        if expression != new_expression:
                            try:
                                knob.setExpression(new_expression, index)
                            except Exception as exception:
                                import traceback
                                traceback.print_exc()
                                print("Warning: Unable to substitute expression knob '{}' on node '{}' with replacements. Old Value: {} vs. New Value {}".format(node, knob, knob_value, new_knob_value))

        script_dir = os.path.dirname(script_path)
        if not os.path.exists(script_dir):
            try:
                os.makedirs(script_dir)
            except OSError as error:
                if error.errno != errno.EEXIST:
                    raise

        # Get all the correct knob values for the write node. (This is used later - See NOTE below)
        correct_knob_values = {}
        for knob in self.additional_write_node_properties:
            if knob in write_node.knobs():
                value = write_node.knob(knob).value()
                correct_knob_values[knob] = value

        ocio_file = root_node.knob("OCIOConfigPath").value()
        print("Using OCIO: {}".format(ocio_file))

        print("Saved Nuke script to: \n\n{}\n\n".format(script_path))
        nuke.scriptSaveAs(script_path, overwrite=1)

        # NOTE: Nuke on Windows has a nasty bug where it changes some of the knob 
        # settings on the write node when saving the script. This error only occurs 
        # when running nuke in terminal mode, and currently seems to only affect 
        # the codec profile knobs (More testing is required for specific knobs 
        # effected).
        # To get around this, we are going to open the nuke script after saving 
        # as a text file, then use some regex magic to find the Write node and 
        # confirm it's correct - If not, we will print a warning (To assist with 
        # understanding how it's wrong for the Foundry bug report), and then 
        # correct the value to what it should be.
        # This bug seems to only manifest when the following conditions are met:
        #   - Nuke is run in terminal mode.
        #   - Specific knobs are set on the Write node. (mov_prores_codec_profile as example)
        #   - The write node was created in the current terminal session. (A 
        #     pre-existing write node in an opened nuke script lets you set the 
        #     knob correctly)

        print ("Validating the nuke script is correct...")
        with open(script_path, "r") as script_file:
            script_text = script_file.read()
        
        # Find the Write node in the script.
        write_node_regex = r"Write \{(?:.|\n)*?\n[ ]*\}"

        write_node_text_matches = re.findall(write_node_regex, script_text)
        for write_node_text_match in write_node_text_matches:
            write_node_text = write_node_text_match

            # We only want to modify the wolfkrow write node. We should leave 
            # other write nodes intact.
            if self.write_node_name not in write_node_text:
                continue

            for knob in correct_knob_values:
                correct_knob_value = correct_knob_values[knob]
                knob_regex = f"{knob} [\"']?(.*)[\"']"
                knob_text_match = re.search(knob_regex, write_node_text)
                if knob_text_match:
                    knob_value = knob_text_match.group(1)
                    if knob_value != correct_knob_value:
                        print("Warning: Knob '{}' on Write node is incorrect. Expected: '{}', Found: '{}'".format(knob, correct_knob_value, knob_value))
                        print("Correcting...")
                        write_node_text = re.sub(knob_regex, f"{knob} \"{correct_knob_value}\"", write_node_text)

        # Now sub the corrected write node into the script.
        script_text = re.sub(write_node_regex, write_node_text, script_text)

        with open(script_path, "w") as script_file:
            script_file.write(script_text)

        return 0


# INFO: ===========================================================================
# Nuke Render Run is the part of the nuke render which actually does the rendering.
# The first task handles the concatenation and generation of the nuke script.
# =================================================================================

class NukeRenderRun(NukeTask, SequenceTask):
    """ NukeRender Task implementation. Will accept a list of nuke scripts, concatenate 
        them together (See "TODO: concatenation" function for logic), then substitute 
        the replacements for each.

        Will create a Read node at the top of the node graph with the specified settings.
        Will create a Write node at the bottom of the node graph with the specified settings.
    """

    script = TaskAttribute(default_value=None, configurable=True, attribute_type=str, 
        description="list of nuke scripts to concatenate together. Python scripts will be executed."
    )

    write_node = TaskAttribute(default_value=None, configurable=True, attribute_type=str, 
        description="Name of the write node to execute in the script."
    )

    increment = TaskAttribute(
        default_value=1, 
        configurable=True, 
        attribute_type=int, 
        description="The increments to use when rendering. Ex: 10 will render every 10th frame."
    )

    def __init__(self, **kwargs):
        """ Initialize the NukeRenderRun Object

            Kwargs:
        """
        super(NukeRenderRun, self).__init__(**kwargs)

    def validate(self):
        """ Preforms Validation checks for NukeRenderRun Task.

            Raises:
                TaskValidationException: NukeRenderRun task is not properly initialized
        """
        super(NukeRenderRun, self).validate()

    def setup(self):
        """ Will create destination directory if it does not already exist.

            Raises: 
                OSError: Unable to create destination directory
        """
        pass

    def run(self):
        """ Performs the nuke render.
        """
        # Import nuke here because the main engine which creates the tasks will not be run in a nuke process.
        import nuke

        print("Rendering nuke script: \n\n{}\n\n".format(self.script))

        ocio_file = nuke.root().knob("OCIOConfigPath").value()
        print("Using OCIO: {}".format(ocio_file))

        # Open the nuke script.
        nuke.scriptOpen(self.script)

        print(f"Executing: {self.write_node}: {self.start_frame}-{self.end_frame}:{self.increment}")
        # Execute the write node to kick off the render.
        nuke.execute(self.write_node, self.start_frame, self.end_frame, self.increment)
        return 0
