# WAN Video Generator — User Guide

## What This App Does

Converts a single still image into an AI-generated video using the WAN2.1 model. Everything runs locally on your PC — no internet, no cloud, no data leaves your machine.

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10 64-bit | Windows 11 |
| **GPU** | NVIDIA RTX 3060 (12GB) | RTX 4090 (24GB) |
| **RAM** | 16GB | 32GB+ |
| **Storage** | 50GB free | 100GB free |
| **Python** | 3.10+ | 3.11 |
| **CUDA** | 12.1+ | 12.4 |

### What You Can Generate Per GPU

| GPU (VRAM) | Max Resolution | Max Duration |
|------------|---------------|--------------|
| 24GB (4090) | 1080p | 15 seconds |
| 16GB (4070Ti/4080) | 720p | 10 seconds |
| 12GB (3060/4060Ti) | 480p | 5 seconds |
| CPU only | 480p | 2 seconds (very slow) |

---

## Installation

### Step 1: Install Python 3.10+
1. Download from https://www.python.org/downloads/
2. **IMPORTANT:** Check "Add Python to PATH" during installation

### Step 2: Install NVIDIA CUDA Toolkit
1. Download CUDA 12.4 from https://developer.nvidia.com/cuda-downloads
2. Install with default settings
3. Restart your PC

### Step 3: Setup the Application
1. Extract the project folder to any location (e.g., `C:\WAN_Video_Generator\`)
2. Double-click `install.bat`
3. Wait for all dependencies to install (this takes 5-10 minutes)

### Step 4: Download the Model (One-Time)
1. Make sure you're connected to the internet
2. Open a terminal in the project folder
3. Run: `venv\Scripts\activate && python download_model.py -r 480p`
4. For 720p model: `python download_model.py -r 720p`
5. For both: `python download_model.py -r both`
6. Each model is ~25GB — be patient

After this step, **you never need internet again**.

---

## Running the App

Double-click `run.bat` — the GUI will open.

---

## Basic Usage

### 1. Load an Image
- Click **Browse Image** or drag-and-drop a file onto the window
- Supported formats: JPEG, PNG, BMP, WEBP, TIFF

### 2. Write a Prompt
- Describe the motion you want in the video
- Be specific: "A woman slowly turns her head, her hair blowing in the wind"
- No character limit — write as much detail as needed

### 3. Choose Settings
- **Resolution:** 480p, 720p, or 1080p (depends on your GPU)
- **Video Length:** 2s to 15s
- **Quality:** Draft (fast) to Ultra (slow but best quality)

### 4. Generate
- Click **Generate Video**
- First time: the model will load into GPU memory (takes 1-3 minutes)
- Generation progress shows in the progress bar
- Output is saved as MP4 in `~/WAN_Videos/`

### 5. Extend Video
- After generating a video, click **Extend from Last Frame**
- Write a new prompt for the continuation
- The app takes the last frame and generates more video from it
- All segments are automatically concatenated into one combined video

---

## Advanced Settings (Expert Panel)

| Setting | Default | Description |
|---------|---------|-------------|
| **CFG Scale** | 5.0 | How closely the AI follows your prompt. Higher = more literal, lower = more creative |
| **Inference Steps** | 50 | More steps = better quality but slower. 20-30 for drafts, 50-80 for final |
| **Seed** | -1 (random) | Set a specific number to reproduce the same video. -1 = different each time |
| **Negative Prompt** | (preset) | Describes what you DON'T want in the video |
| **CPU Offloading** | Off | Moves parts of the model to CPU to save GPU memory. Slower but uses less VRAM |
| **Group Offloading** | Off | More aggressive memory saving. Enable if you get out-of-memory errors |

---

## How to Swap Model Checkpoints

If a newer WAN model is released:

1. Download the new model from Hugging Face (look for `-Diffusers` repos)
2. Place it in: `~/.wan_video_generator/models/`
3. The folder structure should be:
   ```
   models/
     Wan-AI--Wan2.1-I2V-14B-480P-Diffusers/
       transformer/
       vae/
       image_encoder/
       text_encoder/
       scheduler/
       model_index.json
   ```
4. Restart the app — it will detect the new model automatically

For Wan2.2 or newer versions, rename the folder to match the expected pattern or update the `MODEL_REPOS` dict in `core/engine.py`.

---

## Troubleshooting

### "CUDA out of memory"
- Lower the resolution (try 480p)
- Reduce video length
- Enable CPU Offloading or Group Offloading in Advanced settings
- Close other GPU-heavy apps (games, other AI tools)

### "Model not found"
- Run `download_model.py` while connected to internet
- Check that model files are in `~/.wan_video_generator/models/`

### Generation is very slow
- Make sure you're using GPU, not CPU (check Device setting)
- Lower inference steps (try 20-30 for drafts)
- Check that your GPU drivers are up to date

### App doesn't start
- Make sure Python 3.10+ is installed and in PATH
- Run `install.bat` again
- Try running manually: `venv\Scripts\activate && python main.py`

---

## File Locations

| Item | Location |
|------|----------|
| Models | `~/.wan_video_generator/models/` |
| Output videos | `~/WAN_Videos/` |
| Logs | `~/.wan_video_generator/logs/` |
