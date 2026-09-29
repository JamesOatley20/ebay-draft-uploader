"""Create eBay UK drafts from local item folders."""

__version__ = "3.0.4"


class AppError(Exception):
    """An error that can be shown to the person using the app."""


class SessionStopped(AppError):
    """A local stop request, without cancelling a task on eBay."""
