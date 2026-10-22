class QoraStateError(Exception):
    """Base error for durable QORA state operations."""


class StateNotFoundError(QoraStateError):
    pass


class StateVersionConflictError(QoraStateError):
    pass


class DuplicateEventError(QoraStateError):
    pass


class InvalidStateUpdateError(QoraStateError):
    pass

