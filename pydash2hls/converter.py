from __future__ import annotations

import os
import requests
import xmltodict

from pydash2hls.exceptions import InvalidPath, InvalidFileContent, InvalidProfile, MissingRemoteUrl


class Converter:

    def __init__(self, mdp_srt, mdp_json, url):
        self.mdp_srt = mdp_srt
        self.mdp_json = mdp_json
        self.mdp_url = url
        # init
        self.profile = self._manifest_profile()

    @classmethod
    def from_remote(cls, method, url, **kwargs) -> Converter:
        r = requests.request(method=method, url=url, **kwargs)
        if not r.ok:
            raise InvalidPath("Unable to load remote file.")
        mdp_srt = r.content.decode('utf-8')
        try:
            mdp_json = xmltodict.parse(mdp_srt)
        except Exception as e:
            raise InvalidFileContent(f"Unable to load file, {e}")
        return cls(mdp_srt, mdp_json, url)

    @classmethod
    def from_local(cls, path: str) -> Converter:
        if not os.path.exists(path):
            raise InvalidPath('Invalid file path.')
        with open(path, mode='rb') as f:
            mdp_srt = f.read().decode('utf-8')
            f.close()
        try:
            mdp_json = xmltodict.parse(mdp_srt)
        except Exception as e:
            raise InvalidFileContent(f"Unable to load file, {e}")
        return cls(mdp_srt, mdp_json, None)

    @staticmethod
    def _get_key(adaptation: dict, representation: dict, key: str) -> str:
        value = representation[key] if key in representation else None
        if value is None:
            value = adaptation[key] if key in adaptation else None
        return value

    def _get_profile(self, profile_id: str) -> dict:
        profile = None
        for p in self.profile:
            if p['id'] == profile_id:
                profile = p
                break
        if profile is None:
            raise InvalidProfile(f"Profile does not exist, {profile_id}")
        return profile

    def _manifest_profile(self) -> list:
        source = None if self.mdp_url is None else '/'.join(self.mdp_url.split('/')[:-1])
        profiles = []

        for adaptation in self.mdp_json['MPD']['Period']['AdaptationSet']:
            drm = {}
            if 'ContentProtection' in adaptation:
                for protection in adaptation['ContentProtection']:
                    KEYS = [
                        ['@cenc:default_KID', 'kid'],
                        ['cenc:pssh', 'widevine'],
                        ['mspr:pro', 'playready'],
                        ['ms:laurl', 'license']]

                    for key in KEYS:
                        if key[0] in protection:
                            drm[key[1]] = protection[key[0]]

            if type(adaptation['Representation']) == list:
                for representation in adaptation['Representation']:
                    mime_type = self._get_key(adaptation, representation, '@mimeType')
                    if mime_type is None:
                        mime_type = 'video/mp4' if 'avc' in representation['@codecs'] else 'audio/m4a'
                    start_with_sap = self._get_key(adaptation, representation, '@startWithSAP')
                    start_with_sap = '1' if start_with_sap is None else start_with_sap
                    profile = {
                        'id': representation['@id'],
                        'mimeType': mime_type,
                        'codecs': representation['@codecs'],
                        'bandwidth': int(representation['@bandwidth']),
                        'startWithSAP': start_with_sap
                    }
                    if 'audio' in profile['mimeType'] or '@audioSamplingRate' in representation:
                        profile['audioSamplingRate'] = representation['@audioSamplingRate']
                    else:
                        profile['width'] = int(representation['@width'])
                        profile['height'] = int(representation['@height'])
                        if '@frameRate' in representation:
                            frame_rate = representation['@frameRate']
                        elif '@maxFrameRate ' in adaptation:
                            frame_rate = adaptation['@maxFrameRate']
                        else:
                            frame_rate = '1/1'
                        frame_rate = frame_rate if '/' in frame_rate else f"{frame_rate}/1"
                        profile['frameRate'] = round(int(frame_rate.split('/')[0]) / int(frame_rate.split('/')[1]), 3)
                        profile['sar'] = representation.get('@sar', '1:1')

                    # build urls
                    fragments = []
                    if 'SegmentTemplate' in adaptation:
                        # Segment parts
                        position = 0
                        number = int(adaptation['SegmentTemplate']['@startNumber'] if '@startNumber' in adaptation['SegmentTemplate'] else 1) - 1
                        timescale = int(adaptation['SegmentTemplate']['@timescale'])
                        timelines = adaptation['SegmentTemplate']['SegmentTimeline']['S']
                        for timeline in timelines:
                            for i in range(int(timeline['@r']) + 1 if '@r' in timeline else 1):  # Fixed segment offset
                                # init
                                number += 1
                                extinf = int(timelines[position]['@d']) / timescale
                                media = adaptation['SegmentTemplate']['@media']
                                if not media.startswith('http'):
                                    if source is None:
                                        raise MissingRemoteUrl("Remote manifest url required.")
                                    media = f"{source}/{media}"

                                # build
                                if "$Number$" in media:
                                    media = media.replace("$Number$", str(number))
                                if "$Time$" in media:
                                    time = timelines[position]['@t'] if '@t' in timelines[position] else 0
                                    time += int(timelines[position]['@d'])
                                    media = media.replace("$Time$", str(time))
                                if "$RepresentationID$" in media:
                                    media = media.replace("$RepresentationID$", profile['id'])
                                if '$Bandwidth$' in media:
                                    media = media.replace('$Bandwidth$', str(profile['bandwidth']))
                                fragments.append({
                                    'range': '0-',
                                    'extinf': f"{extinf:.3f}",
                                    'media': media
                                })
                            position += 1
                    else:
                        # Direct link
                        segment = representation['SegmentBase']['@indexRange']
                        extinf = (int(segment.split('-')[1]) - int(segment.split('-')[0])) / 1000
                        fragments.append({
                            'range': segment,
                            'extinf': f"{extinf:.3f}",
                            'media': f"{source}/{representation['BaseURL']}"
                        })

                    profile['fragments'] = fragments
                    profile['drm'] = drm
                    profiles.append(profile)
            else:
                # Other sources
                pass
        return profiles

    def build_hls(self, profile_id: str) -> str:
        profile = self._get_profile(profile_id)

        if profile['fragments'][0]['media'].startswith('https://v.vrv.co/'):
            # HLS: VRV.co master m3u8
            hls = ['#EXTM3U']
            KEYS = [
                'f1-{T}1-x3',  # 720
                'f2-{T}1-x3',  # 1080
                'f3-{T}1-x3',  # 480
                'f4-{T}1-x3',  # 360
                'f5-{T}1-x3',  # 240
                'f6-{T}1-x3'  # 80
            ]
            source = profile['fragments'][0]['media']
            host = source.split('_,')[0]
            cloudflare = source.split('?')[1]
            files = source.split('_,')[1].split(',.urlset')[0].split(',')
            audio = self._get_profile(KEYS[0].replace('{T}', 'a'))
            for i in range(len(files)):
                video = self._get_profile(KEYS[i].replace('{T}', 'v'))
                hls.append(f'#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH={video["bandwidth"]},RESOLUTION={video["width"]}x{video["height"]},FRAME-RATE={video["frameRate"]},CODECS="{video["codecs"]},{audio["codecs"]}"')
                hls.append(f"{host}_{files[i]}/index-v1-a1.m3u8?{cloudflare}")
        else:
            # HLS: index m3u8
            hls = ['#EXTM3U', '#EXT-X-TARGETDURATION:4', '#EXT-X-ALLOW-CACHE:YES', '#EXT-X-PLAYLIST-TYPE:VOD']
            if 'licenseUrl' in profile['drm']:
                hls.append(f'#EXT-X-KEY:METHOD=SAMPLE-AES,URI="{profile["drm"]["license"]}"')
            hls += ['#EXT-X-VERSION:5', '#EXT-X-MEDIA-SEQUENCE:1']
            for fragment in profile['fragments']:
                hls.append(f"#EXTINF:{fragment['extinf']},")
                hls.append(fragment['media'])
            hls.append('#EXT-X-ENDLIST')
        return '\n'.join(hls)

    def media_urls(self, profile_id: str) -> list:
        profile = self._get_profile(profile_id)
        urls = []
        for fragment in profile['fragments']:
            urls.append(fragment['media'])
        return urls
