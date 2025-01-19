from builtins import str
from builtins import range
from builtins import object
from past.builtins import basestring

import copy
import datetime
import os
import platform
import re
import string

from string import Formatter

class WolfkrowFormatter(Formatter):
    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth, auto_arg_index=0):
        """
            Overwrite the _vformat method of the Formatter class to allow for optional
            {} style replacements. If the replacement is not found in the replacements
            then it will simply be kept as is.
        """
        if recursion_depth < 0:
            raise ValueError('Max string recursion exceeded')
        result = []
        for literal_text, field_name, format_spec, conversion in \
                self.parse(format_string):

            # output the literal text
            if literal_text:
                result.append(literal_text)

            # if there's a field, output it
            if field_name is not None:
                # this is some markup, find the object and do
                #  the formatting

                # handle arg indexing when empty field_names are given.
                if field_name == '':
                    if auto_arg_index is False:
                        raise ValueError('cannot switch from manual field '
                                         'specification to automatic field '
                                         'numbering')
                    field_name = str(auto_arg_index)
                    auto_arg_index += 1
                elif field_name.isdigit():
                    if auto_arg_index:
                        raise ValueError('cannot switch from manual field '
                                         'specification to automatic field '
                                         'numbering')
                    # disable auto arg incrementing, if it gets
                    # used later on, then an exception will be raised
                    auto_arg_index = False

                # given the field_name, find the object it references
                #  and the argument it came from

                # WOLFKROW CUSTOMIZATION: If the field_name is not found in the 
                # kwargs or args, then just return the original string
                try:
                    obj, arg_used = self.get_field(field_name, args, kwargs)
                except (KeyError, IndexError):
                    obj = "{" + field_name
                    if format_spec:
                        obj += ":" + format_spec
                    
                    if conversion:
                        obj += conversion

                    obj += "}"
                    result.append(obj)
                    continue
                # WOLFKROW CUSTOMIZATION END

                used_args.add(arg_used)

                # do any conversion on the resulting object
                obj = self.convert_field(obj, conversion)

                # expand the format spec, if needed
                format_spec, auto_arg_index = self._vformat(
                    format_spec, args, kwargs,
                    used_args, recursion_depth-1,
                    auto_arg_index=auto_arg_index)

                # format the object and append to the result
                result.append(self.format_field(obj, format_spec))

        return ''.join(result), auto_arg_index

