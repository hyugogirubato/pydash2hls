from __future__ import annotations

import base64
import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import requests
import xmltodict

from pydash2hls.exceptions import (
    InvalidFileContent,
    InvalidPath,
    InvalidProfile,
    MissingRemoteUrl,
)


def _get_drm(adaptation: dict) -> dict:
    drm = {}
    for protection in adaptation.get("ContentProtection", []):
        keys = {
            "kid": "@cenc:default_KID",
            "widevine": "cenc:pssh",
            "playready": "mspr:pro",
            "license": "ms:laurl",
        }

        for key, value in keys.items():
            if value in protection:
                scheme_id = re.sub(
                    r"[^0-9a-f]",
                    "",
                    protection.get("@schemeIdUri", "").replace("urn:uuid:", "").lower(),
                )
                if scheme_id == "edef8ba979d64acea3c827dcd51d21ed":
                    key = "widevine"
                elif scheme_id == "9a04f07998404286ab92e65be0885f95":
                    key = "playready"

                item = protection[value]
                item = item if isinstance(item, str) else item["#text"]
                drm[key] = item.lower() if key == "kid" else item
    return drm


class Converter:
    def __init__(self, mdp_srt: str, mdp_dict: dict, url: Optional[str] = None):
        self.mdp_srt = mdp_srt
        self.mdp_dict = mdp_dict
        self.mdp_url = url
        self.profiles: list[dict[str, Any]] = []
        self._manifest_profiles()

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

    def _existing_profile(self, profile_id: str) -> Optional[int]:
        for i, profile in enumerate(self.profiles):
            if profile["id"] == profile_id:
                return i
        return None

    def _manifest_profiles(self) -> None:
        source = (
            None if self.mdp_url is None else "/".join(self.mdp_url.split("/")[:-1])
        )

        # Period
        periods = self.mdp_dict["MPD"]["Period"]
        periods = periods if isinstance(periods, list) else [periods]

        for i, period in enumerate(periods):
            adaptations = period["AdaptationSet"]
            adaptations = (
                adaptations if isinstance(adaptations, list) else [adaptations]
            )
            for adaptation in adaptations:
                # Representations
                representations = adaptation["Representation"]
                representations = (
                    representations
                    if isinstance(representations, list)
                    else [representations]
                )

                for representation in representations:
                    mime_type = self._get_key(
                        adaptation, representation, "@mimeType"
                    ) or (
                        "video/mp4"
                        if "avc" in representation["@codecs"]
                        else "audio/m4a"
                    )
                    start_with_sap = (
                        self._get_key(adaptation, representation, "@startWithSAP")
                        or "1"
                    ) == "1"
                    if "video" not in mime_type and "audio" not in mime_type:
                        continue

                    profile = {
                        "id": representation.get("@id") or adaptation.get("@id"),
                        "mimeType": mime_type,
                        "codecs": representation.get("@codecs")
                        or adaptation.get("@codecs"),
                        "bandwidth": int(
                            representation.get("@bandwidth")
                            or adaptation.get("@bandwidth")
                        ),
                        "startWithSAP": start_with_sap,
                    }
                    if (
                        "audio" in profile["mimeType"]
                        or "@audioSamplingRate" in representation
                    ):
                        profile["audioSamplingRate"] = representation.get(
                            "@audioSamplingRate"
                        )
                    else:
                        profile["width"] = int(representation["@width"])
                        profile["height"] = int(representation["@height"])
                        frame_rate = (
                            representation.get("@frameRate")
                            or adaptation.get("@maxFrameRate")
                            or "1/1"
                        )
                        frame_rate = (
                            frame_rate if "/" in frame_rate else f"{frame_rate}/1"
                        )
                        profile["frameRate"] = round(
                            int(frame_rate.split("/")[0])
                            / int(frame_rate.split("/")[1]),
                            3,
                        )
                        profile["sar"] = representation.get("@sar", "1:1")

                    # DRM
                    drm = _get_drm(adaptation)
                    item = adaptation.get("SegmentTemplate")
                    if not item:
                        item = representation.get("SegmentTemplate")
                        drm = _get_drm(representation)

                    index = self._existing_profile(profile["id"])
                    fragments = (
                        [] if index is None else self.profiles[index]["fragments"]
                    )
                    if item:
                        position = 0
                        number = int(item.get("@startNumber", 1)) - 1
                        timescale = int(item["@timescale"])

                        # Initialization
                        if len(fragments) == 0 and "@initialization" in item:
                            media = item["@initialization"]
                            media = media.replace("$RepresentationID$", profile["id"])
                            media = media.replace(
                                "$Bandwidth$", str(profile["bandwidth"])
                            )
                            if not media.startswith("http"):
                                if "BaseURL" in representation:
                                    base_url = representation["BaseURL"]
                                    base_url = (
                                        base_url
                                        if isinstance(base_url, list)
                                        else [base_url]
                                    )
                                    source = base_url[0]

                                if source is None:
                                    raise MissingRemoteUrl(
                                        "Remote manifest URL required."
                                    )

                                if source.endswith("/"):
                                    source = source[:-1]
                                media = f"{source}/{media}"
                            fragments.append(
                                {
                                    "range": "0-",
                                    "extinf": f"{timescale / 1000:.3f}",
                                    "media": media,
                                }
                            )

                        # Timelines
                        timelines = item["SegmentTimeline"]["S"]
                        timelines = (
                            timelines if type(timelines) is list else [timelines]
                        )

                        for timeline in timelines:
                            for _ in range(int(timeline.get("@r", 0)) + 1):
                                number += 1
                                extinf = int(timelines[position]["@d"]) / timescale
                                media = item["@media"]

                                if not media.startswith("http"):
                                    if "BaseURL" in representation:
                                        base_url = representation["BaseURL"]
                                        base_url = (
                                            base_url
                                            if isinstance(base_url, list)
                                            else [base_url]
                                        )
                                        source = base_url[0]

                                    if source is None:
                                        raise MissingRemoteUrl(
                                            "Remote manifest URL required."
                                        )

                                    if source.endswith("/"):
                                        source = source[:-1]
                                    media = f"{source}/{media}"

                                media = media.replace("$Number$", str(number))
                                time = int(timelines[position].get("@t", 0)) + int(
                                    timelines[position]["@d"]
                                )
                                media = media.replace("$Time$", str(time))
                                media = media.replace(
                                    "$RepresentationID$", profile["id"]
                                )
                                media = media.replace(
                                    "$Bandwidth$", str(profile["bandwidth"])
                                )
                                fragments.append(
                                    {
                                        "range": "0-",
                                        "extinf": f"{extinf:.3f}",
                                        "media": media,
                                    }
                                )
                            position += 1
                    else:
                        drm = _get_drm(adaptation)
                        segment = representation["SegmentBase"]
                        start, end = map(int, segment["@indexRange"].split("-"))
                        if "Initialization" in segment:
                            start, _ = map(
                                int, segment["Initialization"]["@range"].split("-")
                            )

                        extinf = (end - start) / 1000
                        fragments.append(
                            {
                                "range": f"{start}-{end}",
                                "extinf": f"{extinf:.3f}",
                                "media": f"{source}/{representation['BaseURL']}",
                            }
                        )

                    profile["fragments"] = fragments
                    profile["drm"] = drm

                    index = self._existing_profile(profile["id"])
                    if index is None:
                        self.profiles.append(profile)
                    else:
                        if not self.profiles[index]["drm"]:
                            self.profiles[index]["drm"] = profile["drm"]
                        self.profiles[index]["fragments"] = profile["fragments"]

    def build_hls(self, profile_id: str, licence: Optional[str] = None) -> str:
        profile = self._get_profile(profile_id)
        sequence = 0 if len(profile["fragments"]) == 1 else 1
        duration, _ = Counter(
            [float(f["extinf"]) for f in profile["fragments"]]
        ).most_common(1)[0]
        hls = [
            "#EXTM3U",
            "#EXT-X-VERSION:6",
            f"#EXT-X-MEDIA-SEQUENCE:{sequence}",
            f"#EXT-X-TARGETDURATION:{int(duration)}",
            "#EXT-X-PLAYLIST-TYPE:VOD",
            "#EXT-X-ALLOW-CACHE:YES",
        ]

        if licence:
            kid, key = licence.split(":")
            key_uri = "data:text/plain;base64," + base64.b64encode(
                bytes.fromhex(key)
            ).decode("utf-8")
            key_id = "0x" + bytes.fromhex(kid).hex().upper()
            key_iv = "0x00000000000000000000000000000000"
            hls.append(
                f'#EXT-X-KEY:METHOD=SAMPLE-AES-CTR,URI="{key_uri}",KEYID={key_id},IV={key_iv},KEYFORMATVERSIONS="1",KEYFORMAT="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"'
            )
        else:
            licence = profile["drm"].get("license")
            if licence:
                hls.append(f'#EXT-X-KEY:METHOD=SAMPLE-AES,URI="{licence}"')

        hls.extend(
            f"#EXTINF:{fragment['extinf']},\n{fragment['media']}"
            for fragment in profile["fragments"]
        )
        hls.append("#EXT-X-ENDLIST")
        return "\n".join(hls)

    def media_urls(self, profile_id: str) -> list:
        profile = self._get_profile(profile_id)
        return [fragment["media"] for fragment in profile["fragments"]]
