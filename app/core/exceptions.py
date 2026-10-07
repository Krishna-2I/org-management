class AppException(Exception):
    status_code = 500
    code = "internal_error"
    default_message = "Something went wrong"

    def __init__(self, message: str | None = None, details=None):
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppException):
    status_code = 400
    code = "bad_request"
    default_message = "Bad request"


class UnauthorizedError(AppException):
    status_code = 401
    code = "unauthorized"
    default_message = "Authentication required"


class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"
    default_message = "You do not have permission to do this"


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"
    default_message = "Resource not found"


class ConflictError(AppException):
    status_code = 409
    code = "conflict"
    default_message = "Resource already exists or conflicts"
