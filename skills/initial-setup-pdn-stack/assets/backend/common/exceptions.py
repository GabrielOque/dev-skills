"""
The API error contract: every error response is

    {"code": "SCREAMING_SNAKE_CASE", "message": "English, for developers", "detail": ...?}

`code` is stable and machine-readable — the frontend maps it to the copy a
person reads. `message` is for logs and developers, never shown in the UI.
`detail` is optional context (field errors, the position of a bad line…).
"""

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

STATUS_CODES = {
    status.HTTP_400_BAD_REQUEST: ("MALFORMED_REQUEST", "The request body could not be parsed"),
    status.HTTP_401_UNAUTHORIZED: ("AUTHENTICATION_REQUIRED", "Authentication credentials were not provided or are invalid"),
    status.HTTP_403_FORBIDDEN: ("PERMISSION_DENIED", "You don't have permission to perform this action"),
    status.HTTP_404_NOT_FOUND: ("NOT_FOUND", "The requested resource was not found"),
    status.HTTP_405_METHOD_NOT_ALLOWED: ("METHOD_NOT_ALLOWED", "Method not allowed"),
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: ("UNSUPPORTED_MEDIA_TYPE", "Unsupported media type"),
    status.HTTP_429_TOO_MANY_REQUESTS: ("TOO_MANY_REQUESTS", "Too many requests, try again later"),
}


class ServiceError(APIException):
    """
    A business rule refused the operation.

    Raise it from a service (or a view) and DRF answers
    `{"code", "message", "detail"?}` with `status_code`:

        raise ServiceError("ROLE_NAME_TAKEN", "A role with that name already exists", 409)
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "SERVICE_ERROR"

    def __init__(self, code, message, status_code=status.HTTP_400_BAD_REQUEST, detail=None):
        body = {"code": code, "message": message}
        if detail is not None:
            body["detail"] = detail
        super().__init__(body)
        self.status_code = status_code


def _already_in_contract(data):
    code = data.get("code") if isinstance(data, dict) else None
    return isinstance(code, str) and code.isupper()


def api_exception_handler(exc, context):
    """Normalizes every DRF error to the contract above. Errors DRF does not
    handle (real bugs) still propagate as 500s and get logged."""
    response = drf_exception_handler(exc, context)
    if response is None or _already_in_contract(response.data):
        return response

    data = response.data
    if isinstance(exc, ValidationError):
        response.data = {
            "code": "VALIDATION_ERROR",
            "message": "The submitted data is invalid",
            "detail": data,
        }
        return response

    # simplejwt answers `{"detail", "code": "token_not_valid", "messages"}`.
    if isinstance(data, dict) and data.get("code") == "token_not_valid":
        response.data = {"code": "TOKEN_INVALID", "message": "The token is invalid or expired"}
        return response

    code, message = STATUS_CODES.get(response.status_code, ("ERROR", "The request could not be processed"))
    body = {"code": code, "message": message}
    if isinstance(data, dict) and data.get("detail"):
        body["detail"] = str(data["detail"])
    response.data = body
    return response
