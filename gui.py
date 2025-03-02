"""
gui.py – Contains the graphical user interface for the IDM clone.
This module builds a main window that mimics IDM’s layout,
including a menu bar, toolbar, download task table, dialogs, and clipboard monitoring.
"""

import re
import os
from PyQt5.QtWidgets import (QMainWindow, QTableWidget, QTableWidgetItem, QProgressBar,
                             QVBoxLayout, QWidget, QAction, QToolBar, QMenu, QDialog, QLabel,
                             QLineEdit, QPushButton, QFileDialog, QSpinBox, QDateTimeEdit,
                             QHBoxLayout, QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from download_manager import DownloadManager
from settings import SettingsManager
from logger import Logger

class IDMMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDM Clone")
        self.resize(800, 600)
        # Load settings and initialize logger
        self.settings = SettingsManager()
        self.logger = Logger()
        # Create download manager and pass settings & logger
        self.download_manager = DownloadManager(self.logger, self.settings)
        self.init_ui()
        self.setup_timers()

    def init_ui(self):
        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create toolbar and menu bar
        self.create_toolbar()
        self.create_menu_bar()
        
        # Create table for download tasks with 6 columns:
        # File Name, File Size, Progress, Speed, ETA, and Status.
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["File Name", "File Size", "Progress", "Speed", "ETA", "Status"])
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.table)
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        add_action = QAction("Add New Download", self)
        add_action.triggered.connect(self.open_add_dialog)
        file_menu.addAction(add_action)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        file_menu.addAction(settings_action)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        add_action = QAction("Add", self)
        add_action.triggered.connect(self.open_add_dialog)
        toolbar.addAction(add_action)
        
        pause_action = QAction("Pause All", self)
        pause_action.triggered.connect(self.pause_all_downloads)
        toolbar.addAction(pause_action)
        
        resume_action = QAction("Resume All", self)
        resume_action.triggered.connect(self.resume_all_downloads)
        toolbar.addAction(resume_action)
        
    def setup_timers(self):
        # Timer to update download table every second.
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_table)
        self.update_timer.start(1000)
        
        # Timer for clipboard monitoring (every 2 seconds)
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(2000)
        
        # Timer to check for scheduled downloads
        self.schedule_timer = QTimer(self)
        self.schedule_timer.timeout.connect(self.download_manager.check_scheduled_downloads)
        self.schedule_timer.start(1000)
        
    def refresh_table(self):
        tasks = self.download_manager.get_tasks()
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(task.file_name))
            self.table.setItem(row, 1, QTableWidgetItem(self.human_readable_size(task.file_size)))
            # Add a progress bar widget to display progress.
            progress_bar = QProgressBar()
            progress_bar.setValue(task.progress)
            self.table.setCellWidget(row, 2, progress_bar)
            self.table.setItem(row, 3, QTableWidgetItem(f"{task.speed} KB/s"))
            self.table.setItem(row, 4, QTableWidgetItem(task.eta))
            self.table.setItem(row, 5, QTableWidgetItem(task.status))
            
    def human_readable_size(self, size):
        # Convert bytes to a human-readable format.
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
        
    def show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if index.isValid():
            row = index.row()
            task = self.download_manager.get_tasks()[row]
            menu = QMenu(self)
            if task.status == "Downloading":
                pause_action = QAction("Pause", self)
                pause_action.triggered.connect(lambda: self.pause_download(task))
                menu.addAction(pause_action)
            elif task.status == "Paused":
                resume_action = QAction("Resume", self)
                resume_action.triggered.connect(lambda: self.resume_download(task))
                menu.addAction(resume_action)
            cancel_action = QAction("Cancel", self)
            cancel_action.triggered.connect(lambda: self.cancel_download(task))
            menu.addAction(cancel_action)
            menu.exec_(self.table.viewport().mapToGlobal(pos))
            
    def pause_download(self, task):
        self.download_manager.pause_task(task)
        
    def resume_download(self, task):
        self.download_manager.resume_task(task)
        
    def cancel_download(self, task):
        self.download_manager.cancel_task(task)
        
    def pause_all_downloads(self):
        self.download_manager.pause_all()
        
    def resume_all_downloads(self):
        self.download_manager.resume_all()
        
    def open_add_dialog(self):
        dialog = AddDownloadDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            download_info = dialog.get_info()
            self.download_manager.add_download(**download_info)
        
    def open_settings_dialog(self):
        dialog = SettingsDialog(self, self.settings)
        dialog.exec_()
        
    def check_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if self.is_valid_url(text):
            # Prompt the user if a download URL is detected in the clipboard.
            reply = QMessageBox.question(self, "Download URL Detected",
                                         f"Detected URL in clipboard:\n{text}\nDo you want to download it?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                dialog = AddDownloadDialog(self, prefill_url=text)
                if dialog.exec_() == QDialog.Accepted:
                    download_info = dialog.get_info()
                    self.download_manager.add_download(**download_info)
                clipboard.clear()  # Clear the clipboard to avoid repeated prompts.
                
    def is_valid_url(self, text):
        # A basic check for a valid URL (HTTP, HTTPS, or FTP).
        pattern = re.compile(r'^(https?|ftp)://')
        return bool(pattern.match(text))

class AddDownloadDialog(QDialog):
    def __init__(self, parent=None, prefill_url=""):
        super().__init__(parent)
        self.setWindowTitle("Add New Download")
        self.setModal(True)
        self.init_ui(prefill_url)
        
    def init_ui(self, prefill_url):
        layout = QVBoxLayout(self)
        
        # Download URL
        self.url_label = QLabel("Download URL:")
        self.url_input = QLineEdit()
        self.url_input.setText(prefill_url)
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_input)
        
        # Destination folder
        self.dest_label = QLabel("Destination Folder:")
        dest_layout = QHBoxLayout()
        self.dest_input = QLineEdit()
        self.dest_button = QPushButton("Browse")
        self.dest_button.clicked.connect(self.browse_folder)
        dest_layout.addWidget(self.dest_input)
        dest_layout.addWidget(self.dest_button)
        layout.addWidget(self.dest_label)
        layout.addLayout(dest_layout)
        
        # Custom file name
        self.name_label = QLabel("Custom File Name (optional):")
        self.name_input = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        
        # Number of segments/threads
        self.segments_label = QLabel("Number of Segments/Threads:")
        self.segments_input = QSpinBox()
        self.segments_input.setMinimum(1)
        self.segments_input.setMaximum(16)
        self.segments_input.setValue(4)
        layout.addWidget(self.segments_label)
        layout.addWidget(self.segments_input)
        
        # Schedule download (optional)
        self.schedule_label = QLabel("Schedule Download (optional):")
        self.schedule_input = QDateTimeEdit()
        self.schedule_input.setCalendarPopup(True)
        self.schedule_input.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(self.schedule_label)
        layout.addWidget(self.schedule_input)
        
        # OK and Cancel buttons
        btn_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_button)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout)
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.dest_input.setText(folder)
            
    def get_info(self):
        return {
            "url": self.url_input.text(),
            "dest_folder": self.dest_input.text() if self.dest_input.text() else self.parent().settings.default_download_dir,
            "file_name": self.name_input.text(),
            "segments": self.segments_input.value(),
            "schedule_time": self.schedule_input.dateTime().toPyDateTime() if self.schedule_input.dateTime() > QDateTime.currentDateTime() else None
        }

