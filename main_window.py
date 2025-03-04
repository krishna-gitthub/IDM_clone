#!/usr/bin/env python3
"""
main_window.py – Main window for IDM Clone Professional Edition.
Features:
  • Menu bar with Tasks, File, and Help menus.
  • Toolbar with Add URL, Resume, Stop, Stop All, and Delete actions.
  • A table listing downloads with columns for File Name, Size, Status, Progress, Speed, Time Left, and Date Added.
  • An Add URL dialog with fields for URL, destination folder, custom file name, number of segments, schedule time, and video resolution.
  • A download details window that opens on double-click or when a download starts/resumes.
  • Integration with DownloadManager, SettingsManager, and Logger (make sure these modules are updated accordingly).
"""

import sys
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QProgressBar,
    QVBoxLayout, QWidget, QAction, QToolBar, QMenu, QDialog, QLabel, QLineEdit,
    QPushButton, QFileDialog, QSpinBox, QDateTimeEdit, QHBoxLayout, QMessageBox,
    QComboBox, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from download_manager import DownloadManager   # Ensure this module is updated with video support.
from settings import SettingsManager            # Your settings module.
from logger import Logger                         # Your logger module.


class AddUrlDialog(QDialog):
    def __init__(self, default_folder):
        super().__init__()
        self.setWindowTitle("Add URL")
        self.default_folder = default_folder
        self.init_ui()

    def init_ui(self):
        self.resize(400, 250)
        layout = QVBoxLayout(self)
        # URL input
        self.url_edit = QLineEdit()
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(self.url_edit)
        # Destination folder input
        self.folder_edit = QLineEdit(self.default_folder)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(browse_btn)
        layout.addWidget(QLabel("Destination Folder:"))
        layout.addLayout(folder_layout)
        # File name input
        self.file_edit = QLineEdit()
        layout.addWidget(QLabel("Custom File Name (optional):"))
        layout.addWidget(self.file_edit)
        # Number of segments
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(1, 32)
        self.segments_spin.setValue(4)
        layout.addWidget(QLabel("Number of Segments:"))
        layout.addWidget(self.segments_spin)
        # Schedule download time
        self.schedule_edit = QDateTimeEdit()
        self.schedule_edit.setCalendarPopup(True)
        self.schedule_edit.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(QLabel("Schedule Download (optional):"))
        layout.addWidget(self.schedule_edit)
        # Video resolution selection
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Best", "1080p", "720p", "480p", "360p"])
        layout.addWidget(QLabel("Video Resolution (if applicable):"))
        layout.addWidget(self.resolution_combo)
        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.folder_edit.setText(folder)

    def get_info(self):
        schedule_dt = self.schedule_edit.dateTime().toPyDateTime()
        if schedule_dt <= datetime.datetime.now():
            schedule_dt = None
        return {
            "url": self.url_edit.text().strip(),
            "dest_folder": self.folder_edit.text().strip(),
            "file_name": self.file_edit.text().strip(),
            "segments": self.segments_spin.value(),
            "schedule_time": schedule_dt,
            "resolution": self.resolution_combo.currentText()
        }

class IDMMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDM Clone - Professional Edition")
        self.resize(900, 600)
        
        # Initialize settings, logger, and download manager.
        self.settings = SettingsManager()
        self.logger = Logger()
        self.download_manager = DownloadManager(self.logger, self.settings)
        self.details_windows = {}  # Dictionary to track open details windows.
        
        # Set up UI.
        self.init_ui()
        self.setup_timers()

    def init_ui(self):
        # Create central widget and layout.
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create menu bar and toolbar.
        self.create_menu_bar()
        self.create_toolbar()
        
        # Create table widget to display downloads.
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "File Name", "Size", "Status", "Progress", "Speed", "Time Left", "Date Added"
        ])
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        self.layout.addWidget(self.table)

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        tasks_menu = menubar.addMenu("Tasks")
        add_action = QAction("Add URL...", self)
        add_action.triggered.connect(self.add_url_dialog)
        tasks_menu.addAction(add_action)
        
        resume_action = QAction("Resume", self)
        resume_action.triggered.connect(self.resume_selected)
        tasks_menu.addAction(resume_action)
        
        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self.stop_selected)
        tasks_menu.addAction(stop_action)
        
        stop_all_action = QAction("Stop All", self)
        stop_all_action.triggered.connect(self.stop_all)
        tasks_menu.addAction(stop_all_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected)
        tasks_menu.addAction(delete_action)
        
        file_menu = menubar.addMenu("File")
        set_dir_action = QAction("Set Default Download Directory", self)
        set_dir_action.triggered.connect(self.set_default_dir)
        file_menu.addAction(set_dir_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About IDM Clone...", self)
        about_action.triggered.connect(self.about_dialog)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        add_btn = QAction("Add URL", self)
        add_btn.triggered.connect(self.add_url_dialog)
        toolbar.addAction(add_btn)
        resume_btn = QAction("Resume", self)
        resume_btn.triggered.connect(self.resume_selected)
        toolbar.addAction(resume_btn)
        stop_btn = QAction("Stop", self)
        stop_btn.triggered.connect(self.stop_selected)
        toolbar.addAction(stop_btn)
        stop_all_btn = QAction("Stop All", self)
        stop_all_btn.triggered.connect(self.stop_all)
        toolbar.addAction(stop_all_btn)
        delete_btn = QAction("Delete", self)
        delete_btn.triggered.connect(self.delete_selected)
        toolbar.addAction(delete_btn)

    def setup_timers(self):
        # Update table every second.
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_table)
        self.update_timer.start(1000)

    def refresh_table(self):
        tasks = self.download_manager.get_all_tasks()
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(task.file_name))
            size_str = f"{task.file_size/1024:.2f} KB" if task.file_size else "N/A"
            self.table.setItem(row, 1, QTableWidgetItem(size_str))
            self.table.setItem(row, 2, QTableWidgetItem(task.status))
            
            # Progress column with progress bar.
            progress_bar = QProgressBar()
            progress_bar.setValue(task.progress)
            self.table.setCellWidget(row, 3, progress_bar)
            
            speed_str = f"{task.speed:.1f} KB/s" if task.speed > 0 else "0 KB/s"
            self.table.setItem(row, 4, QTableWidgetItem(speed_str))
            self.table.setItem(row, 5, QTableWidgetItem(task.eta))
            self.table.setItem(row, 6, QTableWidgetItem(task.date_added.strftime("%b %d, %Y %H:%M:%S")))

    def add_url_dialog(self):
        dialog = AddUrlDialog(self.settings.default_download_dir)
        if dialog.exec_() == QDialog.Accepted:
            info = dialog.get_info()
            self.download_manager.add_download(
                info['url'],
                info['dest_folder'],
                info['file_name'],
                info['segments'],
                info['schedule_time'],
                resolution=info['resolution']
            )
            # Optionally, open details window immediately.
            last_task = self.download_manager.last_task()
            if last_task:
                self.open_details_window(last_task)

    def open_details_window(self, task):
        # Bring existing details window to front if already open.
        if task in self.details_windows:
            self.details_windows[task].raise_()
            self.details_windows[task].activateWindow()
        else:
            details_win = DownloadDetailsWindow(task, self.download_manager, self.logger)
            details_win.show()
            details_win.destroyed.connect(lambda: self.details_windows.pop(task, None))
            self.details_windows[task] = details_win

    def on_table_double_click(self, row, col):
        tasks = self.download_manager.get_all_tasks()
        if 0 <= row < len(tasks):
            self.open_details_window(tasks[row])

    def resume_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            task = self.download_manager.get_all_tasks()[row]
            self.download_manager.resume_task(task)
            self.open_details_window(task)

    def stop_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            task = self.download_manager.get_all_tasks()[row]
            self.download_manager.stop_task(task)

    def stop_all(self):
        self.download_manager.stop_all()

    def delete_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            task = self.download_manager.get_all_tasks()[row]
            reply = QMessageBox.question(self, "Confirm Delete",
                                         "Are you sure you want to delete this download?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.download_manager.remove_task(task)

    def set_default_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Download Directory")
        if folder:
            self.settings.default_download_dir = folder
            self.settings.save()

    def about_dialog(self):
        QMessageBox.information(self, "About IDM Clone",
                                "IDM Clone - Professional Edition\nDeveloped in Python using PyQt5.\nAll rights reserved.")

# Download Details Window – appears when a download starts/resumes or on double-click.
class DownloadDetailsWindow(QDialog):
    def __init__(self, task, download_manager, logger):
        super().__init__()
        self.task = task
        self.download_manager = download_manager
        self.logger = logger
        self.setWindowTitle(f"Download Details - {task.file_name}")
        self.resize(500, 350)
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        self.tab_widget = QTabWidget(self)
        self.status_tab = QWidget()
        self.speed_tab = QWidget()
        self.options_tab = QWidget()
        self.tab_widget.addTab(self.status_tab, "Status")
        self.tab_widget.addTab(self.speed_tab, "Speed Limiter")
        self.tab_widget.addTab(self.options_tab, "Completion Options")
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tab_widget)
        
        # Status Tab Layout
        s_layout = QVBoxLayout(self.status_tab)
        self.status_label = QLabel(f"Status: {self.task.status}")
        self.size_label = QLabel("File Size: N/A")
        self.downloaded_label = QLabel("Downloaded: N/A")
        self.speed_label = QLabel("Speed: N/A")
        self.eta_label = QLabel("ETA: N/A")
        self.progress_bar = QProgressBar()
        s_layout.addWidget(self.status_label)
        s_layout.addWidget(self.size_label)
        s_layout.addWidget(self.downloaded_label)
        s_layout.addWidget(self.speed_label)
        s_layout.addWidget(self.eta_label)
        s_layout.addWidget(self.progress_bar)
        
        # Speed Limiter Tab Layout
        sp_layout = QVBoxLayout(self.speed_tab)
        self.limiter_label = QLabel("Set Speed Limit (KB/s), 0 for unlimited:")
        self.limiter_spin = QSpinBox()
        self.limiter_spin.setRange(0, 100000)
        self.limiter_spin.setValue(0)
        sp_layout.addWidget(self.limiter_label)
        sp_layout.addWidget(self.limiter_spin)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_speed_limit)
        sp_layout.addWidget(apply_btn)
        sp_layout.addStretch()
        
        # Completion Options Tab Layout
        o_layout = QVBoxLayout(self.options_tab)
        self.shutdown_checkbox = QPushButton("Shutdown computer on completion (demo)")
        self.shutdown_checkbox.setCheckable(True)
        o_layout.addWidget(self.shutdown_checkbox)
        o_layout.addStretch()
        
        # Bottom Buttons
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

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(500)

    def update_ui(self):
        self.status_label.setText(f"Status: {self.task.status}")
        if self.task.file_size:
            self.size_label.setText(f"File Size: {self.task.file_size/1024:.2f} KB")
            downloaded = (self.task.file_size * self.task.progress / 100)
            self.downloaded_label.setText(f"Downloaded: {downloaded/1024:.2f} KB")
        else:
            self.size_label.setText("File Size: N/A")
            self.downloaded_label.setText("Downloaded: N/A")
        self.speed_label.setText(f"Speed: {self.task.speed:.1f} KB/s")
        self.eta_label.setText(f"ETA: {self.task.eta}")
        self.progress_bar.setValue(self.task.progress)
        if self.task.status == "Downloading":
            self.pause_btn.setText("Pause")
        elif self.task.status == "Paused":
            self.pause_btn.setText("Resume")
        else:
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
        limit = self.limiter_spin.value()
        self.logger.log(f"Speed limit for {self.task.file_name} set to {limit} KB/s (not enforced in demo).")

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IDMMainWindow()
    window.show()
    sys.exit(app.exec_())
