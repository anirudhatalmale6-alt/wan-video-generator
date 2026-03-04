"""GPU and VRAM detection utilities."""

import subprocess
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class GPUInfo:
    name: str
    vram_total_mb: int
    vram_free_mb: int
    cuda_available: bool
    device_index: int = 0

    @property
    def vram_total_gb(self) -> float:
        return self.vram_total_mb / 1024

    @property
    def vram_free_gb(self) -> float:
        return self.vram_free_mb / 1024


@dataclass
class HardwareProfile:
    gpus: list
    cpu_name: str
    ram_total_mb: int
    recommended_device: str  # "cuda", "cpu"
    max_resolution: str  # "1080p", "720p", "480p"
    max_frames: int
    max_video_seconds: float
    warnings: list


def detect_gpus() -> list:
    """Detect all available GPUs and their VRAM."""
    gpus = []

    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                total_mb = props.total_mem // (1024 * 1024)
                free_mb = total_mb  # Approximate; actual free depends on usage
                try:
                    free_mb = torch.cuda.mem_get_info(i)[0] // (1024 * 1024)
                except Exception:
                    pass
                gpus.append(GPUInfo(
                    name=props.name,
                    vram_total_mb=total_mb,
                    vram_free_mb=free_mb,
                    cuda_available=True,
                    device_index=i,
                ))
    except ImportError:
        pass

    # Fallback: try nvidia-smi
    if not gpus:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for i, line in enumerate(result.stdout.strip().split("\n")):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        gpus.append(GPUInfo(
                            name=parts[0],
                            vram_total_mb=int(float(parts[1])),
                            vram_free_mb=int(float(parts[2])),
                            cuda_available=True,
                            device_index=i,
                        ))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return gpus


def get_cpu_info() -> str:
    """Get CPU name."""
    import platform
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
            if len(lines) > 1:
                return lines[1]
        else:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
    except Exception:
        pass
    return platform.processor() or "Unknown CPU"


def get_ram_total_mb() -> int:
    """Get total system RAM in MB."""
    try:
        import psutil
        return psutil.virtual_memory().total // (1024 * 1024)
    except ImportError:
        return 0


def get_hardware_profile() -> HardwareProfile:
    """Analyze hardware and determine optimal settings."""
    gpus = detect_gpus()
    cpu_name = get_cpu_info()
    ram_total = get_ram_total_mb()
    warnings = []

    if not gpus:
        return HardwareProfile(
            gpus=gpus,
            cpu_name=cpu_name,
            ram_total_mb=ram_total,
            recommended_device="cpu",
            max_resolution="480p",
            max_frames=33,
            max_video_seconds=2.0,
            warnings=[
                "No CUDA GPU detected. Running on CPU will be extremely slow.",
                "For best results, install an NVIDIA GPU with at least 12GB VRAM.",
            ],
        )

    best_gpu = max(gpus, key=lambda g: g.vram_total_mb)
    vram_gb = best_gpu.vram_total_gb

    if vram_gb >= 24:
        max_res = "1080p"
        max_frames = 241  # ~15 sec at 16fps
        max_secs = 15.0
    elif vram_gb >= 16:
        max_res = "720p"
        max_frames = 161  # ~10 sec at 16fps
        max_secs = 10.0
        warnings.append(
            f"GPU has {vram_gb:.0f}GB VRAM. 720p up to 10 seconds recommended. "
            "1080p may work with group offloading but will be slower."
        )
    elif vram_gb >= 12:
        max_res = "480p"
        max_frames = 81  # ~5 sec at 16fps
        max_secs = 5.0
        warnings.append(
            f"GPU has {vram_gb:.0f}GB VRAM. 480p up to 5 seconds recommended. "
            "Higher settings may cause out-of-memory errors."
        )
    else:
        max_res = "480p"
        max_frames = 33  # ~2 sec at 16fps
        max_secs = 2.0
        warnings.append(
            f"GPU has only {vram_gb:.0f}GB VRAM. Very limited generation capability. "
            "Recommend upgrading to at least 12GB VRAM GPU."
        )

    if ram_total < 32 * 1024:
        warnings.append(
            f"System has {ram_total // 1024}GB RAM. 32GB+ recommended for "
            "CPU offloading during generation."
        )

    return HardwareProfile(
        gpus=gpus,
        cpu_name=cpu_name,
        ram_total_mb=ram_total,
        recommended_device="cuda",
        max_resolution=max_res,
        max_frames=max_frames,
        max_video_seconds=max_secs,
        warnings=warnings,
    )


# Resolution presets: (height, width, max_area)
RESOLUTION_PRESETS = {
    "480p": {"height": 480, "width": 832, "max_area": 480 * 832, "label": "480p (832x480)"},
    "720p": {"height": 720, "width": 1280, "max_area": 720 * 1280, "label": "720p (1280x720)"},
    "1080p": {"height": 1080, "width": 1920, "max_area": 1080 * 1920, "label": "1080p (1920x1080)"},
}

# Frame presets: must follow 4k+1 formula
DURATION_PRESETS = {
    "2s": {"frames": 33, "seconds": 2.0, "label": "2 seconds"},
    "3s": {"frames": 49, "seconds": 3.0, "label": "3 seconds"},
    "5s": {"frames": 81, "seconds": 5.0, "label": "5 seconds"},
    "8s": {"frames": 129, "seconds": 8.0, "label": "8 seconds"},
    "10s": {"frames": 161, "seconds": 10.0, "label": "10 seconds"},
    "12s": {"frames": 193, "seconds": 12.0, "label": "12 seconds"},
    "15s": {"frames": 241, "seconds": 15.0, "label": "15 seconds"},
}


def get_valid_frame_count(target_seconds: float, fps: int = 16) -> int:
    """Get nearest valid frame count (4k+1) for target duration."""
    target_frames = int(target_seconds * fps)
    k = round((target_frames - 1) / 4)
    return max(4 * k + 1, 5)
