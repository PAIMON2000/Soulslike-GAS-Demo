"""Remove explicitly retired, unreferenced trees after verified offline backup.

Uses normal asset deletion; never rebuilds graphs or renames engine objects.
"""
import hashlib,json,shutil
from pathlib import Path
import unreal
P=Path(unreal.Paths.project_dir()).resolve()
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE before cleanup'
audit=json.loads((P/'Saved/ObsoleteTreeAudit.json').read_text(encoding='utf-8'))
reference=json.loads((P/'docs/reproduction/ds3-standard-action-reference.json').read_text(encoding='utf-8'))
assert len(reference)==11
old=[x['path'] for x in audit['old_trees']]
assert len(old)==8 and len(set(old))==8
assert all('/StandardReadable/' not in p and '/Validation/' not in p for p in old)
lib=unreal.EditorAssetLibrary
controller=unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
ed=unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
binding=[p.get_pin_value() for n in ed.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name())=='BTAsset']
assert binding==['/Game/Gameplay/AI/DS3BrokenSword/StandardReadable/BT_DS3_CombatOverview.BT_DS3_CombatOverview']
backup=P/'LocalBackups/RemovedBehaviorTrees-2026-11-09'
backup.mkdir(parents=True,exist_ok=True)
records=[]
for path in old:
 refs=[str(x) for x in lib.find_package_referencers_for_asset(path,True)]
 assert not refs, (path,refs)
 relative=Path(path.removeprefix('/Game/')+'.uasset')
 source=(P/'Content'/relative).resolve();destination=(backup/relative).resolve()
 assert source.is_relative_to(P/'Content') and destination.is_relative_to(backup)
 assert source.is_file()
 destination.parent.mkdir(parents=True,exist_ok=True)
 digest=hashlib.sha256(source.read_bytes()).hexdigest()
 if destination.exists():assert hashlib.sha256(destination.read_bytes()).hexdigest()==digest
 else:shutil.copy2(source,destination)
 assert hashlib.sha256(destination.read_bytes()).hexdigest()==digest
 records.append(dict(asset=path,backup=destination.relative_to(P).as_posix(),sha256=digest))
(backup/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
editors=unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
for path in old:
 asset=unreal.load_asset(path)
 if asset:editors.close_all_editors_for_asset(asset)
 del asset
unreal.SystemLibrary.collect_garbage()
for path in old:
 assert not lib.find_package_referencers_for_asset(path,True), path
 assert lib.delete_asset(path), 'Normal asset deletion failed: '+path
 assert not lib.does_asset_exist(path), path
for relative in ['Gameplay/AI/DS3BrokenSword/Readable','Gameplay/AI/DS3BrokenSword/ReadableStandard',
                 'Gameplay/AI/DS3BrokenSword/Standard','Gameplay/AI/Archive/BeforeDS3BrokenSword','Gameplay/AI/Archive']:
 directory=(P/'Content'/relative).resolve();assert directory.is_relative_to(P/'Content')
 if directory.is_dir() and not any(directory.iterdir()):directory.rmdir()
main=unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/StandardReadable/BT_DS3_CombatOverview')
lib.sync_browser_to_objects([main.get_path_name()]);editors.open_editor_for_assets([main])
result=dict(date='2026-11-09',removed=records,active_tree=binding[0],deleted_count=len(records),active_binding_preserved=True)
(P/'Saved/RemovedBehaviorTrees.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('OBSOLETE_TREES_REMOVED',len(records))
