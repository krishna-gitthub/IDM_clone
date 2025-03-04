"""
segment.py – Represents a single segment in a segmented download.
Handles the actual HTTP range request, writing to a temporary file,
and reporting downloaded bytes back to the DownloadTask.
"""

import os
import requests
import time

class Segment:
    def __init__(self, url, dest_folder, file_name, start, end, logger, settings):
        self.url = url
        self.dest_folder = dest_folder
        self.file_name = file_name
        self.start = start
        self.end = end  # Can be None for unknown length.
        self.logger = logger
        self.settings = settings

        self.downloaded = 0
        self.is_finished = False
        self.is_stopped = False

        seg_id = f"{start or 0}-{end or 'end'}"
        self.temp_path = os.path.join(dest_folder, f"{file_name}.part_{seg_id}")

    def download(self, stop_event, pause_event):
        if self.is_finished or self.is_stopped:
            return

        headers = {}
        if self.settings.user_agent:
            headers["User-Agent"] = self.settings.user_agent
        if self.start is not None and self.end is not None:
            downloaded_so_far = 0
            if os.path.exists(self.temp_path):
                downloaded_so_far = os.path.getsize(self.temp_path)
            actual_start = self.start + downloaded_so_far
            headers["Range"] = f"bytes={actual_start}-{self.end}"

        try:
            with requests.get(self.url, headers=headers, stream=True, timeout=10) as r:
                r.raise_for_status()
                mode = "ab" if os.path.exists(self.temp_path) else "wb"
                with open(self.temp_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=65536):  # 64 KB chunks
                        if stop_event.is_set():
                            self.is_stopped = True
                            break
                        while not pause_event.is_set() and not stop_event.is_set():
                            time.sleep(0.1)
                        if stop_event.is_set():
                            self.is_stopped = True
                            break
                        if chunk:
                            f.write(chunk)
                            self.downloaded += len(chunk)
            if not self.is_stopped:
                if self.end is not None:
                    total_length = (self.end - self.start) + 1
                    if self.downloaded >= total_length:
                        self.is_finished = True
                else:
                    self.is_finished = True
        except Exception as e:
            self.logger.log(f"Segment download error [{self.temp_path}]: {e}")
            self.is_stopped = True

    @property
    def remaining(self):
        if self.end is None or self.is_finished:
            return 0
        total_length = (self.end - self.start) + 1
        return max(0, total_length - self.downloaded)
