#!/usr/bin/env python3
"""Download Piper TTS voice models for offline use.

Run this script once while connected to the internet.
After download, voice narration works fully offline.
"""

import argparse
import os
import sys
import urllib.request

# Voice models hosted on GitHub releases for Piper TTS
# Format: (voice_id, onnx_url, config_url)
VOICE_DOWNLOADS = {
    "en_US-amy-medium": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
    },
    "en_US-joe-medium": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/joe/medium/en_US-joe-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/joe/medium/en_US-joe-medium.onnx.json",
    },
    "en_US-lessac-high": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx.json",
    },
    "en_US-ryan-high": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/high/en_US-ryan-high.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/high/en_US-ryan-high.onnx.json",
    },
    "en_GB-alan-medium": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json",
    },
    "en_GB-alba-medium": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/medium/en_GB-alba-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/medium/en_GB-alba-medium.onnx.json",
    },
}


def download_file(url, target_path):
    """Download a file with progress reporting."""
    print(f"  Downloading: {os.path.basename(target_path)}")

    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, int(downloaded / total_size * 100))
            bar = "#" * (pct // 2) + "-" * (50 - pct // 2)
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(f"\r  [{bar}] {pct}% ({mb:.1f}/{total_mb:.1f} MB)", end="", flush=True)

    urllib.request.urlretrieve(url, target_path, reporthook=progress_hook)
    print()  # Newline after progress


def main():
    parser = argparse.ArgumentParser(description="Download Piper TTS voice models")
    parser.add_argument(
        "--voice", "-v",
        choices=list(VOICE_DOWNLOADS.keys()) + ["all"],
        default="all",
        help="Which voice to download (default: all)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=os.path.join(os.path.expanduser("~"), ".wan_video_generator", "voices"),
        help="Directory to store voice models",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.voice == "all":
        voices = VOICE_DOWNLOADS
    else:
        voices = {args.voice: VOICE_DOWNLOADS[args.voice]}

    print(f"\n{'=' * 60}")
    print(f"Downloading {len(voices)} Piper TTS voice(s)")
    print(f"Target: {args.output_dir}")
    print(f"{'=' * 60}\n")

    for voice_id, urls in voices.items():
        print(f"\nVoice: {voice_id}")

        for key, url in urls.items():
            ext = ".onnx" if key == "onnx" else ".onnx.json"
            target = os.path.join(args.output_dir, f"{voice_id}{ext}")

            if os.path.exists(target):
                print(f"  Already exists: {os.path.basename(target)}")
                continue

            download_file(url, target)

    print(f"\n{'=' * 60}")
    print("All voice downloads complete!")
    print(f"Voices stored in: {args.output_dir}")
    print(f"{'=' * 60}\n")

    # Also remind about Piper executable
    print("IMPORTANT: You also need the Piper TTS executable.")
    print("Download from: https://github.com/rhasspy/piper/releases")
    print("Extract piper.exe to the 'piper/' folder next to the app.")


if __name__ == "__main__":
    main()
