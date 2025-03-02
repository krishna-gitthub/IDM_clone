#!/usr/bin/env python3
"""
IDM Clone – A complete Internet Download Manager replica in Python.
Usage: python idm_clone.py
Dependencies:
    - PyQt5
    - requests
"""

import sys
from PyQt5.QtWidgets import QApplication
from gui import IDMMainWindow

def main():
    app = QApplication(sys.argv)
    window = IDMMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
