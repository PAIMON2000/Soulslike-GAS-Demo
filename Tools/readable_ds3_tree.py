"""Edit presentation metadata only; export a source-linked local reading archive.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>.
Use -ReadabilityVerify on a second invocation to verify the saved package.
"""
import json
import re
import shutil
from pathlib import Path
import unreal

PROJECT = Path(unreal.Paths.project_dir())
ASSET = '/Game/Gameplay/AI/DS3BrokenSword/BT_DS3BrokenSword'
OUT = PROJECT / 'Saved/DS3-Readability'
OUT.mkdir(parents=True, exist_ok=True)
tree = unreal.load_asset(ASSET)
assert tree, ASSET
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
VERIFY = '-ReadabilityVerify' in unreal.SystemLibrary.get_command_line()

def read_export(path):
    data = path.read_bytes()
    return data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')

def export(path):
    task = unreal.AssetExportTask()
    task.object = tree
    task.filename = str(path)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = unreal.ObjectExporterT3D()
    assert unreal.Exporter.run_asset_export_task(task)
    return read_export(path)

def semantic(text):
    # These are the only allowed differences in the full reflected object export.
    return '\n'.join(line for line in text.splitlines()
                     if not re.match(r'\s*(NodeName|NodeComment|CachedDescription)=', line))

labels = {
    'Root': ('断剑敌人｜行动周期', '有目标时执行完整行动周期；无目标时等待。当前树不含死亡、受击、巡逻和感知外层。'),
    'ActionCycle': ('战斗周期｜从上到下执行', '初始化 → 选择一次行动 → 执行到底 → 恢复走速和朝向 → 抽取攻击后调整 → 执行调整。'),
    'Init': ('① 初始化比例、速度与攻击历史', 'BTT_DSInit；UnitScale 默认100厘米/脚本单位是移植假设；不代表原游戏实测比例。'),
    'Decide': ('② 按原优先级与权重选招一次', 'BTT_DSDecide：事件/变体 → 队伍角色 → 侧后方向 → 普通距离权重；随后仅对3003过滤20秒冷却，再抽取Action。运行中不逐帧重抽。具体权重见 docs/research/06-黑魂3断剑敌人行为树反推.md。'),
    'Dispatch': ('③ 执行已选行动｜按Action匹配', '此选择器匹配已经抽出的Action；横向分支顺序不是招式概率，也不是重新选招。'),
    'AfterMode': ('④ 恢复步行并朝向目标', 'BTT_DSLocomotion；沿用现有移动配置。'),
    'AfterChoice': ('⑤ 决定是否追加攻击后走位', 'BTT_DSAfterAttack：普通攻击50%、特殊20/21为100%，移动行动不追加；再按距离表决定AfterAction。'),
    'AfterDispatch': ('⑥ 执行攻击后走位｜按AfterAction匹配', '1侧移 / 2后退 / 3靠近 / 其他结束本轮。'),
    'AfterSide': ('攻击后侧移', '持续时间与距离读取攻击后选择结果；导航圆弧为原生侧移的近似实现。'),
    'AfterBack': ('攻击后后退', '读取攻击后选择结果；沿用现有限时相对移动。'),
    'AfterApproach': ('攻击后靠近', '读取攻击后选择结果；沿用现有限时相对移动。'),
    'NoAfterMove': ('不追加走位｜立即结束本轮', 'Wait=0，不是攻击冷却。'),
    'NoTarget': ('无目标｜等待0.2秒后重查', '仅处理本树的无目标等待；不代表已实现巡逻或脱战归位。'),
    'ValidTarget': ('条件：目标有效｜失效时中止', 'TargetActor已设置；保留原有Both中断模式及任务清理。'),
    'Act11': ('后退拉开距离 [Act11]', '必要时接近目标后，最多后退4秒，目标距离10脚本单位。'),
    'Act12': ('围绕目标侧移 [Act12]', '侧移最多2秒；保留现有范围退出判断，越界后结束并重新决策。'),
    'Act13': ('原地转向目标 [Act13]', '最多3秒；原生有限转向，随机角度门槛15～20度。'),
    'Act54': ('110054变体专用接近 [Act54]', '特殊变体分支，非普通攻击。'),
    'Retreat11': ('后退｜最多4秒，拉至10单位', 'DSRelativeMove Mode=2；导航位移为项目替代实现。'),
    'Relative12': ('侧移｜最多2秒，保留范围退出', 'DSRelativeMove Mode=1；不是每Tick重新抽取行动。'),
    'Relative13': ('转身｜最多3秒', 'DSRelativeMove Mode=4；原生转向，不播放独立魂3转身动画。'),
}
actions = {
    1: ('连击A', '3000 → 3001 → 可选3002'),
    2: ('连击B', '3001 → 3002 → 可选3000'),
    4: ('固定两段攻击', '3002 → 3001'),
    5: ('独立冷却攻击', '3003；仅此招受20秒冷却过滤'),
    6: ('远距攻击', '3007；前进速度为项目替代参数'),
    20: ('特殊动作20005', '当前以近战动画替代，未复刻原生特殊效果'),
    21: ('特殊动作20006', '当前以近战动画替代，未复刻原生特殊效果'),
}
for aid, (title, detail) in actions.items():
    labels['Act'+str(aid)] = (f'{title} [Act{aid:02d}]', '配置接近 → 原生寻路 → '+detail+'。')
