#!/usr/bin/env python3
"""
IDM Clone – A complete Internet Download Manager replica in Python.
Usage: python idm_clone.py
Dependencies:
    - PyQt5
    - requests
    - yt-dlp
"""

import sys
import traceback

from PyQt5.QtWidgets import QApplication
from gui import IDMMainWindow

# Global exception hook to capture any unhandled exceptions.
def exception_hook(exctype, value, tb):
    traceback.print_exception(exctype, value, tb)
    input("Press Enter to exit...")
    sys.exit(1)

sys.excepthook = exception_hook

def main():
    app = QApplication(sys.argv)
    window = IDMMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
