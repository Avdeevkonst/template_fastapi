class Oauth2Error(Exception):
    """Base class for custom exception applicatioin"""


class SchemaError(Oauth2Error):
    """Occurs when the type of a variable is unexpected"""
