"""Export the current tactical trees as a reading-only archive."""
import unreal,json
from pathlib import Path
P=Path(unreal.Paths.project_dir())
main=unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/Tactical/BT_断剑怪_历史_战术战斗总览')
display=json.loads((P/'Tools/ds3_readable_labels.json').read_text(encoding='utf-8'))
notes={int(k):v for k,v in display['NOTES'].items()}
monster='110050 断剑敌人（树上决策版）';states=[];nodes=[];outline=[]
def add(n,parent,priority,depth,category='all',condition='true'):
    identity=str(len(nodes))+'__'+n.get_outer().get_name()+'__'+n.get_name();nid='ue_'+identity;sid='source_'+identity
    title=str(n.get_editor_property('node_name'))
    note='UE对象：'+n.get_path_name()
    if isinstance(n,unreal.BTDecorator_Blackboard):
        key=n.get_editor_property('blackboard_key').get_editor_property('selected_key_name')
        note+='；黑板条件：'+str(key)
        if str(key)=='Action' and n.get_editor_property('int_value') in notes and n.get_editor_property('arithmetic_operation')==unreal.ArithmeticKeyOperation.EQUAL:
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
                p='guards_'+str(len(nodes))+'__'+child.get_outer().get_name()+'__'+child.get_name()
                nodes.append(dict(id=p,name='前提与执行：'+str(child.get_editor_property('node_name')),type='顺序器',parent=nid,
                                  priority=100-i,category=category,condition='true',sourceIds=[],note='装饰器附着于该节点；超时不是普通前置判断。'))
                for j,d in enumerate(c.decorators):add(d,p,200-j,depth+1,category)
            add(child,p,100-i if p==nid else 0,depth+1,category)
nodes.extend([
    dict(id='root',name='断剑敌人｜树上决策版',type='顺序器',parent='',priority=0,category='all',condition='true',sourceIds=[],note='真实UE决策、恢复与执行子树展开。'),
    dict(id='runtime_guard',name='推演边界：原生任务须在UE验证',type='条件',parent='root',priority=1000,category='all',condition='UE_RUNTIME_ONLY',sourceIds=[],note='有意返回UNKNOWN，避免示例推演误读原生语义。')])
add(main.root_node,'root',0,0)
archive=dict(schemaVersion=2,title='断剑敌人｜树上决策版',monsters=[monster],states=states,trees={monster:nodes},
             log=[dict(at='2026-11-09',name='树上决策版',text='判断规则、冷却过滤和攻击后走位已迁入行为树条件；动作执行保留。')],
             provenance=dict(asset=main.get_path_name(),simulationSupported=False))
data=P/'ashen-tree/data';data.mkdir(parents=True,exist_ok=True)
for filename in ['断剑敌人-树上决策版.json','断剑敌人-可读标准版.json','断剑敌人-当前UE行为树.json']:
    (data/filename).write_text(json.dumps(archive,ensure_ascii=False,indent=2),encoding='utf-8')

assert len({n['id'] for n in nodes})==len(nodes)
(P/'Saved/DS3-Tactical/outline.md').write_text('\n'.join(outline),encoding='utf-8')
print('TACTICAL_ARCHIVE_EXPORTED',len(nodes))
