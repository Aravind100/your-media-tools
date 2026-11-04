

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

app = FastAPI(
    title="Your Media Tools API",
    version="1.0.0"
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

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "500"))
PROCESS_TIMEOUT = int(
    os.getenv("PROCESS_TIMEOUT_SECONDS", "900")
)

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"
}


def binary(name):
    path = shutil.which(name)

    if not path:
        raise HTTPException(
            status_code=503,
            detail=f"{name} is not installed."
        )

    return path


def run_command(command):
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
            detail="Processing timed out. Try a smaller file."
        )

    if result.returncode != 0:
        raise HTTPException(
            status_code=422,
            detail="Media processing failed. Check the uploaded file."
        )

    return result


def inspect_media(path):
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


@app.get("/")
def home():
    return {
        "name": "Your Media Tools API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None
    }


@app.post("/api/process")
async def process_media(
    file: UploadFile = File(...),
    operation: Literal[
        "to_mp3", "to_mp4", "compress"
    ] = Form(...),
    audio_bitrate: Literal[
        "128k", "192k", "320k"
    ] = Form("192k"),
    quality: Literal[
        "high", "balanced", "small"
    ] = Form("balanced")
):
    filename = Path(file.filename or "media").name
    extension = Path(filename).suffix.lower()

    if extension not in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format."
        )

    work_dir = Path(
        tempfile.mkdtemp(prefix="media-tools-")
    )

    input_path = work_dir / f"input{extension}"
    output_path = None

    try:
        size = 0

        with input_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > MAX_UPLOAD_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Maximum upload size is {MAX_UPLOAD_MB} MB."
                    )

                destination.write(chunk)

        if size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        streams = inspect_media(input_path)
        ffmpeg = binary("ffmpeg")

        if operation == "to_mp3":

            if not streams["audio"]:
                raise HTTPException(
                    status_code=400,
                    detail="No audio stream found."
                )

            output_path = work_dir / "converted.mp3"

            command = [
                ffmpeg, "-hide_banner", "-loglevel", "error",
                "-y", "-i", str(input_path),
                "-vn",
                "-codec:a", "libmp3lame",
                "-b:a", audio_bitrate,
                str(output_path)
            ]

            download_name = "your-media-tools.mp3"
            media_type = "audio/mpeg"

        elif operation == "to_mp4":

            if not streams["video"]:
                raise HTTPException(
                    status_code=400,
                    detail="No video stream found."
                )

            output_path = work_dir / "converted.mp4"

            command = [
                ffmpeg, "-hide_banner", "-loglevel", "error",
                "-y", "-i", str(input_path),
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "160k",
                "-movflags", "+faststart",
                str(output_path)
            ]

            download_name = "your-media-tools.mp4"
            media_type = "video/mp4"

        else:

            if not streams["video"]:
                raise HTTPException(
                    status_code=400,
                    detail="Video compression requires a video file."
                )

            crf = {
                "high": "20",
                "balanced": "25",
                "small": "30"
            }[quality]

            output_path = work_dir / "compressed.mp4"

            command = [
                ffmpeg, "-hide_banner", "-loglevel", "error",
                "-y", "-i", str(input_path),
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", crf,
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                str(output_path)
            ]

            download_name = "your-media-tools-compressed.mp4"
            media_type = "video/mp4"

        run_command(command)

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise HTTPException(
                status_code=500,
                detail="Output file was not created."
            )

        return FileResponse(
            path=output_path,
            filename=download_name,
            media_type=media_type,
            background=BackgroundTask(
                shutil.rmtree,
                work_dir,
                ignore_errors=True
            )
        )

    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise

    finally:
        await file.close()
