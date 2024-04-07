from enum import Enum


class UserRole(Enum):
    user = "user"
    administrator = "admin"
    noone = ""


class WSAction(Enum):
    CREATE = "CREATE"
    DELETE = "DELETE"
    UPDATE = "UPDATE"
