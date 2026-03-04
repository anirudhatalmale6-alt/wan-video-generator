"""WAN Image-to-Video generation engine (supports WAN 2.1 and 2.2)."""

import gc
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import torch
from PIL import Image

from utils.gpu_detect import (
    RESOLUTION_PRESETS,
    detect_gpus,
    get_valid_frame_count,
)
from utils.image_utils import load_and_resize_image, resize_image, extract_last_frame

logger = logging.getLogger(__name__)


# Model repository IDs — WAN 2.2 (default, best quality) and WAN 2.1 (fallback)
MODEL_REPOS = {
    # WAN 2.2 — latest, best quality, more realistic motion
    "wan2.2": "Wan-AI/Wan2.2-I2V-A14B-Diffusers",
    # WAN 2.1 — stable fallback
    "wan2.1-480p": "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
    "wan2.1-720p": "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers",
}

# Default model version
DEFAULT_MODEL = "wan2.2"

DEFAULT_NEGATIVE_PROMPT = (
    "Bright tones, overexposed, static, blurred details, subtitles, style, works, "
    "paintings, images, static, overall gray, worst quality, low quality, JPEG compression "
    "residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, "
    "deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, "
    "three legs, many people in the background, walking backwards"
)


@dataclass
class GenerationSettings:
    """Settings for video generation."""
    prompt: str = ""
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT
    resolution: str = "480p"  # "480p", "720p", "1080p"
    model_version: str = "wan2.2"  # "wan2.2" (best), "wan2.1"
    duration_seconds: float = 5.0
    fps: int = 16
    guidance_scale: float = 5.0
    num_inference_steps: int = 50
    seed: int = -1  # -1 = random
    device: str = "cuda"  # "cuda", "cpu"
    enable_cpu_offload: bool = False
    enable_group_offload: bool = False


@dataclass
class GenerationResult:
    """Result of a video generation."""
    frames: list = field(default_factory=list)
    output_path: str = ""
    generation_time: float = 0.0
    num_frames: int = 0
    resolution: tuple = (0, 0)
    seed_used: int = 0
    success: bool = False
    error: str = ""


