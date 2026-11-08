"""Read saved standard assets, verify action equivalence, export reading archives."""
import json,re
from pathlib import Path
import unreal
P=Path(unreal.Paths.project_dir());OUT=P/'Saved/DS3-Standard'
AI='/Game/Gameplay/AI/DS3BrokenSword/'
display=json.loads((P/'Tools/ds3_readable_labels.json').read_text(encoding='utf-8'))
groups=display['GROUPS'];titles={int(k):v for k,v in display['TITLES'].items()}
notes={int(k):v for k,v in display['NOTES'].items()}
source=unreal.load_asset(AI+'BT_DS3BrokenSword')
main=unreal.load_asset(AI+'StandardReadable/BT_DS3_CombatOverview');assert main and main.root_node
subtrees=[unreal.load_asset(AI+'StandardReadable/BT_DS3_'+g[0]) for g in groups];assert all(subtrees)
bb=main.blackboard_asset
assert all(t.blackboard_asset==bb for t in subtrees)
target=next(k for k in bb.get_editor_property('keys') if str(k.get_editor_property('entry_name'))=='TargetActor')
assert target.get_editor_property('key_type').get_editor_property('BaseClass')==unreal.Actor.static_class()

def kids(n):return [c.child_composite or c.child_task for c in n.children]
original_dispatch=kids(kids(source.root_node)[0])[2]
original={c.decorators[0].get_editor_property('int_value'):c for c in original_dispatch.children}
def shape(c):
    n=c.child_composite or c.child_task
    return dict(name=n.get_name(),cls=n.get_class().get_path_name(),
                decorators=[d.get_name() for d in c.decorators],ops=[x.export_text() for x in c.decorator_ops],
                children=[shape(x) for x in n.children] if isinstance(n,unreal.BTCompositeNode) else [])
def config(n):
    # Compare every serialized leaf override represented in the original export.
    # Same class guarantees the same remaining class defaults.
    t=unreal.AssetExportTask();t.object=n;t.filename=str(OUT/'node-check.t3d')
    t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=unreal.ObjectExporterT3D()
    assert unreal.Exporter.run_asset_export_task(t)
    b=Path(t.filename).read_bytes();s=b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    lines=[]
    for line in s.splitlines():
        if line.startswith('   ') and not line.startswith('      ') and '=' in line:
            if not re.match(r'\s*(NodeName|TreeAsset|ParentNode|CachedDescription)=',line):lines.append(line)
    return lines
def leaves(c):
    n=c.child_composite or c.child_task;result=list(c.decorators)
    if isinstance(n,unreal.BTCompositeNode):
        for ch in n.children:result+=leaves(ch)
    else:result.append(n)
    return result
checked=[]
for (_,title,ids),tree in zip(groups,subtrees):
    assert str(tree.root_node.get_editor_property('node_name'))==title
    actual={c.decorators[0].get_editor_property('int_value'):c for c in tree.root_node.children}
    assert set(actual)==set(ids)
    for aid in ids:
        assert shape(actual[aid])==shape(original[aid]), ('Action shape',aid)
        a={n.get_name():n for n in leaves(original[aid])}
        for n in leaves(actual[aid]):assert config(n)==config(a[n.get_name()]), ('Action configuration',aid,n.get_name())
        checked.append(aid)
new_dispatch=kids(kids(main.root_node)[0])[2]
assert [c.get_editor_property('behavior_asset').get_path_name() for c in kids(new_dispatch)]==[s.get_path_name() for s in subtrees]
assert len(kids(kids(main.root_node)[0]))==6

monster='110050 断剑敌人（可读标准版）';states=[];nodes=[];outline=[]
def add(n,parent,priority,depth,category='all',condition='true'):
    identity=n.get_outer().get_name()+'__'+n.get_name();nid='ue_'+identity;sid='source_'+identity
    title=str(n.get_editor_property('node_name'))
    note='UE对象：'+n.get_path_name()
    if isinstance(n,unreal.BTDecorator_Blackboard):
        key=n.get_editor_property('blackboard_key').get_editor_property('selected_key_name')
        note+='；黑板条件：'+str(key)
        if str(key)=='Action':
            aid=n.get_editor_property('int_value');note+='='+str(aid)+'；'+notes[aid]
    typ='选择器' if isinstance(n,unreal.BTComposite_Selector) else '顺序器' if isinstance(n,unreal.BTCompositeNode) or isinstance(n,unreal.BTTask_RunBehavior) else '条件' if isinstance(n,unreal.BTDecorator) else '动作'
    nodes.append(dict(id=nid,name=title,type=typ,parent=parent,priority=priority,category=category,
                      condition='UE_RUNTIME_ONLY' if typ=='条件' else condition,sourceIds=[sid],note=note))
    states.append(dict(id=sid,name=title,originalName=n.get_name(),monster=monster,category=category,
                       trigger=note,priority=priority,entry=note,exit='沿用UE任务完成、失败、中止与超时',
                       mutex='',transitions='',phase='当前UE原型',distance='原脚本单位，UnitScale为移植假设',
                       status='实际资产重新加载校验',raw=note,notes='原脚本编号与权重只作来源说明，分类不改变概率。'))
    outline.append('  '*depth+'- '+title)
    if isinstance(n,unreal.BTTask_RunBehavior):
        target=n.get_editor_property('behavior_asset')
        cat='range' if 'Spacing' in target.get_name() else 'attack'
        add(target.root_node,nid,0,depth+1,cat)
    elif isinstance(n,unreal.BTCompositeNode):
        for i,c in enumerate(n.children):
            child=c.child_composite or c.child_task;p=nid
            if c.decorators:
                p='guards_'+child.get_outer().get_name()+'__'+child.get_name()
                nodes.append(dict(id=p,name='前提与执行：'+str(child.get_editor_property('node_name')),type='顺序器',parent=nid,
                                  priority=100-i,category=category,condition='true',sourceIds=[],note='装饰器附着于该节点；超时不是普通前置判断。'))
                for j,d in enumerate(c.decorators):add(d,p,200-j,depth+1,category)
            add(child,p,100-i if p==nid else 0,depth+1,category)
