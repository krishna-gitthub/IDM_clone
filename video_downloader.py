"""
video_downloader.py – Implements video downloading using yt-dlp.
This class wraps yt-dlp to download videos from sites like YouTube, Vimeo, etc.,
and integrates with the IDM clone UI by updating progress, speed, ETA, and status.
"""

import os
import time
import datetime
import yt_dlp

class VideoDownloadTask:
    def __init__(self, url, dest_folder, file_name, schedule_time, settings, logger, resolution="Best"):
        self.url = url
        self.dest_folder = dest_folder
        # Use custom file name if provided; otherwise, let yt-dlp decide.
        self.file_name = file_name if file_name else ""
        self.schedule_time = schedule_time
        self.settings = settings
        self.logger = logger
        self.resolution = resolution  # Desired resolution (e.g. "1080p", "720p", "Best")
        
        # UI properties expected by the main window
        self.date_added = datetime.datetime.now()
        self.status = "Queued"
        self.progress = 0
        self.file_size = 0
        self.speed = 0
        self.eta = "N/A"

    def start(self):
        self.status = "Downloading"
        # Configure output template.
        if self.file_name:
            outtmpl = os.path.join(self.dest_folder, self.file_name + ".%(ext)s")
        else:
            outtmpl = os.path.join(self.dest_folder, '%(title)s.%(ext)s')
            
        ydl_opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
        }
        # If resolution is not "Best", set format filter.
        if self.resolution.lower() != "best":
            try:
                height = int(self.resolution.lower().replace("p", ""))
                ydl_opts['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
            except Exception as e:
                self.logger.log(f"Error setting resolution: {e}")
        # Set custom user-agent if provided.
        if self.settings.user_agent:
            ydl_opts['http_headers'] = {'User-Agent': self.settings.user_agent}
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([self.url])
            except Exception as e:
                self.logger.log(f"Error downloading video from {self.url}: {e}")
                self.status = "Error"

    def start_download(self):
        # Alias so that DownloadManager can call start_download() on any task.
        self.start()

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
            if d.get('speed'):
                self.speed = d.get('speed') / 1024.0
            else:
                self.speed = 0
            if d.get('eta'):
                self.eta = time.strftime("%H:%M:%S", time.gmtime(d.get('eta')))
            else:
                self.eta = "N/A"
        elif d['status'] == 'finished':
            self.progress = 100
            self.status = "Completed"
            self.eta = "00:00:00"
            self.logger.log(f"Video download completed: {self.file_name or self.url}")
