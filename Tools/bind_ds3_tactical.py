"""Switch only the controller's tree reference after structural verification."""
import unreal,json
from pathlib import Path
P=Path(unreal.Paths.project_dir()); OUT=P/'Saved/DS3-Tactical'
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
report=json.loads((OUT/'verified.json').read_text(encoding='utf-8')); assert report['passed']
tree=unreal.load_asset(report['main']); controller=unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
ed=unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
pins=[p for n in ed.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name())=='BTAsset']; assert len(pins)==1
p=pins[0]; old=p.get_pin_value()
assert old in ['/Game/Gameplay/AI/DS3BrokenSword/StandardReadable/BT_DS3_CombatOverview.BT_DS3_CombatOverview',tree.get_path_name()],old
bbpins=[p for n in ed.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name())=='BlackboardAsset']
assert len(bbpins)==1 and bbpins[0].get_pin_value()==tree.blackboard_asset.get_path_name()
try:
    assert p.set_pin_value(tree.get_path_name()) or p.get_pin_value()==tree.get_path_name()
    unreal.BlueprintEditorLibrary.compile_blueprint(controller); assert not ed.list_nodes_with_errors()
    assert unreal.EditorAssetLibrary.save_loaded_asset(controller,False)
except Exception:
    p.set_pin_value(old); unreal.BlueprintEditorLibrary.compile_blueprint(controller); unreal.EditorAssetLibrary.save_loaded_asset(controller,False); raise
(OUT/'binding.json').write_text(json.dumps(dict(old=old,new=tree.get_path_name(),passed=True),indent=2),encoding='utf-8')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([tree])
unreal.EditorAssetLibrary.sync_browser_to_objects([tree.get_path_name()])
print('TACTICAL_BOUND',tree.get_path_name())
