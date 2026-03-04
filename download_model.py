#!/usr/bin/env python3
"""Download WAN model weights for offline use.

Run this script once while connected to the internet.
After download, the application works fully offline.

Default: Downloads WAN 2.2 (best quality, recommended).
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Download WAN model weights")
    parser.add_argument(
        "--model", "-m",
        choices=["wan2.2", "wan2.1-480p", "wan2.1-720p", "all"],
        default="wan2.2",
        help="Which model to download (default: wan2.2 — best quality)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=os.path.join(os.path.expanduser("~"), ".wan_video_generator", "models"),
        help="Directory to store models",
    )
    args = parser.parse_args()

    from huggingface_hub import snapshot_download

    models = {
        "wan2.2": ("WAN 2.2 (Best Quality)", "Wan-AI/Wan2.2-I2V-A14B-Diffusers"),
        "wan2.1-480p": ("WAN 2.1 480p", "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers"),
        "wan2.1-720p": ("WAN 2.1 720p", "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers"),
    }

    to_download = []
    if args.model == "all":
        to_download = list(models.items())
    else:
        to_download = [(args.model, models[args.model])]

    print(f"\n{'=' * 60}")
    print(f"WAN Video Generator — Model Download")
    print(f"{'=' * 60}\n")

    for key, (name, repo_id) in to_download:
        safe_name = repo_id.replace("/", "--")
        local_dir = os.path.join(args.output_dir, safe_name)
        os.makedirs(local_dir, exist_ok=True)

        print(f"Downloading: {name}")
        print(f"Repository:  {repo_id}")
        print(f"Target:      {local_dir}")
        print(f"This may take a while (~25GB)...\n")

        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
        )

        print(f"\n  {name} downloaded successfully!")
        print(f"  Location: {local_dir}\n")

    print("=" * 60)
    print("All downloads complete!")
    print("You can now run the application fully offline.")
    print("=" * 60)


if __name__ == "__main__":
    main()
