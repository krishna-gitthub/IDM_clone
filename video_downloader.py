"""
video_downloader.py – Implements video downloading using yt-dlp.
This class wraps yt-dlp to download videos from sites like YouTube, Vimeo, etc.,
and integrates with the IDM clone UI by updating progress and status.
"""

import os
import time
from datetime import datetime
import yt_dlp

class VideoDownloadTask:
    def __init__(self, url, dest_folder, file_name, schedule_time, settings, logger):
        self.url = url
        self.dest_folder = dest_folder
        # If a custom file name is provided, use it; otherwise let yt-dlp decide.
        self.file_name = file_name if file_name else ""
        self.schedule_time = schedule_time
        self.settings = settings
        self.logger = logger
        
        # Attributes for UI updates.
        self.file_size = 0  # Not available until download starts.
        self.progress = 0   # Percentage (0-100)
        self.speed = 0      # Not available
        self.eta = "N/A"
        self.status = "Queued"
        
        # Configure output template.
        if self.file_name:
            outtmpl = os.path.join(self.dest_folder, self.file_name + ".%(ext)s")
        else:
            outtmpl = os.path.join(self.dest_folder, '%(title)s.%(ext)s')
            
        self.ydl_opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
        }
        # Optionally set user-agent if provided.
        if self.settings.user_agent:
            self.ydl_opts['http_headers'] = {'User-Agent': self.settings.user_agent}
            
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            self.status = "Downloading"
            if d.get('total_bytes'):
                total = d.get('total_bytes')
                downloaded = d.get('downloaded_bytes', 0)
                self.progress = int(downloaded / total * 100)
                self.file_size = total
            elif d.get('total_bytes_estimate'):
                total = d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                self.progress = int(downloaded / total * 100)
                self.file_size = total
            else:
                self.progress = 0
        elif d['status'] == 'finished':
            self.progress = 100
            self.status = "Completed"
            self.logger.log(f"Video download completed: {self.file_name or self.url}")
            
    def start(self):
        self.status = "Downloading"
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                ydl.download([self.url])
            except Exception as e:
                self.logger.log(f"Error downloading video from {self.url}: {e}")
                self.status = "Error"