for aid in [1, 2, 4, 5, 6, 11, 12, 13, 20, 21, 54]:
    s = str(aid)
    labels['Select'+s] = (f'条件：已选Act{aid:02d}', f'黑板Action == {aid}；概率已在②选招任务中决定。')
    labels['Mode'+s] = ('配置接近速度与目标距离', f'Act{aid:02d}的现有BTT_DSLocomotion配置；距离沿用脚本单位换算，实际半径扣除角色胶囊半径。')
    labels['Approach'+s] = ('寻路接近至本招距离', '原生MoveTo，保留现有黑板目标、半径、路径和超时设置。')
    labels['ApproachBudget'+s] = ('接近超时｜读取ApproachLife', '原有时间预算：步行4秒 / 跑步8秒；保持原配置。')
for aid in [1, 2]:
    s = str(aid)
    labels['ComboLength'+s] = ('一次决定两段或三段连击', '两段25% / 三段75%；连段进行中不重抽。')
    labels['ThirdChoice'+s] = ('是否追加第三击', 'ThirdHit为真执行第三击，否则立即结束连段。')
    labels['ThirdHit'+s] = ('条件：本轮选择了三段', '黑板ThirdHit已设置。')
    labels['NoThird'+s] = ('两段完成｜跳过第三击', 'Wait=0，立即完成，无额外冷却。')
for i, title in [(1, '侧移'), (2, '后退'), (3, '靠近')]:
    labels['After'+str(i)] = (f'条件：攻击后{title}', f'黑板AfterAction == {i}。')

prefix = tree.get_path_name()+':'
objects = [o for o in unreal.ObjectIterator() if isinstance(o, unreal.Object) and unreal.Object.get_path_name(o).startswith(prefix)]
nodes = []
def collect(n):
    nodes.append(n)
    if isinstance(n, unreal.BTCompositeNode):
        for c in n.children:
            nodes.extend(c.decorators)
            collect(c.child_composite or c.child_task)
collect(tree.root_node)
export(OUT/'loaded.t3d')
# Editor saves may rename native instances. Resolve roles by the existing topology,
# never rely on generated UObject suffixes or rebuild the connected tree.
roles = {}
def bind(n, role):
    roles[n.get_name()] = role
    return n
def children(n):
    return [c.child_composite or c.child_task for c in n.children]
root = bind(tree.root_node, 'Root')
cycle, idle = children(root)
bind(cycle, 'ActionCycle'); bind(idle, 'NoTarget')
bind(root.children[0].decorators[0], 'ValidTarget')
cycle_roles = ['Init', 'Decide', 'Dispatch', 'AfterMode', 'AfterChoice', 'AfterDispatch']
assert len(cycle.children) == len(cycle_roles)
for n, role in zip(children(cycle), cycle_roles):
    bind(n, role)
dispatch = children(cycle)[2]
action_order = [1, 2, 4, 5, 6, 20, 21, 11, 12, 13, 54]
assert len(dispatch.children) == len(action_order)
for c, aid in zip(dispatch.children, action_order):
    action = c.child_composite
    bind(action, 'Act'+str(aid)); bind(c.decorators[0], 'Select'+str(aid))
    tasks = children(action)
    bind(tasks[0], 'Mode'+str(aid))
    if aid in actions or aid in [11, 54]:
        bind(tasks[1], 'Approach'+str(aid))
        if aid in actions:
            bind(action.children[1].decorators[0], 'ApproachBudget'+str(aid))
    if aid in [1, 2]:
        bind(tasks[2], 'ComboLength'+str(aid))
        optional = bind(tasks[-1], 'ThirdChoice'+str(aid))
        bind(optional.children[0].decorators[0], 'ThirdHit'+str(aid))
        bind(children(optional)[1], 'NoThird'+str(aid))
    elif aid == 11:
        bind(tasks[2], 'Retreat11')
    elif aid in [12, 13]:
        bind(tasks[1], 'Relative'+str(aid))
after = children(cycle)[5]
for i, (c, role) in enumerate(zip(after.children, ['AfterSide', 'AfterBack', 'AfterApproach', 'NoAfterMove'])):
    bind(c.child_task, role)
    if i < 3:
        bind(c.decorators[0], 'After'+str(i+1))
