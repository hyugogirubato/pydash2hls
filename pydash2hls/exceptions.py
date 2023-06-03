class PyDash2HLSException(Exception):
    """Exceptions used by pydash2hls."""


class InvalidPath(PyDash2HLSException):
    """Invalid file path."""


class InvalidFileContent(PyDash2HLSException):
    """The contents of the file are not in DASH format or are incompatible."""


class InvalidProfile(PyDash2HLSException):
    """The selected profile is invalid."""


class MissingRemoteUrl(PyDash2HLSException):
    """Remote file URL is missing."""
