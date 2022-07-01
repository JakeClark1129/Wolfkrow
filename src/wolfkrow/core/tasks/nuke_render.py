""" Module implementing a nuke render task.
"""

import errno
import logging
import os

from .task import Task, TaskAttribute
from .sequence_task import SequenceTask
from .task_exceptions import TaskValidationException


class NukeTask(Task):
    def export_to_command_line(self, temp_dir=None, deadline=False):
        """ Will generate a `wolfkrow_run_task` command line command to run in 
            order to re-construct and run this task via command line. 

            Appends a '--' to the end of the command because nuke will try to accept
            the last arguments as a frame number/range.
        """
        exported = super(NukeTask, self).export_to_command_line(deadline=deadline)

        updated_exported = []
        # Append a "--" to the end of the command so that nuke does not consume 
        # the last argument as a frame number/range.
        for export in exported:
            obj, command = export
            command = "{} $".format(command)
            updated_exported.append((obj, command))
        return updated_exported

class NukeRender(NukeTask):

    scripts = TaskAttribute(default_value=[], configurable=True, attribute_type=list, 
        description="list of nuke scripts to concatenate together. Python scripts will be executed."
    )

    # Attributes for read node
    source = TaskAttribute(default_value="", configurable=True, attribute_type=str)

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
    codec = TaskAttribute(default_value=8, configurable=True, attribute_options=range(0, 13), attribute_type=int, 
        description="""
    Which Codec to render the quicktime with.
        0 - Apple ProRes 4444 XQ
        1 - Apple ProRes 4444
        2 - Apple ProRes 422 HQ
        3 - Apple ProRes 422
        4 - Apple ProRes 422 LT
        5 - Apple ProRes 422 Proxy
        6 - Avid DNxHD codec
        7 - N/A
        8 - Photo - JPEG
        9 - MPEG-1 Video
        10 - MPEG-4 Video
        11 - PNG
        12 - Animation
        13 - Uncompressed 10-bit 4:2:2
    """)
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

    # Input frame range
    input_start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int)
    input_end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int)

    # Render frame range, and frame increment
    render_start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int)
    render_end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int)
    render_increment = TaskAttribute(
        default_value=1, 
        configurable=True, 
        attribute_type=int, 
        description="The increments to use when rendering. Ex: 10 will render every 10th frame."
    )
    chunk_size = TaskAttribute(default_value=8, configurable=True, attribute_type=int, 
    description="Number of frames to split each task into for running on multiple machines. 0 to perform no chunking")
    generate_quicktimes_in_chunks = TaskAttribute(
        default_value=False, 
        configurable=True, 
        attribute_type=bool,
        description="Whether or not to generate quicktimes in chunks, or in a single "
            "render. Useful for long quicktimes which you want to concatenate back "
            "together after a distributed render on the farm."
    )
    additional_read_node_properties = TaskAttribute(
        default_value=None, 
        configurable=True, 
        attribute_type=dict, 
        description="Dictionary containing key value pairs as 'knob_name': 'knob_value'"
    )
    additional_write_node_properties = TaskAttribute(
        default_value=None, 
        configurable=True, 
        attribute_type=dict, 
        description="Dictionary containing key value pairs as 'knob_name': 'knob_value'"
    )
    root_node_properties = TaskAttribute(
        default_value=None, 
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
            task_name=self.name,
        )

        chunk_size = self.chunk_size
        if self.file_type.lower() in ["mov"] and self.generate_quicktimes_in_chunks is False:
            chunk_size = self.render_end_frame - self.render_start_frame + 1

        # Create NukeRenderRun task.
        nuke_render_run = NukeRenderRun(
            name=self.name + "_render",
            script=script_path, 
            write_node=self.write_node_name,
            start_frame=self.render_start_frame, 
            end_frame=self.render_end_frame, 
            increment=self.render_increment,
            chunk_size=chunk_size,
            command_line_executable=self.command_line_executable,
            python_script_executable=self.python_script_executable,
        )

        return [nuke_render_run]

    def validate(self):
        """ Preforms Validation checks for NukeRenderRun Task.

            Raises:
                TaskValidationException: NukeRenderRun task is not properly initialized
        """
        super(NukeRender, self).validate()

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
            must accept 1 input, and not have anything connected. (Write, 
            Constant, Merge, Switch, etc... are not acceptable)

            Will traverse up the node tree using depth-first traversal, and returns 
            the first acceptable node found.

            Note: This function makes assumptions about the node tree.
                1) There is no downward branching. (Multiple outputs are not allowed.)
                2) The current node tree is not cyclic. (Not possible in nuke currently)

            Args:
                bottom_node (Node): Node to get the top node of.
        """

        inputs = bottom_node.inputs()
        if inputs == 0 and bottom_node.maximumInputs() == 1:
            return bottom_node

        for i in range(0, inputs):
            input_node = bottom_node.input(i)
            # Nuke does not allow for cyclic node graphs, so we can assume that this will eventually return.
            top_node = self._find_top_node(input_node)
            if top_node is not None:
                return top_node
        
        # This node does not have any acceptable top_node nodes
        return None

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

        # Node indicating the bottom node was not found. Use slightly more intelligent ways to determing the bottom_node
        if bottom_node is None:
            bottom_node = self._find_bottom_node(top_node or random_node)

        # Node indicating the top node was not found. Use slightly more intelligent ways to determing the top_node
        if top_node is None:
            top_node = self._find_top_node(bottom_node)

        # No acceptable top_node found. don't connect anything.
        if top_node is None:
            print("Supplied nuke script '{nuke_script}' contains no acceptable top node. Skipping.").format(
                nuke_script=script
            )
            return current_bottom_node

        # Connect the current_bottom_node to the new scripts top_node. 
        # current_bottom_node will be None for an empty nuke script
        if current_bottom_node is not None:
            top_node.setInput(0, current_bottom_node)

        return bottom_node

    def _concatenate_nuke_scripts(self):
        current_bottom_node = None
        for script in self.scripts:
            _, ext = os.path.splitext(script)
            if ext == ".py":
                # TODO: execute python scripts (HOW???) Look into pyscript_knob
                # https://learn.foundry.com/nuke/developers/70/pythonreference/
                pass
            elif ext == ".nk":
                current_bottom_node = self._append_nuke_script(script, current_bottom_node)
        return current_bottom_node

    def set_node_knob_values_from_dict(self, node, value_dict):
        """ Will iterate a given a dictionary of knob_name: value, and will assign 
            each value found to the corresponding knob on the node.

            Args:
                node: The Node object of a nuke node.
                value_dict (dict): Dictionary of knob names, and the value to set.
        """

        for key, value in value_dict.items():
            if key in node.knobs():
                failed = False
                try:
                    knob = node.knob(key)
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
        bottom_node = self._concatenate_nuke_scripts()

        top_node = None
        # bottom_node will be None when there is no 'scripts' in self.scripts (or 
        # all scripts are empty/invalid)
        if bottom_node:
            # Determine the top node of the script, in order to attach a read node to it.
            top_node = self._find_top_node(bottom_node)

        # Create Read node for self.source
        read_node = nuke.createNode("Read")
        read_node.knob("raw").setValue(True)
        read_node.knob("file").setValue(self.source)
        read_node.knob("first").setValue(self.input_start_frame)
        read_node.knob("last").setValue(self.input_end_frame)

        if self.additional_read_node_properties:
            self.set_node_knob_values_from_dict(read_node, self.additional_read_node_properties)

        time_offset = None
        if self.input_start_frame != self.render_start_frame:
            time_offset = nuke.createNode("TimeOffset")
            time_offset.setSelected(False)
            time_offset.knob("time_offset").setValue(self.render_start_frame - self.input_start_frame)
            time_offset.setInput(0, read_node)

        if top_node:
            if time_offset:
                top_node.setInput(0, time_offset)
            else:
                top_node.setInput(0, read_node)

        # determine the destination file path:

        # If the destination is just a directory, calculate the output filename 
        # from the input name.
        if self.destination.endswith(os.sep):
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

        # Set values for arbitrary knobs and values.
        if self.additional_write_node_properties:
            self.set_node_knob_values_from_dict(write_node, self.additional_write_node_properties)

        if self.root_node_properties:
            root_node = nuke.toNode("root")
            self.set_node_knob_values_from_dict(root_node, self.root_node_properties)

        # If there is no bottom node, set the read node as the bottom_node
        if not bottom_node:
            bottom_node = read_node

        write_node.setInput(0, bottom_node)

        # Save out the generated nuke script.
        script_path = "{root_dir}/{task_name}.nk".format(
            root_dir=self.temp_dir,
            task_name=self.name,
        )

        # Now that everything is concatenated, substitute all the replacements:
        import wolfkrow.core.utils as utils        
        all_nodes = nuke.allNodes()
        for node in all_nodes:
            for knob_name in node.knobs():
                knob = node[knob_name]
                knob_value = knob.value()
                if isinstance(knob_value, basestring):
                    new_knob_value = utils.replace_replacements(knob_value, self.replacements)
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
                        import re
                        expression = animation.expression()
                        expression = re.sub("\\\\{", "{", expression)
                        expression = re.sub("\\\\}", "}", expression)
                        new_expression = utils.replace_replacements(expression, self.replacements)
                        if expression != new_expression:
                            try:
                                knob.setExpression(new_expression, index)
                            except Exception as exception:
                                import traceback
                                traceback.print_exc()
                                print("Warning: Unable to substitute expression knob '{}' on node '{}' with replacements. Old Value: {} vs. New Value {}".format(node, knob, knob_value, new_knob_value))
        nuke.scriptSaveAs(script_path, overwrite=1)
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

        # Open the nuke script.
        nuke.scriptOpen(self.script)

        # Execute the write node to kick off the render.
        nuke.execute(self.write_node, self.start_frame, self.end_frame, self.increment)
        return 0
