class Oauth2Error(Exception):
    """Base class for custom exception applicatioin"""


class SchemaError(Oauth2Error):
    """Occurs when the type of a variable is unexpected"""


class AlreadyDisconnectedError(Oauth2Error):
    """Base class for connection error"""


class WsAlreadyDisconnectedError(AlreadyDisconnectedError):
    """Occurs when user not in connection pool"""
