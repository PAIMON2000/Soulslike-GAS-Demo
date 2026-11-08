"""Compatibility entry: verify/export the CURRENT tree, never recreate retired trees."""
import runpy
from pathlib import Path
p=Path(__file__).parent
runpy.run_path(str(p/'verify_ds3_tactical_actions.py'))
runpy.run_path(str(p/'export_ds3_tactical.py'))
