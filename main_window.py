"""
main_window.py – Implements the main IDM-like window UI.
Features:
  • Menu bar (Tasks, File, View, Help)
  • Toolbar (Add URL, Resume, Stop, Stop All, Delete, etc.)
  • A table listing downloads with columns:
      - File Name
      - Size
      - Status
      - Progress (with bar)
      - Speed
      - Time Left
      - Date Added
  • No categories (as requested).
  • Double-click or start/resume triggers a "download details" window.
"""

import os
import re
import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem, QProgressBar, QVBoxLayout,
    QWidget, QAction, QToolBar, QMenu, QMessageBox, QFileDialog, QDialog,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QDateTimeEdit
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from download_manager import DownloadManager, DownloadTask
from download_details_window import DownloadDetailsWindow
from settings import SettingsManager
from logger import Logger

class IDMMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDM Clone - Professional Edition")
        self.resize(900, 550)

        # Instantiate settings, logger, and download manager
        self.settings = SettingsManager()
        self.logger = Logger()
        self.download_manager = DownloadManager(self.logger, self.settings)

        # Keep references to any open "details" windows so they remain open
        self.details_windows = {}

        # Setup UI
        self.init_ui()
        self.setup_timers()

    def init_ui(self):
        # Central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Create menubar, toolbar
        self.create_menu_bar()
        self.create_toolbar()

        # Create table for downloads
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "File Name", "Size", "Status", "Progress", "Speed", "Time Left", "Date Added"
        ])
        # Double-click to open details window
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

        view_menu = menubar.addMenu("View")
        # Could add UI toggles here if needed

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
        # Timer to update table every second
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_table)
        self.update_timer.start(1000)

        # Timer to check scheduled downloads
        self.schedule_timer = QTimer(self)
        self.schedule_timer.timeout.connect(self.download_manager.check_scheduled_downloads)
        self.schedule_timer.start(1000)

        # (Optional) Timer for clipboard integration if you want
        # (Not strictly required based on your request)

    def refresh_table(self):
        tasks = self.download_manager.get_all_tasks()
        self.table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(task.file_name))
            if task.file_size > 0:
                size_str = self.human_readable_size(task.file_size)
            else:
                size_str = "N/A"
            self.table.setItem(row, 1, QTableWidgetItem(size_str))

            self.table.setItem(row, 2, QTableWidgetItem(task.status))

            # Progress
            progress_item = QTableWidgetItem(f"{task.progress}%")
            progress_bar = QProgressBar()
            progress_bar.setValue(task.progress)
            self.table.setCellWidget(row, 3, progress_bar)
            self.table.setItem(row, 3, progress_item)  # invisible item behind progress bar

            # Speed
            speed_str = f"{task.speed:.1f} KB/s" if task.speed > 0 else "0 KB/s"
            self.table.setItem(row, 4, QTableWidgetItem(speed_str))

            # Time Left
            self.table.setItem(row, 5, QTableWidgetItem(task.eta))

            # Date Added
            self.table.setItem(row, 6, QTableWidgetItem(task.date_added.strftime("%b %d, %Y %H:%M:%S")))

    def add_url_dialog(self):
        dialog = AddUrlDialog(self.settings.default_download_dir)
        if dialog.exec_() == QDialog.Accepted:
            info = dialog.get_info()
            self.download_manager.add_download(**info)
            # If user wants the "details" window to appear immediately:
            # find the newly added task and open details
            last_task = self.download_manager.last_task()
            if last_task:
                self.open_details_window(last_task)

    def resume_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        task = self.download_manager.get_all_tasks()[row]
        self.download_manager.resume_task(task)
        # Open the details window if not already open
        self.open_details_window(task)

    def stop_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        task = self.download_manager.get_all_tasks()[row]
        self.download_manager.stop_task(task)

    def stop_all(self):
        self.download_manager.stop_all()

    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        task = self.download_manager.get_all_tasks()[row]
        confirm = QMessageBox.question(self, "Confirm Delete",
                                       "Are you sure you want to remove this download from the list?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.download_manager.remove_task(task)

    def set_default_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Download Directory")
        if folder:
            self.settings.default_download_dir = folder
            self.settings.save()

    def about_dialog(self):
        QMessageBox.information(self, "About IDM Clone",
                                "IDM Clone - Professional Edition\n"
                                "Developed in Python with PyQt5.\n"
                                "Provides multi-threaded, dynamic segmentation downloads.\n"
                                "Not affiliated with the official IDM product.")

    def on_table_double_click(self, row, column):
        if row < 0:
            return
        task = self.download_manager.get_all_tasks()[row]
        self.open_details_window(task)

    def open_details_window(self, task):
        # If there's already a details window for this task, bring it to front
        if task in self.details_windows:
            self.details_windows[task].raise_()
            self.details_windows[task].activateWindow()
            return

        # Otherwise create a new one
        details_win = DownloadDetailsWindow(task, self.download_manager)
        details_win.show()
        details_win.destroyed.connect(lambda: self.cleanup_details_window(task))
        self.details_windows[task] = details_win

    def cleanup_details_window(self, task):
        if task in self.details_windows:
            del self.details_windows[task]

    def human_readable_size(self, size):
        # Convert bytes to a human-readable format
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"


class AddUrlDialog(QDialog):
    def __init__(self, default_folder):
        super().__init__()
        self.setWindowTitle("Add URL")
        self.default_folder = default_folder
        self.init_ui()

    def init_ui(self):
        self.resize(400, 200)
        layout = QVBoxLayout(self)

        # URL
        url_label = QLabel("URL:")
        self.url_edit = QLineEdit()
        layout.addWidget(url_label)
        layout.addWidget(self.url_edit)

        # Destination folder
        folder_label = QLabel("Destination Folder:")
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit(self.default_folder)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(browse_btn)
        layout.addWidget(folder_label)
        layout.addLayout(folder_layout)

        # File name
        file_label = QLabel("Custom File Name (optional):")
        self.file_edit = QLineEdit()
        layout.addWidget(file_label)
        layout.addWidget(self.file_edit)

        # Segments
        seg_label = QLabel("Number of Segments:")
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(1, 32)
        self.segments_spin.setValue(4)
        layout.addWidget(seg_label)
        layout.addWidget(self.segments_spin)

        # Schedule time
        schedule_label = QLabel("Schedule Download (optional):")
        self.schedule_edit = QDateTimeEdit()
        self.schedule_edit.setCalendarPopup(True)
        self.schedule_edit.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(schedule_label)
        layout.addWidget(self.schedule_edit)

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
            "schedule_time": schedule_dt
        }
