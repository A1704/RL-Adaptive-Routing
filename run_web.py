"""
Launcher for the web-based interactive RL Adaptive Routing Visualizer.
Runs a local server and automatically opens it in your default browser.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_app import start_server

if __name__ == "__main__":
    start_server(port=8080)

