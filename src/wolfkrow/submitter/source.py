

import os
import pyseq
import re

class SourceItem():
    def __init__(self, path):
        self.path = path

        self.frame_regex = re.compile(r"%(0[0-9]+)+d")
        pyseq_path = re.sub(self.frame_regex, "*", path)
        sequence = pyseq.get_sequences(pyseq_path)[0]

        self.pyseq = sequence

        self.replacements = self._get_replacements()

        # 0 is enabled, 1 unused (but means partial enabled), 2 is enabled
        self.enabled = 2

        self.name = self.replacements["basename"]

        self.selected_workflow = 0

    def _get_replacements(self):
        image_data = {}

        image_data["external_dependencies"] = ""

        basename = os.path.basename(self.path)
        # Put chunk size first, so it's early on in the options.
        if self.pyseq.length() > 0:
            start_frame = self.pyseq.start()
            end_frame = self.pyseq.end()
            frame_count = end_frame - start_frame + 1

            # This is an arbitrary number... Really, it should scale based on the number of render licenses/nodes you have.
            max_chunks = 30
            preferred_chunk_size = 48

            # Use 48 frame chunks unless the frame count is massive. In those cases
            # increase the chunk size to keep the number of chunks down to optimize
            # out the startup time of the tasks (Ex: Launching Nuke or Deadline 
            # worker startup process).
            if frame_count // preferred_chunk_size > max_chunks:
                image_data["chunk_size"] = frame_count // max_chunks
            else:
                image_data["chunk_size"] = preferred_chunk_size

        else:
            image_data["chunk_size"] = 1

        image_data["input_path"] = self.path
        image_data["file_name"] = basename

        base, extension = os.path.splitext(basename)

        image_data["extension"] = extension.lower()[1:]
        image_data["EXTENSION"] = extension.upper()[1:]

        image_data["total_size"] = self.pyseq.format("%H").strip()

        if self.pyseq.length() > 0:
            # Minimum of 4 digits for the frame padding
            last_frame_length = len(str(self.pyseq.end()))
            frame_padding = f"%0{last_frame_length if last_frame_length >= 4 else 4}d"
            image_data["frame_padding"] = frame_padding

            # The base name of the file without the frame number or extension. Assumes file_name.%04d.exr format.
            file_name = self.pyseq.format("%h")
            # Strip the extra . off the end.
            if file_name.endswith("."):
                file_name = file_name[:-1]
            image_data["basename"] = file_name

            # The original padding of the sequence
            image_data["source_frame_padding"] = self.pyseq.format("%p")

            # Start and end frames
            image_data["start_frame"] = start_frame
            image_data["end_frame"] = end_frame
            image_data["frame_range"] = f"{start_frame}-{end_frame}"
            image_data["frame_count"] = frame_count
            
            image_data["missing_frames"] = self.pyseq.missing()

        # TODO: This format string contains a bug in the padding number. Ensure it's set to %04d rather than %d.
        image_data["source_path"] = self.pyseq.format("%D%h%p%t")
        # TODO: This format string contains a bug in the padding number. Ensure it's set to %04d rather than %d.
        image_data["source_path_root"] = self.pyseq.format("%D")

        return image_data
    
    def get_replacement_by_index(self, index):
        """ NOTE: This relies on our replacements dict being ordered and created consistently... Will probably need to revisit this.
        """

        return list(self.replacements.values())[index]
    
    def set_replacement_by_index(self, index, value):
        key = list(self.replacements.keys())[index]
        self.replacements[key] = value

    