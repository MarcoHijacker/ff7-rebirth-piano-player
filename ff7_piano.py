"""Entry point, used both for `python ff7_piano.py` and for the PyInstaller build."""
import sys

from ff7piano.app import main

if __name__ == "__main__":
    sys.exit(main())
