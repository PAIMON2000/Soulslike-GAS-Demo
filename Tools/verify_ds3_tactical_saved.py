"""Independent commandlet reload: no UI, no gameplay asset writes."""
import runpy,json
from pathlib import Path
import unreal
p=Path(unreal.Paths.project_dir())
runpy.run_path(str(p/'Tools/verify_ds3_tactical.py'),init_globals={'SKIP_BLUEPRINT_UI':True})
runpy.run_path(str(p/'Tools/verify_ds3_tactical_actions.py'))
out=p/'Saved/DS3-Tactical'
(out/'saved-reload.json').write_text(json.dumps(dict(passed=True,independent_process=True)),encoding='utf-8')
print('TACTICAL_SAVED_RELOAD_PASSED')
