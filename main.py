#!/usr/bin/env python3
"""
main.py – Entry point for the IDM Clone.
Run with: python main.py
"""

import sys
import traceback
from PyQt5.QtWidgets import QApplication
from main_window import IDMMainWindow

def exception_hook(exctype, value, tb):
    traceback.print_exception(exctype, value, tb)
    input("Press Enter to exit...")
    sys.exit(1)

def main():
    sys.excepthook = exception_hook
    app = QApplication(sys.argv)
    window = IDMMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
