# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.5] - 2023-06-07

### Fixed

- Identification of DRM systems using the same key.
- Creation of the profile with `Representation` and/or `AdaptationSet`.
- Correction of the dynamic value `#EXT-X-TARGETDURATION`.

### Changed

- `startWithSAP` transformed into a boolean.

## [2.1.4] - 2023-06-06

### Added

- Added support for Widevine keys directly in HLS.

### Fixed

- Fixed support for multiple `Periods`.
- Corrected the `Representation` type.
- Handled missing `Initialization` segments.
- Fixed the `Timelines` type.
- Correctly calculated the number of segments.
- Fixed the base URL ending with a `/`.
- Fixed the range for direct links.

### Changed

- Limited the conversion to video/audio files only.
- Updated HLS version to `6`.
- Dynamically calculated `#EXT-X-MEDIA-SEQUENCE`.
- Dynamically calculated `#EXT-X-TARGETDURATION`.

## [2.1.3] - 2023-06-05

### Added

- Multiple representation support.

### Fixed

- DRM handle for multiple formats.
- Segment duration.

## [2.1.2] - 2023-06-04

### Changed

- Update `README.md`.

## [2.1.1] - 2023-06-04

### Changed

- New name of some variables.

## [2.1.0] - 2023-06-03

### Added

- Support for all web errors.

### Changed

- Import of a file using `pathlib`.
- Advanced customization of remote loading.
- Code optimization.

## [2.0.1] - 2022-12-16

### Added

- Loading of a remote file.
- Loading of a local file.
- Custom error handling in the library.
- Support for customized parameters.

### Fixed

- Generic link creation to `index.m3u8`.

### Changed

- Removed interactive mode.
- Removed specific creation of VRV links.
- Parsing of the DASH file using `xmltodict`.

## [1.0.0] - 2022-03-26

### Added

- Initial release.

[2.1.5]: https://github.com/hyugogirubato/pydash2hls/releases/tag/v2.1.5
[2.1.4]: https://github.com/hyugogirubato/pydash2hls/releases/tag/v2.1.4
[2.1.3]: https://github.com/hyugogirubato/pydash2hls/releases/tag/v2.1.3
[2.1.2]: https://github.com/hyugogirubato/pydash2hls/releases/tag/v2.1.2
[2.1.1]: https://github.com/hyugogirubato/pydash2hls/releases/tag/v2.1.1
[2.1.0]: https://github.com/hyugogirubato/pydash2hls/releases/tag/v2.1.0
[2.0.1]: https://github.com/hyugogirubato/pydash2hls/releases/tag/v2.0.1
[1.0.0]: https://github.com/hyugogirubato/pydash2hls/releases/tag/v1.0.0
