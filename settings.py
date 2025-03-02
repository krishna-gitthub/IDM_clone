"""
settings.py – Implements the SettingsManager class.
It maintains user preferences such as default download directory,
maximum concurrent downloads, proxy settings, user-agent string, and speed limit.
Settings are loaded from and saved to a JSON file.
"""

import json
import os

class SettingsManager:
    def __init__(self):
        # Default settings
        self.default_download_dir = os.path.expanduser("~/Downloads")
        self.max_concurrent_downloads = 3
        self.proxy = ""
        self.user_agent = "IDMClone/1.0"
        self.speed_limit = 0  # 0 means unlimited
        
        self.settings_file = "idm_settings.json"
        self.load()
        
    def load(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self.default_download_dir = data.get("default_download_dir", self.default_download_dir)
                    self.max_concurrent_downloads = data.get("max_concurrent_downloads", self.max_concurrent_downloads)
                    self.proxy = data.get("proxy", self.proxy)
                    self.user_agent = data.get("user_agent", self.user_agent)
                    self.speed_limit = data.get("speed_limit", self.speed_limit)
            except Exception as e:
                print("Error loading settings:", e)
                
    def save(self):
        data = {
            "default_download_dir": self.default_download_dir,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "proxy": self.proxy,
            "user_agent": self.user_agent,
            "speed_limit": self.speed_limit
        }
        try:
            with open(self.settings_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Error saving settings:", e)
