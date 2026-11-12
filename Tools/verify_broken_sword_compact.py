"""Run the ordinary enemy's PIE checks."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('verify_ds3_tactical_runtime.py')),
               init_globals={'COMPACT_RUN': True})
