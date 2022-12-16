# pydash2hls
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Release](https://img.shields.io/github/release-date/hyugogirubato/pydash2hls?style=plastic)](https://github.com/hyugogirubato/pydash2hls/releases)
![Total Downloads](https://img.shields.io/github/downloads/hyugogirubato/pydash2hls/total.svg?style=plastic)

Python library to convert DASH file to HLS.

# Usage

### Basic Usage

```python
>>> from pydash2hls import Converter
>>> converter = Converter.from_local('manifest.mpd')
>>> converter = Converter.from_remote(method='GET', url='https://...') # Recommended option
>>> profiles = converter.profile
>>> hls_content = converter.build_hls(profile_id=profiles[0]['id'])
>>> with open('index.m3u8', mode='w', encoding='utf-8') as f:
...    f.write(hls_content)
...    f.close()
```

# Installation

To install, you can either clone the repository and run `python setup.py install`
