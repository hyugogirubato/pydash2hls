""""
Project: DashToHLS
File: main.py
Date: 2022.03.25
"""

import argparse
import json
import sys

import dash2hls


def _show_media(source):
    for i in range(len(source)):
        print(f"\nList of media available for: {source[i]['media']['label']}")
        print('{0:<6} {1:<14} {2:<14} {3:<14}'.format('Index', 'Type', 'Bandwidth', 'Quality', 'Codecs'))
        for media in source[i]['media']['representations']:
            if media['mimeType'] == 'video/mp4':
                print('{0:<6} {1:<14} {2:<14} {3:<14}'.format(
                    i,
                    media['mimeType'],
                    media['bandwidth'],
                    f"{media['width']}x{media['height']}",
                    media['codecs']
                ))
            else:
                print('{0:<6} {1:<14} {2:<14} {3:<14}'.format(
                    i,
                    media['mimeType'],
                    media['bandwidth'],
                    f"{media['audioSamplingRate']}",
                    ''
                ))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', type=str, default=None, help='Manifest file url.')
    parser.add_argument('--headers', type=str, default=None, help='Using a custom header.')
    parser.add_argument('--list', '-l', action='store_true', help='List of available media.')
    parser.add_argument('--media', '-m', type=int, default=0, help='Index of selected media.')
    parser.add_argument('--bandwidth', '-b', type=int, default=None, help='Choice of quality among the selected media.')
    parser.add_argument('--path', '-p', type=str, default=None, help='Custom save path of HLS file.')
    parser.add_argument('--output', '-o', type=str, default=None, help='Output file name (without extension).')
    args = parser.parse_args()

    try:
        headers = json.dumps(args.headers)
        if headers == 'null':
            headers = None
    except Exception as e:
        headers = None

    mdp = dash2hls.Converter(args.input, headers=headers)
    if args.list:
        _show_media(mdp.json_manifest)

    mdp.save_hls(mdp.json_manifest[args.media], args.bandwidth, path=args.path, file=args.output)
    sys.exit(0)


if __name__ == '__main__':
    main()