class VideoGenerationEngine:
    """Main engine for WAN image-to-video generation (supports WAN 2.1 and 2.2)."""

    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir or os.path.join(
            os.path.expanduser("~"), ".wan_video_generator", "models"
        )
        self.pipe = None
        self.current_model_res = None
        self._progress_callback: Optional[Callable] = None
        self._cancel_requested = False

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates: callback(step, total, message)."""
        self._progress_callback = callback

    def cancel(self):
        """Request cancellation of current generation."""
        self._cancel_requested = True

    def _report_progress(self, step: int, total: int, message: str = ""):
        """Report progress through callback."""
        if self._progress_callback:
            self._progress_callback(step, total, message)

    def _get_model_repo(self, resolution: str, model_version: str = "wan2.2") -> str:
        """Get the appropriate model repo for resolution and model version."""
        if model_version == "wan2.2":
            # WAN 2.2 uses a single unified model for all resolutions
            return MODEL_REPOS["wan2.2"]
        else:
            # WAN 2.1 has separate models per resolution
            if resolution in ("720p", "1080p"):
                return MODEL_REPOS["wan2.1-720p"]
            return MODEL_REPOS["wan2.1-480p"]

    def _get_max_area(self, resolution: str) -> int:
        """Get max pixel area for resolution."""
        preset = RESOLUTION_PRESETS.get(resolution)
        if preset:
            return preset["max_area"]
        return RESOLUTION_PRESETS["480p"]["max_area"]

    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.pipe is not None

    def get_model_path(self, resolution: str, model_version: str = "wan2.2") -> str:
        """Get local path where model should be stored."""
        repo = self._get_model_repo(resolution, model_version)
        safe_name = repo.replace("/", "--")
        return os.path.join(self.model_dir, safe_name)

    def is_model_downloaded(self, resolution: str, model_version: str = "wan2.2") -> bool:
        """Check if model weights exist locally."""
        model_path = self.get_model_path(resolution, model_version)
        if os.path.isdir(model_path):
            # Check for key files
            has_transformer = os.path.isdir(os.path.join(model_path, "transformer"))
            has_vae = os.path.isdir(os.path.join(model_path, "vae"))
            return has_transformer and has_vae
        return False

    def download_model(self, resolution: str, model_version: str = "wan2.2"):
        """Download model weights from Hugging Face Hub."""
        from huggingface_hub import snapshot_download

        repo = self._get_model_repo(resolution, model_version)
        model_path = self.get_model_path(resolution, model_version)

        self._report_progress(0, 100, f"Downloading {repo}...")
        logger.info(f"Downloading model {repo} to {model_path}")

        os.makedirs(model_path, exist_ok=True)

        snapshot_download(
            repo_id=repo,
            local_dir=model_path,
            local_dir_use_symlinks=False,
        )

        self._report_progress(100, 100, "Download complete")
        logger.info(f"Model downloaded to {model_path}")

    def load_model(self, resolution: str, device: str = "cuda",
                   enable_cpu_offload: bool = False,
                   enable_group_offload: bool = False,
                   model_version: str = "wan2.2"):
        """Load the model pipeline."""
        from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
        from transformers import CLIPVisionModel

        model_key = f"{model_version}_{resolution}"

        # Unload previous model if different
        if self.pipe is not None and self.current_model_res != model_key:
            self.unload_model()

        if self.pipe is not None:
            return  # Already loaded

        repo = self._get_model_repo(resolution, model_version)
        model_path = self.get_model_path(resolution, model_version)

        # Use local path if downloaded, otherwise use repo ID (requires internet)
        model_source = model_path if self.is_model_downloaded(resolution, model_version) else repo

        self._report_progress(0, 4, "Loading image encoder...")
        logger.info(f"Loading model from {model_source}")

        # Load VAE and image encoder in float32 for quality
        image_encoder = CLIPVisionModel.from_pretrained(
            model_source,
            subfolder="image_encoder",
            torch_dtype=torch.float32,
        )

        self._report_progress(1, 4, "Loading VAE...")

        vae = AutoencoderKLWan.from_pretrained(
            model_source,
            subfolder="vae",
            torch_dtype=torch.float32,
        )

        self._report_progress(2, 4, "Loading transformer (this may take a while)...")

        # Load main pipeline in bfloat16 for efficiency
        self.pipe = WanImageToVideoPipeline.from_pretrained(
            model_source,
            vae=vae,
            image_encoder=image_encoder,
            torch_dtype=torch.bfloat16,
        )

        self._report_progress(3, 4, "Configuring device and memory optimization...")

        # Apply memory optimization strategies
        if enable_cpu_offload:
            self.pipe.enable_model_cpu_offload()
            logger.info("Enabled model CPU offloading")
        elif enable_group_offload:
            self._apply_group_offloading()
            logger.info("Enabled group offloading")
        elif device == "cuda":
            self.pipe.to("cuda")
        else:
            self.pipe.to("cpu")

        # Disable safety checker (no content filtering)
        if hasattr(self.pipe, "safety_checker"):
            self.pipe.safety_checker = None

        self.current_model_res = model_key
        self._report_progress(4, 4, f"Model loaded successfully ({model_version})")
        logger.info(f"Model loaded and ready ({model_version})")

    def _apply_group_offloading(self):
        """Apply group offloading for low-VRAM GPUs."""
        try:
            from diffusers.hooks.group_offloading import apply_group_offloading

            onload_device = torch.device("cuda")
            offload_device = torch.device("cpu")

            # Offload text encoder at block level
            if hasattr(self.pipe, "text_encoder") and self.pipe.text_encoder is not None:
                apply_group_offloading(
                    self.pipe.text_encoder,
                    onload_device=onload_device,
                    offload_device=offload_device,
                    offload_type="block_level",
                    num_blocks_per_group=4,
                )

            # Offload transformer at leaf level with streaming
            if hasattr(self.pipe, "transformer") and self.pipe.transformer is not None:
                self.pipe.transformer.enable_group_offload(
                    onload_device=onload_device,
                    offload_device=offload_device,
                    offload_type="leaf_level",
                    use_stream=True,
                )

            logger.info("Group offloading applied successfully")
        except Exception as e:
            logger.warning(f"Group offloading failed, falling back to CPU offload: {e}")
            self.pipe.enable_model_cpu_offload()

    def unload_model(self):
        """Unload model from memory."""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            self.current_model_res = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            logger.info("Model unloaded")

    def generate(
        self,
        image: Image.Image,
        settings: GenerationSettings,
        output_path: str,
    ) -> GenerationResult:
        """Generate video from image and settings."""
        self._cancel_requested = False
        start_time = time.time()
        result = GenerationResult()

        try:
            # Validate
            if image is None:
                raise ValueError("No input image provided")
            if not settings.prompt.strip():
                raise ValueError("Prompt cannot be empty")

            # Determine frame count
            num_frames = get_valid_frame_count(settings.duration_seconds, settings.fps)

            # Get resolution parameters
            max_area = self._get_max_area(settings.resolution)

            # Determine mod_value from pipeline
            if self.pipe is not None:
                try:
                    mod_value = (
                        self.pipe.vae_scale_factor_spatial
                        * self.pipe.transformer.config.patch_size[1]
                    )
                except Exception:
                    mod_value = 16
            else:
                mod_value = 16

            # Resize image
            self._report_progress(0, 100, "Preparing image...")
            processed_image = resize_image(image.copy(), max_area, int(mod_value))

            height = processed_image.height
            width = processed_image.width

            logger.info(
                f"Generating: {width}x{height}, {num_frames} frames, "
                f"steps={settings.num_inference_steps}, cfg={settings.guidance_scale}"
            )

            # Set seed
            if settings.seed >= 0:
                seed = settings.seed
            else:
                seed = int(torch.randint(0, 2**32 - 1, (1,)).item())

            generator = torch.Generator(
                device="cpu"  # Generator on CPU for reproducibility
            ).manual_seed(seed)

            result.seed_used = seed

            # Build step callback for progress
            total_steps = settings.num_inference_steps

            def step_callback(pipe, step_index, timestep, callback_kwargs):
                if self._cancel_requested:
                    raise InterruptedError("Generation cancelled by user")
                progress = int((step_index / total_steps) * 90) + 5  # 5-95%
                self._report_progress(
                    progress, 100,
                    f"Generating... Step {step_index + 1}/{total_steps}"
                )
                return callback_kwargs

            # Generate
            self._report_progress(5, 100, "Starting generation...")

            output = self.pipe(
                image=processed_image,
                prompt=settings.prompt,
                negative_prompt=settings.negative_prompt,
                height=height,
                width=width,
                num_frames=num_frames,
                guidance_scale=settings.guidance_scale,
                num_inference_steps=settings.num_inference_steps,
                generator=generator,
                callback_on_step_end=step_callback,
            )

            frames = output.frames[0]

            # Export to video
            self._report_progress(95, 100, "Encoding video...")
            from diffusers.utils import export_to_video

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            export_to_video(frames, output_path, fps=settings.fps)

            elapsed = time.time() - start_time

            result.frames = frames
            result.output_path = output_path
            result.generation_time = elapsed
            result.num_frames = len(frames)
            result.resolution = (width, height)
            result.success = True

            self._report_progress(100, 100, f"Done! ({elapsed:.1f}s)")
            logger.info(f"Generation complete: {output_path} ({elapsed:.1f}s)")

        except InterruptedError:
            result.error = "Generation cancelled"
            logger.info("Generation cancelled by user")

        except torch.cuda.OutOfMemoryError:
            result.error = (
                "Out of GPU memory! Try:\n"
                "- Lower resolution (e.g., 480p instead of 720p)\n"
                "- Shorter duration\n"
                "- Enable CPU offloading in settings\n"
                "- Close other GPU-heavy applications"
            )
            logger.error("CUDA out of memory during generation")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        except Exception as e:
            result.error = str(e)
            logger.error(f"Generation error: {e}", exc_info=True)

        return result

    def extend_video(
        self,
        last_frame: Image.Image,
        settings: GenerationSettings,
        output_path: str,
    ) -> GenerationResult:
        """Generate a continuation video from the last frame of a previous generation."""
        return self.generate(last_frame, settings, output_path)
