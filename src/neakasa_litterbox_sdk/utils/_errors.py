"""Readable descriptions of the network failures the transports wrap."""

from __future__ import annotations


def describe_cause(error: BaseException) -> str:
    """Return the error's message, or name the failure when it carries none.

    ``aiohttp`` reports an expired ``ClientTimeout`` as a bare
    ``TimeoutError`` whose ``str()`` is empty, which would leave the
    wrapping message ending in a dangling colon.
    """
    message = str(error)
    if message:
        return message
    if isinstance(error, TimeoutError):
        return "request timed out"
    return type(error).__name__
