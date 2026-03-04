#!/usr/bin/env python3
"""Download WAN2.1 model weights for offline use.

Run this script once while connected to the internet.
After download, the application works fully offline.
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Download WAN2.1 model weights")
    parser.add_argument(
        "--resolution", "-r",
        choices=["480p", "720p", "both"],
        default="480p",
        help="Which model to download (default: 480p)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=os.path.join(os.path.expanduser("~"), ".wan_video_generator", "models"),
        help="Directory to store models",
    )
    args = parser.parse_args()

    from huggingface_hub import snapshot_download

    models = {
        "480p": "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
        "720p": "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers",
    }

    to_download = []
    if args.resolution == "both":
        to_download = list(models.items())
    else:
        to_download = [(args.resolution, models[args.resolution])]

    for res, repo_id in to_download:
        safe_name = repo_id.replace("/", "--")
        local_dir = os.path.join(args.output_dir, safe_name)
        os.makedirs(local_dir, exist_ok=True)

        print(f"\n{'=' * 60}")
        print(f"Downloading: {repo_id}")
        print(f"Resolution:  {res}")
        print(f"Target:      {local_dir}")
        print(f"{'=' * 60}\n")
        print("This may take a while (model is ~25GB)...\n")

        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
        )

        print(f"\n  {res} model downloaded successfully!")
        print(f"  Location: {local_dir}\n")

    print("=" * 60)
    print("All downloads complete!")
    print("You can now run the application fully offline.")
    print("=" * 60)


if __name__ == "__main__":
    main()
