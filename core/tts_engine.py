"""Offline Text-to-Speech engine using Piper TTS.

Piper is a fast, local neural TTS system that runs entirely offline.
It supports multiple voices and languages with natural-sounding output.
"""

import logging
import os
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VoiceInfo:
    """Information about an available TTS voice."""
    id: str
    name: str
    language: str
    gender: str  # "male" or "female"
    quality: str  # "low", "medium", "high"
    sample_rate: int
    description: str


# Built-in voice catalog (Piper ONNX voices)
# Users download the .onnx + .onnx.json files to the voices directory
VOICE_CATALOG = [
    VoiceInfo(
        id="en_US-amy-medium",
        name="Amy (US Female)",
        language="en_US",
        gender="female",
        quality="medium",
        sample_rate=22050,
        description="Natural US English female voice, medium quality",
    ),
    VoiceInfo(
        id="en_US-joe-medium",
        name="Joe (US Male)",
        language="en_US",
        gender="male",
        quality="medium",
        sample_rate=22050,
        description="Natural US English male voice, medium quality",
    ),
    VoiceInfo(
        id="en_US-lessac-high",
        name="Lessac (US Female - High Quality)",
        language="en_US",
        gender="female",
        quality="high",
        sample_rate=22050,
        description="High quality US English female voice",
    ),
    VoiceInfo(
        id="en_US-libritts_r-medium",
        name="LibriTTS (US - Multi-speaker)",
        language="en_US",
        gender="female",
        quality="medium",
        sample_rate=22050,
        description="Multi-speaker US English voice",
    ),
    VoiceInfo(
        id="en_US-ryan-high",
        name="Ryan (US Male - High Quality)",
        language="en_US",
        gender="male",
        quality="high",
        sample_rate=22050,
        description="High quality US English male voice",
    ),
    VoiceInfo(
        id="en_GB-alan-medium",
        name="Alan (British Male)",
        language="en_GB",
        gender="male",
        quality="medium",
        sample_rate=22050,
        description="British English male voice",
    ),
    VoiceInfo(
        id="en_GB-alba-medium",
        name="Alba (British Female)",
        language="en_GB",
        gender="female",
        quality="medium",
        sample_rate=22050,
        description="British English female voice",
    ),
]


