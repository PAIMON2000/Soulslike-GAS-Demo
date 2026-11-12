"""Remove the previous tree assets after verifying the backup and live binding."""
import hashlib
import json
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir()).resolve()
reports = project / 'Saved/DS3-Compact'
build = json.loads((reports / 'build.json').read_text(encoding='utf-8'))
runtime = json.loads((reports / 'runtime.json').read_text(encoding='utf-8'))
assert runtime['passed'] and len(runtime['tests']) == 14
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()

lib = unreal.EditorAssetLibrary
editors = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
controller = unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
editor = unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
binding, = [p.get_pin_value() for n in editor.list_all_nodes() for p in n.list_all_pins()
            if str(p.get_pin_name()) == 'BTAsset']
assert binding == build['main']
main = unreal.load_asset(binding)
active = set()


def visit_tree(tree):
    path = tree.get_path_name()
    if path not in active:
        active.add(path)
        visit_children(tree.root_node)


def visit_children(composite):
    for child in composite.children:
        if child.child_composite:
            visit_children(child.child_composite)
        if isinstance(child.child_task, unreal.BTTask_RunBehavior):
            visit_tree(child.child_task.behavior_asset)
        assert not isinstance(child.child_task, unreal.BTTask_RunBehaviorDynamic)


visit_tree(main)
assert active == {build['main'], build['execution']}, active

archive = (project / build['backup']).resolve()
assert archive.is_relative_to(project / 'LocalBackups')
manifest = archive / 'manifest.json'
backup = json.loads(manifest.read_text(encoding='utf-8'))
assert backup['main'] == build['previous']
old = {}
for relative, digest in backup['files'].items():
    saved = (archive / 'Content' / relative).resolve()
    assert saved.is_relative_to(archive / 'Content')
    assert hashlib.sha256(saved.read_bytes()).hexdigest() == digest, saved
    if saved.name.startswith('BT_'):
        assert relative.startswith('Gameplay/AI/DS3BrokenSword/')
        package = '/Game/' + relative.removesuffix('.uasset')
        assert package not in {path.split('.')[0] for path in active}
        source = project / 'Content' / relative
        if source.is_file():
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, source
        old[package] = relative
for relative in backup.get('retired_trees', []):
    assert not (project / 'Content' / relative).exists()
    old['/Game/' + relative.removesuffix('.uasset')] = relative
assert len(old) == 23

remaining = {path for path in old if lib.does_asset_exist(path)}
referencers = {path: set(map(str, lib.find_package_referencers_for_asset(path, True))) - {path}
               for path in remaining}
external = {path: refs - remaining for path, refs in referencers.items() if refs - remaining}
assert not external, external

# Establish a complete safe deletion order before editing any packages.
order = []
pending = remaining.copy()
while pending:
    ready = sorted(path for path in pending if not (referencers[path] & pending))
    assert ready, pending
    order.extend(ready)
    pending.difference_update(ready)

for path in order:
    asset = unreal.load_asset(path)
    editors.close_all_editors_for_asset(asset)
    del asset
unreal.SystemLibrary.collect_garbage()
for path in order:
    refs = set(map(str, lib.find_package_referencers_for_asset(path, True))) - {path}
    assert not refs, (path, refs)
    assert lib.delete_asset(path), path
    assert not lib.does_asset_exist(path), path
assert all(not (project / 'Content' / relative).exists() for relative in old.values())

# Keep the previously live version in the restore directory.
retired = sorted(relative for relative in old.values()
                 if Path(relative).name.startswith(('BT_断剑怪_历史_', 'BT_断剑怪_验证_')))
assert len(retired) == 10
backup['retired_trees'] = retired
for relative in retired:
    backup['files'].pop(relative, None)
updated_manifest = manifest.with_suffix('.tmp')
updated_manifest.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding='utf-8')
updated_manifest.replace(manifest)
for relative in retired:
    saved = (archive / 'Content' / relative).resolve()
    assert saved.is_relative_to(archive / 'Content')
    saved.unlink(missing_ok=True)

lib.sync_browser_to_objects([binding])
editors.open_editor_for_assets([main])
result = dict(main=binding, action_tree=build['execution'], backup=build['backup'],
              archived_trees=len(old) - len(retired), deleted=sorted(old),
              tests=[test['name'] for test in runtime['tests']])
(reports / 'retired.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('BROKEN_SWORD_TREES_REMOVED', len(old))