for n in nodes:
    if isinstance(n, unreal.BTTask_BlueprintBase) and n.get_name().startswith('Strike'):
        attack = n.get_editor_property('SourceAttackID')
        labels[n.get_name()] = (f'执行攻击{attack}｜替代动画', 'BTT_DSAttack；使用项目独立蒙太奇/GAS能力，保留命中、完成与中止逻辑。不是魂3原动画。')
canonical_labels = labels.copy()
for actual, role in roles.items():
    labels[actual] = canonical_labels[role]
missing = [n.get_name() for n in nodes if n.get_name() not in labels]
assert not missing, f'Unmapped live nodes: {missing}'

if VERIFY:
    assert all(str(n.get_editor_property('node_name')) == labels[n.get_name()][0] for n in nodes)
    current = export(OUT/'reloaded.t3d')
    assert semantic(current) == semantic(read_export(OUT/'before.t3d')), 'Runtime properties changed'
    (OUT/'verified.json').write_text(json.dumps({'passed': True, 'node_count': len(nodes), 'saved_labels_verified': True, 'full_export_except_presentation_unchanged': True, 'allowed_presentation_fields': ['NodeName', 'NodeComment', 'CachedDescription']}, indent=2), encoding='utf-8')
    print('READABILITY_RELOAD_VERIFIED', len(nodes))
else:
    backup = PROJECT/'LocalBackups/DS3Readability-2026-11-07'
    backup.mkdir(parents=True, exist_ok=True)
    source = PROJECT/'Content/Gameplay/AI/DS3BrokenSword/BT_DS3BrokenSword.uasset'
    target = backup/source.name
    if not target.exists():
        shutil.copy2(source, target)
    before = export(OUT/'before.t3d')
    # Match editor wrappers to runtime nodes from the standard text export.
    stack, mapping = [], {}
    for line in before.splitlines():
        if line.strip().startswith('Begin Object'):
            m = re.search(r'Name="([^"]+)"', line)
            stack.append(m.group(1) if m else '')
        elif line.strip() == 'End Object':
            stack.pop()
        elif 'NodeInstance=' in line and stack and stack[-1].startswith('BehaviorTreeGraphNode'):
            m = re.search(r"NodeInstance=.*?:([^']+)'", line)
            if m:
                mapping[m.group(1)] = stack[-1]
    for n in nodes:
        title, note = labels[n.get_name()]
        n.modify()
        n.set_editor_property('node_name', title)
        wrapper = mapping.get(n.get_name())
        if wrapper:
            graphnode = unreal.find_object(None, prefix+'Behavior Tree.'+wrapper)
            assert graphnode
            graphnode.modify()
            unreal.get_default_object(unreal.SystemLibrary).call_method(
                'SetStringPropertyByName', (graphnode, unreal.Name('NodeComment'), note))
    after = export(OUT/'after.t3d')
    assert semantic(before) == semantic(after), 'Unexpected non-presentation change; refusing to save'
    # UE 5.8 FBlackboardKeySelector::PreSave rejects the existing TargetActor
    # object key against MoveTo's transient Actor filter. Preserve the existing
    # serialized key without changing the blackboard or runtime task behavior.
    # AllowedTypes is UPROPERTY(transient); restore it immediately after saving.
    filters = []
    try:
        for n in nodes:
            if isinstance(n, unreal.BTTask_MoveTo):
                key = n.get_editor_property('blackboard_key')
                filters.append((n, list(key.get_editor_property('allowed_types'))))
                key.set_editor_property('allowed_types', [])
                n.set_editor_property('blackboard_key', key)
        assert unreal.EditorAssetLibrary.save_loaded_asset(tree, False)
    finally:
        for n, allowed in filters:
            key = n.get_editor_property('blackboard_key')
            key.set_editor_property('allowed_types', allowed)
            n.set_editor_property('blackboard_key', key)
    print('READABILITY_SAVED', len(nodes))

# A faithful reading hierarchy, not an attempted emulator of native UE tasks.
# The explicit UNKNOWN guard prevents the generic demo simulator inventing results.
archive_dir = PROJECT/'ashen-tree/data'
archive_dir.mkdir(parents=True, exist_ok=True)
monster = '110050 断剑敌人（当前UE原型）'
states, reading = [], []
outline = []

def category(n):
    name = roles.get(n.get_name(), n.get_name())
    if name == 'Init':
        return 'life'
    if name == 'ValidTarget' or name == 'NoTarget':
        return 'target'
    if name.startswith(('Mode', 'Approach', 'After', 'Relative', 'Retreat')) or name in ['Act11', 'Act12', 'Act13', 'Act54']:
        return 'range'
    return 'attack'

