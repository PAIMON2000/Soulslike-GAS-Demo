"""Show the right-flank rule's two cooldown cases in the native tree."""
import shutil
import sys
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(project / 'Tools'))
import ds3_tactical_graph as graph

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
graph.OUT = project / 'Saved/DS3-Planner'
planner = '/Game/Gameplay/AI/DS3BrokenSword/Planner/'
tree = unreal.load_asset(planner + 'Grouped/BT_断剑怪_侧后响应')
selection = unreal.load_asset(planner + 'Grouped/BT_断剑怪_选择本轮行动')
assert graph.kids(selection.root_node)[3].behavior_asset == tree
right = tree.root_node.children[0]
assert str(right.child_composite.get_editor_property('node_name')) == '06 玩家贴近右侧'
weights, execute = graph.kids(right.child_composite)
assert weights.get_class().get_name() == 'BTT_SetCandidates_C'
assert isinstance(execute, unreal.BTTask_RunBehavior)

cooldown, *_ = graph.kids(execute.behavior_asset.root_node)
gate = cooldown.children[0].decorators[0]
assert str(gate.get_editor_property('blackboard_key').get_editor_property('selected_key_name')) == 'Cooldown3003Ready'
assert gate.get_editor_property('basic_operation') == unreal.BasicKeyOperation.NOT_SET
assert cooldown.children[0].child_task.get_class().get_name() == 'BTT_ExcludeCoolingAttack_C'

ids = (1, 2, 4, 5, 6, 11, 12, 13, 20, 21, 54)
values = {i: weights.get_editor_property(f'W{i}') for i in ids}
assert {i for i, value in values.items() if value} == {2, 5, 13}
combo, single, turn = (f'{values[i]:g}' for i in (2, 5, 13))
candidate_title = f'挥砍B {combo} · 转身 {turn} · 冷却就绪再加单击 {single}'


def runtime_config(exported):
    blocks = graph.blocks(exported)
    return {
        node.get_name(): [line for line in blocks[node.get_name()].splitlines()
                          if not line.lstrip().startswith('NodeName=')]
        for node in graph.walk(tree)
    }


before_export = graph.export(tree, 'right-flank-before.t3d')
before = runtime_config(before_export)
asset = project / 'Content/Gameplay/AI/DS3BrokenSword/Planner/Grouped/BT_断剑怪_侧后响应.uasset'
backup = project / 'LocalBackups/DS3-Planner-2026-11-13/BT_DS3_Facing-before-labels.uasset'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(asset, backup)

# Keep the actual entry conditions adjacent to the candidate summary in the graph.
for decorator, label in zip(right.decorators, ('间距 ≤ 2', '右侧角度 ≥ 45°', '右侧角度 ≤ 135°'), strict=True):
    decorator.set_editor_property('node_name', label)
weights.set_editor_property('node_name', candidate_title)
execute.set_editor_property('node_name', '按上述权重抽一次，再执行行动')
wrapper = unreal.find_object(None, tree.get_path_name() + ':Behavior Tree.BehaviorTreeGraphNode_Task_0')
wrapper_export = before_export.split('Begin Object Name="BehaviorTreeGraphNode_Task_0"', 1)[1].split('End Object', 1)[0]
assert wrapper and f":{weights.get_name()}'" in wrapper_export
unreal.get_default_object(unreal.SystemLibrary).call_method(
    'SetIntPropertyByName', (wrapper, unreal.Name('NodePosX'), -96))
assert runtime_config(graph.export(tree, 'right-flank-labeled.t3d')) == before, 'Unexpected behavior change'
assert graph.lib.save_loaded_asset(tree, False)
assert runtime_config(graph.export(tree, 'right-flank-saved.t3d')) == before, 'Save changed behavior parameters'

editors = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
editors.close_all_editors_for_asset(tree)
editors.open_editor_for_assets([tree])
graph.lib.sync_browser_to_objects([tree.get_path_name()])
print('RIGHT_FLANK_LABELED', tree.get_path_name(), candidate_title)
