"""Archive the existing enemy and build the ordinary enemy as two native trees."""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(project / 'Tools'))
import ds3_tactical_graph as graph

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
root = '/Game/Gameplay/AI/DS3BrokenSword/'
graph.DEST = root + 'Compact/'
graph.OUT = project / 'Saved/DS3-Compact'
graph.OUT.mkdir(parents=True, exist_ok=True)
controller = unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
editor = unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
pin, = [p for n in editor.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name()) == 'BTAsset']
old = unreal.load_asset(pin.get_pin_value())
assert old.get_name() == 'BT_断剑怪_战斗循环'

source = project / 'Content'
archive = project / 'LocalBackups/断剑怪_分层版_2026-11-13'
manifest = archive / 'manifest.json'
if not manifest.exists():
    paths = [*sorted((source / 'Gameplay/AI/DS3BrokenSword').rglob('*.uasset')),
             source / 'Gameplay/AI/BP_EnemyAIController.uasset']
    files = {}
    for path in paths:
        relative = path.relative_to(source)
        destination = archive / 'Content' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == digest
        files[relative.as_posix()] = digest
    manifest.write_text(json.dumps(dict(main=old.get_path_name(), files=files), ensure_ascii=False, indent=2), encoding='utf-8')
archived = json.loads(manifest.read_text(encoding='utf-8'))
assert archived['main'] == old.get_path_name()
for relative, digest in archived['files'].items():
    assert hashlib.sha256((archive / 'Content' / relative).read_bytes()).hexdigest() == digest

init, measure, decision = graph.kids(graph.kids(old.root_node)[0])
rules = graph.kids(decision.behavior_asset.root_node)
facing = rules[3].behavior_asset
distance = rules[5].behavior_asset
far, mid, near = distance.root_node.children
ordinary = [(far.child_composite.children[-1], far.decorators),
            (mid.child_composite.children[-1], mid.decorators), (near, [])]
execute = graph.kids(facing.root_node.children[0].child_composite)[1].behavior_asset
cooldown, draw, dispatch, restore, recover = graph.kids(execute.root_node)
read_after, prepare, recovery_gate, recovery_move = graph.kids(recover.behavior_asset.root_node)
normal_gate = recovery_gate.children[0]
spacing = normal_gate.child_task.behavior_asset.root_node

source_exports = {}
key_info = {str(k.get_editor_property('entry_name')): (i, k.get_editor_property('key_type').get_class())
            for i, k in enumerate(graph.bb.get_editor_property('keys'))}


def create(tree, cls, title):
    node = unreal.new_object(cls, outer=tree)
    graph.label(node, title, title)
    return node


def child(node, decorators=()):
    entry = graph.plain_child(node)
    entry.set_editor_property('decorators', list(decorators))
    return entry


def compose(tree, cls, title, entries):
    node = create(tree, cls, title)
    node.set_editor_property('children', entries)
    return node


def clone(node, tree, title=None):
    parent = node.get_outer()
    if parent.get_path_name() not in source_exports:
        source_exports[parent.get_path_name()] = graph.blocks(graph.export(parent, parent.get_name() + '-source.t3d'))
    block = source_exports[parent.get_path_name()][node.get_name()]
    out = create(tree, node.get_class(), str(node.get_editor_property('node_name')))
    derived = {'Children', 'TreeAsset', 'ParentNode', 'CachedDescription', 'OperationType',
               'BasicOperation', 'ArithmeticOperation', 'TextOperation'}
    for prop in dict.fromkeys(re.findall(r'^      (\w+)=', block, re.M)):
        if prop not in derived:
            out.set_editor_property(prop, node.get_editor_property(prop))
    if isinstance(node, unreal.BTDecorator_Blackboard):
        key = node.get_editor_property('blackboard_key')
        index, key_type = key_info[str(key.get_editor_property('selected_key_name'))]
        key.set_editor_property('selected_key_id', index)
        key.set_editor_property('selected_key_type', key_type)
        out.set_editor_property('blackboard_key', key)
        op = 'arithmetic_operation' if key_type.get_name().endswith(('_Int', '_Float')) else 'basic_operation'
        out.set_editor_property(op, node.get_editor_property(op))
    if isinstance(node, unreal.BTCompositeNode):
        assert not node.services
        out.set_editor_property('children', [clone_entry(entry, tree) for entry in node.children])
    if title:
        graph.label(out, title, title)
    return out


def clone_entry(entry, tree):
    result = child(clone(entry.child_composite or entry.child_task, tree), [clone(g, tree) for g in entry.decorators])
    result.set_editor_property('decorator_ops', list(entry.decorator_ops))
    return result


