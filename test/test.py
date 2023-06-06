import os
from pathlib import Path
from pydash2hls import Converter

PARENT = Path(__file__).resolve().parent

if __name__ == "__main__":
    # https://www.viki.com/videos/1232215v-cinderella-chef-season-1-episode-1
    url = "https://m-content6-viki.s.llnwi.net/1232215v/dash/mpdhd_high_5fd13d_2305290843.mpd"
    licence = "6c9f7a102be64c01af2dca78df1743cb:3e590520c1e61daa8479c69bf625bd6a"
    profile_id = "0"  # 1080p

    converter = Converter.from_remote(url)

    path_index = PARENT / "index.m3u8"
    path_index.write_text(converter.build_hls(profile_id=profile_id, licence=licence))

    os.system(" ".join([
        'ffplay',
        '-hide_banner',
        '-loglevel', 'error',
        '-allowed_extensions', 'ALL',
        '-protocol_whitelist', 'file,http,https,tcp,tls,crypto,data',
        '-i', f'"{path_index}"'
    ]))