nodes.extend([
    dict(id='root',name='断剑敌人｜可读标准版',type='顺序器',parent='',priority=0,category='all',condition='true',sourceIds=[],note='真实UE总览和四类子树展开。'),
    dict(id='runtime_guard',name='推演边界：原生任务须在UE验证',type='条件',parent='root',priority=1000,category='all',condition='UE_RUNTIME_ONLY',sourceIds=[],note='有意返回UNKNOWN，避免示例推演误读原生语义。')])
add(main.root_node,'root',0,0)
archive=dict(schemaVersion=2,title='断剑敌人｜可读标准版',monsters=[monster],states=states,trees={monster:nodes},
             log=[dict(at='2026-11-08',name='可读标准版',text='按人类意图拆分总览与四类子树，原11种行动逐项校验。')],
             provenance=dict(asset=main.get_path_name(),simulationSupported=False))
data=P/'ashen-tree/data';data.mkdir(parents=True,exist_ok=True)
for filename in ['断剑敌人-可读标准版.json','断剑敌人-当前UE行为树.json']:
    (data/filename).write_text(json.dumps(archive,ensure_ascii=False,indent=2),encoding='utf-8')
report=dict(passed=True,checked_action_count=len(checked),checked_actions=sorted(checked),
            saved_action_configuration_and_order_unchanged=True,group_calls_verified=True,target_key_typed_as_actor=True,main=main.get_path_name())
(OUT/'reload-verified.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
doc='# 断剑敌人行为树：可读标准版\n\n当前总览：`'+main.get_path_name()+'`。旧树`BT_DS3BrokenSword`保留。\n\n'
doc+='## 先看总览\n\n准备本轮战斗 → 根据局势选择一次行动 → 四类行动入口 → 恢复步行与朝向 → 决定攻击后调整 → 调整距离或结束本轮。双击类别节点打开子树。\n\n'
doc+='## 四类行动\n\n'
for (suffix,title,ids),tree in zip(groups,subtrees):
    doc+='### '+title+'\n\n资产：`'+tree.get_path_name()+'`。\n\n'
    for aid in ids:doc+='- **'+titles[aid]+'**：'+notes[aid]+f' 来源Act{aid:02d}。\n'
    doc+='\n'
doc+='## 如何理解选择规则\n\n'+display['RULES']+'\n\n四类是阅读分组。不会先抽类别再抽动作，也不代表距离外不能选择近身招式；近身攻击仍可先寻路接近。权重经过特例和冷却过滤后才归一化。\n\n'
doc+='## 完整层级\n\n'+'\n'.join(outline)+'\n\n'
doc+='## 边界与验证\n\n新资产的每种行动保持原任务配置、子节点顺序、装饰器及其逻辑。选招任务、攻击后调整任务、伤害与动画资源均沿用当前原型。动画、位移与特殊效果的替代边界见[原复刻说明](断剑敌人行为树复刻.md)。\n\n'
doc+='整理器可导入`ashen-tree/data/断剑敌人-可读标准版.json`。导入前先导出个人编辑记录；通用示例推演不支持原生子树、随机权重和中断，档案有意用UNKNOWN守卫阻止误演。\n'
doc+='\n标准版使用独立`BB_DS3_Standard`，将TargetActor明确为Actor，修复UE正常保存时清空寻路目标的类型校验问题。原黑板保留。控制器同时绑定标准总览与标准黑板；回退需同时恢复两者。\n'
(P/'docs/design/断剑敌人行为树阅读指南.md').write_text(doc,encoding='utf-8')
print('STANDARD_RELOAD_AND_EXPORT_PASSED',report)
