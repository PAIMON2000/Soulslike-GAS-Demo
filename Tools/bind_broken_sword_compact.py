"""Bind the controller to the compact tree."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('bind_ds3_planner_ue.py')),
               init_globals={'BUILD_FOLDER': 'DS3-Compact'})