class SettingsDialog(QDialog):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.settings = settings
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Default download directory
        self.dir_label = QLabel("Default Download Directory:")
        self.dir_input = QLineEdit(self.settings.default_download_dir)
        self.dir_button = QPushButton("Browse")
        self.dir_button.clicked.connect(self.browse_folder)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_button)
        layout.addWidget(self.dir_label)
        layout.addLayout(dir_layout)
        
        # Maximum concurrent downloads
        self.concurrent_label = QLabel("Max Concurrent Downloads:")
        self.concurrent_input = QSpinBox()
        self.concurrent_input.setMinimum(1)
        self.concurrent_input.setMaximum(10)
        self.concurrent_input.setValue(self.settings.max_concurrent_downloads)
        layout.addWidget(self.concurrent_label)
        layout.addWidget(self.concurrent_input)
        
        # Proxy settings (optional)
        self.proxy_label = QLabel("Proxy Settings (optional, format: host:port):")
        self.proxy_input = QLineEdit(self.settings.proxy)
        layout.addWidget(self.proxy_label)
        layout.addWidget(self.proxy_input)
        
        # User-Agent string
        self.ua_label = QLabel("User-Agent String:")
        self.ua_input = QLineEdit(self.settings.user_agent)
        layout.addWidget(self.ua_label)
        layout.addWidget(self.ua_input)
        
        # Speed limit (KB/s)
        self.speed_label = QLabel("Speed Limit (KB/s, 0 for unlimited):")
        self.speed_input = QSpinBox()
        self.speed_input.setMinimum(0)
        self.speed_input.setMaximum(10000)
        self.speed_input.setValue(self.settings.speed_limit)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.speed_input)
        
        # OK and Cancel buttons
        btn_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.save_settings)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_button)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout)
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Download Directory")
        if folder:
            self.dir_input.setText(folder)
            
    def save_settings(self):
        self.settings.default_download_dir = self.dir_input.text()
        self.settings.max_concurrent_downloads = self.concurrent_input.value()
        self.settings.proxy = self.proxy_input.text()
        self.settings.user_agent = self.ua_input.text()
        self.settings.speed_limit = self.speed_input.value()
        self.settings.save()  # Save settings persistently
        self.accept()
