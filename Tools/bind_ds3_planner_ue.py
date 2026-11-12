"""Switch the controller between the planner tree and the prior tactical tree."""
import json
import shutil
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir())
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
folder = globals().get('BUILD_FOLDER', 'DS3-Planner')
report = json.loads((project / 'Saved' / folder / 'build.json').read_text(encoding='utf-8'))
tree = unreal.load_asset(report['previous' if globals().get('RESTORE_PREVIOUS') else 'main'])
controller = unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
editor = unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
pins = [p for node in editor.list_all_nodes() for p in node.list_all_pins()]
tree_pin, = [p for p in pins if str(p.get_pin_name()) == 'BTAsset']
bb_pin, = [p for p in pins if str(p.get_pin_name()) == 'BlackboardAsset']
assert bb_pin.get_pin_value() == tree.blackboard_asset.get_path_name()
previous = tree_pin.get_pin_value()
assert previous in (report['previous'], report['main']), previous

backup = project / 'LocalBackups/DS3-Planner-2026-11-13/BP_EnemyAIController.uasset'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(project / 'Content/Gameplay/AI/BP_EnemyAIController.uasset', backup)

def bind(path):
    if tree_pin.get_pin_value() != path:
        tree_pin.set_pin_value(path)
    assert tree_pin.get_pin_value() == path
    unreal.BlueprintEditorLibrary.compile_blueprint(controller)
    assert not editor.list_nodes_with_errors()
    assert unreal.EditorAssetLibrary.save_loaded_asset(controller, False)

try:
    bind(tree.get_path_name())
except Exception:
    bind(previous)
    raise

unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([tree])
unreal.EditorAssetLibrary.sync_browser_to_objects([tree.get_path_name()])
print('DS3_BOUND', tree.get_path_name())
