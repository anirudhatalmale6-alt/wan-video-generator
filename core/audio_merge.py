"""Audio-Video merge utilities.

Combines generated video (MP4) with TTS audio (WAV) into a single
MP4 file with both visual and audio tracks.
"""

import logging
import os
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


def merge_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    video_volume: float = 1.0,
    audio_volume: float = 1.0,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
) -> str:
    """Merge audio and video into a single MP4 file using ffmpeg.

    Args:
        video_path: Path to input video (MP4)
        audio_path: Path to input audio (WAV)
        output_path: Path for output video with audio
        video_volume: Volume multiplier for any existing video audio (0-1)
        audio_volume: Volume multiplier for the TTS audio (0-1)
        fade_in: Audio fade-in duration in seconds
        fade_out: Audio fade-out duration in seconds

    Returns:
        Path to the merged output file
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    ffmpeg_path = _find_ffmpeg()
    if not ffmpeg_path:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg:\n"
            "Download from: https://ffmpeg.org/download.html\n"
            "Or install via: pip install imageio-ffmpeg"
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Build audio filter chain
    audio_filters = []
    if audio_volume != 1.0:
        audio_filters.append(f"volume={audio_volume}")
    if fade_in > 0:
        audio_filters.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out > 0:
        # Get audio duration to calculate fade-out start
        audio_dur = _get_duration(ffmpeg_path, audio_path)
        if audio_dur > fade_out:
            audio_filters.append(
                f"afade=t=out:st={audio_dur - fade_out}:d={fade_out}"
            )

    filter_str = ",".join(audio_filters) if audio_filters else None

    # Build ffmpeg command
    cmd = [
        ffmpeg_path,
        "-y",  # Overwrite output
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",  # Don't re-encode video
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",  # Cut to shortest stream
        "-map", "0:v:0",  # Video from first input
        "-map", "1:a:0",  # Audio from second input
    ]

    if filter_str:
        cmd.extend(["-af", filter_str])

    cmd.append(output_path)

    logger.info(f"Merging audio+video: {' '.join(cmd)}")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg merge failed: {proc.stderr}")

    if not os.path.exists(output_path):
        raise RuntimeError("Merged output file was not created")

    logger.info(f"Merged output: {output_path}")
    return output_path


def add_background_music(
    video_path: str,
    music_path: str,
    output_path: str,
    music_volume: float = 0.3,
    loop_music: bool = True,
) -> str:
    """Add background music track to a video.

    Args:
        video_path: Input video (may already have voice audio)
        music_path: Background music file (MP3/WAV/OGG)
        output_path: Output path
        music_volume: Volume for music (0-1, default 0.3 for background)
        loop_music: Loop music if shorter than video

    Returns:
        Path to output file
    """
    ffmpeg_path = _find_ffmpeg()
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg not found")

    cmd = [
        ffmpeg_path,
        "-y",
        "-i", video_path,
        "-i", music_path,
    ]

    if loop_music:
        # Insert stream_loop before the music input
        cmd = [
            ffmpeg_path,
            "-y",
            "-i", video_path,
            "-stream_loop", "-1",
            "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[out]",
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path,
        ]
    else:
        cmd.extend([
            "-filter_complex",
            f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[out]",
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path,
        ])

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg music merge failed: {proc.stderr}")

    return output_path


def _find_ffmpeg() -> Optional[str]:
    """Find ffmpeg executable."""
    # Check imageio-ffmpeg first (bundled with pip install)
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.exists(path):
            return path
    except (ImportError, RuntimeError):
        pass

    # Check PATH
    for name in ["ffmpeg", "ffmpeg.exe"]:
        try:
            result = subprocess.run(
                ["where" if os.name == "nt" else "which", name],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                path = result.stdout.strip().split("\n")[0]
                if os.path.exists(path):
                    return path
        except Exception:
            pass

    # Check common locations
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "ffmpeg", "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    return None


def _get_duration(ffmpeg_path: str, file_path: str) -> float:
    """Get media file duration using ffprobe."""
    ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0.0
