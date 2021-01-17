import os
import re
import string
import yaml


def load_settings(settings_file):
    with open(settings_file, "r") as handle:
        file_contents = handle.read()
    settings = yaml.load(file_contents, Loader=yaml.FullLoader)
    return settings

settings = None
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
            replace_replacements_dict_crawler(value, replacements)
        elif isinstance(value, list):
            for index in range(len(value)):
                if isinstance(value[index], dict):
                    replace_replacements_dict_crawler(value[index], replacements)
                elif isinstance(value[index], str):
                    value[index] = string.Formatter().vformat(value[index], (), replacements)
        elif isinstance(value, str):                    
            # Replace any replacements in the string.
            dictionary[key] = _replace_replacements(value, replacements, sgtk=sgtk)

def _replace_replacements(value, replacements, sgtk=None):

    # Replace the replacements following the regular string format syntax ("{name}").
    # Note: Replacing these replacements first, allows you to use a replacement 
    # in the name of a SGTK template.
    value = string.Formatter().vformat(value, (), replacements)

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

    missing_fields = template.missing_keys(replacements)
    if len(missing_fields) > 0:
        return None

    value = template.apply_fields(replacements)
    return value
# ==============================================================================