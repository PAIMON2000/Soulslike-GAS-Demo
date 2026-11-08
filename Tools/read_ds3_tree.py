"""Read the controller-bound tree into a small standalone, collapsible reader."""
import unreal,json
from pathlib import Path
P=Path(unreal.Paths.project_dir());controller=unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
ed=unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
pins=[p for n in ed.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name())=='BTAsset'];assert len(pins)==1
main=unreal.load_asset(pins[0].get_pin_value());assert isinstance(main,unreal.BehaviorTree)
explain={
'BTT_DSInit_C':'首次执行时记录怪物半径、速度和单位换算；之后跳过初始化。',
'BTT_ReadSituation_C':'测量当前距离、目标相对方向、自身血量与3003冷却，写入共享记录。',
'BTT_SetCandidates_C':'命中这条规则后，使用下面这些候选权重；这一步还没有发动攻击。',
'BTT_ExcludeCoolingAttack_C':'把3003对应招式的权重归零，其他候选保留。',
'BTT_DrawCandidate_C':'按剩余权重抽一次，记下本轮行动；攻击中不再重新抽取。',
'BTT_DSLocomotion_C':'配置走路／跑步、接近距离和转向速度，并朝向目标。',
'BTT_DSAttack_C':'发动这个攻击，等待结束；尚未结束时，后面的步骤等待。',
'BTT_DSComboChoice_C':'为本次连击决定是否追加第三击。',
'BTT_DSRelativeMove_C':'执行侧移、后退、靠近或转身，直到完成、超时或被中止。',
'BTT_PrepareRecovery_C':'清空上一轮走位选择，准备本轮随机值、时长和后退距离。',
'BTT_SetRecovery_C':'记录此分支决定的走位方式，交给后续移动节点执行。',
'BTTask_MoveTo':'寻路接近目标；到达才继续，失败则向上返回失败。',
'BTTask_Wait':'等待指定时间，然后返回成功。'}
titles={1:'连击A',2:'连击B',4:'固定两段',5:'3003冷却攻击',6:'前冲攻击',11:'后退',12:'侧移',13:'转身',20:'特殊20005',21:'特殊20006',54:'变体专用接近'}
def prop(o,k):
 try:return o.get_editor_property(k)
 except:return None
def read(n,stack):
 cls=n.get_class().get_name();d=dict(name=str(n.get_editor_property('node_name')),path=n.get_path_name(),kind='动作',explanation=explain.get(cls,''),children=[],parameters=[])
 if isinstance(n,unreal.BTCompositeNode):
  sequence=isinstance(n,unreal.BTComposite_Sequence)
  d.update(kind='按顺序完成' if sequence else '按优先级尝试',explanation='依次执行；当前步骤完成才进入下一步。某一步失败，则本组失败。' if sequence else '按编号依次尝试；失败才看下一个，成功即结束本组，正在运行则等待。')
  for i,c in enumerate(n.children):
   item=read(c.child_composite or c.child_task,stack);item['order']=i+1
   item['conditions']=[dict(name=str(x.get_editor_property('node_name')),path=x.get_path_name(),kind='持续限制' if isinstance(x,unreal.BTDecorator_TimeLimit) else '条件') for x in c.decorators]
   d['children'].append(item)
 elif isinstance(n,unreal.BTTask_RunBehavior):
  tree=n.behavior_asset;assert tree.get_path_name() not in stack,'Recursive tree not supported by this reader'
  d.update(kind='展开内部步骤',explanation='这里调用另一棵树，下面已直接展开；完成后回到当前层继续。',asset=tree.get_path_name())
  d['children']=[read(tree.root_node,stack+[tree.get_path_name()])]
 if cls=='BTT_SetCandidates_C':
  d['parameters']=[f'{title}：权重 {prop(n,"W"+str(aid)):g}' for aid,title in titles.items() if prop(n,'W'+str(aid))]
 for k,label in [('TurnRate','转向速度（度/秒）'),('BaseRange','接近目标距离（脚本单位）'),('SourceAttackID','攻击编号'),('Mode','移动模式：1侧移/2后退/3靠近/4转身'),('Duration','最长执行秒数')]:
  v=prop(n,k)
  if v is not None:d['parameters'].append(f'{label}：{v}')
 return d
data=dict(controller=controller.get_path_name(),main=main.get_path_name(),root=read(main.root_node,[main.get_path_name()]))
out=P/'ashen-tree';raw=json.dumps(data,ensure_ascii=False,indent=2)
(out/'data/断剑怪-只读树.json').write_text(raw,encoding='utf-8')
html=(P/'Tools/ds3_reader.html').read_text(encoding='utf-8').replace('__TREE_DATA__',raw.replace('</','<\\/'))
(out/'断剑怪-从这里看.html').write_text(html,encoding='utf-8')
print('READ_ONLY_TREE_EXPORTED',data['main'])
