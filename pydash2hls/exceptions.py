class PyDash2HLSException(Exception):
    """Exceptions used by pydash2hls."""


class InvalidPath(PyDash2HLSException):
    """File path is invalid."""


class InvalidFileContent(PyDash2HLSException):
    """Contents of the file is not a DASH file or is incompatible."""


class InvalidProfile(PyDash2HLSException):
    """Selected profile is invalid."""


class MissingRemoteUrl(PyDash2HLSException):
    """Remote file url is required."""
