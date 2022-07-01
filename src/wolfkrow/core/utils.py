import os
import re
import string
import yaml


settings = None 
def load_settings(settings_file):
    global settings
    with open(settings_file, "r") as handle:
        file_contents = handle.read()
    settings = yaml.load(file_contents, Loader=yaml.Loader)
    return settings

default_settings_file = os.path.join(os.path.dirname(__file__), "settings.yaml")
load_settings(default_settings_file)


# ==============================================================================
# Replacement Utilities
# ==============================================================================
class ReplacementsDict(dict):
    """ Implement the __missing__ method for dictionary so that it returns '{<key>}' 
        when the value is not present so that when it is passed to the str.format 
        function, missing keys do not raise an exception.
    """

    def __missing__(self, key):
        return "{" + key + "}"

def replace_replacements_dict_crawler(dictionary, replacements, sgtk=None):
    """ Iterates through a dictionary looking for {replacement_name} tokens, and
        replaces them with the corresponding value found in the replacements dict.

        Args:
            dictionary: Dictionary containing strings to replace the replacements for.
            replacements: Dictionary of values to use as the replacements.
            sgtk: Optional Shotgun toolkit instance to allow the use of templates.
    """

    for key, value in dictionary.items():
        if isinstance(value, dict):
            replace_replacements_dict_crawler(value, replacements, sgtk=sgtk)
        elif isinstance(value, list):
            for index in range(len(value)):
                if isinstance(value[index], dict):
                    replace_replacements_dict_crawler(value[index], replacements, sgtk=sgtk)
                elif isinstance(value[index], str):
                    value[index] = string.Formatter().vformat(value[index], (), replacements)
        elif isinstance(value, str):                    
            # Replace any replacements in the string.
            dictionary[key] = replace_replacements(value, replacements, sgtk=sgtk)

def replace_replacements(value, replacements, sgtk=None):

    # Replace the replacements following the regular string format syntax ("{name}").
    # Note: Replacing these replacements first, allows you to use a replacement 
    # in the name of a SGTK template.
    try:
        value = string.Formatter().vformat(value, (), replacements)
    except IndexError:
        # There is some cases where "value" might contain sub-strings like {0}, 
        # which will fail with an index error because we are passing an empty set
        # into the vformat call.
        # TODO: Define a special list, which when indexed returns a string.
        #   EG: smart_list[4] == "{4}"
        #   which will allow us to just leave these string as they were without 
        #   catching any exceptions.
        print("Warning: Failed to replace value '{}'".format(value))
        pass

    # Check for SGTK templates defined in the config.
    regexp = "(SGTKTEMPLATE<)(.*)(>)"
    replace_str = "SGTKTEMPLATE<{}>"
    matches = re.findall(regexp, value)
    for match in matches:
        template_name = match[1]
        template_value = _get_sgtk_template_value(template_name, replacements, sgtk=sgtk)
        if template_value:
            sub = replace_str.format(match[1])
            value = value.replace(sub, template_value)

    return value

def _get_sgtk_template_value(template_name, replacements, sgtk=None):
    """ Will attempt to find the given template name in the sgtk instace, and 
        then use the replacements dict as the fields to get the substituted
        template.
    """

    if sgtk is None:
        # TODO: ERROR: Workflow builder initialized without sgtk instance, BUT sgtk templates found in workflow.
        return None

    template = sgtk.templates.get(template_name)
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
# ==============================================================================