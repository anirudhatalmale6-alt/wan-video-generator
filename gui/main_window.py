"""Main application window."""

import logging
import os
import sys
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QUrl, QTimer
from PyQt6.QtGui import QPixmap, QImage, QIcon, QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QFileDialog, QProgressBar, QGroupBox, QTabWidget,
    QCheckBox, QMessageBox, QSplitter, QFrame, QApplication,
    QSlider, QSizePolicy,
)

from core.engine import VideoGenerationEngine, GenerationSettings, DEFAULT_NEGATIVE_PROMPT
from core.tts_engine import TTSEngine, VOICE_CATALOG
from core.audio_merge import merge_audio_video
from core.video_concat import concat_videos, get_video_info
from utils.gpu_detect import (
    get_hardware_profile, RESOLUTION_PRESETS, DURATION_PRESETS,
)
from utils.image_utils import (
    is_supported_image, get_image_info, extract_last_frame, SUPPORTED_FORMATS,
)
from gui.worker import GenerationWorker, ModelLoadWorker, ExtendWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WAN Video Generator — AI Image-to-Video")
        self.setMinimumSize(1100, 750)
        self.resize(1280, 800)

        # State
        self.engine = VideoGenerationEngine()
        self.tts_engine = TTSEngine()
        self.current_image_path = None
        self.current_image = None
        self.last_generated_frames = None
        self.last_output_path = None
        self.generation_segments = []  # Paths of generated segments for concat
        self.worker = None
        self.hw_profile = None

        self._build_ui()
        self._detect_hardware()

    def _detect_hardware(self):
        """Detect hardware on startup."""
        self.hw_profile = get_hardware_profile()
        info_parts = []

        if self.hw_profile.gpus:
            gpu = self.hw_profile.gpus[0]
            info_parts.append(f"GPU: {gpu.name} ({gpu.vram_total_gb:.0f}GB VRAM)")
        else:
            info_parts.append("GPU: None detected (CPU mode)")

        info_parts.append(f"CPU: {self.hw_profile.cpu_name}")
        info_parts.append(f"RAM: {self.hw_profile.ram_total_mb // 1024}GB")
        info_parts.append(f"Recommended max: {self.hw_profile.max_resolution}, "
                          f"{self.hw_profile.max_video_seconds:.0f}s")

        self.hw_info_label.setText("  |  ".join(info_parts))

        if self.hw_profile.warnings:
            self.status_label.setText("Warning: " + self.hw_profile.warnings[0])

        # Set default device
        if self.hw_profile.recommended_device == "cpu":
            self.device_combo.setCurrentIndex(1)  # CPU

        self._update_resolution_limits()

    def _update_resolution_limits(self):
        """Update available options based on hardware."""
        # All options remain available but we highlight recommended ones
        pass

    def _build_ui(self):
        """Build the complete UI."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 8, 12, 8)

        # Header
        header = QHBoxLayout()
        title = QLabel("WAN Video Generator")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()
        subtitle = QLabel("Offline AI Image-to-Video  |  Powered by WAN2.1")
        subtitle.setObjectName("subtitleLabel")
        header.addWidget(subtitle)
        main_layout.addLayout(header)

        # Hardware info bar
        self.hw_info_label = QLabel("Detecting hardware...")
        self.hw_info_label.setObjectName("hwInfoLabel")
        main_layout.addWidget(self.hw_info_label)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # === LEFT PANEL: Image + Prompt ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)

        # Image upload section
        img_group = QGroupBox("Input Image")
        img_layout = QVBoxLayout(img_group)

        self.image_preview = QLabel("Drop image here or click Browse")
        self.image_preview.setObjectName("imagePreview")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumHeight(220)
        self.image_preview.setMaximumHeight(350)
        self.image_preview.setSizePolicy(QSizePolicy.Policy.Expanding,
                                         QSizePolicy.Policy.Expanding)
        img_layout.addWidget(self.image_preview)

        img_btn_row = QHBoxLayout()
        self.browse_btn = QPushButton("Browse Image")
        self.browse_btn.clicked.connect(self._browse_image)
        img_btn_row.addWidget(self.browse_btn)

        self.img_info_label = QLabel("")
        self.img_info_label.setObjectName("statusLabel")
        img_btn_row.addWidget(self.img_info_label)
        img_btn_row.addStretch()
        img_layout.addLayout(img_btn_row)

        left_layout.addWidget(img_group)

        # Prompt section
        prompt_group = QGroupBox("Prompt")
        prompt_layout = QVBoxLayout(prompt_group)

        prompt_label = QLabel("Describe the motion/animation you want:")
        prompt_layout.addWidget(prompt_label)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Example: A woman slowly turns her head and smiles, "
            "her hair gently blowing in the wind, cinematic lighting"
        )
        self.prompt_edit.setMinimumHeight(80)
        self.prompt_edit.setMaximumHeight(150)
        prompt_layout.addWidget(self.prompt_edit)

        left_layout.addWidget(prompt_group)

        # Voice / Narration section
        voice_group = QGroupBox("Voice Output")
        voice_layout = QVBoxLayout(voice_group)

        self.enable_voice_check = QCheckBox(
            "Read prompt as voice in output video"
        )
        self.enable_voice_check.toggled.connect(self._toggle_voice_panel)
        voice_layout.addWidget(self.enable_voice_check)

        voice_hint = QLabel(
            "When enabled, your prompt text above will be spoken as voice "
            "narration and merged into the final video audio."
        )
        voice_hint.setWordWrap(True)
        voice_hint.setObjectName("statusLabel")
        voice_layout.addWidget(voice_hint)

        # Voice settings container (hidden by default)
        self.voice_settings_widget = QWidget()
        voice_settings_layout = QVBoxLayout(self.voice_settings_widget)
        voice_settings_layout.setContentsMargins(0, 4, 0, 0)

        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("Voice:"))
        self.voice_combo = QComboBox()
        for v in VOICE_CATALOG:
            self.voice_combo.addItem(f"{v.name}  ({v.quality})", v.id)
        self.voice_combo.setCurrentIndex(0)
        voice_row.addWidget(self.voice_combo, 1)
        voice_settings_layout.addLayout(voice_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self.voice_speed_combo = QComboBox()
        self.voice_speed_combo.addItem("Slow (0.75x)", "0.75")
        self.voice_speed_combo.addItem("Normal (1.0x)", "1.0")
        self.voice_speed_combo.addItem("Fast (1.25x)", "1.25")
        self.voice_speed_combo.addItem("Very Fast (1.5x)", "1.5")
        self.voice_speed_combo.setCurrentIndex(1)
        speed_row.addWidget(self.voice_speed_combo, 1)

        speed_row.addWidget(QLabel("Volume:"))
        self.voice_volume_combo = QComboBox()
        self.voice_volume_combo.addItem("Low (50%)", "0.5")
        self.voice_volume_combo.addItem("Medium (75%)", "0.75")
        self.voice_volume_combo.addItem("Full (100%)", "1.0")
        self.voice_volume_combo.setCurrentIndex(2)
        speed_row.addWidget(self.voice_volume_combo, 1)
        voice_settings_layout.addLayout(speed_row)

        self.voice_settings_widget.setVisible(False)
        voice_layout.addWidget(self.voice_settings_widget)

        left_layout.addWidget(voice_group)
        left_layout.addStretch()

        splitter.addWidget(left_panel)

        # === RIGHT PANEL: Settings + Controls ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)

        # Settings tabs
        tabs = QTabWidget()

        # --- Basic Settings Tab ---
        basic_tab = QWidget()
        basic_layout = QGridLayout(basic_tab)
        basic_layout.setSpacing(10)
        basic_layout.setContentsMargins(12, 12, 12, 12)
        row = 0

        # Resolution
        basic_layout.addWidget(QLabel("Resolution:"), row, 0)
        self.resolution_combo = QComboBox()
        for key, preset in RESOLUTION_PRESETS.items():
            self.resolution_combo.addItem(preset["label"], key)
        self.resolution_combo.setCurrentIndex(0)  # Default 480p
        basic_layout.addWidget(self.resolution_combo, row, 1)
        row += 1

        # Duration
        basic_layout.addWidget(QLabel("Video Length:"), row, 0)
        self.duration_combo = QComboBox()
        for key, preset in DURATION_PRESETS.items():
            self.duration_combo.addItem(preset["label"], key)
        self.duration_combo.setCurrentIndex(2)  # Default 5s
        basic_layout.addWidget(self.duration_combo, row, 1)
        row += 1

        # FPS
        basic_layout.addWidget(QLabel("Frame Rate (FPS):"), row, 0)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(8, 30)
        self.fps_spin.setValue(16)
        basic_layout.addWidget(self.fps_spin, row, 1)
        row += 1

        # Device
        basic_layout.addWidget(QLabel("Device:"), row, 0)
        self.device_combo = QComboBox()
        self.device_combo.addItem("CUDA (NVIDIA GPU)", "cuda")
        self.device_combo.addItem("CPU (Very Slow)", "cpu")
        basic_layout.addWidget(self.device_combo, row, 1)
        row += 1

        # Quality preset
        basic_layout.addWidget(QLabel("Quality:"), row, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Draft (20 steps) — Fast", "20")
        self.quality_combo.addItem("Standard (30 steps)", "30")
        self.quality_combo.addItem("High (50 steps) — Default", "50")
        self.quality_combo.addItem("Ultra (80 steps) — Slow", "80")
        self.quality_combo.setCurrentIndex(2)  # Default High
        basic_layout.addWidget(self.quality_combo, row, 1)
        row += 1

        basic_layout.setRowStretch(row, 1)
        tabs.addTab(basic_tab, "Basic Settings")

        # --- Advanced Settings Tab ---
        adv_tab = QWidget()
        adv_layout = QGridLayout(adv_tab)
        adv_layout.setSpacing(10)
        adv_layout.setContentsMargins(12, 12, 12, 12)
        row = 0

        # CFG Scale
        adv_layout.addWidget(QLabel("CFG Scale:"), row, 0)
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(1.0, 20.0)
        self.cfg_spin.setValue(5.0)
        self.cfg_spin.setSingleStep(0.5)
        adv_layout.addWidget(self.cfg_spin, row, 1)
        row += 1

        # Inference steps (manual override)
        adv_layout.addWidget(QLabel("Inference Steps:"), row, 0)
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(10, 150)
        self.steps_spin.setValue(50)
        adv_layout.addWidget(self.steps_spin, row, 1)
        row += 1

        # Seed
        adv_layout.addWidget(QLabel("Seed (-1 = random):"), row, 0)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 2147483647)
        self.seed_spin.setValue(-1)
        adv_layout.addWidget(self.seed_spin, row, 1)
        row += 1

        # Negative prompt
        adv_layout.addWidget(QLabel("Negative Prompt:"), row, 0, 1, 2)
        row += 1
        self.neg_prompt_edit = QTextEdit()
        self.neg_prompt_edit.setPlainText(DEFAULT_NEGATIVE_PROMPT)
        self.neg_prompt_edit.setMaximumHeight(100)
        adv_layout.addWidget(self.neg_prompt_edit, row, 0, 1, 2)
        row += 1

        # Memory optimization
        adv_layout.addWidget(QLabel("Memory Optimization:"), row, 0, 1, 2)
        row += 1

        self.cpu_offload_check = QCheckBox("Enable CPU Offloading (saves VRAM, slower)")
        adv_layout.addWidget(self.cpu_offload_check, row, 0, 1, 2)
        row += 1

        self.group_offload_check = QCheckBox(
            "Enable Group Offloading (aggressive VRAM saving)"
        )
        adv_layout.addWidget(self.group_offload_check, row, 0, 1, 2)
        row += 1

        adv_layout.setRowStretch(row, 1)
        tabs.addTab(adv_tab, "Advanced / Expert")

        # --- Model Tab ---
        model_tab = QWidget()
        model_layout = QVBoxLayout(model_tab)
        model_layout.setContentsMargins(12, 12, 12, 12)

        model_layout.addWidget(QLabel(
            "Model: WAN2.1 Image-to-Video 14B\n"
            "Source: Wan-AI (Hugging Face)\n\n"
            "The model will be downloaded automatically on first use.\n"
            "480p model: ~25GB download\n"
            "720p model: ~25GB download\n\n"
            "Models are stored in:\n"
            "~/.wan_video_generator/models/"
        ))

        model_path_row = QHBoxLayout()
        self.model_path_label = QLabel(
            os.path.join(os.path.expanduser("~"), ".wan_video_generator", "models")
        )
        self.model_path_label.setObjectName("statusLabel")
        model_path_row.addWidget(self.model_path_label)

        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.clicked.connect(self._open_model_folder)
        model_path_row.addWidget(open_folder_btn)
        model_layout.addLayout(model_path_row)

        self.load_model_btn = QPushButton("Load / Reload Model")
        self.load_model_btn.clicked.connect(self._load_model)
        model_layout.addWidget(self.load_model_btn)

        self.model_status_label = QLabel("Model not loaded")
        self.model_status_label.setObjectName("statusLabel")
        model_layout.addWidget(self.model_status_label)

        model_layout.addStretch()
        tabs.addTab(model_tab, "Model")

        right_layout.addWidget(tabs)

        # Output section
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)

        out_path_row = QHBoxLayout()
        out_path_row.addWidget(QLabel("Save to:"))
        self.output_path_label = QLabel(self._default_output_dir())
        self.output_path_label.setObjectName("statusLabel")
        out_path_row.addWidget(self.output_path_label, 1)
        change_output_btn = QPushButton("Change")
        change_output_btn.clicked.connect(self._change_output_dir)
        out_path_row.addWidget(change_output_btn)
        output_layout.addLayout(out_path_row)

        right_layout.addWidget(output_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([500, 500])

        main_layout.addWidget(splitter, 1)

        # === BOTTOM: Controls + Progress ===
        controls_frame = QFrame()
        controls_frame.setStyleSheet(
            "QFrame { background-color: #16213e; border-radius: 8px; padding: 8px; }"
        )
        controls_layout = QVBoxLayout(controls_frame)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%v% — %p")
        controls_layout.addWidget(self.progress_bar)

        # Buttons row
        btn_row = QHBoxLayout()

        self.generate_btn = QPushButton("Generate Video")
        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.clicked.connect(self._start_generation)
        btn_row.addWidget(self.generate_btn)

        self.extend_btn = QPushButton("Extend from Last Frame")
        self.extend_btn.setObjectName("extendBtn")
        self.extend_btn.setEnabled(False)
        self.extend_btn.clicked.connect(self._start_extend)
        btn_row.addWidget(self.extend_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_generation)
        btn_row.addWidget(self.cancel_btn)

        btn_row.addStretch()

        self.open_output_btn = QPushButton("Open Last Video")
        self.open_output_btn.setEnabled(False)
        self.open_output_btn.clicked.connect(self._open_last_video)
        btn_row.addWidget(self.open_output_btn)

        controls_layout.addLayout(btn_row)

        # Status label
        self.status_label = QLabel("Ready — Load an image to begin")
        self.status_label.setObjectName("statusLabel")
        controls_layout.addWidget(self.status_label)

        main_layout.addWidget(controls_frame)

        # Connect quality combo to steps spin
        self.quality_combo.currentIndexChanged.connect(self._quality_changed)

    def _toggle_voice_panel(self, checked: bool):
        """Show/hide voice settings panel."""
        self.voice_settings_widget.setVisible(checked)

    def _default_output_dir(self) -> str:
        """Get default output directory."""
        d = os.path.join(os.path.expanduser("~"), "WAN_Videos")
        os.makedirs(d, exist_ok=True)
        return d

    def _quality_changed(self):
        """Sync quality preset with steps spinbox."""
        steps = int(self.quality_combo.currentData())
        self.steps_spin.setValue(steps)

    def _browse_image(self):
        """Open file dialog to select an image."""
        formats = " ".join(f"*{ext}" for ext in SUPPORTED_FORMATS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Input Image", "",
            f"Image Files ({formats});;All Files (*)"
        )
        if path:
            self._load_image(path)

    def _load_image(self, path: str):
        """Load and display the selected image."""
        if not is_supported_image(path):
            QMessageBox.warning(self, "Unsupported Format",
                                f"File format not supported. Use: {', '.join(SUPPORTED_FORMATS)}")
            return

        try:
            from PIL import Image as PILImage
            self.current_image = PILImage.open(path).convert("RGB")
            self.current_image_path = path

            # Show preview
            pixmap = QPixmap(path)
            scaled = pixmap.scaled(
                self.image_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_preview.setPixmap(scaled)

            # Show info
            info = get_image_info(path)
            self.img_info_label.setText(
                f"{info.get('width', '?')}x{info.get('height', '?')} | "
                f"{info.get('format', '?')} | {info.get('size_kb', 0):.0f}KB"
            )
            self.status_label.setText(f"Image loaded: {os.path.basename(path)}")
            self.generation_segments.clear()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")

    def _change_output_dir(self):
        """Change output directory."""
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if d:
            self.output_path_label.setText(d)

    def _open_model_folder(self):
        """Open model folder in file explorer."""
        path = self.model_path_label.text()
        os.makedirs(path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _get_settings(self) -> GenerationSettings:
        """Build GenerationSettings from UI state."""
        res_key = self.resolution_combo.currentData()
        dur_key = self.duration_combo.currentData()
        dur_preset = DURATION_PRESETS[dur_key]

        return GenerationSettings(
            prompt=self.prompt_edit.toPlainText().strip(),
            negative_prompt=self.neg_prompt_edit.toPlainText().strip(),
            resolution=res_key,
            duration_seconds=dur_preset["seconds"],
            fps=self.fps_spin.value(),
            guidance_scale=self.cfg_spin.value(),
            num_inference_steps=self.steps_spin.value(),
            seed=self.seed_spin.value(),
            device=self.device_combo.currentData(),
            enable_cpu_offload=self.cpu_offload_check.isChecked(),
            enable_group_offload=self.group_offload_check.isChecked(),
        )

    def _get_output_path(self, suffix: str = "") -> str:
        """Generate unique output file path."""
        out_dir = self.output_path_label.text()
        os.makedirs(out_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        name = f"wan_video_{timestamp}{suffix}.mp4"
        return os.path.join(out_dir, name)

    def _load_model(self):
        """Load the model in background."""
        settings = self._get_settings()
        self._set_ui_busy(True, "Loading model...")

        self.worker = ModelLoadWorker(
            self.engine,
            settings.resolution,
            settings.device,
            settings.enable_cpu_offload,
            settings.enable_group_offload,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_model_loaded)
        self.worker.start()

    def _on_model_loaded(self, success: bool, message: str):
        """Handle model load completion."""
        self._set_ui_busy(False)
        if success:
            self.model_status_label.setText("Model loaded and ready")
            self.status_label.setText("Model loaded — ready to generate!")
        else:
            self.model_status_label.setText(f"Load failed: {message}")
            self.status_label.setText(f"Model load error: {message}")
            QMessageBox.critical(self, "Model Error", f"Failed to load model:\n\n{message}")

    def _start_generation(self):
        """Start video generation."""
        if self.current_image is None:
            QMessageBox.warning(self, "No Image", "Please load an input image first.")
            return

        settings = self._get_settings()
        if not settings.prompt:
            QMessageBox.warning(self, "No Prompt", "Please enter a prompt describing the desired motion.")
            return

        # Auto-load model if needed
        if not self.engine.is_model_loaded():
            reply = QMessageBox.question(
                self, "Load Model",
                "The model needs to be loaded first. This may take several minutes "
                "and requires significant disk space for the first download.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            # Load model then start generation
            self._set_ui_busy(True, "Loading model before generation...")
            self.worker = ModelLoadWorker(
                self.engine, settings.resolution, settings.device,
                settings.enable_cpu_offload, settings.enable_group_offload,
            )
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(
                lambda ok, msg: self._after_model_load_generate(ok, msg, settings)
            )
            self.worker.start()
            return

        self._run_generation(settings)

    def _after_model_load_generate(self, success: bool, message: str,
                                   settings: GenerationSettings):
        """After model loads, start generation."""
        if success:
            self.model_status_label.setText("Model loaded and ready")
            self._run_generation(settings)
        else:
            self._set_ui_busy(False)
            QMessageBox.critical(self, "Model Error", f"Failed to load model:\n\n{message}")

    def _run_generation(self, settings: GenerationSettings):
        """Actually run the generation."""
        output_path = self._get_output_path()
        self._set_ui_busy(True, "Generating video...")

        self.worker = GenerationWorker(
            self.engine, self.current_image, settings, output_path
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_generation_complete)
        self.worker.error.connect(self._on_generation_error)
        self.worker.start()

    def _start_extend(self):
        """Extend video from last frame."""
        if self.last_generated_frames is None:
            QMessageBox.warning(self, "No Video", "Generate a video first before extending.")
            return

        settings = self._get_settings()
        if not settings.prompt:
            QMessageBox.warning(self, "No Prompt",
                                "Enter a prompt for the video extension.")
            return

        try:
            last_frame = extract_last_frame(self.last_generated_frames)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract last frame: {e}")
            return

        output_path = self._get_output_path("_ext")
        self._set_ui_busy(True, "Extending video from last frame...")

        self.worker = ExtendWorker(
            self.engine, last_frame, settings, output_path
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_extend_complete)
        self.worker.error.connect(self._on_generation_error)
        self.worker.start()

    def _merge_voice_with_video(self, video_path: str) -> str:
        """If voice is enabled, generate TTS from prompt and merge with video. Returns final path."""
        if not self.enable_voice_check.isChecked():
            return video_path

        # Use the main prompt text as voice narration
        voice_text = self.prompt_edit.toPlainText().strip()
        if not voice_text:
            return video_path

        voice_id = self.voice_combo.currentData()
        speed = float(self.voice_speed_combo.currentData())
        volume = float(self.voice_volume_combo.currentData())

        self.status_label.setText("Generating voice narration...")
        self.progress_bar.setFormat("Generating voice narration...")

        try:
            # Generate TTS audio
            wav_path = video_path.replace(".mp4", "_voice.wav")
            self.tts_engine.synthesize(
                text=voice_text,
                output_path=wav_path,
                voice_id=voice_id,
                speed=speed,
            )

            # Merge audio with video
            self.status_label.setText("Merging voice with video...")
            self.progress_bar.setFormat("Merging voice with video...")

            merged_path = video_path.replace(".mp4", "_with_voice.mp4")
            merge_audio_video(
                video_path=video_path,
                audio_path=wav_path,
                output_path=merged_path,
                audio_volume=volume,
                fade_in=0.2,
                fade_out=0.3,
            )

            # Clean up temp WAV
            try:
                os.remove(wav_path)
            except OSError:
                pass

            return merged_path

        except Exception as e:
            logger.error(f"Voice merge failed: {e}")
            self.status_label.setText(f"Voice merge failed: {e} — video saved without audio")
            return video_path

    def _on_generation_complete(self, result):
        """Handle generation completion."""
        if result.success:
            # Try to add voice narration if enabled
            final_path = self._merge_voice_with_video(result.output_path)

            self._set_ui_busy(False)
            self.last_generated_frames = result.frames
            self.last_output_path = final_path
            self.generation_segments.append(final_path)
            self.extend_btn.setEnabled(True)
            self.open_output_btn.setEnabled(True)

            has_voice = final_path != result.output_path
            voice_tag = " + Voice" if has_voice else ""

            # Update seed display if random
            if self.seed_spin.value() == -1:
                self.status_label.setText(
                    f"Done!{voice_tag} {result.resolution[0]}x{result.resolution[1]}, "
                    f"{result.num_frames} frames, seed={result.seed_used}, "
                    f"{result.generation_time:.1f}s  |  {final_path}"
                )
            else:
                self.status_label.setText(
                    f"Done!{voice_tag} {result.generation_time:.1f}s  |  {final_path}"
                )

            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Generation complete!")
        else:
            self._set_ui_busy(False)
            self.status_label.setText(f"Error: {result.error}")
            QMessageBox.critical(self, "Generation Failed", result.error)

    def _on_extend_complete(self, result):
        """Handle extension completion."""
        self._set_ui_busy(False)

        if result.success:
            self.last_generated_frames = result.frames
            self.generation_segments.append(result.output_path)

            # Auto-concatenate all segments
            if len(self.generation_segments) > 1:
                try:
                    concat_path = self._get_output_path("_combined")
                    concat_videos(
                        self.generation_segments,
                        concat_path,
                        fps=self.fps_spin.value(),
                    )
                    self.last_output_path = concat_path
                    info = get_video_info(concat_path)
                    self.status_label.setText(
                        f"Extended! Combined {len(self.generation_segments)} segments: "
                        f"{info.get('duration', 0):.1f}s  |  {concat_path}"
                    )
                except Exception as e:
                    self.last_output_path = result.output_path
                    self.status_label.setText(
                        f"Extension done (concat failed: {e})  |  {result.output_path}"
                    )
            else:
                self.last_output_path = result.output_path
                self.status_label.setText(f"Extended!  |  {result.output_path}")

            self.open_output_btn.setEnabled(True)
            self.progress_bar.setValue(100)
        else:
            self.status_label.setText(f"Extension error: {result.error}")
            QMessageBox.critical(self, "Extension Failed", result.error)

    def _on_generation_error(self, error_msg: str):
        """Handle worker error."""
        self._set_ui_busy(False)
        self.status_label.setText(f"Error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)

    def _cancel_generation(self):
        """Cancel ongoing generation."""
        if self.engine:
            self.engine.cancel()
        self.status_label.setText("Cancelling...")
        self.cancel_btn.setEnabled(False)

    def _on_progress(self, step: int, total: int, message: str):
        """Update progress bar."""
        if total > 0:
            pct = int((step / total) * 100)
            self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(message or f"{step}/{total}")
        self.status_label.setText(message)

    def _set_ui_busy(self, busy: bool, message: str = ""):
        """Enable/disable UI during operations."""
        self.generate_btn.setEnabled(not busy)
        self.extend_btn.setEnabled(not busy and self.last_generated_frames is not None)
        self.browse_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.load_model_btn.setEnabled(not busy)

        if busy:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat(message)
            self.status_label.setText(message)
        elif not message:
            self.progress_bar.setFormat("Ready")

    def _open_last_video(self):
        """Open last generated video in default player."""
        if self.last_output_path and os.path.exists(self.last_output_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output_path))

    # Drag and drop support
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if is_supported_image(path):
                self._load_image(path)
                break
