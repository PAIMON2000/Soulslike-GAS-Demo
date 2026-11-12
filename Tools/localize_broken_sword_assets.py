"""Translate task comments and standardize the live compact tree asset names."""
import json
import sys
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(project / 'Tools'))
from ds3_blueprint_graph import AI, TASK_COMMENTS

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
library = unreal.EditorAssetLibrary
editors = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
compact = AI + 'Compact/'
names = {
    'BT_断剑怪_普通战斗': 'BT_BrokenSword_Combat',
    'BT_断剑怪_行动与收招': 'BT_BrokenSword_ExecuteAction',
}
trees = []
renames = []
for old, new in names.items():
    path = compact + (new if library.does_asset_exist(compact + new) else old)
    tree = unreal.load_asset(path)
    assert isinstance(tree, unreal.BehaviorTree) and tree.get_path_name().split('.')[0] == path
    trees.append(tree)
    if path == compact + old:
        renames.append(unreal.AssetRenameData(asset=tree, new_package_path=compact.rstrip('/'), new_name=new))

main, action = trees
controller = unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
graph = unreal.BlueprintEditorLibrary.find_event_graph(controller)
editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
pin, = [p for node in editor.list_all_nodes() for p in node.list_all_pins() if str(p.get_pin_name()) == 'BTAsset']
assert pin.get_pin_value() == main.get_path_name()
links = [entry.child_task for entry in main.root_node.children[0].child_composite.children
         if isinstance(entry.child_task, unreal.BTTask_RunBehavior)]
assert len(links) == 1 and links[0].behavior_asset == action

tasks = []
updated = 0
for name, translation in TASK_COMMENTS.items():
    asset = unreal.load_asset(AI + name)
    graph = unreal.BlueprintEditorLibrary.find_event_graph(asset)
    task_editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    comments = task_editor.list_comment_nodes()
    assert comments, name
    changed = False
    for comment in comments:
        original = comment.get_comment_text()
        if any('\u4e00' <= char <= '\u9fff' for char in original):
            continue
        text = translation
        if '144040' in original:
            text += ' 此早期版本尚未补齐 144040 在未触发指定条件时的加权候选。'
        comment.set_comment_text(text)
        assert comment.get_comment_text() == text
        changed = True
        updated += 1
    if changed:
        tasks.append(asset)
if tasks:
    assert library.save_loaded_assets(tasks, False)

if renames:
    for tree in trees:
        editors.close_all_editors_for_asset(tree)
    assert unreal.AssetToolsHelpers.get_asset_tools().rename_assets(renames)
    if pin.get_pin_value() != main.get_path_name():
        pin.set_pin_value(main.get_path_name())
    unreal.BlueprintEditorLibrary.compile_blueprint(controller)
    assert not editor.list_nodes_with_errors()
    assert library.save_loaded_assets([controller, *trees], False)

assert pin.get_pin_value() == main.get_path_name() and links[0].behavior_asset == action
assert [tree.get_name() for tree in trees] == list(names.values())
for old in names:
    assert not (project / 'Content' / (compact.removeprefix('/Game/') + old + '.uasset')).exists(), old

out = project / 'Saved/DS3-Compact'
build_file = out / 'build.json'
build = json.loads(build_file.read_text(encoding='utf-8'))
build.update(main=main.get_path_name(), execution=action.get_path_name())
build_file.write_text(json.dumps(build, ensure_ascii=False, indent=2), encoding='utf-8')

editors.open_editor_for_assets([main])
library.sync_browser_to_objects([main.get_path_name()])
print('COMPACT_TREES_RENAMED', main.get_path_name(), action.get_path_name())
print('BTT_COMMENTS_LOCALIZED', len(tasks), updated)
