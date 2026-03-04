"""Video concatenation and extension utilities."""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def concat_videos(video_paths: List[str], output_path: str, fps: int = 16) -> str:
    """Concatenate multiple MP4 videos into one using imageio/ffmpeg."""
    import imageio

    if not video_paths:
        raise ValueError("No videos to concatenate")

    if len(video_paths) == 1:
        # Just copy
        import shutil
        shutil.copy2(video_paths[0], output_path)
        return output_path

    # Read all frames from all videos
    all_frames = []
    for vpath in video_paths:
        reader = imageio.get_reader(vpath)
        for frame in reader:
            all_frames.append(frame)
        reader.close()

    # Write combined video
    writer = imageio.get_writer(output_path, fps=fps, codec="libx264",
                                quality=8, pixelformat="yuv420p")
    for frame in all_frames:
        writer.append_data(frame)
    writer.close()

    logger.info(f"Concatenated {len(video_paths)} videos -> {output_path} "
                f"({len(all_frames)} frames)")
    return output_path


def get_video_info(video_path: str) -> dict:
    """Get basic video information."""
    try:
        import imageio
        reader = imageio.get_reader(video_path)
        meta = reader.get_meta_data()
        n_frames = reader.count_frames()
        reader.close()
        return {
            "path": video_path,
            "frames": n_frames,
            "fps": meta.get("fps", 16),
            "duration": n_frames / meta.get("fps", 16),
            "size": meta.get("size", (0, 0)),
            "codec": meta.get("codec", "unknown"),
            "file_size_mb": os.path.getsize(video_path) / (1024 * 1024),
        }
    except Exception as e:
        return {"error": str(e)}
