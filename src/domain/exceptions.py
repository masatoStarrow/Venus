"""
Domain exceptions for the interactions service.
"""


class DomainError(Exception):
    """Base domain error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class InteractionNotFoundError(DomainError):
    def __init__(self, message: str = "No existe una interacción con ese ID") -> None:
        super().__init__(code="INTERACTION_NOT_FOUND", message=message)


class ClientNotFoundError(DomainError):
    def __init__(self, message: str = "No existe un cliente con ese ID") -> None:
        super().__init__(code="CLIENT_NOT_FOUND", message=message)


class InteractionAlreadyClosedError(DomainError):
    def __init__(self, message: str = "La interacción ya está cerrada") -> None:
        super().__init__(code="INTERACTION_ALREADY_CLOSED", message=message)


class ForbiddenError(DomainError):
    def __init__(self, message: str = "No tiene permisos para esta acción") -> None:
        super().__init__(code="FORBIDDEN", message=message)


class AttachmentNotFoundError(DomainError):
    def __init__(self, message: str = "No existe un adjunto con ese ID") -> None:
        super().__init__(code="ATTACHMENT_NOT_FOUND", message=message)


class FileTooLargeError(DomainError):
    def __init__(self, message: str = "El archivo excede el tamaño máximo permitido (10 MB)") -> None:
        super().__init__(code="FILE_TOO_LARGE", message=message)


class InvalidFileTypeError(DomainError):
    def __init__(self, message: str = "Tipo de archivo no permitido") -> None:
        super().__init__(code="INVALID_FILE_TYPE", message=message)
