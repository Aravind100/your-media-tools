
import os
import re
import json
import shutil
import subprocess
import tempfile
import asyncio

from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

app = FastAPI(
    title="Your Media Tools API",
    version="1.1.0"
)

origins = [
    item.strip()
    for item in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000"
    ).split(",")
    if item.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
PROCESS_TIMEOUT = int(
    os.getenv("PROCESS_TIMEOUT_SECONDS", "900")
)

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY", ""
).strip()


VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv",
    ".webm", ".avi", ".m4v"
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a",
    ".aac", ".ogg", ".flac"
}


# --------------------------------------------------
# SYSTEM UTILITIES
# --------------------------------------------------

def binary(name: str) -> str:
    path = shutil.which(name)

    if not path:
        raise HTTPException(
            status_code=503,
            detail=f"{name} is not installed on the server."
        )

    return path


def run_command(command: list):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=PROCESS_TIMEOUT
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Processing timed out. Please try a smaller file."
        )

    if result.returncode != 0:
        raise HTTPException(
            status_code=422,
            detail="Media processing failed. Please check the uploaded file."
        )

    return result


def inspect_media(path: Path):
    result = run_command([
        binary("ffprobe"),
        "-v", "error",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1",
        str(path)
    ])

    types = set()

    for line in result.stdout.splitlines():
        if "=" in line:
            types.add(line.split("=", 1)[1].strip())

    return {
        "video": "video" in types,
        "audio": "audio" in types
    }


async def save_upload(
    file: UploadFile,
    destination: Path
):
    total_size = 0

    try:
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Maximum upload size is {MAX_UPLOAD_MB} MB."
                    )

                output.write(chunk)

    finally:
        await file.close()

    if total_size == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )


def cleanup_directory(directory: str):
    shutil.rmtree(directory, ignore_errors=True)


def create_file_response(
    output_path: Path,
    directory: str,
    filename: str,
    media_type: str
):
    return FileResponse(
        path=str(output_path),
        filename=filename,
        media_type=media_type,
        background=BackgroundTask(
            cleanup_directory,
            directory
        )
    )


# --------------------------------------------------
# YOUTUBE URL AND API UTILITIES
# --------------------------------------------------

def extract_youtube_video_id(url: str):
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()

        video_id = None

        if host in {
            "youtu.be",
            "www.youtu.be"
        }:
            video_id = parsed.path.strip("/").split("/")[0]

        elif host in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com"
        }:
            if parsed.path == "/watch":
                video_id = parse_qs(
                    parsed.query
                ).get("v", [None])[0]

            elif parsed.path.startswith((
                "/shorts/",
                "/embed/",
                "/live/"
            )):
                parts = parsed.path.strip("/").split("/")

                if len(parts) >= 2:
                    video_id = parts[1]

        if video_id and re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            video_id
        ):
            return video_id

        return None

    except Exception:
        return None


def fetch_youtube_video(video_id: str):

    if not YOUTUBE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="YouTube API is not configured on the server."
        )

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,contentDetails,statistics"
        f"&id={video_id}"
        f"&key={YOUTUBE_API_KEY}"
    )

    request = Request(
        url,
        headers={"Accept": "application/json"}
    )

    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as exc:

        try:
            error_data = json.loads(
                exc.read().decode("utf-8")
            )

            reason = (
                error_data.get("error", {})
                .get("errors", [{}])[0]
                .get("reason", "")
            )

        except Exception:
            reason = ""

        if reason == "quotaExceeded":
            raise HTTPException(
                status_code=429,
                detail="YouTube API quota exceeded. Try again later."
            )

        if reason in {
            "keyInvalid",
            "accessNotConfigured"
        }:
            raise HTTPException(
                status_code=503,
                detail="YouTube API key is invalid or the API is not enabled."
            )

        raise HTTPException(
            status_code=502,
            detail="YouTube could not process this video request."
        )

    except (URLError, TimeoutError):
        raise HTTPException(
            status_code=504,
            detail="Could not connect to YouTube. Please try again."
        )

    items = data.get("items", [])

    if not items:
        raise HTTPException(
            status_code=404,
            detail="Video not found or unavailable through the YouTube API."
        )

    video = items[0]

    snippet = video.get("snippet", {})
    details = video.get("contentDetails", {})
    statistics = video.get("statistics", {})

    thumbnails = snippet.get("thumbnails", {})

    thumbnail = (
        thumbnails.get("maxres")
        or thumbnails.get("standard")
        or thumbnails.get("high")
        or thumbnails.get("medium")
        or thumbnails.get("default")
        or {}
    )

    return {
        "platform": "YouTube",
        "video_id": video_id,
        "title": snippet.get("title"),
        "channel": snippet.get("channelTitle"),
        "description": snippet.get("description"),
        "published_at": snippet.get("publishedAt"),
        "duration": details.get("duration"),
        "views": statistics.get("viewCount"),
        "likes": statistics.get("likeCount"),
        "thumbnail": thumbnail.get("url"),
        "video_url": (
            f"https://www.youtube.com/watch?v={video_id}"
        ),
        "embed_url": (
            f"https://www.youtube.com/embed/{video_id}"
        )
    }


