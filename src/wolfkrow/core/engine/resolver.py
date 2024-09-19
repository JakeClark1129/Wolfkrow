from __future__ import print_function
from builtins import str
from builtins import range
from builtins import object
from past.builtins import basestring

import os
import re
import string

class ReplacementsDict(dict):
    """ Implement the __missing__ method for dictionary so that it returns '{<key>}' 
        when the value is not present so that when it is passed to the str.format 
        function, missing keys do not raise an exception.
    """

    def __missing__(self, key):
        return "{" + key + "}"

class Resolver(object):

    RESOLVER_TOKEN = "@resolver"
    SGTK_TEMPLATE_REGEX = "(SGTKTEMPLATE<)(.*)(>)"

    def __init__(self, replacements, search_paths, sgtk=None, resolver_token=RESOLVER_TOKEN):
        """_summary_

        Args:
            replacements (dict): Dictionary of values to use as the replacements.
            sgtk: Optional Shotgun toolkit instance to allow the use of templates.
        """
        self.replacements = replacements
        self.search_paths = search_paths
        self.sgtk = sgtk
        self.resolver_token = resolver_token

    def resolve(self, value):
        """
        Recurses into dicts + lists searching for {replacement_name} or
        @resolver tokens, replacing them with the corresponding value found in
        the replacements dict or path found on disk.

        NOTE: This function recursively iterates through a dictionary or list.
        Dictionaries or lists containing themselves will cause infinite
        recursion.

        Args:
            value (str, dict or list): An instance to do replacements for.
        """
        # FIXME(TM): Should this deep copy? We're currently changing lists +
        # dicts in place.
        replaced_value = value

        if isinstance(value, dict):
            for key, dict_value in list(value.items()):
                replaced_value[key] = self.resolve(dict_value)

        elif isinstance(value, list):
            for index, list_value in list(enumerate(value)):
                replaced_value[index] = self.resolve(list_value)

        elif isinstance(value, basestring):
            replaced_value = self._replace_replacements(value)
            replaced_value = self._resolve_prefix(replaced_value)

        return replaced_value

    def _resolve_prefix(self, path):
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
            search_path = self._replace_replacements(resolved_path)

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

    def _replace_replacements(self, value):

        # First, expand environment variables.
        # Doing this first allows us to set environment variables inside of a replacement
        # name which will allow for some neat use cases. Such as setting the name of the
        # replacement you want to use in the environment. IE: {$MY_REPLACEMENT_NAME_FROM_ENV}
        value = os.path.expandvars(value)

        # If there are no replacements passed in, then there is nothing left to do.
        # This is useful in cases where we don't have replacements, but still want to 
        # do environment variable expansion.
        if self.replacements is None:
            return value

        # Replace the replacements following the regular string format syntax ("{name}").
        # Note: Replacing these replacements first, allows you to use a replacement 
        # in the name of a SGTK template.
        try:
            value = string.Formatter().vformat(value, (), self.replacements)
        except IndexError:
            # There is some cases where "value" might contain sub-strings like {0}, 
            # which will fail with an index error because we are passing an empty set
            # into the vformat call.
            # TODO: Define a special list, which when indexed returns a string.
            #   EG: smart_list[4] == "{4}"
            #   which will allow us to just leave these string as they were without 
            #   catching any exceptions.
            print("Warning: Failed to replace value '{}'".format(value))

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
        # values of replaceed replacements.
        value = os.path.expandvars(value)

        return value
        
    def _get_sgtk_template_value(self, template_name):
        """ Will attempt to find the given template name in the sgtk instace, and 
            then use the replacements dict as the fields to get the substituted
            template.
        """

        if self.sgtk is None:
            # TODO: ERROR: Workflow builder initialized without sgtk instance, 
            # BUT sgtk templates found in workflow.
            return None

        template = self.sgtk.templates.get(template_name)
        if template is None:
            return None

        # Ensure that the replacements dict contains all the fields required for the template.
        missing_fields = template.missing_keys(self.replacements)
        if len(missing_fields) > 0:
            return None

        # Attempt to convert the fields to the correct type before calling 
        # apply_fields for the template.
        corrected_fields = {}

        for field in template.keys:
            if field in self.replacements:
                corrected_fields[field] = template.keys[field].value_from_str(str(self.replacements[field]))

        value = template.apply_fields(corrected_fields)
        return value
