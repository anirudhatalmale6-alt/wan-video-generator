"""Image processing utilities."""

import math
from pathlib import Path
from typing import Tuple

from PIL import Image


SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}


def is_supported_image(path: str) -> bool:
    """Check if file is a supported image format."""
    return Path(path).suffix.lower() in SUPPORTED_FORMATS


def load_and_resize_image(
    image_path: str,
    max_area: int,
    mod_value: int = 16,
) -> Image.Image:
    """Load image and resize to fit within max_area while maintaining aspect ratio.

    Dimensions are snapped to multiples of mod_value as required by the model.
    """
    image = Image.open(image_path).convert("RGB")
    return resize_image(image, max_area, mod_value)


def resize_image(
    image: Image.Image,
    max_area: int,
    mod_value: int = 16,
) -> Image.Image:
    """Resize image to fit within max_area, snapping to mod_value multiples."""
    aspect_ratio = image.height / image.width

    # Calculate new dimensions maintaining aspect ratio within max_area
    new_height = round(math.sqrt(max_area * aspect_ratio))
    new_width = round(math.sqrt(max_area / aspect_ratio))

    # Snap to mod_value
    new_height = (new_height // mod_value) * mod_value
    new_width = (new_width // mod_value) * mod_value

    # Ensure minimum dimensions
    new_height = max(new_height, mod_value)
    new_width = max(new_width, mod_value)

    if (new_width, new_height) != (image.width, image.height):
        image = image.resize((new_width, new_height), Image.LANCZOS)

    return image


def extract_last_frame(video_frames: list) -> Image.Image:
    """Extract the last frame from a list of PIL Image frames."""
    if not video_frames:
        raise ValueError("No frames to extract from")
    last = video_frames[-1]
    if isinstance(last, Image.Image):
        return last.copy()
    # If it's a tensor, convert
    import torch
    import numpy as np
    if isinstance(last, torch.Tensor):
        arr = last.cpu().numpy()
        if arr.ndim == 3 and arr.shape[0] in (1, 3):
            arr = arr.transpose(1, 2, 0)
        arr = (arr * 255).clip(0, 255).astype(np.uint8)
        return Image.fromarray(arr)
    raise TypeError(f"Unsupported frame type: {type(last)}")


def get_image_info(path: str) -> dict:
    """Get basic image information."""
    try:
        with Image.open(path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size_kb": Path(path).stat().st_size / 1024,
            }
    except Exception as e:
        return {"error": str(e)}
