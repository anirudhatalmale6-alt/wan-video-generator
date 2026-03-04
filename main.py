#!/usr/bin/env python3
"""WAN Video Generator — Offline AI Image-to-Video Application.

Converts still images into AI-generated videos using the WAN2.1 model,
entirely offline with no external API calls or telemetry.
"""

import logging
import os
import sys

# Configure logging
log_dir = os.path.join(os.path.expanduser("~"), ".wan_video_generator", "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(log_dir, "wan_video_generator.log"),
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Launch the application."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from gui.main_window import MainWindow
    from gui.styles import DARK_THEME

    # Enable high DPI scaling
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("WAN Video Generator")
    app.setOrganizationName("WAN Video Generator")
    app.setApplicationVersion("1.0.0")

    # Apply dark theme
    app.setStyleSheet(DARK_THEME)

    # Enable drag and drop
    window = MainWindow()
    window.setAcceptDrops(True)
    window.show()

    logger.info("Application started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
