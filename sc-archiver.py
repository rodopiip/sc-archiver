import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import xattr

from dateutil import parser as date_parser
from httpx import AsyncClient
from pyrfc6266 import parse as parse_disp
from soundcloud import BasicTrack, SoundCloud

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SC ARCHIVER")
logging.getLogger("httpx").setLevel(logging.WARNING)


@dataclass
class ContentMetadata:
    filename: str
    last_modified: datetime

    @staticmethod
    def from_content_headeres(headers) -> "ContentMetadata":
        _, parsed_params = parse_disp(headers.get("Content-Disposition"))
        dispositions = {disp.name: disp.value for disp in parsed_params}

        filename = dispositions.get("filename*", dispositions.get("filename"))
        if not filename:
            raise ValueError("No filename in content disposition")

        try:
            last_modified = date_parser.parse(headers.get("Last-Modified"))
        except Exception as e:
            last_modified = datetime.now()

        return ContentMetadata(filename=filename, last_modified=last_modified)


def parse_args():
    parser = argparse.ArgumentParser(description="SoundCloud Archive Downloader")
    parser.add_argument("--client-id", required=True, help="SoundCloud Client ID")
    parser.add_argument(
        "--auth-token", required=True, help="SoundCloud Authentication Token"
    )
    parser.add_argument(
        "--download-folder",
        type=Path,
        default=Path("soundcloud_archive"),
        help="Folder where tracks will be downloaded (default: soundcloud_archive)",
    )
    parser.add_argument(
        "--num-parallel-downloads",
        type=int,
        default=5,
        help="Number of parallel downloads (default: 5)",
    )

    args = parser.parse_args()
    return args


args = parse_args()

if args.download_folder.exists() and not args.download_folder.is_dir():
    logger.error(f"{args.download_folder} is not a directory")
    exit(1)

if not args.download_folder.exists():
    os.makedirs(args.download_folder.resolve())

SEM = asyncio.Semaphore(args.num_parallel_downloads)
COUNTER_LOCK = asyncio.Lock()
SUCCESS = 0
FAILURE = 0


async def download_track(
    client: AsyncClient, sc: SoundCloud, track: BasicTrack, download_folder: Path
):
    logger.info(f"Downloading {track.title}")
    global SUCCESS, FAILURE

    async with SEM:
        try:
            download_url = sc.get_track_original_download(track.id)
            response = await client.get(download_url)
            response.raise_for_status()
        except Exception as e:
            async with COUNTER_LOCK:
                FAILURE += 1
            logger.error(f"Failed to download {track.title}: {e}")
            return

    try:
        meta = ContentMetadata.from_content_headeres(response.headers)
    except Exception as e:
        async with COUNTER_LOCK:
            FAILURE += 1
        logger.error(f"Failed to obtain metadata from headers {track.title}: {e}")
        return
    
    meta_filename = Path(meta.filename)
    filename = f"{track.title}{meta_filename.suffix}"
    filename = filename.replace("/", "_")
    path = download_folder / filename
    logger.debug(f"Downloading as {path} modified {meta.last_modified}")
    
    try:
        with path.open("wb") as f:
            f.write(response.content)
        os.utime(path, (meta.last_modified.timestamp(), meta.last_modified.timestamp()))
        xattr.setxattr(path, "original.filename", meta.filename.encode())
    except Exception as e:
        async with COUNTER_LOCK:
            FAILURE += 1
        logger.error(f"Failed to save {track.title}: {e} as {path.absolute()}")
        return
    
    logger.info(f"Downloaded {track.title} successfully to {path.absolute()}")
    
    async with COUNTER_LOCK:
        global SUCCESS
        SUCCESS += 1


async def main():
    sc = SoundCloud(client_id=args.client_id, auth_token=args.auth_token)
    if not sc.is_client_id_valid():
        logger.error("Invalid client ID")
        exit(1)
    
    if not sc.is_auth_token_valid():
        logger.error("Invalid authentication token")
        exit(1)

    me = sc.get_me()
    tracks = sc.get_user_tracks(me.id)
    logger.info(f"Credentials are valid. Starting download.")
    async with AsyncClient() as client:
        async with asyncio.TaskGroup() as tg:
            for track in tracks:
                tg.create_task(download_track(client, sc, track, args.download_folder))

    logger.info("Download finished.")
    if SUCCESS:
        logger.info(f"Downloaded {SUCCESS} track(s) successfully.")
    if FAILURE:
        logger.info(f"Failed to download {FAILURE} track(s).")


if __name__ == "__main__":
    asyncio.run(main())
