from enum import Enum

class AuditEvent(str, Enum):
    read = "READ"
    create = "CREATE"
    update = "UPDATE"
    delete = "DELETE"