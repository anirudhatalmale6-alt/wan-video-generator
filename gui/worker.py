"""Background worker threads for non-blocking operations."""

from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image


class GenerationWorker(QThread):
    """Worker thread for video generation."""
    progress = pyqtSignal(int, int, str)  # step, total, message
    finished = pyqtSignal(object)  # GenerationResult
    error = pyqtSignal(str)

    def __init__(self, engine, image, settings, output_path):
        super().__init__()
        self.engine = engine
        self.image = image
        self.settings = settings
        self.output_path = output_path

    def run(self):
        try:
            self.engine.set_progress_callback(
                lambda step, total, msg: self.progress.emit(step, total, msg)
            )
            result = self.engine.generate(self.image, self.settings, self.output_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ModelLoadWorker(QThread):
    """Worker thread for model loading."""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, engine, resolution, device, cpu_offload, group_offload,
                 model_version="wan2.2"):
        super().__init__()
        self.engine = engine
        self.resolution = resolution
        self.device = device
        self.cpu_offload = cpu_offload
        self.group_offload = group_offload
        self.model_version = model_version

    def run(self):
        try:
            self.engine.set_progress_callback(
                lambda step, total, msg: self.progress.emit(step, total, msg)
            )

            # Check if model needs downloading
            if not self.engine.is_model_downloaded(self.resolution, self.model_version):
                self.progress.emit(0, 100, f"Model not found locally. Downloading {self.model_version}...")
                self.engine.download_model(self.resolution, self.model_version)

            self.engine.load_model(
                self.resolution,
                self.device,
                self.cpu_offload,
                self.group_offload,
                self.model_version,
            )
            self.finished.emit(True, f"Model loaded successfully ({self.model_version})")
        except Exception as e:
            self.finished.emit(False, str(e))


class ExtendWorker(QThread):
    """Worker thread for video extension."""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, engine, last_frame, settings, output_path):
        super().__init__()
        self.engine = engine
        self.last_frame = last_frame
        self.settings = settings
        self.output_path = output_path

    def run(self):
        try:
            self.engine.set_progress_callback(
                lambda step, total, msg: self.progress.emit(step, total, msg)
            )
            result = self.engine.extend_video(
                self.last_frame, self.settings, self.output_path
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
