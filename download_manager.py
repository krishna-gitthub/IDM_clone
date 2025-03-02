"""
download_manager.py – Contains the core download functionality.
It implements multi-threaded segmented downloads for HTTP/FTP as well as video downloads via yt-dlp,
along with scheduling and queue management.
"""

import os
import threading
import time
import requests
from datetime import datetime

from logger import Logger

# Standard direct download task using segmented download.
class DownloadTask:
    def __init__(self, url, dest_folder, file_name, segments, schedule_time, settings, logger):
        self.url = url
        self.dest_folder = dest_folder
        # If no custom file name is provided, use the last part of the URL.
        self.file_name = file_name if file_name else url.split("/")[-1]
        self.segments = segments
        self.schedule_time = schedule_time  # None or a datetime object
        self.settings = settings
        self.logger = logger
        
        self.file_size = 0
        self.progress = 0         # In percentage (0–100)
        self.speed = 0            # In KB/s
        self.eta = "N/A"          # Estimated time remaining as string
        self.status = "Queued"
        
        self.threads = []
        self.pause_event = threading.Event()
        self.pause_event.set()    # Not paused by default
        self.cancelled = False
        self.downloaded_bytes = 0
        self.lock = threading.Lock()
        
    def start(self):
        self.status = "Downloading"
        # Retrieve file size using a HEAD request.
        try:
            headers = {}
            if self.settings.user_agent:
                headers["User-Agent"] = self.settings.user_agent
            response = requests.head(self.url, headers=headers, allow_redirects=True)
            if "Content-Length" in response.headers:
                self.file_size = int(response.headers["Content-Length"])
            else:
                self.file_size = 0
        except Exception as e:
            self.logger.log(f"Error getting file size for {self.url}: {e}")
            self.status = "Error"
            return
        
        # Compute byte ranges for each segment.
        part_size = self.file_size // self.segments if self.file_size else None
        
        self.start_time = time.time()
        # Spawn threads to download each segment.
        for i in range(self.segments):
            start_byte = i * part_size if part_size is not None else None
            if i == self.segments - 1 and self.file_size:
                end_byte = self.file_size - 1
            elif self.file_size:
                end_byte = (i + 1) * part_size - 1
            else:
                end_byte = None
            t = threading.Thread(target=self.download_segment, args=(i, start_byte, end_byte))
            t.start()
            self.threads.append(t)
            
        # Monitor and update progress.
        monitor_thread = threading.Thread(target=self.monitor_progress)
        monitor_thread.start()
        
    def download_segment(self, segment_index, start_byte, end_byte):
        headers = {}
        if self.settings.user_agent:
            headers["User-Agent"] = self.settings.user_agent
        if start_byte is not None and end_byte is not None:
            headers["Range"] = f"bytes={start_byte}-{end_byte}"
        local_filename = os.path.join(self.dest_folder, f"{self.file_name}.part{segment_index}")
        
        # Enable resumable downloads if a part file already exists.
        mode = "ab" if os.path.exists(local_filename) else "wb"
        downloaded = os.path.getsize(local_filename) if os.path.exists(local_filename) else 0
        if start_byte is not None:
            headers["Range"] = f"bytes={start_byte+downloaded}-{end_byte}"
        
        try:
            with requests.get(self.url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(local_filename, mode) as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        # Respect pause/resume.
                        while not self.pause_event.is_set():
                            time.sleep(0.1)
                        if self.cancelled:
                            return
                        if chunk:
                            f.write(chunk)
                            with self.lock:
                                self.downloaded_bytes += len(chunk)
            self.logger.log(f"Segment {segment_index} completed for {self.file_name}")
        except Exception as e:
            self.logger.log(f"Error in segment {segment_index} for {self.file_name}: {e}")
            self.status = "Error"
            
    def monitor_progress(self):
        # Wait for all segments to finish.
        for t in self.threads:
            t.join()
        if self.cancelled:
            self.status = "Cancelled"
            return
        # Merge downloaded segments.
        self.merge_parts()
        self.status = "Completed"
        self.progress = 100
        self.logger.log(f"Download completed: {self.file_name}")
        
    def merge_parts(self):
        final_path = os.path.join(self.dest_folder, self.file_name)
        with open(final_path, "wb") as outfile:
            for i in range(self.segments):
                part_file = os.path.join(self.dest_folder, f"{self.file_name}.part{i}")
                if os.path.exists(part_file):
                    with open(part_file, "rb") as infile:
                        outfile.write(infile.read())
                    os.remove(part_file)
                    
    def update_progress(self):
        if self.file_size:
            self.progress = int((self.downloaded_bytes / self.file_size) * 100)
        else:
            self.progress = 0
        elapsed = time.time() - self.start_time
        self.speed = int(self.downloaded_bytes / 1024 / elapsed) if elapsed > 0 else 0
        if self.speed > 0 and self.file_size:
            remaining = self.file_size - self.downloaded_bytes
            eta_seconds = remaining / (self.speed * 1024)
            self.eta = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))
        else:
            self.eta = "N/A"
            
    def pause(self):
        if self.status == "Downloading":
            self.pause_event.clear()
            self.status = "Paused"
            self.logger.log(f"Download paused: {self.file_name}")
            
    def resume(self):
        if self.status == "Paused":
            self.pause_event.set()
            self.status = "Downloading"
            self.logger.log(f"Download resumed: {self.file_name}")
            
    def cancel(self):
        self.cancelled = True
        self.pause_event.set()
        self.logger.log(f"Download cancelled: {self.file_name}")

# DownloadManager: Chooses between direct file download and video download (via yt-dlp)
class DownloadManager:
    def __init__(self, logger, settings):
        self.tasks = []
        self.logger = logger
        self.settings = settings
        self.lock = threading.Lock()
        
    def add_download(self, url, dest_folder, file_name, segments, schedule_time):
        # Determine if the URL is from a video site.
        if any(domain in url.lower() for domain in ["youtube", "youtu.be", "vimeo", "dailymotion"]):
            # Use the video downloader via yt-dlp.
            from video_downloader import VideoDownloadTask
            task = VideoDownloadTask(url, dest_folder, file_name, schedule_time, settings=self.settings, logger=self.logger)
        else:
            task = DownloadTask(url, dest_folder, file_name, segments, schedule_time, settings=self.settings, logger=self.logger)
        with self.lock:
            self.tasks.append(task)
        if schedule_time and schedule_time > datetime.now():
            task.status = "Scheduled"
            self.logger.log(f"Download scheduled for {task.file_name} at {schedule_time}")
        else:
            threading.Thread(target=task.start).start()
        return task
        
    def get_tasks(self):
        # Update progress for tasks that are active.
        for task in self.tasks:
            if hasattr(task, "update_progress") and task.status in ["Downloading", "Paused"]:
                task.update_progress()
        return self.tasks
        
    def pause_task(self, task):
        if hasattr(task, "pause"):
            task.pause()
        
    def resume_task(self, task):
        if hasattr(task, "resume"):
            task.resume()
        
    def cancel_task(self, task):
        if hasattr(task, "cancel"):
            task.cancel()
        
    def pause_all(self):
        for task in self.tasks:
            if hasattr(task, "pause") and task.status == "Downloading":
                task.pause()
                
    def resume_all(self):
        for task in self.tasks:
            if hasattr(task, "resume") and task.status == "Paused":
                task.resume()
                
    def check_scheduled_downloads(self):
        now = datetime.now()
        for task in self.tasks:
            if task.status == "Scheduled" and task.schedule_time <= now:
                threading.Thread(target=task.start).start()
                task.status = "Downloading"
