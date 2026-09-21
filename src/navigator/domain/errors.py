from __future__ import annotations


class NavigatorError(Exception):
    """Base application/domain error."""


class InvalidInn(NavigatorError, ValueError):
    pass


class CompanyNotFound(NavigatorError):
    pass


class CompanyLookupUnavailable(NavigatorError):
    pass


class ProfileIncomplete(NavigatorError):
    pass


class InvalidStateTransition(NavigatorError):
    pass


class MeasureNotFound(NavigatorError):
    pass


class ChecklistAlreadyExists(NavigatorError):
    pass


class ChecklistNotFound(NavigatorError):
    pass


class RateLimitExceeded(NavigatorError):
    pass
