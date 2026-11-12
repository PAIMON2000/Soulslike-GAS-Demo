"""Rebuild the planner's ordered rules with native UE nodes and existing actions."""
import json
import re
import sys
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(project / 'Tools'))
import ds3_tactical_graph as graph

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
planner_path = '/Game/Gameplay/AI/DS3BrokenSword/Planner/'
graph.DEST = planner_path + 'Grouped/'
graph.OUT = project / 'Saved/DS3-Planner'
graph.OUT.mkdir(parents=True, exist_ok=True)
old = unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/Tactical/BT_BrokenSword_Combat')
draft = json.loads((project / 'ashen-tree/data/断剑怪-策划阅读树.json').read_text(encoding='utf-8'))
assert old and old.blackboard_asset == graph.bb
init, decide, *_ = graph.kids(graph.kids(old.root_node)[0])
decision = decide.behavior_asset
measure, rules, *_ = graph.kids(decision.root_node)

source_exports = {}


def collect(tree):
    if tree.get_path_name() in source_exports:
        return
    source_exports[tree.get_path_name()] = graph.blocks(graph.export(tree, tree.get_name() + '-source.t3d'))
    for node in graph.walk(tree):
        if isinstance(node, unreal.BTTask_RunBehavior):
            collect(node.behavior_asset)


collect(old)


def make(tree, cls, title):
    node = unreal.new_object(cls, outer=tree)
    graph.label(node, title, title)
    return node


def child(node, decorators=()):
    entry = graph.plain_child(node)
    entry.set_editor_property('decorators', list(decorators))
    return entry


def composite(tree, cls, title, entries):
    node = make(tree, cls, title)
    node.set_editor_property('children', entries)
    return node


def clone(node, tree, title=None):
    out = make(tree, node.get_class(), str(node.get_editor_property('node_name')))
    source = source_exports[node.get_outer().get_path_name()][node.get_name()]
    derived = {'Children', 'TreeAsset', 'ParentNode', 'CachedDescription', 'OperationType',
               'BasicOperation', 'ArithmeticOperation', 'TextOperation'}
    for prop in dict.fromkeys(re.findall(r'^      (\w+)=', source, re.M)):
        if prop not in derived:
            out.set_editor_property(prop, node.get_editor_property(prop))
    if isinstance(node, unreal.BTDecorator_Blackboard):
        selector = node.get_editor_property('blackboard_key')
        name = selector.get_editor_property('selected_key_name')
        keys = list(graph.bb.get_editor_property('keys'))
        index, key = next((i, k) for i, k in enumerate(keys) if k.get_editor_property('entry_name') == name)
        key_type = key.get_editor_property('key_type').get_class()
        selector.set_editor_property('selected_key_type', key_type)
        selector.set_editor_property('selected_key_id', index)
        out.set_editor_property('blackboard_key', selector)
        operation = ('arithmetic_operation' if key_type.get_name().endswith(('_Int', '_Float'))
                     else 'basic_operation')
        # UE recalculates its internal operation when the exposed property changes.
        out.set_editor_property(operation, node.get_editor_property(operation))
    if isinstance(node, unreal.BTCompositeNode):
        assert not node.services
        entries = []
        for entry in node.children:
            copy = child(clone(entry.child_composite or entry.child_task, tree),
                         [clone(decorator, tree) for decorator in entry.decorators])
            copy.set_editor_property('decorator_ops', list(entry.decorator_ops))
            entries.append(copy)
        out.set_editor_property('children', entries)
    if title:
        graph.label(out, title, title)
    return out


def run(tree, asset, title):
    node = make(tree, unreal.BTTask_RunBehavior, title)
    node.set_editor_property('behavior_asset', asset)
    return node


def save(tree, root):
    tree.set_editor_property('root_node', root)
    graph.finalize(tree)


# Validate the planner order and map every condition to its original typed UE node.
def original_rules(node, guards=()):
    if isinstance(node, unreal.BTTask_RunBehavior):
        yield from original_rules(node.behavior_asset.root_node, guards)
    elif isinstance(node, unreal.BTComposite_Selector):
        for entry in node.children:
            assert not entry.decorator_ops
            yield from original_rules(entry.child_composite or entry.child_task,
                                      guards + tuple(entry.decorators))
    else:
        assert node.get_class().get_name() == 'BTT_SetCandidates_C'
        yield node, guards


branches = draft['subtrees']['rules']['children']
original = list(original_rules(rules))
assert len(branches) == len(original) == 19
action_ids = {'连击A': 1, '连击B': 2, '固定两段': 4, '3003冷却攻击': 5, '前冲攻击': 6,
              '后退': 11, '侧移': 12, '转身': 13, '特殊20005': 20, '特殊20006': 21, '变体专用接近': 54}
for branch, (task, guards) in zip(branches, original):
    assert branch['source'] == task.get_path_name()
    assert [n['source'] for n in branch['children'][:-1]] == [g.get_path_name() for g in guards]
    candidates = branch['children'][-1]['children'][0]['children']
    expected = {action_ids[n['refAction']]: n['weight'] for n in candidates}
    assert all(task.get_editor_property(f'W{aid}') == expected.get(aid, 0) for aid in action_ids.values())

def new_tree(name):
    path = graph.DEST + name
    pending = unreal.find_object(None, path + '.' + name)
    if pending:
        # A failed build can leave an empty factory graph in memory before its first save.
        asset_file = project / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        assert not asset_file.exists() and not pending.root_node, path
        assert unreal.find_object(None, pending.get_path_name() + ':Behavior Tree'), path
        graph.created.append(pending)
        return pending
    return graph.new_tree(name)

