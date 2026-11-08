"""Retire the superseded entry only after tests; retain active execution subtrees."""
import unreal,json,shutil,hashlib
from pathlib import Path
P=Path(unreal.Paths.project_dir()); out=P/'Saved/DS3-Tactical'
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
for name in ['verified','runtime','recovery-sampling']:
    assert json.loads((out/(name+'.json')).read_text(encoding='utf-8'))['passed'],name
draw=json.loads((out/'sampling.json').read_text(encoding='utf-8'))
assert len(draw['tests'])>=4 and all(t['passed'] for t in draw['tests'][:4])
old='/Game/Gameplay/AI/DS3BrokenSword/StandardReadable/BT_DS3_CombatOverview'
main=unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/Tactical/BT_BrokenSword_Combat')
controller=unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
ed=unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
pins=[p for n in ed.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name())=='BTAsset']
assert len(pins)==1 and pins[0].get_pin_value()==main.get_path_name()
lib=unreal.EditorAssetLibrary; subsystem=unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
if lib.does_asset_exist(old):
    refs=list(lib.find_package_referencers_for_asset(old,True)); assert not refs,refs
    src=P/'Content/Gameplay/AI/DS3BrokenSword/StandardReadable/BT_DS3_CombatOverview.uasset'
    dst=P/'LocalBackups/Tactical-2026-11-09/BT_DS3_CombatOverview.uasset'
    shutil.copy2(src,dst); assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dst.read_bytes()).digest()
    asset=unreal.load_asset(old); subsystem.close_all_editors_for_asset(asset); del asset
    unreal.SystemLibrary.collect_garbage(); assert lib.delete_asset(old); assert not lib.does_asset_exist(old)
    (out/'retired-main.json').write_text(json.dumps(dict(path=old,backup=str(dst),referencers=refs),indent=2),encoding='utf-8')
# Close only this task's generated inspection tabs; show the useful entry and decisions.
for path in lib.list_assets('/Game/Gameplay/AI/DS3BrokenSword/Tactical',True,False):
    a=unreal.load_asset(path)
    if a and a!=main: subsystem.close_all_editors_for_asset(a)
test=unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/Validation/BT_TacticalRecoveryOnce')
if test: subsystem.close_all_editors_for_asset(test)
decision=unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/Tactical/BT_DecisionRules')
subsystem.open_editor_for_assets([main,decision]);lib.sync_browser_to_objects([main.get_path_name()])
print('TACTICAL_FINALIZED',main.get_path_name())
