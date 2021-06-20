""" Module implementing a nuke render task.
"""

import errno
import os
import shutil

from .task import Task, TaskAttribute
from .task_exceptions import TaskValidationException


class NukeRender(Task):
    """ NukeRender Task implementation. Will accept a list of nuke scripts, concatenate 
        them together (See "TODO: concatenation" function for logic), then substitute 
        the replacements for each.

        Will create a Read node at the top of the node graph with the specified settings.
        Will create a Write node at the bottom of the node graph with the specified settings.
    """

    scripts = TaskAttribute(default_value="", configurable=True, attribute_type=list, 
        description="list of nuke scripts to concatenate together. Python scripts will be executed.")

    # Attributes for read node
    source = TaskAttribute(default_value="", configurable=True, attribute_type=str)

    # Attributes for write node
    write_node_class = TaskAttribute(default_value="Write", configurable=True, attribute_type=str)
    destination = TaskAttribute(default_value="", configurable=True, attribute_type=str)
    file_type = TaskAttribute(default_value="exr", configurable=True, attribute_type=str)
    bit_depth = TaskAttribute(default_value="16 bit half", configurable=True, attribute_type=str)
    codec = TaskAttribute(default_value=8, configurable=True, attribute_options=range(0, 13), attribute_type=int, description="""Which Codec to render the quicktime with.
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
        0 - ZIP (1 scanlines)
        1 - ZIP (16 scanlines)
        2 - PIZ Wavelet (32 scanlines)
        3 - RLE
        4 - B44
        5 - B44a
        6 - DWAA
        7 - DWAB
    
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

    # Render frame range, and frame increment
    start_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int)
    end_frame = TaskAttribute(default_value=None, configurable=True, attribute_type=int)
    increment = TaskAttribute(
        default_value=1, 
        configurable=True, 
        attribute_type=int, 
        description="The increments to use when rendering. Ex: 10 will render every 10th frame."
    )
    additional_write_node_properties = TaskAttribute(
        default_value=None, 
        configurable=True, 
        attribute_type=dict, 
        description="Dictionary containing key value pairs as 'knob_name': 'knob_value'"
    )

    def __init__(self, **kwargs):
        """ Initialize the NukeRender Object

            Kwargs:
        """
        super(NukeRender, self).__init__(**kwargs)
        self.executable = "Nuke 12.2v2.lnk"

    def validate(self):
        """ Preforms Validation checks for NukeRender Task.

            Raises:
                TaskValidationException: NukeRender task is not properly initialized
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

    def export_to_command_line(self, deadline=False):
        """ Will generate a `wolfkrow_run_task` command line command to run in order to 
            re-construct and run this task via command line. 

            Appends a '--' to the end of the command because nuke will try to execute
            accept the last arguments as a frame number/range.
        """
        obj, command = super(NukeRender, self).export_to_command_line(deadline=deadline)
        command = "{} --".format(command)
        return (obj, command)

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
            top_node.set_input(0, current_bottom_node)

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


    def run(self):
        """ Performs the nuke render.
        """

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
        read_node.knob("file").setValue(self.source)
        read_node.knob("first").setValue(self.start_frame)
        read_node.knob("last").setValue(self.end_frame)
        if top_node:
            top_node.setInput(0, read_node)

        # Create Write node for self.destination
        write_node = nuke.createNode(self.write_node_class)
        write_node.knob("file").setValue(self.destination)
        write_node.knob("file_type").setValue(self.file_type)

        if self.file_type in ["exr", "dpx", "png", "tiff", "sgi"]:
            write_node.knob("datatype").setValue(self.bit_depth)
        elif self.file_type in ["mov"]:
            write_node.knob("mov64_codec").setValue(self.codec)

        if self.file_type in ["exr", "sgi", "targa", "tiff"]:
            if self.compression:
                write_node.knob("compression").setValue(self.compression)

        # Set values for arbitrary knobs and values.
        if self.additional_write_node_properties:
            for key, value in self.additional_write_node_properties.items():
                if key in write_node.knobs():
                    write_node.knob(key).setValue(value)

        # If there is no bottom node, set the read node as the bottom_node
        if not bottom_node:
            bottom_node = read_node

        write_node.setInput(0, bottom_node)

        # Save out the generated nuke script.
        script_path = "{root_dir}/{task_name}.nk".format(
            root_dir=self.temp_dir,
            task_name=self.name,
        )
        nuke.scriptSaveAs(script_path, overwrite=1)

        # Execute the write node to kick off the render.
        nuke.execute(write_node.knob("name").value(), self.start_frame, self.end_frame, self.increment)
        return 0