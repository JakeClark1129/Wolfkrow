# NukeRender

The NukeRender task is a task that executes a nuke render with the given parameters. It accepts a single input, and a list of nuke scripts to use for rendering. The nuke scripts are not treated as typical Nuke scripts, instead they should have no Read node, or Write node at the top and bottom of the script tree. These nuke scripts get concatenated into a single script which is used for rendering. This is ideal because it allows you to quickly build modular nuke scripts to complete a render task.

The modularity provides a distinct advantage to a single large nuke script because it allows you to re-use the same nuke script in multiple processes. Then, if you want to change how something is done, you are able to substitute just a small part of the nuke script. 
This is especially useful when you have 2 similar processes that have slightly different requirements. For example, some processes might by identical except for the final resolution and color space of the output. This would allow you to swap out a "reformat_to_1920x1080.nk" nuke script, with a "reformat_to_3840x2160.nk" nuke script. 


# Nuke Script Concatenation

The list of nuke scripts passed into the task will be concatenated together into a single script. To keep the concatenation process simple and free of odd behavior, it's recommended to follow these rules:
1. There is a single node tree.
2. There is a single valid "Top" node.
3. There is no downward branching (Multiple outputs are not allowed).

To start, we open a fresh nuke script, then paste each script in order. After each paste, we calculate the Bottom and Top nodes, and then connect the top node to the previous pastes bottom node.

After concatenation is finished, a Read node is created and connected to the Top node, and a write node is created and connected to the Bottom node.

## Top Node

The top node is found by searching for a node called "top" in the script tree.

Failing this, it will start at the bottom node of the script tree, then recursively traverse depth first up the script tree. then return the first node with 0 inputs found. 
The top node must only accept a single input. If your top node is a multi-input node (such as merge), then it's recommended you attach a Dot node to the input you wish to be treated as the top.

## Bottom Node:

The bottom node is found by searching for a node called "bottom" in the script tree.

Failing this, it will pick a random node, and then traverse downwards until it finds the bottom node.

# Replacements

After the script concatenation, we iterate through every knob in every node in the script tree to resolve and replacements. This allows you to use replacements in expressions and text nodes to customize the behavior of nuke scripts based on the content being processed.


# Additional TaskAttributes:

scripts: List of nuke scripts to concatenate together
source: File path to the source file(s) to use. Used to create a read node at the top of the nuke script.
write_node_class: The class of the write node to create. Defaults to "Write"
write_node_name: Name of the write node to create/render from. If left unset, will automatically determine its own name (recommended)
destination: The file path to write the output to. Is used to create a write node at the bottom of the nuke script
file_type: The file type to set on the write node. Defaults to "exr"
bit_depth: The bit depth to set on the write node. Defaults to "16 bit half"
codec: The codec to write the Quicktime with. Defaults to "Photo - JPEG"
compression: The Compression algorithm to use when writing the file.
input_start_frame: The start frame of the source to start from.
input_end_frame: The end frame of the source to end at. 
render_start_frame: The start frame to renumber the output to. 
render_end_frame: The end frame to stop rendering at (After the renumbering)
render_increment: The increments to use when rendering. Ex: 10 will render every 10th frame.
chunk_size: Number of frames to split each task into for running on multiple machines. 0 to perform no chunking.
generate_quicktime_in_chunks: Whether or not to generate quicktimes in chunks. Must normally be followed up by a ConcatenateQuicktime task.
additional_read_node_properties: Dictionary containing key value pairs as 'knob_name': 'knob_value'
additional_write_node_properties: Dictionary containing key value pairs as 'knob_name': 'knob_value'
root_node_properties: Dictionary containing key value pairs as 'knob_name': 'knob_value'

NOTE: Not all TaskAttributes are active at the same time. Ex: The codec is only active when the file_file is "mov", and bit depth is only active when the output type is "exr", "dpx" or any other output type with a bit depth. Refer to Nuke to know which values are available in which scenarios. 