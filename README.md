# PyDash2HLS

[![License](https://img.shields.io/github/license/hyugogirubato/pydash2hls)](https://github.com/hyugogirubato/pydash2hls/blob/master/LICENSE)
[![Release](https://img.shields.io/github/release-date/hyugogirubato/pydash2hls)](https://github.com/hyugogirubato/pydash2hls/releases)
[![Latest Version](https://img.shields.io/pypi/v/pydash2hls)](https://pypi.org/project/pydash2hls/)

PyDash2HLS is a Python library for converting DASH (Dynamic Adaptive Streaming over HTTP) manifest files to HLS (HTTP
Live Streaming) format.

## Features

- Convert MPD files to HLS format
- Support for remote and local MPD files
- Retrieve media URLs for a specific profile
- Handle DRM (Digital Rights Management) information in MPD files

## Installation

You can install PyDash2HLS using pip:

````shell
pip install pydash2hls
````

## Usage

### Converter Initialization

To initialize the Converter class, you can use the following methods:

#### Initialization from a Remote URL

````python
from pydash2hls import Converter

# Initialize Converter from a remote URL
url = "http://example.com/manifest.mpd"
converter = Converter.from_remote(url)
````

#### Initialization from a Local File

````python
from pydash2hls import Converter
from pathlib import Path

# Initialize Converter from a local file
file_path = Path("path/to/manifest.mpd")
converter = Converter.from_local(file_path)
````

### Building HLS Manifest

To build an HLS manifest for a specific profile, you can use the `build_hls()` method:

````python
# Build HLS manifest for a profile
profile_id = "profile1"
hls_manifest = converter.build_hls(profile_id)
````

### Getting Media URLs

To retrieve a list of media URLs for a specific profile, you can use the `media_urls()` method:

````python
# Get media URLs for a profile
profile_id = "profile1"
media_urls = converter.media_urls(profile_id)
````

### Exceptions

The following exceptions can be raised by PyDash2HLS:

- `InvalidPath`: Raised when the file path is invalid.
- `InvalidFileContent`: Raised when the contents of the file are not in DASH format or are incompatible.
- `InvalidProfile`: Raised when the selected profile is invalid.
- `MissingRemoteUrl`: Raised when a remote file URL is required but not provided.

### License

This project is licensed under the [GPL v3 License](https://github.com/hyugogirubato/pydash2hls/blob/master/LICENSE).

