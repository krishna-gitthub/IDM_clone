"""
download_manager.py – Manages the list of downloads, scheduling, dynamic segmentation, etc.
Now includes logic to detect YouTube/streaming sites and use VideoDownloadTask (yt-dlp).
"""

import os
import threading
import datetime

from segment import Segment
from settings import SettingsManager
from logger import Logger

# Import your VideoDownloadTask
# Make sure video_downloader.py is in the same folder and has the VideoDownloadTask class.
from video_downloader import VideoDownloadTask

class DownloadTask:
    """
    Represents a single download with dynamic segmentation (for regular HTTP/FTP).
    """
    def __init__(self, url, dest_folder, file_name, segments, schedule_time, logger, settings):
        self.url = url
        self.dest_folder = dest_folder
        self.file_name = file_name if file_name else os.path.basename(url)
        self.segments = segments
        self.schedule_time = schedule_time
        self.logger = logger
        self.settings = settings

        # For UI
        self.file_size = 0
        self.progress = 0
        self.speed = 0
        self.eta = "N/A"
        self.status = "Queued"
        self.date_added = datetime.datetime.now()

        # Threading events/locks
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially
        self._lock = threading.Lock()

        # Segments
        self._segments = []
        self._total_downloaded = 0
        self._start_time = None

    def start_download(self):
        # Only start if we're Queued, Paused, or Error (allowing re-try)
        if self.status not in ["Queued", "Paused", "Error"]:
            return
        self.status = "Downloading"
        self._stop_event.clear()
        self._pause_event.set()

        self.logger.log(f"Starting download (segmented): {self.file_name}")
        self._fetch_file_size()

        self._start_time = datetime.datetime.now()

        # Create initial segments
        self._create_segments()

        # Monitor thread
        monitor_thread = threading.Thread(target=self._monitor_progress, daemon=True)
        monitor_thread.start()

        # Start each segment
        for seg in self._segments:
            t = threading.Thread(target=self._download_segment, args=(seg,), daemon=True)
            t.start()

    def _fetch_file_size(self):
        import requests
        try:
            headers = {}
            if self.settings.user_agent:
                headers["User-Agent"] = self.settings.user_agent
            r = requests.head(self.url, headers=headers, allow_redirects=True, timeout=10)
            cl = r.headers.get("Content-Length")
            if cl:
                self.file_size = int(cl)
        except Exception as e:
            self.logger.log(f"Error fetching file size for {self.url}: {e}")

    def _create_segments(self):
        """Create initial segments based on file_size."""
        if self.file_size > 0:
            part_size = self.file_size // self.segments
            for i in range(self.segments):
                start = i * part_size
                end = ((i + 1) * part_size) - 1
                if i == self.segments - 1:
                    end = self.file_size - 1
                seg = Segment(self.url, self.dest_folder, self.file_name, start, end, self.logger, self.settings)
                self._segments.append(seg)
        else:
            # Unknown size => single open-ended segment
            seg = Segment(self.url, self.dest_folder, self.file_name, 0, None, self.logger, self.settings)
            self._segments.append(seg)

    def _download_segment(self, seg: Segment):
        seg.download(self._stop_event, self._pause_event)

    def _monitor_progress(self):
        import time
        self._speed_samples = []
        last_total = self._total_downloaded
        while not self._stop_event.is_set():
            with self._lock:
                current_total = self._total_downloaded
            delta = current_total - last_total
            speed_sample = delta / 1024.0  # KB/s for the last second
            self._speed_samples.append(speed_sample)
            if len(self._speed_samples) > 5:
                self._speed_samples.pop(0)
            avg_speed = sum(self._speed_samples) / len(self._speed_samples)
            self.speed = avg_speed
            last_total = current_total

            elapsed = (datetime.datetime.now() - self._start_time).total_seconds()
            if self.file_size > 0:
                self.progress = int((self._total_downloaded / self.file_size) * 100)
                remaining = self.file_size - self._total_downloaded
                if self.speed > 0:
                    eta_sec = remaining / (self.speed * 1024)
                    self.eta = time.strftime("%H:%M:%S", time.gmtime(eta_sec))
                else:
                    self.eta = "N/A"
            else:
                self.progress = 0
                self.eta = "N/A"

            if all(s.is_finished for s in self._segments):
                self._merge_segments()
                if not self._stop_event.is_set():
                    self.status = "Completed"
                break

            self._attempt_dynamic_segmentation()
            time.sleep(1)


    def _attempt_dynamic_segmentation(self):
        """If a segment finished, find the largest active segment and split it."""
        if self.file_size == 0:
            return  # can't re-split effectively if unknown

        finished_segments = [s for s in self._segments if s.is_finished]
        if not finished_segments:
            return
        active_segments = [s for s in self._segments if not s.is_finished and not s.is_stopped]
        if not active_segments:
            return

        largest_seg = max(active_segments, key=lambda x: x.remaining)
        if largest_seg.remaining > 1024 * 1024:  # at least 1 MB
            midpoint = largest_seg.start + (largest_seg.remaining // 2)
            new_seg_start = midpoint + 1
            new_seg_end = largest_seg.end

            largest_seg.end = midpoint

            new_seg = Segment(self.url, self.dest_folder, self.file_name,
                              new_seg_start, new_seg_end, self.logger, self.settings)
            self._segments.append(new_seg)
            t = threading.Thread(target=self._download_segment, args=(new_seg,), daemon=True)
            t.start()

    def _merge_segments(self):
        final_path = os.path.join(self.dest_folder, self.file_name)
        try:
            with open(final_path, "wb") as out:
                for seg in sorted(self._segments, key=lambda x: x.start if x.start else 0):
                    seg_path = seg.temp_path
                    if os.path.exists(seg_path):
                        with open(seg_path, "rb") as f:
                            out.write(f.read())
                        os.remove(seg_path)
            self.logger.log(f"Download completed and merged: {self.file_name}")
        except Exception as e:
            self.logger.log(f"Error merging segments for {self.file_name}: {e}")
            self.status = "Error"

    def pause(self):
        if self.status == "Downloading":
            self._pause_event.clear()
            self.status = "Paused"
            self.logger.log(f"Paused: {self.file_name}")

    def resume(self):
        if self.status == "Paused":
            self._pause_event.set()
            self.status = "Downloading"
            self.logger.log(f"Resumed: {self.file_name}")

    def stop(self, pause_only=False):
        self._stop_event.set()
        if pause_only:
            self._pause_event.clear()
            self.status = "Paused"
        else:
            self.status = "Cancelled"
            self.logger.log(f"Stopped: {self.file_name}")


class DownloadManager:
    """
    Manages multiple downloads, scheduling, stopping, removing, etc.
    Now also checks if the URL is from a streaming site (YouTube, Vimeo, etc.)
    and uses VideoDownloadTask from video_downloader.py if so.
    """
    def __init__(self, logger: Logger, settings: SettingsManager):
        self.logger = logger
        self.settings = settings
        self.tasks = []
        self._lock = threading.Lock()

    def add_download(self, url, dest_folder, file_name, segments, schedule_time, resolution="Best"):
        if not dest_folder:
            dest_folder = self.settings.default_download_dir
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder, exist_ok=True)

        # Check if it's a known video/streaming site.
        if any(domain in url.lower() for domain in ["youtube", "youtu.be", "vimeo", "dailymotion"]):
            from video_downloader import VideoDownloadTask
            task = VideoDownloadTask(
                url=url,
                dest_folder=dest_folder,
                file_name=file_name,
                schedule_time=schedule_time,
                settings=self.settings,
                logger=self.logger,
                resolution=resolution
            )
            self.logger.log(f"Detected streaming/video site. Using VideoDownloadTask for {file_name or url}")
        else:
            task = DownloadTask(url, dest_folder, file_name, segments, schedule_time, self.logger, self.settings)

        with self._lock:
            self.tasks.append(task)

        now = datetime.datetime.now()
        if schedule_time and schedule_time > now:
            task.status = "Scheduled"
            self.logger.log(f"Download scheduled for {task.file_name} at {schedule_time}")
        else:
            import threading
            threading.Thread(target=task.start_download, daemon=True).start()

        return task


    def last_task(self):
        with self._lock:
            return self.tasks[-1] if self.tasks else None

    def get_all_tasks(self):
        with self._lock:
            return list(self.tasks)

    def remove_task(self, task):
        task.stop()
        with self._lock:
            if task in self.tasks:
                self.tasks.remove(task)

    def resume_task(self, task):
        """
        For a paused segmented task, we can resume in place.
        For a video task, we typically rely on yt-dlp's logic, which doesn't do partial segment resume the same way.
        """
        if task.status == "Paused":
            # If it's a segmented DownloadTask
            if isinstance(task, DownloadTask):
                # We can re-start the same task logic
                threading.Thread(target=task.start_download, daemon=True).start()
            else:
                # If it's a VideoDownloadTask, there's limited 'resume' support
                task.resume()
        elif task.status in ["Cancelled", "Completed", "Error"]:
            # Possibly re-download from scratch or ignore
            pass
        else:
            # If it's "Downloading" or "Queued"
            if hasattr(task, "resume"):
                task.resume()

    def stop_task(self, task, pause_only=False):
        task.stop(pause_only=pause_only)

    def stop_all(self):
        for task in self.get_all_tasks():
            if task.status in ["Downloading", "Paused", "Queued", "Scheduled"]:
                task.stop()

    def check_scheduled_downloads(self):
        now = datetime.datetime.now()
        for task in self.get_all_tasks():
            if task.status == "Scheduled" and task.schedule_time and task.schedule_time <= now:
                self.logger.log(f"Scheduled download starting: {task.file_name}")
                threading.Thread(target=task.start_download, daemon=True).start()
