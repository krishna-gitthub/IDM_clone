"""
download_details_window.py – The separate window that appears
when a download starts or is resumed, emulating IDM's extra window.

Contains:
  • A QTabWidget with tabs:
      1) Download Status
      2) Speed Limiter
      3) Options on Completion
  • Real-time progress and status updates.
  • Basic speed limiter control (per-download).
  • A "Pause"/"Resume" button and "Stop" button.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QLabel, QProgressBar,
    QPushButton, QHBoxLayout, QSpinBox, QCheckBox
)
from PyQt5.QtCore import QTimer
import time

class DownloadDetailsWindow(QDialog):
    def __init__(self, task, download_manager):
        super().__init__()
        self.task = task
        self.download_manager = download_manager

        self.setWindowTitle(f"Download Details - {task.file_name}")
        self.resize(500, 300)

        self.tab_widget = QTabWidget()
        self.status_tab = QWidget()
        self.speed_tab = QWidget()
        self.options_tab = QWidget()

        self.tab_widget.addTab(self.status_tab, "Download Status")
        self.tab_widget.addTab(self.speed_tab, "Speed Limiter")
        self.tab_widget.addTab(self.options_tab, "Options on Completion")

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tab_widget)

        # Initialize each tab
        self.init_status_tab()
        self.init_speed_tab()
        self.init_options_tab()

        # Bottom buttons: Pause/Resume, Stop, Close
        btn_layout = QHBoxLayout()
        self.pause_btn = QPushButton("Pause" if self.task.status == "Downloading" else "Resume")
        self.pause_btn.clicked.connect(self.toggle_pause_resume)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_download)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.close_btn)
        main_layout.addLayout(btn_layout)

        # Timer to update UI
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(500)

    def init_status_tab(self):
        layout = QVBoxLayout(self.status_tab)

        self.status_label = QLabel(f"Status: {self.task.status}")
        self.size_label = QLabel("File size: 0")
        self.downloaded_label = QLabel("Downloaded: 0")
        self.speed_label = QLabel("Speed: 0 KB/s")
        self.time_left_label = QLabel("Time left: N/A")
        self.progress_bar = QProgressBar()

        layout.addWidget(self.status_label)
        layout.addWidget(self.size_label)
        layout.addWidget(self.downloaded_label)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.time_left_label)
        layout.addWidget(self.progress_bar)

    def init_speed_tab(self):
        layout = QVBoxLayout(self.speed_tab)
        self.limiter_label = QLabel("Set speed limit (KB/s). 0 for unlimited:")
        self.limiter_spin = QSpinBox()
        self.limiter_spin.setRange(0, 999999)
        self.limiter_spin.setValue(0)  # 0 means unlimited
        # If you want to apply a per-download speed limit, you'd integrate logic in the manager.
        layout.addWidget(self.limiter_label)
        layout.addWidget(self.limiter_spin)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_speed_limit)
        layout.addWidget(apply_btn)
        layout.addStretch()

    def init_options_tab(self):
        layout = QVBoxLayout(self.options_tab)
        self.shutdown_check = QCheckBox("Shut down computer when download completes")
        # In a real app, you'd wire this to actual system commands
        layout.addWidget(self.shutdown_check)
        layout.addStretch()

    def update_ui(self):
        self.status_label.setText(f"Status: {self.task.status}")

        if self.task.file_size > 0:
            self.size_label.setText(f"File size: {self.human_readable_size(self.task.file_size)}")
            downloaded_str = self.human_readable_size(int(self.task.progress / 100 * self.task.file_size))
        else:
            downloaded_str = "N/A"
        self.downloaded_label.setText(f"Downloaded: {downloaded_str}")

        speed_str = f"{self.task.speed:.1f} KB/s"
        self.speed_label.setText(f"Speed: {speed_str}")

        self.time_left_label.setText(f"Time left: {self.task.eta}")

        self.progress_bar.setValue(self.task.progress)

        # Update pause button label
        if self.task.status == "Downloading":
            self.pause_btn.setText("Pause")
        elif self.task.status == "Paused":
            self.pause_btn.setText("Resume")
        elif self.task.status in ["Completed", "Error", "Cancelled"]:
            self.pause_btn.setEnabled(False)

    def toggle_pause_resume(self):
        if self.task.status == "Downloading":
            self.download_manager.stop_task(self.task, pause_only=True)
        elif self.task.status == "Paused":
            self.download_manager.resume_task(self.task)

    def stop_download(self):
        self.download_manager.stop_task(self.task)
        self.stop_btn.setEnabled(False)

    def apply_speed_limit(self):
        # In a real scenario, you'd store this limit in the task or manager
        limit = self.limiter_spin.value()
        # For demonstration, we'll just log it
        self.download_manager.logger.log(f"Speed limit for {self.task.file_name} set to {limit} KB/s (not fully enforced in code).")

    def human_readable_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
