""""
Project: DashToHLS
File: dash2hls.py
Date: 2022.03.25
"""

import html
import os
import sys
import requests
from termcolor import cprint
from colorama import init

_REAL_PATH = os.path.realpath(__file__)
_DIR_PATH = os.path.dirname(_REAL_PATH)


def _eprint(message):
    cprint(f'ERROR: {message}', color='red')
    sys.exit(1)


def _get_text_manifest(url, headers):
    if headers is None:
        headers = {}
    if url is None:
        _eprint('Url required for manifest retrieval.')
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.text
    else:
        _eprint('Failed to get manifest.')


def _get_key(source, init=None, start='"', end='"'):
    try:
        if not init is None:
            source = source.split(init)[1]
        value = source.split(start)[1].split(end)[0]
        try:
            return int(value)
        except Exception as e:
            return value
    except Exception as e:
        return None


def _get_timeline(source):
    timescale = _get_key(source, start='timescale="', end='"')
    source = source.split('<SegmentTimeline>')[1].split('</SegmentTimeline>')[0]
    times = []
    for item in source.split('<S'):
        repeat = 1
        if 'd="' in item:
            if 'r="' in item:
                repeat = repeat + _get_key(item, start='r="', end='"')
            times.append({
                'start': _get_key(item, start='t="', end='"'),
                'duration': _get_key(item, start='d="', end='"'),
                'repeat': repeat
            })

    segment_count = 0
    for item in times:
        segment_count += item['repeat']

    return {
        'segmentCount': segment_count,
        'timescale': timescale,
        'times': times
    }


def _get_media_url(source, mdp_url):
    media_url = []
    media = _get_key(source, init='<SegmentTemplate', start='media="', end='"')
    if not media.startswith('http'):
        exist = False
        for item in source.split('<BaseURL'):
            if item.startswith('>http'):
                url = _get_key(item, start='>', end='</BaseURL')
                if not url is None:
                    exist = True
                    url = html.unescape(f'{url}{media}')
                    if not url in media_url:
                        media_url.append(url)
        if not exist:
            media_url.append(html.unescape(f"{mdp_url.split('?')[0].rsplit('/', 1)[0]}/{media}"))
    else:
        media_url.append(media)
    return media_url


def _get_media_representations(source):
    representations = []
    for item in source.split('<Representation'):
        if 'bandwidth' in item:
            if 'audioSamplingRate="' in item:
                representations.append({
                    'id': _get_key(item, start='id="', end='"'),
                    'mimeType': 'audio/mp4',
                    'bandwidth': _get_key(item, start=' bandwidth="', end='"'),
                    'audioSamplingRate': _get_key(item, start='audioSamplingRate="', end='"')
                })
            else:
                representations.append({
                    'id': _get_key(item, start='id="', end='"'),
                    'mimeType': 'video/mp4',
                    'codecs': _get_key(item, start='codecs="', end='"'),
                    'width': _get_key(item, start=' width="', end='"'),
                    'height': _get_key(item, start='height="', end='"'),
                    'bandwidth': _get_key(item, start=' bandwidth="', end='"')
                })

    return representations


def _get_json_manifest(source, mdp_url):
    items = []
    period = source.split('<Period>')[1].split('</Period>')[0]
    for adaptation in period.split('<AdaptationSet'):
        if '<Representation' in adaptation:
            label_id = _get_key(adaptation, start='id="', end='"')
            if 'maxWidth="' in adaptation:
                media_type = 'video'
                label = f'{label_id}_V_video'
            else:
                media_type = 'audio'
                label = f'{label_id}_A_audio'

            if '<Label>' in adaptation:
                label = _get_key(adaptation, start='<Label>', end='</Label>')

            items.append({
                'widevine': {
                    'pssh': _get_key(adaptation, start='<cenc:pssh>', end='</cenc:pssh>'),
                    'playReady': _get_key(adaptation, start='<mspr:pro>', end='</mspr:pro>'),
                    'licenseUrl': _get_key(adaptation, init='<ms:laurl', start='"', end='"'),
                    'kid': _get_key(adaptation, start='cenc:default_KID="', end='"')
                },
                'media': {
                    'label': label,
                    'type': media_type,
                    'timeline': _get_timeline(adaptation.split('<SegmentTemplate')[1].split('</SegmentTemplate>')[0]),
                    'url': _get_media_url(adaptation, mdp_url),
                    'representations': _get_media_representations(adaptation)
                }
            })
    return items


def _build_hls(source, media):
    hls = ['#EXTM3U', '#EXT-X-TARGETDURATION:2', '#EXT-X-ALLOW-CACHE:YES', '#EXT-X-PLAYLIST-TYPE:VOD']
    if not source['widevine']['licenseUrl'] is None:
        hls.append(f'#EXT-X-KEY:METHOD=SAMPLE-AES,URI="{source["widevine"]["licenseUrl"]}"')
    hls += ['#EXT-X-VERSION:3', '#EXT-X-MEDIA-SEQUENCE:1']
    url = source['media']['url'][0]
    range_count = source['media']['timeline']['segmentCount']
    if '$Bandwidth$' in url:
        range_count = len(source['media']['timeline']['times'])

    timescale = source['media']['timeline']['timescale']
    timeline = 0
    for i in range(range_count):
        if '$RepresentationID$' in url:
            url = url.replace('$RepresentationID$', str(media['id']))
        if '$Bandwidth$' in url:
            url = url.replace('$Bandwidth$', str(media['bandwidth']))

        if '$Time$' in url:
            item = source['media']['timeline']['times'][i]

            extinf = item['duration'] / timescale
            if not item['start'] is None:
                timeline = item['start']

            if timeline == 0 or not item['start'] is None:
                hls.append(f'#EXTINF:{extinf},')
                hls.append(url.replace('$Time$', str(timeline)))

            for t in range(item['repeat']):
                timeline += item['duration']
                hls.append(f'#EXTINF:{extinf},')
                hls.append(url.replace('$Time$', str(timeline)))

        elif '$Number$' in url:
            extinf = 0.0
            index = -1
            for item in source['media']['timeline']['times']:
                index += item['repeat']
                if index >= i:
                    extinf = item['duration'] / timescale
                    break

            hls.append(f'#EXTINF:{extinf},')
            hls.append(url.replace('$Number$', str(i + 1)))

    hls.append('#EXT-X-ENDLIST')
    return '\n'.join(hls)


class Converter:

    def __init__(self, url, headers=None):
        init()
        self.url = url
        self.text_manifest = _get_text_manifest(self.url, headers)
        try:
            self.json_manifest = _get_json_manifest(self.text_manifest, self.url)
        except Exception as e:
            _eprint('Unable to generate manifest json.')

    @staticmethod
    def get_hls(source, bandwidth):
        media = None
        if bandwidth is None:
            bandwidth = 0
            for item in source['media']['representations']:
                if item['bandwidth'] > bandwidth:
                    bandwidth = item['bandwidth']
                    media = item
        else:
            for item in source['media']['representations']:
                if item['bandwidth'] == bandwidth:
                    media = item
                    break
        if media is None:
            _eprint('The selected media is not available.')

        return _build_hls(source, media)

    def save_hls(self, source, bandwidth, path=None, file=None):
        hls = self.get_hls(source, bandwidth)
        if path is None:
            path = _DIR_PATH

        if file is None:
            file = 'index_video'
            if source['media']['type'] == 'audio':
                file = 'index_audio'

        output = os.path.join(path, f'{file}.m3u8')
        if not os.path.exists(path):
            os.makedirs(path)
        file = open(output, 'w', encoding='utf-8')
        file.write(hls)
        file.close()
