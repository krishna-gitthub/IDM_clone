"""
settings.py – Manages user preferences (download directory, user-agent, etc.)
"""

import os
import json

class SettingsManager:
    def __init__(self):
        self.default_download_dir = os.path.expanduser("~/Downloads")
        self.user_agent = "IDMClone/1.0"
        self.settings_file = "idm_settings.json"
        self.load()

    def load(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self.default_download_dir = data.get("default_download_dir", self.default_download_dir)
                    self.user_agent = data.get("user_agent", self.user_agent)
            except:
                pass

    def save(self):
        data = {
            "default_download_dir": self.default_download_dir,
            "user_agent": self.user_agent
        }
        with open(self.settings_file, "w") as f:
            json.dump(data, f, indent=4)