def add(n, parent, priority, depth):
    name = n.get_name()
    title, note = labels[name]
    sid = 'source_'+name
    nid = 'ue_'+name
    typ = ('选择器' if isinstance(n, unreal.BTComposite_Selector) else
           '顺序器' if isinstance(n, unreal.BTCompositeNode) else
           '条件' if isinstance(n, unreal.BTDecorator) else '动作')
    states.append(dict(id=sid, name=title, originalName=name, monster=monster,
                       category=category(n), trigger='依父节点顺序及附着装饰器；见关联节点',
                       priority=priority, entry=note, exit='沿用当前UE任务完成/失败/中止逻辑',
                       mutex='', transitions='', phase='当前UE原型', distance='沿用现有配置',
                       status='实际资产已读取；可读性整理',
                       raw=n.get_path_name()+'\n类型：'+n.get_class().get_name()+'\n'+note,
                       notes='来源：当前UE资产；脚本对应关系见docs/design/断剑敌人行为树复刻.md。'))
    reading.append(dict(id=nid, name=title, type=typ, parent=parent, priority=priority,
                        category=category(n), condition='UE_RUNTIME_ONLY' if typ == '条件' else 'true',
                        sourceIds=[sid], note=note+'\nUE对象：'+n.get_path_name()))
    outline.append('  '*depth+'- '+title+'：'+note)
    if isinstance(n, unreal.BTCompositeNode):
        for i, c in enumerate(n.children):
            child = c.child_composite or c.child_task
            p = nid
            if c.decorators:
                p = 'guard_'+child.get_name()
                reading.append(dict(id=p, name='条件与执行：'+labels[child.get_name()][0], type='顺序器',
                                    parent=nid, priority=100-i, category=category(child), condition='true',
                                    sourceIds=['source_'+d.get_name() for d in c.decorators],
                                    note='阅读分组；装饰器在UE中附着于节点，超时装饰器不是普通前置条件。'))
                for j, d in enumerate(c.decorators):
                    add(d, p, 200-j, depth+1)
            add(child, p, 100-i if p == nid else 0, depth+1)

reading.extend([
    dict(id='root', name='当前UE行为树｜只读语义映射', type='顺序器', parent='', priority=0,
         category='all', condition='true', sourceIds=[], note='以下是实际UE层级；通用Tick推演不支持原生任务和随机选招。'),
    dict(id='runtime_guard', name='推演边界：须在Unreal验证', type='条件', parent='root', priority=1000,
         category='all', condition='UE_RUNTIME_ONLY', sourceIds=[],
         note='此条件有意返回UNKNOWN；防止将替代动画、权重任务和原生中断错误模拟为示例动作。')
])
add(tree.root_node, 'root', 0, 0)
archive = dict(schemaVersion=2, title='断剑敌人｜真实UE行为树可读档案', monsters=[monster],
               states=states, trees={monster: reading}, log=['2026-11-07 从当前UE资产导出；仅修改名称和注释，语义完整导出对比。'],
               provenance=dict(asset=ASSET, simulationSupported=False,
                               note='阅读映射，不是魂3原生树；UNKNOWN守卫有意禁止示例推演。'))
(archive_dir/'断剑敌人-当前UE行为树.json').write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding='utf-8')
doc = PROJECT/'docs/design/断剑敌人行为树阅读指南.md'
doc.write_text('# 断剑敌人行为树阅读指南\n\n'
               '当前资产：`'+ASSET+'`。本次整理只改中文显示名称与节点注释；保留节点对象名、连接、顺序、装饰器、中断、权重和任务参数。\n\n'
               '## 怎么读\n\n主干按①到⑥从上到下看；③的分支按Action匹配已经抽好的行动，不代表横向优先级或概率。'
               '展开单个Act分支，看配置接近、寻路、攻击顺序；悬停节点可查看注释。原编号用于追溯源脚本。\n\n'
               '## 当前完整层级\n\n'+'\n'.join(outline)+'\n\n'
               '## 在整理器查看\n\n导入 `ashen-tree/data/断剑敌人-当前UE行为树.json`。导入会替换当前档案，先导出自己的编辑记录。'
               '原始状态栏保存实际UE对象来源，行为树栏保存层级和注释。八类分类只标记现有内容，不补造死亡、受击、巡逻等未实现分支。'
               '该档案开头的推演边界条件有意返回UNKNOWN；选招权重、原生寻路、超时和中断须在UE验证，不能用示例推演冒充实际运行。\n\n'
               '## 证据与回退\n\n修改前资产：`LocalBackups/DS3Readability-2026-11-07/BT_DS3BrokenSword.uasset`。'
               '完整反射导出及二次加载验证：`Saved/DS3-Readability/`。只允许NodeName、NodeComment和编辑器CachedDescription显示缓存发生差异。'
               '原脚本证据和替代实现边界见[复刻说明](断剑敌人行为树复刻.md)。\n', encoding='utf-8')
print('READING_ARCHIVE_EXPORTED', len(states), len(reading))
