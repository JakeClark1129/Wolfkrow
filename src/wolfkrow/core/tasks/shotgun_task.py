""" Module implementing the FileCopy task.
"""

import re

from wolfkrow.core.tasks.task import Task, TaskAttribute
from wolfkrow.core.tasks.task_exceptions import TaskValidationException

class ShotgunTask(Task):
    """ Base Task for all tasks that interact with shotgun. This task handles 
        creation of a shotgun connection, and authentication.
    """

    shotgun_site = TaskAttribute(
        default_value=None, 
        required=True,
        configurable=False,
        description="The url to your shotgun site."
    )

    http_proxy = TaskAttribute(
        default_value=None, 
        required=False,
        configurable=False,
        attribute_type=str,
        description="HTTP proxy server to reroute SG traffic through."
    )

    authenticated_user = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="Serialized authenticated user to be deserialized on the farm. Deprecated, Please use user name, and auth token instead.")

    user_name = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="User name of user to authenticate with"
    )

    auth_token = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="The Auth token to use for the user."
    )

    session_metadata = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="Metadata for the users session."
    )

    script_name = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="The name of the script as it is registered in shotgun."
    )

    api_key = TaskAttribute(
        default_value=None,
        required=False,
        configurable=False,
        description="The unique identifier of the API key for the script being run."
    )

    def __init__(self, **kwargs):
        """ Initialize the ShotgunTask Object

            Args:
        """
        super(ShotgunTask, self).__init__(**kwargs)

    def validate(self):
        """ Preforms Validation checks to ensure the ShotgunTask Task is properly initialized.

            Raises:
                TaskValidationException: ShotgunTask task is not properly initialized
        """

        for attr_name, attr in list(self.task_attributes.items()):
            if attr.required is True and getattr(self, attr_name) is None:
                
                raise TaskValidationException("Required argument {arg} not supplied.".format(
                    arg=attr_name
                ))

    def setup(self):
        """ Sets up shotgun connection to be used later in the run method.
        """

        if self.user_name and self.auth_token:
            import sgtk
            authenticator = sgtk.authentication.ShotgunAuthenticator()

            user = authenticator.create_session_user(
                login=self.user_name,
                session_token=self.auth_token,
                host=self.shotgun_site,
                http_proxy=self.http_proxy,
                session_metadata=self.session_metadata
            )
            self._sg = user.create_sg_connection()

        elif self.authenticated_user is not None:
            # in some cases, the '\n' character will be interpreted as '\\n' (backslash, 
            # and an n). Fix that here.
            self.authenticated_user = self.authenticated_user.replace("\\n", "\n")

            import sgtk
            user = sgtk.authentication.deserialize_user(self.authenticated_user)
            self._sg = user.create_sg_connection()
        elif self.script_name and self.api_key:
            import shotgun_api3
            self._sg = shotgun_api3.Shotgun(
                self.shotgun_site, 
                script_name=self.script_name, 
                api_key=self.api_key
            )


    def process_sg_fields(self, fields):
        """ Process SG fields to ensure they are in the correct format for the shotgun api.

            Args:
                fields (dict): The fields to process

            Returns:
                dict: The processed fields
        """

        entity_schema = self._sg.schema_field_read(self.entity_type)

        processed_fields = {}

        sg_type_conversion_map = {
            "number": int,
            "float": float,
            "entity": dict,
        }

        for field in fields:
            field_value = fields[field]

            sg_schema_type = entity_schema.get(field, {}).get("data_type", {}).get("value")
            python_schema_type = sg_type_conversion_map.get(sg_schema_type)

            # If our field is not the same type that the SG Scheme expects, then let's convert it.
            if python_schema_type and not isinstance(field_value, python_schema_type):
                field_value = TaskAttribute.convert_to_type(field_value, python_schema_type)

            # For Entities we check for the ID field and convert it to an int.
            if sg_schema_type == "entity" and isinstance(field_value, dict):
                field_value = field_value.copy() # Copy the dict so we don't modify the original

                id = field_value.get("id")
                if id:
                    try:
                        field_value["id"] = int(id)
                    except ValueError:
                        print("Warning: Could not convert ID to int: {}".format(id))

            elif sg_schema_type == "url" and isinstance(field_value, dict):
                field_value = field_value.copy() # Copy the dict so we don't modify the original

                # SG has a bug on Windows where backslashes MUST be used for the 
                # drive letter, or it doubles up on the drive letter.
                # Autodesk internal Ticket number to reference to follow up on this issue:
                #   SG-4373
                windows_path_regex = "[a-zA-Z]:/"
                for key in field_value:
                    if key == "local_path" or key == "local_path_windows":
                        if re.match(windows_path_regex, field_value[key]):
                            print("Warning: Detected Windows Drive Letter path in field '{}'. ".format(field))
                            print("    Converting slashes to backslashes.")
                            print("    This is required due to a bug in Shotgun")
                            field_value[key] = field_value[key].replace("/", "\\")

            processed_fields[field] = field_value

        return processed_fields