class Resolver(object):

    RESOLVER_TOKEN = "#resolver"
    SGTK_TEMPLATE_REGEX = "(SGTKTEMPLATE<)(.*?)(>)"
    DATETIME_REGEX = "(DATE<)(.*?)(>)"

    # We want to store the current time once, so that all date tokens are using the exact same time
    TIME = datetime.datetime.now()

    def __init__(self, replacements, search_paths=None, path_swap_lookup=None, sgtk=None, resolver_token=RESOLVER_TOKEN):
        """_summary_

        Args:
            replacements (dict): Dictionary of values to use as the replacements.

        Kwargs:
            search_paths (list): List of paths to use in place of the RESOLVER_TOKEN.
            path_swap_lookup (dict): Lookup dictionary for swapping paths between 
                different operating systems. Allows for different operating 
                systems to be used from submission to execution of a task.
            sgtk: Optional Shotgun toolkit instance to allow the use of templates.
        """
        self.path_swap_lookup = path_swap_lookup or {}
        self.sgtk = sgtk
        self.resolver_token = resolver_token

        # Store a reference to the original replacements dict, so any updates are 
        # automatically updated here as well.
        self._replacements = replacements

        if not replacements:
            self._replacements = {}

        # We need to perform the os path swap before resolving the replacements 
        # because otherwise the prefix resolve will always fail because they won't
        # be searching for the correct paths.
        self.search_paths = [] 
        for search_path in search_paths or []:
            self.search_paths.append(self._os_path_swap(search_path))

        # TODO: We get lots of resolvers defined, and so we need to resolve all the
        #   same replacements many times... We should try to optimize this because 
        #   wolfkrow is noticeably slower than it should be.
        self.resolved_replacements = self.resolve_replacements(self._replacements)

    def refresh_replacements(self, replacements=None):
        """ Refreshes the replacements dict. This is useful if you want to update 
            the replacements dict and then refresh the resolved replacements.

            Should be called by the Task whenever it's replacements are updated.

        Kwargs:
            replacements (dict): *Optional* New dictionary of replacements to 
                use in place of the current replacements.
        """

        if replacements:
            self._replacements = replacements

        self.resolved_replacements = self.resolve_replacements(self._replacements)

    def resolve_replacements(self, replacements):
        """ Iterates through the replacements dict and resolves any replacements 
            that are within other replacements.

            NOTE: This is not a recursive function, so there is no risk of an infinite 
                replacements loop. eg: foo = "{bar}", bar = "{foo}". 
                If such a case exists, you will not get an error, the looped 
                replacement will simply not be resolved. The final unreplaced 
                replacement will change depending on the order that the replacements 
                are iterated through.
        """

        # First we copy the replacements so that we can modify them without affecting the original.
        replacements = copy.deepcopy(replacements)

        # For each replacement, we iterate through all other replacements and resolve it.
        for replacement in replacements:
            # Get the current replacement
            single_replacement = {replacement: replacements[replacement]}

            # Now iterate through all the other replacements and resolve it.
            for replacement_b in replacements:
                replacements[replacement_b] = self.resolve(
                    replacements[replacement_b], 
                    replacements=single_replacement
                )

        return replacements

    def resolve(self, value, replacements=None):
        """
        Recurses into dicts + lists searching for {replacement_name} or
        @resolver tokens, replacing them with the corresponding value found in
        the replacements dict or path found on disk.

        NOTE: This function recursively iterates through a dictionary or list.
        Dictionaries or lists containing themselves will cause infinite
        recursion.

        Args:
            value (str, dict or list): An instance to do replacements for.
            replacements (dict): The replacements to use for replacing instead of the replacements assigned on this object.
        """
        replaced_value = copy.copy(value)

        if isinstance(value, dict):
            for key, dict_value in list(value.items()):
                replaced_value[key] = self.resolve(dict_value, replacements=replacements)

        elif isinstance(value, list):
            for index, list_value in list(enumerate(value)):
                replaced_value[index] = self.resolve(list_value, replacements=replacements)

        elif isinstance(value, basestring):
            replaced_value = self._replace_replacements(value, replacements=replacements)
            replaced_value = self._resolve_prefix(replaced_value, replacements=replacements)
            replaced_value = self._os_path_swap(replaced_value)

        return replaced_value

    def _resolve_prefix(self, path, replacements=None):
        """
        
        NOTE: This is called from the resolve method which will pass in ALL values 
            found in the wolfkrow task graph. Most of these will not be paths, 
            but this function is intended to only work for paths. The intention
            is that the user only adds the resolver token to a path value. Otherwise,
            this function will do nothing because it checks for paths on disk.

        Args:
            path (str): The path to try and call the resolver on.
            replacements (dict):  Dictionary of values to use as the replacements.
            resolver_token (str, optional): The token to search for at the start 
                of path. Defaults to the RESOLVER_TOKEN attribute.

        Returns:
            str: The resolved path.
        """
        # The resolver only resolves prefix values that start with the token.
        if not path.startswith(self.resolver_token):
            return path

        # Strip the resolver token from the path. Also strip the leading slash if present.
        path_postfix = path[len(self.resolver_token):]
        if path_postfix.startswith(os.path.sep) or path_postfix.startswith(os.path.altsep):
            path_postfix = path_postfix[1:]

        searched_paths = []
        for search_path in self.search_paths:
            resolved_path = os.path.join(search_path, path_postfix)

            # It's possible that the search_path variable has some replacements 
            # which have not been resolved yet, so we need to resolve the path 
            # again now.
            search_path = self._replace_replacements(resolved_path, replacements=replacements)

            searched_paths.append(search_path)
            # See if we resolved to a path that exists.
            if os.path.exists(search_path):
                return search_path

        # No valid path was found. Return the original path, and print a warning.
        print("Warning: Could not resolve path '{}'".format(path))
        print("Searched paths:")
        for searched_path in searched_paths:
            print("    {}".format(searched_path))

        return path

    def _replace_replacements(self, value, replacements=None):

        # First, expand environment variables.
        # Doing this first allows us to set environment variables inside of a replacement
        # name which will allow for some neat use cases. Such as setting the name of the
        # replacement you want to use in the environment. IE: {$MY_REPLACEMENT_NAME_FROM_ENV}
        value = os.path.expandvars(value)

        # Next, replace any date tokens.
        date_regexp = self.DATETIME_REGEX
        matches = re.findall(date_regexp, value)
        for match in matches:
            date_format = match[1]
            sub = "DATE<{}>".format(date_format)
            try:
                date_value = self.TIME.strftime(date_format)
            except ValueError:
                print("Error: Could not format date with format: {}".format(date_format))
                print("See pythons's dattime documentation for valid date formats.")
                date_value = sub
            value = value.replace(sub, date_value)

        replacements = replacements or self.resolved_replacements

        # If there are no replacements passed in, then there is nothing left to do.
        # This is useful in cases where we don't have replacements, but still want to 
        # do environment variable  or date expansion.
        if replacements is None:
            return value

        # Replace the replacements following the regular string format syntax ("{name}").
        # Note: Replacing these replacements first, allows you to use a replacement 
        # in the name of a SGTK template.
        try:
            value = WolfkrowFormatter().vformat(value, (), replacements)
        except:
            print("Replacements: {}".format(replacements))
            print("Error: Could not replace replacements in value: {}".format(value))

            raise

        # Check for SGTK templates defined in the config.
        regexp = self.SGTK_TEMPLATE_REGEX
        replace_str = "SGTKTEMPLATE<{}>"
        matches = re.findall(regexp, value)
        for match in matches:
            template_name = match[1]
            template_value = self._get_sgtk_template_value(template_name)
            if template_value:
                sub = replace_str.format(match[1])
                value = value.replace(sub, template_value)

        # Finally replace any extra environment variables which were added from the 
        # values of replaced replacements.
        value = os.path.expandvars(value)

        return value

    def _get_sgtk_template_value(self, template_name, replacements=None):
        """ Will attempt to find the given template name in the sgtk instace, and 
            then use the replacements dict as the fields to get the substituted
            template.
        """

        replacements = replacements or self.resolved_replacements

        if self.sgtk is None:
            # TODO: ERROR: Workflow builder initialized without sgtk instance, 
            # BUT sgtk templates found in workflow.
            return None

        template = self.sgtk.templates.get(template_name)
        if template is None:
            return None

        # Ensure that the replacements dict contains all the fields required for the template.
        missing_fields = template.missing_keys(replacements)
        if len(missing_fields) > 0:
            return None

        # Attempt to convert the fields to the correct type before calling 
        # apply_fields for the template.
        corrected_fields = {}

        for field in template.keys:
            if field in replacements:
                corrected_fields[field] = template.keys[field].value_from_str(str(replacements[field]))

        value = template.apply_fields(corrected_fields)
        return value

    def _os_path_swap(self, value):
        """ Perform path swapping based on the swap_paths dict. 

        This is helpful for running wolfkrow on different operating systems. There
        will occasionally be cases where you run wolfkrow on one operating system,
        but then execute the tasks on another operating system.

        The swap_paths dict allows you to specify paths for multiple operating
        systems and automatically swap between them based on he current operating
        system.

        NOTE: This just performs a blind string substitution. Meaning if any 
            swap paths accidentally appear in a string, they will be swapped 
            regardless of whether or not they are paths.

        Args:
            value (str): The value to swap the paths in.
        """

        if not self.path_swap_lookup:
            return value

        system = platform.system().lower()
        for swap_path in self.path_swap_lookup:
            # We use the first path in the list of paths for the current OS.
            # This is important so that the user can configure a consistent 
            # default which paths get mapped to.
            current_os_path_options = self.path_swap_lookup[swap_path][system]

            # Only perform the swap if the root path is not already a valid path 
            # for this OS
            if swap_path not in current_os_path_options and swap_path in value:
                default_os_path = current_os_path_options[0]
                value = value.replace(swap_path, default_os_path)

        return value
