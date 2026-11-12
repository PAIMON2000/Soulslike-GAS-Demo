"""Name the existing TeamRole conditions and show their candidates in UE."""
import sys
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(project / 'Tools'))
import ds3_tactical_graph as graph

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
graph.OUT = project / 'Saved/DS3-Planner'
root = '/Game/Gameplay/AI/DS3BrokenSword/'
selection = unreal.load_asset(root + 'Planner/Grouped/BT_断剑怪_选择本轮行动')
team_call = graph.kids(selection.root_node)[2]
team = team_call.behavior_asset
assert team.get_name() == 'BT_断剑怪_队伍配合'
recovery = unreal.load_asset(root + 'Tactical/BT_断剑怪_恢复走位规则')
editors = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
# Opening a loaded tree resolves its editor-side blackboard key descriptions.
editors.open_editor_for_assets([recovery])


def operation(node):
    return node.get_editor_property('arithmetic_operation'), node.get_editor_property('int_value')


op = unreal.ArithmeticKeyOperation
condition_titles = {
    (str(op.EQUAL), 1): '当前角色是旁观（后退或侧移）',
    (str(op.EQUAL), 2): '当前角色是围攻（按间距选行动）',
    (str(op.GREATER_OR_EQUAL), 1): '有队伍配合职责',
    (str(op.LESS_OR_EQUAL), 2): '职责限于旁观或围攻',
}


def runtime_config(tree, tag):
    exported = graph.blocks(graph.export(tree, f'{tree.get_name()}-role-{tag}.t3d'))
    return {node.get_name(): [line for line in exported[node.get_name()].splitlines()
                             if not line.lstrip().startswith(('NodeName=', 'CachedDescription='))]
            for node in graph.walk(tree)}


trees = (selection, team, recovery)
before = {tree.get_name(): runtime_config(tree, 'before') for tree in trees}
for tree in trees:
    for node in graph.walk(tree):
        if not isinstance(node, unreal.BTDecorator_Blackboard):
            continue
        key = node.get_editor_property('blackboard_key').get_editor_property('selected_key_name')
        if str(key) == 'TeamRole':
            kind, value = operation(node)
            node.set_editor_property('node_name', condition_titles[str(kind), value])

team_call.set_editor_property('node_name', '03 队伍配合 · 旁观或围攻')
team.root_node.set_editor_property('node_name', '队伍配合如何行动')
for entry, title in zip(team.root_node.children, ('旁观时保持间距', '围攻 · 远距离', '围攻 · 中近距离'), strict=True):
    branch = entry.child_composite
    branch.set_editor_property('node_name', title)
    candidates = graph.kids(branch)[0]
    assert candidates.get_class().get_name() == 'BTT_SetCandidates_C'
    weights = [(name, candidates.get_editor_property(f'W{index}'))
               for index, name in ((6, '前冲'), (11, '后退'), (12, '侧移'))]
    candidates.set_editor_property('node_name', ' · '.join(f'{name}{value:g}' for name, value in weights if value))

for tree in trees:
    assert runtime_config(tree, 'edited') == before[tree.get_name()]
    assert graph.lib.save_loaded_asset(tree, False)
    assert runtime_config(tree, 'saved') == before[tree.get_name()]

editors.close_all_editors_for_asset(team)
editors.open_editor_for_assets([team])
graph.lib.sync_browser_to_objects([team.get_path_name()])
print('TEAM_ROLE_LABELS_SAVED', team.get_path_name())