def save(tree, node):
    tree.set_editor_property('root_node', node)
    graph.finalize(tree)


selector, sequence = unreal.BTComposite_Selector, unreal.BTComposite_Sequence
action_names = {1: '挥砍A', 2: '挥砍B', 4: '两段挥砍', 5: '冷却单击', 6: '前冲', 12: '侧移', 13: '转身'}
actions = graph.new_tree('BT_BrokenSword_ExecuteAction')
action_entries = {}
for link in graph.kids(dispatch):
    for entry in link.behavior_asset.root_node.children:
        aid = entry.decorators[0].get_editor_property('int_value')
        if aid in action_names:
            assert aid not in action_entries
            action_entries[aid] = clone_entry(entry, actions)
assert set(action_entries) == set(action_names)
motion = compose(actions, selector, '执行选中的攻击或走位', list(action_entries.values()))

# Only the ordinary recovery path is reachable in this version. Keep its
# probability and distance thresholds and reuse the existing movement tasks.
recovery_cases = []
for entry in spacing.children:
    keys = {str(d.get_editor_property('blackboard_key').get_editor_property('selected_key_name'))
            for d in entry.decorators if isinstance(d, unreal.BTDecorator_Blackboard)}
    if 'TeamRole' not in keys:
        recovery_cases.append(clone_entry(entry, actions))
assert len(recovery_cases) == len(spacing.children) - 2
spacing_choice = compose(actions, selector, '按攻击后的新间距选择走位', recovery_cases)
gate = compose(actions, selector, '普通攻击有50%机会追加走位', [
    child(spacing_choice, [clone(d, actions) for d in normal_gate.decorators]),
    clone_entry(recovery_gate.children[-1], actions),
])
save(actions, compose(actions, sequence, '执行本轮行动，然后处理收招', [
    child(motion), child(clone(restore, actions, '恢复步行并面向玩家')),
    child(clone(read_after, actions, '重新测量玩家间距')),
    child(clone(prepare, actions, '准备本轮走位随机值')), child(gate),
    child(clone(recovery_move, actions, '执行选中的收招走位')),
]))

main = graph.new_tree('BT_BrokenSword_Combat')


def candidate(entry, title, extra_guards=()):
    task = graph.kids(entry.child_composite)[0]
    weights = {i: task.get_editor_property(f'W{i}') for i in (1, 2, 4, 5, 6, 11, 12, 13, 20, 21, 54)}
    assert {i for i, w in weights.items() if w} <= set(action_names)
    summary = ' · '.join(f'{action_names[i]}{w:g}' for i, w in weights.items() if w and i != 5)
    if weights[5]:
        summary += f' · 冷却就绪加单击{weights[5]:g}'
    return child(clone(task, main, title + '\n' + summary),
                 [clone(d, main) for d in (*extra_guards, *entry.decorators)])


angles = compose(main, selector, '玩家在侧面或身后', [
    candidate(entry, title) for entry, title in zip(facing.root_node.children,
                                                  ('贴近右侧', '贴近左侧', '偏向右后方', '偏向左后方'), strict=True)
])
front = compose(main, selector, '其余情况按间距选招', [
    candidate(entry, title, guards) for (entry, guards), title in zip(ordinary, ('远距', '中距', '近距'), strict=True)
])
choice = compose(main, selector, '01 先看方向，再看间距', [child(angles), child(front)])
run = create(main, unreal.BTTask_RunBehavior, '03 执行动作与收招 · 双击查看')
run.set_editor_property('behavior_asset', actions)
force = create(main, unreal.BTDecorator_ForceSuccess, '行动结束后开始下一轮')
round_node = compose(main, sequence, '有玩家目标 · 进行一轮交战', [
    child(clone(init, main, '首次准备角色移动数据')),
    child(clone(measure, main, '读取玩家间距、方向和冷却')),
    child(choice), child(clone(cooldown, main, '单击冷却时从候选移除')),
    child(clone(draw, main, '02 按权重抽一次行动')), child(run, [force]),
])
save(main, compose(main, selector, '断剑怪 · 普通战斗', [
    child(round_node, [clone(d, main) for d in old.root_node.children[0].decorators]),
    clone_entry(old.root_node.children[1], main),
]))

report = dict(main=main.get_path_name(), previous=old.get_path_name(), execution=actions.get_path_name(),
              rule_count=7, action_count=7, backup=str(archive.relative_to(project)))
(graph.OUT / 'build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('DS3_COMPACT_BUILT', report)