execution = unreal.load_asset(planner_path + 'BT_DS3_02_ExecuteChoice')
assert execution and execution.blackboard_asset == graph.bb


def signature(guard):
    key = guard.get_editor_property('blackboard_key').get_editor_property('selected_key_name')
    return (str(key), str(guard.get_editor_property('arithmetic_operation')),
            guard.get_editor_property('int_value'), guard.get_editor_property('float_value'))


def rule_entry(tree, index, inherited=()):
    branch = branches[index - 1]
    task, guards = original[index - 1]
    # A failed gate must allow the next rule. Only the already matched execution
    # is wrapped in ForceSuccess, so task failure ends the round.
    inherited_signatures = {signature(g) for g in inherited}
    condition_nodes = [clone(g, tree, n['name']) for g, n in zip(guards, branch['children'][:-1])
                       if signature(g) not in inherited_signatures]
    force_success = make(tree, unreal.BTDecorator_ForceSuccess, '行动结束即结束本轮')
    branch_node = composite(tree, unreal.BTComposite_Sequence, f'{index:02d} {branch["name"]}', [
        child(clone(task, tree, '设置候选与权重')),
        child(run(tree, execution, '过滤、抽取并执行本轮行动'), [force_success]),
    ])
    return child(branch_node, condition_nodes)


def selector(tree, title, entries):
    return composite(tree, unreal.BTComposite_Selector, title, entries)


def subcategory(tree, title, numbers, guards):
    return child(selector(tree, title, [rule_entry(tree, i, guards) for i in numbers]),
                 [clone(g, tree) for g in guards])


team_guards = original[2][1][:2]
assert all(g[:2] == team_guards for _, g in original[2:5])
team = new_tree('BT_DS3_TeamRole')
save(team, selector(team, '先看职责，再看围攻间距', [
    rule_entry(team, i, team_guards) for i in (3, 4, 5)
]))

facing = new_tree('BT_DS3_Facing')
save(facing, selector(facing, '先检查贴近侧面，再检查侧后方', [
    rule_entry(facing, i) for i in (6, 7, 8, 9)
]))

special = new_tree('BT_DS3_SpecialMove')
special_guards = original[9][1][:-1]
hurt_guards = original[11][1][:-1]
assert special_guards == original[10][1]
assert hurt_guards == original[12][1]
save(special, selector(special, '先判断特殊招式能否触发，再看间距', [
    subcategory(special, '专用招式配置', (10, 11), special_guards),
    subcategory(special, '受伤变体已达到血量门槛', (12, 13), hurt_guards),
]))

distance = new_tree('BT_DS3_CombatDistance')
far_guards = original[15][1]
mid_guards = original[17][1]
assert len(far_guards) == len(mid_guards) == 1
assert far_guards[0].get_editor_property('float_value') == 5.5
assert mid_guards[0].get_editor_property('float_value') == 1.5
save(distance, selector(distance, '先按间距分层，再检查变体候选', [
    subcategory(distance, '远距 · 检查变体与普通候选', (14, 15, 16), far_guards),
    subcategory(distance, '中距 · 检查变体与普通候选', (17, 18), mid_guards),
    rule_entry(distance, 19),
]))

ordered = new_tree('BT_DS3_01_SelectAction')
save(ordered, selector(ordered, '按优先级筛选 · 首个命中执行本轮', [
    rule_entry(ordered, 1),
    rule_entry(ordered, 2),
    child(run(ordered, team, '03 队伍职责 · 旁观或围攻'), [clone(g, ordered) for g in team_guards]),
    child(run(ordered, facing, '04 侧面或身后 · 近侧出招或转身')),
    child(run(ordered, special, '05 特殊招式 · 触发条件与间距')),
    child(run(ordered, distance, '06 普通交战 · 远、中、近')),
]))

main = new_tree('BT_DS3_00_GroupedCombat')
round_node = composite(main, unreal.BTComposite_Sequence, '有目标 · 完成一轮战斗', [
    child(clone(init, main, '01 首次准备移动速度与距离换算')),
    child(clone(measure, main, '02 读取间距、方向、血量和冷却')),
    child(run(main, ordered, '03 选择本轮行动 · 双击看六个入口')),
])
save(main, composite(main, unreal.BTComposite_Selector, '断剑怪 · 战斗循环', [
    child(round_node, [clone(d, main) for d in old.root_node.children[0].decorators]),
    child(clone(graph.kids(old.root_node)[1], main, '无有效目标 · 等待0.2秒再检查')),
]))

# Traverse the saved hierarchy and check that its leaf rules still have the same order.
def ordered_leaves(node):
    if isinstance(node, unreal.BTTask_RunBehavior):
        yield from ordered_leaves(node.behavior_asset.root_node)
    elif isinstance(node, unreal.BTComposite_Selector):
        for next_node in graph.kids(node):
            yield from ordered_leaves(next_node)
    else:
        assert isinstance(node.children[1].decorators[0], unreal.BTDecorator_ForceSuccess)
        yield str(node.get_editor_property('node_name'))


assert list(ordered_leaves(ordered.root_node)) == [f'{i:02d} {b["name"]}' for i, b in enumerate(branches, 1)]
assert len(ordered.root_node.children) == 6
flat = unreal.load_asset(planner_path + 'BT_DS3_00_CombatRound')
report = dict(main=main.get_path_name(), previous=flat.get_path_name(), rules=ordered.get_path_name(),
              execution=execution.get_path_name(), top_level_count=6, rule_count=19, action_count=11)
(graph.OUT / 'build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('PLANNER_UE_BUILT', report)
