1.8.0

Welcome to Wolfkrow's First official release notes! This is a fairly big one that brings Wolfkrow much closer to being useful as a standalone tool.
Development will be picking up for the coming Months/Years so be sure to reach out if you have any questions or bug reports.

Also, A first pass at the documentation page is coming soon as well!

# Features

* Lots of general code cleanup and refactoring.
* Task & TaskGraph prefix support. (This should make merging task graphs easier)
* New dependency inheritance mode. (Useful depending on how you want dependencies to be resolved when merging TaskGraphs)
* Json export method is now the default. All other export methods are officially deprecated and will be removed in a future release
* Added slightly improved Task logging to assist with debugging.
    * NukeRender tasks now print the nuke script being created/used for rendering
    * The Json file path is printed when parsing it.
* Inclusion and exclusion filters for environment variables when submitting jobs to Deadline. (See the settings file for more details)
* Replacements now supported in resolver search paths, and the temp directory.
* New ConcatenateQuicktime Task which uses ffmpeg to join multiple quicktimes files together.
* New ShotgunUploadMedia Task which uploads the specified media file to a SG entity.
* New ShotgunUpdateEntity Task which updates fields for the specified Entity in SG
* New ShotgunCreateEntity Task which creates an entity in SG. Takes an optional entity_code attribute. If supplied it will search SG for the entity, and if found, update it rather than create a new one.
* Updated Codec TaskAttribute on the NukeRender task so it expects the Codec name, rather than the index in the dropdown in Nuke. This is a breaking change, so you will need to update your wolfkrow.yml files after updating.
* New external_dependencies attribute available on all Tasks. Use to add a dependency to an existing Deadline job unrelated to the Wolfkrow submission. (Initial set up to queue up a TaskGraph to run immediately after a render completes)
* New NukeSubmitter

# Bug Fixes

* Deadline job submission now correctly prints the job names during submission.
* General bug fixes for Windows support

## Resolver

There are some massive changes to the Resolver in this release so it gets it's own section. This is a greatly improved version of the Resolver and should help make things much cleaner and easier to use.

# Features
* Added new DATE<> resolver token which uses dattimes's strftime under the hood. A single datetine object is constructed the first time the resolver is imported, and reused for all DATE<> tokens.
* Replaced pythons default string .format function with a new version which allows optional `{}` tokens.
* You can use pythons built in string .format formatting. Ex: {version:0>3} which forces 3 digit padding on the version number.
* Changed when replacements are resolved. <-- Small change but large impact. This gets it's own section (See below)
* Replacements within other replacements are now supported.
* When resolving a value, you can now pass in an alternative dictionary of replacements to use instead of the replacements the resolver was initialized with.

# Bug Fixes
* Fixed bug when using multiple sgtk templates in a single string for resolving.
* The resolver no longer modifies the original value passed in.
NOTE: This means that the resolver only returns copies of the original value. (This is very relevant See below)

# Changes to when replacements are resolved

The resolver has always resolved replacements at the earliest opportunity, typically immediately during parsing the of the wolfkrow.yml files.
This has 3 large issues:
1. Any errors or warnings during resolving had to be raised immediately.
2. Even unused replacements had to be resolved (Meaning extra errors and warnings)
3. Changes to the replacements dictionary after parsing the wolfkrow.yml files would not affect the Tasks.

The first is the largest, because the resolver resolved replacements regardless of whether or not they were used. This makes for an overly verbose resolver when warning about failed replacements. OR a not verbose at all resolver.

The second doesn't come up often, but fixing this allows for more control for task definitions over their own replacements.

The new resolver now delays resolving any replacements until the last possible moment.
Now, every Task object initializes it's own resolver, with it's own replacements. Then, the TaskAttributes use this resolver to resolve individual TaskAttributes whenever they are retrieved.
This means that changes to a Tasks replacements will always affect the TaskAttributes. This also means that the resolver can be verbose about failed replacements, because the only replacements which get resolved are replacements which are actually used and required.

Now, this add's a gotcha when writing new Tasks. There was a bug-fix which updated the resolver so that it passes a copy of the original value, rather than modifying it in place. Now that the TaskAttribute is resolving it's value before returning it, this means that it's difficult to update the value of TaskAttributes in a intuitive pythonic way. Ex: The following code will only update the copy of the replacements dictionary. The next time you retrieve the replacements, it will return a new copy of the original value.
```
my_task = Task(<args>)
my_task.replacements["foo"] = "bar"

"foo" in my_task.replacements
False
```
To solve this now, Task definitions need to be diligent in how they retrieve TaskAttributes to modify them.
```
my_task = Task(<args>)

# Get the TaskAttribute value with resolving turned off
replacements = Task.replacements.__get__(self, resolve=False)
replacements["foo"] = "bar"

"foo" in my_task.replacements
True
```
For this reason, it's recommended to define setter functions for TaskAttributes which you want to allow developers to update.
Ex: Task's come with a `update_replacements` function which allows developers to update replacements on a Task object without having to worry about this new un-intuitive feature.

NOTE: This weird behavior is hopefully temporary until I come up with a way of returning intuitive normalcy.

## Nuke Submitter

Very rough initial implementation of a standalone Wolfkrow job submitter. This implementation is in Nuke and is intended to bulk submit all the selected read nodes.

Does some initial work to determine rudementary replacements for each node, and the submits the selected workflow for each ReadNode.

**Emphasis on very rough** This current version is barely fit for purpose, and is intended for proof of concept. A more fleshed out version to come soon. 
When used in combination with the new SG based Tasks, this is intended to be a competitor for SGTK's tk-multi-publish2 app. 