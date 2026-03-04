"""Application styles and theming."""

DARK_THEME = """
QMainWindow {
    background-color: #1a1a2e;
}
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QGroupBox {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 24px;
    font-weight: bold;
    font-size: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: #e94560;
    background-color: #16213e;
    border-radius: 4px;
}
QPushButton {
    background-color: #0f3460;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #1a4a8a;
}
QPushButton:pressed {
    background-color: #0a2540;
}
QPushButton:disabled {
    background-color: #2a2a3e;
    color: #666;
}
QPushButton#generateBtn {
    background-color: #e94560;
    font-size: 16px;
    padding: 14px 30px;
    min-height: 30px;
}
QPushButton#generateBtn:hover {
    background-color: #ff6b81;
}
QPushButton#generateBtn:disabled {
    background-color: #5a2030;
    color: #888;
}
QPushButton#extendBtn {
    background-color: #533483;
    font-size: 14px;
    padding: 12px 24px;
}
QPushButton#extendBtn:hover {
    background-color: #6a45a0;
}
QPushButton#cancelBtn {
    background-color: #c0392b;
    font-size: 14px;
    padding: 12px 24px;
}
QPushButton#cancelBtn:hover {
    background-color: #e74c3c;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0d1b36;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px;
    color: #e0e0e0;
    selection-background-color: #e94560;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #e94560;
}
QComboBox {
    background-color: #0d1b36;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px;
    color: #e0e0e0;
    min-height: 20px;
}
QComboBox:hover {
    border: 1px solid #e94560;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #0f3460;
    selection-background-color: #e94560;
    color: #e0e0e0;
}
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #0f3460;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #e94560;
    border: none;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #e94560;
    border-radius: 3px;
}
QSpinBox, QDoubleSpinBox {
    background-color: #0d1b36;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 6px;
    color: #e0e0e0;
}
QProgressBar {
    background-color: #0d1b36;
    border: 1px solid #0f3460;
    border-radius: 8px;
    text-align: center;
    font-weight: bold;
    color: #ffffff;
    min-height: 24px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e94560, stop:1 #533483);
    border-radius: 7px;
}
QLabel {
    color: #e0e0e0;
}
QLabel#titleLabel {
    font-size: 24px;
    font-weight: bold;
    color: #e94560;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #888;
}
QLabel#statusLabel {
    font-size: 12px;
    color: #aaa;
    padding: 4px;
}
QLabel#hwInfoLabel {
    font-size: 11px;
    color: #888;
    background-color: #0d1b36;
    border-radius: 4px;
    padding: 6px;
}
QLabel#warningLabel {
    color: #f39c12;
    font-size: 12px;
}
QLabel#imagePreview {
    background-color: #0d1b36;
    border: 2px dashed #0f3460;
    border-radius: 8px;
    min-height: 200px;
}
QCheckBox {
    spacing: 8px;
    color: #e0e0e0;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #0f3460;
    background-color: #0d1b36;
}
QCheckBox::indicator:checked {
    background-color: #e94560;
    border: 1px solid #e94560;
}
QTabWidget::pane {
    border: 1px solid #0f3460;
    border-radius: 8px;
    background-color: #16213e;
}
QTabBar::tab {
    background-color: #0d1b36;
    color: #888;
    border: none;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background-color: #16213e;
    color: #e94560;
    font-weight: bold;
}
QTabBar::tab:hover {
    background-color: #1a2a4e;
    color: #e0e0e0;
}
QScrollBar:vertical {
    background-color: #0d1b36;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #0f3460;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #e94560;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
