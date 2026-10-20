"""
One-click desktop launcher for the Reinforcement Learning Adaptive Routing Visualizer.
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from visualizer.gui_app import launch_gui

if __name__ == "__main__":
    print("Launching RL Adaptive Routing Visualizer...")
    launch_gui()