class TTSEngine:
    """Offline Text-to-Speech engine using Piper."""

    def __init__(self, voices_dir: Optional[str] = None):
        self.voices_dir = voices_dir or os.path.join(
            os.path.expanduser("~"), ".wan_video_generator", "voices"
        )
        os.makedirs(self.voices_dir, exist_ok=True)
        self._piper_path: Optional[str] = None

    def get_piper_path(self) -> Optional[str]:
        """Find the Piper executable."""
        if self._piper_path and os.path.exists(self._piper_path):
            return self._piper_path

        # Check in app directory
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(app_dir, "piper", "piper.exe"),
            os.path.join(app_dir, "piper", "piper"),
            os.path.join(self.voices_dir, "..", "piper", "piper.exe"),
            os.path.join(self.voices_dir, "..", "piper", "piper"),
        ]

        # Check PATH
        for name in ["piper", "piper.exe"]:
            try:
                result = subprocess.run(
                    ["where" if os.name == "nt" else "which", name],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    path = result.stdout.strip().split("\n")[0]
                    if os.path.exists(path):
                        candidates.insert(0, path)
            except Exception:
                pass

        for path in candidates:
            if os.path.exists(path):
                self._piper_path = path
                return path

        return None

    def is_available(self) -> bool:
        """Check if Piper TTS is installed and available."""
        return self.get_piper_path() is not None

    def get_available_voices(self) -> List[VoiceInfo]:
        """Get list of voices that are downloaded and ready to use."""
        available = []
        for voice in VOICE_CATALOG:
            model_path = os.path.join(self.voices_dir, f"{voice.id}.onnx")
            config_path = os.path.join(self.voices_dir, f"{voice.id}.onnx.json")
            if os.path.exists(model_path) and os.path.exists(config_path):
                available.append(voice)
        return available

    def get_all_voices(self) -> List[VoiceInfo]:
        """Get full voice catalog (including not-yet-downloaded)."""
        return VOICE_CATALOG.copy()

    def is_voice_downloaded(self, voice_id: str) -> bool:
        """Check if a specific voice model is downloaded."""
        model_path = os.path.join(self.voices_dir, f"{voice_id}.onnx")
        config_path = os.path.join(self.voices_dir, f"{voice_id}.onnx.json")
        return os.path.exists(model_path) and os.path.exists(config_path)

    def download_voice(self, voice_id: str):
        """Download a voice model from Hugging Face / Piper releases."""
        from huggingface_hub import hf_hub_download

        # Piper voices are hosted at rhasspy/piper-voices on HuggingFace
        # Path pattern: <lang>/<lang>-<name>/<quality>/<lang>-<name>-<quality>.onnx
        parts = voice_id.split("-")
        lang = parts[0] + "_" + parts[1]  # e.g., en_US
        name = parts[2]  # e.g., amy
        quality = parts[3] if len(parts) > 3 else "medium"

        hf_path = f"{lang.replace('_', '/')}/{lang}-{name}/{quality}"

        for ext in [".onnx", ".onnx.json"]:
            filename = f"{lang}-{name}-{quality}{ext}"
            target = os.path.join(self.voices_dir, f"{voice_id}{ext}")

            if not os.path.exists(target):
                logger.info(f"Downloading voice file: {filename}")
                downloaded = hf_hub_download(
                    repo_id="rhasspy/piper-voices",
                    filename=f"{hf_path}/{filename}",
                    local_dir=self.voices_dir,
                )
                # Move to expected location
                if os.path.exists(downloaded) and downloaded != target:
                    import shutil
                    shutil.move(downloaded, target)

        logger.info(f"Voice {voice_id} downloaded successfully")

    def synthesize(
        self,
        text: str,
        output_path: str,
        voice_id: str = "en_US-amy-medium",
        speed: float = 1.0,
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """Synthesize speech from text and save as WAV file.

        Args:
            text: The text to speak
            output_path: Output WAV file path
            voice_id: Voice model ID
            speed: Speech speed multiplier (0.5 = slow, 1.0 = normal, 2.0 = fast)
            progress_callback: Optional callback(step, total, message)

        Returns:
            Path to the generated WAV file
        """
        piper_path = self.get_piper_path()
        if not piper_path:
            raise RuntimeError(
                "Piper TTS not found. Please install Piper:\n"
                "Download from: https://github.com/rhasspy/piper/releases\n"
                "Extract to the 'piper/' folder next to the app."
            )

        model_path = os.path.join(self.voices_dir, f"{voice_id}.onnx")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Voice model not found: {voice_id}\n"
                f"Expected at: {model_path}\n"
                "Download voices using the Model tab or download_voices.py"
            )

        if progress_callback:
            progress_callback(0, 100, "Generating speech...")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Build Piper command
        cmd = [
            piper_path,
            "--model", model_path,
            "--output_file", output_path,
            "--length_scale", str(1.0 / speed),  # Piper uses length_scale (inverse of speed)
        ]

        # Run Piper with text piped to stdin
        logger.info(f"Running TTS: voice={voice_id}, speed={speed}, text_len={len(text)}")

        proc = subprocess.run(
            cmd,
            input=text,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if proc.returncode != 0:
            raise RuntimeError(f"Piper TTS failed: {proc.stderr}")

        if not os.path.exists(output_path):
            raise RuntimeError("TTS output file was not created")

        if progress_callback:
            progress_callback(100, 100, "Speech generated")

        logger.info(f"TTS output saved to {output_path}")
        return output_path

    def get_audio_duration(self, wav_path: str) -> float:
        """Get duration of a WAV file in seconds."""
        try:
            with wave.open(wav_path, "r") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / rate
        except Exception:
            return 0.0
