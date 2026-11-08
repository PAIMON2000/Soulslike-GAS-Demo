"""Reversibly bind the independently verified standard overview via public pins."""
import json,shutil
from pathlib import Path
import unreal
P=Path(unreal.Paths.project_dir())
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
report=json.loads((P/'Saved/DS3-Standard/reload-verified.json').read_text(encoding='utf-8'))
assert report['passed'] and report['checked_action_count']==11
tree=unreal.load_asset(report['main']);assert tree and tree.root_node
controller=unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
graph=unreal.BlueprintEditorLibrary.find_event_graph(controller)
editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
pins=[p for n in editor.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name())=='BTAsset']
assert len(pins)==1
pin=pins[0];old=pin.get_pin_value()
bbpins=[p for n in editor.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name())=='BlackboardAsset']
assert len(bbpins)==1
bbpin=bbpins[0];oldbb=bbpin.get_pin_value()
expected='/Game/Gameplay/AI/DS3BrokenSword/BT_DS3BrokenSword.BT_DS3BrokenSword'
assert old in [expected,tree.get_path_name()],old
backup=P/'LocalBackups/DS3Standard-2026-11-08/BP_EnemyAIController.uasset'
if not backup.exists():shutil.copy2(P/'Content/Gameplay/AI/BP_EnemyAIController.uasset',backup)
try:
    assert pin.set_pin_value(tree.get_path_name()) or pin.get_pin_value()==tree.get_path_name()
    assert bbpin.set_pin_value(tree.blackboard_asset.get_path_name()) or bbpin.get_pin_value()==tree.blackboard_asset.get_path_name()
    unreal.BlueprintEditorLibrary.compile_blueprint(controller)
    assert not editor.list_nodes_with_errors()
    assert unreal.EditorAssetLibrary.save_loaded_asset(controller,False)
except Exception:
    pin.set_pin_value(old);bbpin.set_pin_value(oldbb);unreal.BlueprintEditorLibrary.compile_blueprint(controller)
    unreal.EditorAssetLibrary.save_loaded_asset(controller,False)
    raise
(P/'Saved/DS3-Standard/binding.json').write_text(json.dumps(dict(old=old,new=tree.get_path_name(),passed=True),indent=2),encoding='utf-8')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([tree])
print('STANDARD_CONTROLLER_BOUND',tree.get_path_name())
