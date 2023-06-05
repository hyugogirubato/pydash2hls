from __future__ import annotations

from pathlib import Path

import requests
import xmltodict

from pydash2hls.exceptions import InvalidFileContent, InvalidPath, InvalidProfile, MissingRemoteUrl


def _get_drm(adaptation: dict) -> dict:
    drm = {}
    for protection in adaptation.get("ContentProtection", []):
        keys = {
            "kid": "@cenc:default_KID",
            "widevine": "cenc:pssh",
            "playready": "mspr:pro",
            "license": "ms:laurl"
        }

        for key, value in keys.items():
            if value in protection:
                item = protection[value]
                drm[key] = item if isinstance(item, str) else item["#text"]
    return drm


class Converter:

    def __init__(self, mdp_srt: str, mdp_dict: dict, url: str = None):
        self.mdp_srt = mdp_srt
        self.mdp_dict = mdp_dict
        self.mdp_url = url
        self.profiles = self._manifest_profiles()

    @classmethod
    def from_remote(cls, url: str, **kwargs) -> Converter:
        r = requests.request(method=kwargs.get("method", "GET"), url=url, **kwargs)
        r.raise_for_status()
        mdp_srt = r.text
        try:
            mdp_dict = xmltodict.parse(mdp_srt)
        except Exception as e:
            raise InvalidFileContent(f"Unable to load file, {e}")
        return cls(mdp_srt, mdp_dict, url)

    @classmethod
    def from_local(cls, path: Path) -> Converter:
        if not path.is_file():
            raise InvalidPath("Invalid file path.")
        mdp_srt = path.read_text()
        try:
            mdp_dict = xmltodict.parse(mdp_srt)
        except Exception as e:
            raise InvalidFileContent(f"Unable to load file, {e}")
        return cls(mdp_srt, mdp_dict)

    @staticmethod
    def _get_key(adaptation: dict, representation: dict, key: str) -> str:
        return representation.get(key, adaptation.get(key, None))

    def _get_profile(self, profile_id: str) -> dict:
        for profile in self.profiles:
            if profile["id"] == profile_id:
                return profile
        raise InvalidProfile(f"Profile does not exist: {profile_id}")

    def _manifest_profiles(self) -> list:
        source = None if self.mdp_url is None else "/".join(self.mdp_url.split("/")[:-1])
        profiles = []

        for adaptation in self.mdp_dict["MPD"]["Period"]["AdaptationSet"]:
            if isinstance(adaptation["Representation"], list):
                for representation in adaptation["Representation"]:
                    mime_type = self._get_key(adaptation, representation, "@mimeType") or ("video/mp4" if "avc" in representation["@codecs"] else "audio/m4a")
                    start_with_sap = self._get_key(adaptation, representation, "@startWithSAP") or "1"
                    profile = {
                        "id": representation["@id"],
                        "mimeType": mime_type,
                        "codecs": representation["@codecs"],
                        "bandwidth": int(representation["@bandwidth"]),
                        "startWithSAP": start_with_sap
                    }
                    if "audio" in profile["mimeType"] or "@audioSamplingRate" in representation:
                        profile["audioSamplingRate"] = representation.get("@audioSamplingRate")
                    else:
                        profile["width"] = int(representation["@width"])
                        profile["height"] = int(representation["@height"])
                        frame_rate = representation.get("@frameRate") or adaptation.get("@maxFrameRate") or "1/1"
                        frame_rate = frame_rate if "/" in frame_rate else f"{frame_rate}/1"
                        profile["frameRate"] = round(int(frame_rate.split("/")[0]) / int(frame_rate.split("/")[1]), 3)
                        profile["sar"] = representation.get("@sar", "1:1")

                    drm = _get_drm(adaptation)
                    item = adaptation.get("SegmentTemplate")
                    if not item:
                        item = representation.get("SegmentTemplate")
                        drm = _get_drm(representation)

                    fragments = []
                    if item:
                        position = 0
                        number = int(item.get("@startNumber", 1)) - 1
                        timescale = int(item["@timescale"])
                        timelines = item["SegmentTimeline"]["S"]
                        for timeline in timelines:
                            for _ in range(int(timeline.get("@r", 1))):
                                number += 1
                                extinf = int(timelines[position]["@d"]) / timescale
                                media = item["@media"]
                                if not media.startswith("http"):
                                    if source is None:
                                        raise MissingRemoteUrl("Remote manifest URL required.")
                                    media = f"{source}/{media}"

                                media = media.replace("$Number$", str(number))
                                time = int(timelines[position].get("@t", 0)) + int(timelines[position]["@d"])
                                media = media.replace("$Time$", str(time))
                                media = media.replace("$RepresentationID$", profile["id"])
                                media = media.replace("$Bandwidth$", str(profile["bandwidth"]))

                                fragments.append({
                                    "range": "0-",
                                    "extinf": f"{extinf:.3f}",
                                    "media": media
                                })
                            position += 1
                    else:
                        drm = _get_drm(adaptation)
                        segment = representation["SegmentBase"]["@indexRange"]
                        start, end = map(int, segment.split("-"))
                        extinf = (end - start) / 1000
                        fragments.append({
                            "range": segment,
                            "extinf": f"{extinf:.3f}",
                            "media": f"{source}/{representation['BaseURL']}"
                        })

                    profile["fragments"] = fragments
                    profile["drm"] = drm
                    profiles.append(profile)
            else:
                pass
        return profiles

    def build_hls(self, profile_id: str) -> str:
        profile = self._get_profile(profile_id)
        hls = ["#EXTM3U", "#EXT-X-TARGETDURATION:4", "#EXT-X-ALLOW-CACHE:YES", "#EXT-X-PLAYLIST-TYPE:VOD"]
        licence = profile["drm"].get("license")
        if licence:
            hls.append(f'#EXT-X-KEY:METHOD=SAMPLE-AES,URI="{licence}"')
        hls += ["#EXT-X-VERSION:5", "#EXT-X-MEDIA-SEQUENCE:1"]
        hls.extend(f"#EXTINF:{fragment['extinf']},\n{fragment['media']}" for fragment in profile["fragments"])
        hls.append("#EXT-X-ENDLIST")
        return "\n".join(hls)

    def media_urls(self, profile_id: str) -> list:
        profile = self._get_profile(profile_id)
        return [fragment["media"] for fragment in profile["fragments"]]
