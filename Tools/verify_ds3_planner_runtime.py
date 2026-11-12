"""Run the DS3 integration checks and the planner's failure case."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('verify_ds3_tactical_runtime.py')),
               init_globals={'PLANNER_RUN': True})
