"""Give the Broken Sword BehaviorTree assets consistent Chinese names."""
import json
import shutil
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir())
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
root = '/Game/Gameplay/AI/DS3BrokenSword/'
names = {
    'Planner/Grouped/BT_DS3_00_GroupedCombat': '战斗循环',
    'Planner/Grouped/BT_DS3_01_SelectAction': '选择本轮行动',
    'Planner/Grouped/BT_DS3_TeamRole': '队伍配合',
    'Planner/Grouped/BT_DS3_Facing': '侧后响应',
    'Planner/Grouped/BT_DS3_SpecialMove': '特殊招式判断',
    'Planner/Grouped/BT_DS3_CombatDistance': '普通交战间距',
    'Planner/BT_DS3_02_ExecuteChoice': '执行本轮行动',
    'Planner/BT_DS3_01_OrderedRules': '历史_平铺选招规则',
    'Planner/BT_DS3_00_CombatRound': '历史_平铺战斗循环',
    'Tactical/BT_BrokenSword_Combat': '历史_战术战斗总览',
    'Tactical/BT_DecisionRules': '历史_战术选招',
    'Tactical/BT_TeamRole': '历史_战术队伍职责',
    'Tactical/BT_FacingResponse': '历史_战术方向响应',
    'Tactical/BT_SpecialDistance': '历史_战术特殊间距',
    'Tactical/BT_DistanceChoices': '历史_战术交战间距',
    'Tactical/BT_AfterAttack': '攻击后恢复',
    'Tactical/BT_RecoveryDistance': '恢复走位规则',
    'StandardReadable/BT_DS3_Melee': '近身攻击',
    'StandardReadable/BT_DS3_Ranged': '远距攻击',
    'StandardReadable/BT_DS3_Spacing': '调整位置与朝向',
    'StandardReadable/BT_DS3_Special': '执行特殊招式',
    'Validation/BT_DS3PostProbability': '验证_恢复概率',
    'Validation/BT_TacticalRecoveryOnce': '验证_单轮恢复',
}
library = unreal.EditorAssetLibrary
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.wait_for_completion()
assets = {}
renames = {}
for relative, title in names.items():
    old = root + relative
    folder = old.rsplit('/', 1)[0]
    new = folder + '/BT_断剑怪_' + title
    asset = unreal.load_asset(old)
    assert isinstance(asset, unreal.BehaviorTree), old
    assert asset.get_path_name().split('.')[0] == old, old
    assert not library.does_asset_exist(new), new
    assets[old] = asset
    renames[old] = new

controller_path = '/Game/Gameplay/AI/BP_EnemyAIController'
controller = unreal.load_asset(controller_path)
editor = unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
tree_pin, = [p for node in editor.list_all_nodes() for p in node.list_all_pins() if str(p.get_pin_name()) == 'BTAsset']
main_old = root + 'Planner/Grouped/BT_DS3_00_GroupedCombat'
assert tree_pin.get_pin_value().split('.')[0] == main_old


def subtree_links(node):
    if isinstance(node, unreal.BTTask_RunBehavior):
        yield node.behavior_asset
    elif isinstance(node, unreal.BTCompositeNode):
        for entry in node.children:
            yield from subtree_links(entry.child_composite or entry.child_task)


links = {old: list(subtree_links(asset.root_node)) for old, asset in assets.items()}
referencers = {controller_path: controller}
for old in assets:
    for path in library.find_package_referencers_for_asset(old, False):
        if path not in assets and path not in referencers:
            asset = unreal.load_asset(path)
            if asset:
                referencers[path] = asset

backup = project / 'LocalBackups/DS3-TreeNames-2026-11-13'
for path in {*assets, *referencers}:
    relative = Path(path.removeprefix('/Game/') + '.uasset')
    source, destination = project / 'Content' / relative, backup / relative
    if source.is_file() and not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

editors = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
for asset in assets.values():
    editors.close_all_editors_for_asset(asset)
rename_data = []
for old, new in renames.items():
    folder, name = new.rsplit('/', 1)
    rename_data.append(unreal.AssetRenameData(asset=assets[old], new_package_path=folder, new_name=name))
assert unreal.AssetToolsHelpers.get_asset_tools().rename_assets(rename_data)

main = assets[main_old]
if tree_pin.get_pin_value() != main.get_path_name():
    tree_pin.set_pin_value(main.get_path_name())
assert tree_pin.get_pin_value() == main.get_path_name()
unreal.BlueprintEditorLibrary.compile_blueprint(controller)
assert not editor.list_nodes_with_errors()
assert library.save_loaded_assets([*assets.values(), *referencers.values()], False)

for old, new in renames.items():
    asset = unreal.load_asset(new)
    assert asset.get_path_name().split('.')[0] == new
    assert list(subtree_links(asset.root_node)) == links[old], old
    assert all(child.get_name().startswith('BT_断剑怪_') for child in links[old]), old

out = project / 'Saved/DS3-Planner'
build = json.loads((out / 'build.json').read_text(encoding='utf-8'))
for key in ('main', 'previous', 'rules', 'execution'):
    old = build[key].split('.')[0]
    new = renames[old]
    build[key] = new + '.' + new.rsplit('/', 1)[-1]
(out / 'build.json').write_text(json.dumps(build, ensure_ascii=False, indent=2), encoding='utf-8')
(out / 'renames.json').write_text(json.dumps(renames, ensure_ascii=False, indent=2), encoding='utf-8')
editors.open_editor_for_assets([main])
library.sync_browser_to_objects([main.get_path_name()])
print('BROKEN_SWORD_TREES_RENAMED', len(renames), main.get_path_name())