# --------------------------------------------------
# BASIC AND HEALTH ENDPOINTS
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "name": "Your Media Tools API",
        "status": "running",
        "version": "1.1.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "youtube_api_configured": bool(YOUTUBE_API_KEY)
    }


# --------------------------------------------------
# YOUTUBE VIDEO INFORMATION ENDPOINT
# --------------------------------------------------

@app.get("/api/platform/youtube")
async def youtube_video_info(url: str):

    video_id = extract_youtube_video_id(url)

    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid YouTube video URL."
        )

    return await asyncio.to_thread(
        fetch_youtube_video,
        video_id
    )


# --------------------------------------------------
# MEDIA PROCESSING ENDPOINT
# --------------------------------------------------

@app.post("/api/process")
async def process_media(
    file: UploadFile = File(...),

    operation: Literal[
        "to_mp3",
        "to_mp4",
        "compress"
    ] = Form(...),

    audio_bitrate: Literal[
        "128k",
        "192k",
        "320k"
    ] = Form("192k"),

    quality: Literal[
        "high",
        "balanced",
        "small"
    ] = Form("balanced")
):

    original_name = Path(
        file.filename or "upload"
    ).name

    extension = Path(
        original_name
    ).suffix.lower()

    if operation == "to_mp3":
        if extension not in VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Please upload a supported video file."
            )

    else:
        if extension not in VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Please upload a supported video file."
            )

    directory = tempfile.mkdtemp(
        prefix="your-media-tools-"
    )

    input_path = Path(directory) / (
        "input" + extension
    )

    try:
        await save_upload(
            file,
            input_path
        )

        media = inspect_media(input_path)

        if not media["video"]:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file does not contain a video stream."
            )

        output_path = None
        output_filename = None
        media_type = None

        # ------------------------------------------
        # VIDEO TO MP3
        # ------------------------------------------

        if operation == "to_mp3":

            if not media["audio"]:
                raise HTTPException(
                    status_code=400,
                    detail="No audio stream was found in this video."
                )

            output_path = (
                Path(directory) / "converted.mp3"
            )

            output_filename = (
                Path(original_name).stem + ".mp3"
            )

            media_type = "audio/mpeg"

            command = [
                binary("ffmpeg"),
                "-y",
                "-i", str(input_path),
                "-vn",
                "-codec:a", "libmp3lame",
                "-b:a", audio_bitrate,
                "-threads", "1",
                str(output_path)
            ]

        # ------------------------------------------
        # CONVERT VIDEO TO MP4
        # ------------------------------------------

        elif operation == "to_mp4":

            output_path = (
                Path(directory) / "converted.mp4"
            )

            output_filename = (
                Path(original_name).stem + ".mp4"
            )

            media_type = "video/mp4"

            command = [
                binary("ffmpeg"),
                "-y",
                "-i", str(input_path),
                "-map", "0:v:0",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-threads", "1",
                "-movflags", "+faststart",
                str(output_path)
            ]

        # ------------------------------------------
        # VIDEO COMPRESSION
        # ------------------------------------------

        elif operation == "compress":

            quality_settings = {
                "high": "23",
                "balanced": "28",
                "small": "32"
            }

            crf = quality_settings[quality]

            output_path = (
                Path(directory) / "compressed.mp4"
            )

            output_filename = (
                Path(original_name).stem + "_compressed.mp4"
            )

            media_type = "video/mp4"

            command = [
                binary("ffmpeg"),
                "-y",
                "-i", str(input_path),
                "-map", "0:v:0",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", crf,
                "-c:a", "aac",
                "-b:a", "96k",
                "-threads", "1",
                "-movflags", "+faststart",
                str(output_path)
            ]

        # ------------------------------------------
        # RUN PROCESSING
        # ------------------------------------------

        run_command(command)

        if (
            not output_path
            or not output_path.exists()
            or output_path.stat().st_size == 0
        ):
            raise HTTPException(
                status_code=422,
                detail="The output file could not be generated."
            )

        return create_file_response(
            output_path=output_path,
            directory=directory,
            filename=output_filename,
            media_type=media_type
        )

    except Exception:
        cleanup_directory(directory)
        raise
