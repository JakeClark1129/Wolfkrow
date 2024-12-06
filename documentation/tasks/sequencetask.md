# SequenceTask

The Sequence Task is an abstract task which cannot be used directly, but it defines the behavior of many other tasks (Such as the NukeRender Task).

The Sequence Tasks purpose is to handle the sequential nature of many tasks in VFX, primarily anything working with image sequences.

The main difference between Sequence Tasks, and normal Tasks is that Sequence Tasks contain start frame, end frame, and chunk size. These values are used during the task export multiple tasks depending on the frame range and chunk size.

NOTE: Has custom behavior for Deadline where a single task is exported, but provides Deadline with the information required to render in multiple tasks.

Additional TaskAttributes:

start_frame: Frame to start the task from
end_frame: Frame to end the task
chunk_size: Number of frame to split each task into for running on multiple machines. 0 to perform no chunking.