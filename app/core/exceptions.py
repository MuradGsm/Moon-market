class AppError(Exception):
    status_code = 400
    detail = "Bad request"


class EmailAlreadyExists(AppError):
    status_code = 409
    detail = "Email already registered"


class InvalidCredentials(AppError):
    status_code = 401
    detail = "Invalid email or password"


class InvalidToken(AppError):
    status_code = 401
    detail = "Invalid or expired token"


class PermissionDenied(AppError):
    status_code = 403
    detail = "Not enough permissions"

