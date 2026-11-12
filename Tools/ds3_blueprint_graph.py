"""Small editor-only graph builder for the isolated DS3 prototype assets."""
import unreal
AI='/Game/Gameplay/AI/DS3BrokenSword/'
KM='/Script/Engine.KismetMathLibrary.'
BT='/Script/AIModule.BTFunctionLibrary.'
TASK_COMMENTS = {
 'BTT_DSInit': '仅在首次执行时初始化。记录角色胶囊半径与跑步速度。每单位按 100 厘米换算，可在任务上配置。',
 'BTT_DSDecide': '分层版选招任务。每轮只选一次。按普通交战、侧后响应、队伍角色、事件与变体规则设置候选。3003 有独立的 20 秒冷却。ForcedAction 默认是 0，用于测试。',
 'BTT_DSLocomotion': '设置接近目标时的间距、速度和朝向。接近半径扣除角色胶囊半径。距离达到跑步门槛后按概率跑步，更远时强制跑步。步行最多 4 秒，跑步最多 8 秒。',
 'BTT_DSComboChoice': '行动 1、2 在连招开始时只抽一次。25% 打两击，75% 打三击。',
 'BTT_DSAttack': '开始：停止移动，清除 AI 朝向焦点，设置本击动画与攻击编号，再启动攻击能力。成功启动 3003 时记录冷却起点。\n等待：每帧查看 State.Attacking，标签消失后完成任务。\n中止：取消攻击能力，停止移动，然后结束任务。',
 'BTT_DSRelativeMove': '执行侧移、后退、接近或转身。寻路目标每 0.2 秒刷新一次，保持本次选定的移动侧和时长。完成或中止时停止移动。',
 'BTT_DSAfterAttack': '分层版收招任务。普通攻击有 50% 概率调整位置，特殊攻击必定调整，移动行动跳过。调整方式按距离抽取，队伍角色可退到 8 单位或侧移。',
}
bb=unreal.load_asset(AI+'BB_DS3BrokenSword');keys=list(bb.get_editor_property('keys'))
def selector(name):
 i=next(i for i,k in enumerate(keys) if str(k.get_editor_property('entry_name'))==name)
 s=unreal.BlackboardKeySelector();s.set_editor_property('selected_key_name',name);s.set_editor_property('selected_key_id',i);s.set_editor_property('selected_key_type',keys[i].get_editor_property('key_type').get_class());return s
def pin(n,name):
 p=[p for p in n.list_all_pins() if str(p.get_pin_name())==name]
 assert len(p)==1,(n.get_name(),name,[str(x.get_pin_name()) for x in n.list_all_pins()]);return p[0]
def link(a,an,b,bn):assert pin(a,an).try_create_connection(pin(b,bn)),(a.get_name(),an,b.get_name(),bn)
def val(n,name,v):
 p=pin(n,name);ok=p.set_pin_value(str(v));assert ok or p.get_pin_value()==str(v),(name,v,p.get_pin_value())
def seq(a,b,out='then'):link(a,out,b,'execute');return b
def castout(n):return next(str(p.get_pin_name()) for p in n.list_all_pins() if str(p.get_pin_name()).startswith('As'))
class Graph:
 def __init__(self,name,variables,events):
  variables=list(variables)+[(str(k.get_editor_property('entry_name'))+'Key','key',str(k.get_editor_property('entry_name'))) for k in keys]
  self.b=unreal.load_asset(AI+name);assert self.b
  assert self.b.get_path_name().startswith(AI)
  for n,typ,default in variables:
   try:unreal.get_default_object(self.b.generated_class()).get_editor_property(n)
   except:
    pt=unreal.BlueprintEditorLibrary.get_struct_type(unreal.BlackboardKeySelector.static_struct()) if typ=='key' else unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.AnimMontage.static_class()) if typ=='montage' else unreal.BlueprintEditorLibrary.get_basic_type_by_name(typ)
    assert unreal.BlueprintEditorLibrary.add_member_variable(self.b,n,pt),n
   unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(self.b,n,True)
  unreal.BlueprintEditorLibrary.compile_blueprint(self.b)
  unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([self.b])
  self.g=unreal.BlueprintEditorLibrary.find_event_graph(self.b);self.ed=unreal.BlueprintGraphEditor.get_graph_editor(self.g);assert self.ed
  self.ed.remove_nodes([n for n in self.ed.list_all_nodes() if not isinstance(n,unreal.K2Node_Event)])
  self.events={e:self.ed.find_event_node(e) or unreal.BlueprintEditorLibrary.add_event_override(self.b,e,unreal.IntPoint(0,i*1200)) for i,e in enumerate(events)}
  self.variables=variables;self.i=0
 def pos(self,n):
  assert n;n.set_node_pos(unreal.IntPoint(300+(self.i%8)*350,(self.i//8)*260));self.i+=1;return n
 def fn(self,path):return self.pos(self.ed.add_call_function_node(path))
 def get(self,n,cls=''):return self.pos(self.ed.add_get_member_variable_node(n,cls))
 def set(self,n,cls=''):return self.pos(self.ed.add_set_member_variable_node(n,cls))
 def branch(self,cond=None):
  n=self.pos(self.ed.add_branch_node())
  if cond:link(cond[0],cond[1],n,'Condition')
  return n
 def cast(self,n):return self.pos(self.ed.create_node_from_name(next(t for t in self.ed.list_available_nodes([]) if t.endswith('|CastTo'+n)),unreal.Vector2D(0,0),[]))
 def calc(self,name,a,ap='ReturnValue',b=None,bp='ReturnValue',constant=None):
  n=self.fn(KM+name);link(a,ap,n,'A')
  if b is not None:link(b,bp,n,'B')
  elif constant is not None:val(n,'B',constant)
  return n
 def bbget(self,typ,name):
  n=self.fn(BT+'GetBlackboardValueAs'+typ);link(self.get(name+'Key'),name+'Key',n,'Key');return n
 def bbset(self,typ,name,previous,value=None,source=None,out='then'):
  n=self.fn(BT+'SetBlackboardValueAs'+typ);link(self.get(name+'Key'),name+'Key',n,'Key');seq(previous,n,out)
  if source:link(source[0],source[1],n,'Value')
  elif value is not None:val(n,'Value',str(value).lower() if isinstance(value,bool) else value)
  return n
 def store(self,name,previous,value=None,source=None,out='then'):
  n=self.set(name);seq(previous,n,out)
  if source:link(source[0],source[1],n,name)
  elif value is not None:val(n,name,str(value).lower() if isinstance(value,bool) else value)
  return n
 def finish(self,text=None):
  if text is None:text=TASK_COMMENTS[self.b.get_name()]
  self.ed.add_comment_node(text,unreal.Vector2D(0,-250),unreal.Vector2D(2700,160));unreal.BlueprintEditorLibrary.compile_blueprint(self.b)
  errors=self.ed.list_nodes_with_errors();assert not errors,str(errors)
  cdo=unreal.get_default_object(self.b.generated_class())
  for n,typ,default in self.variables:cdo.set_editor_property(n,selector(default) if typ=='key' else default)
  assert unreal.EditorAssetLibrary.save_loaded_asset(self.b,False)
  print('DS3_BP',self.b.get_name(),len(self.ed.list_all_nodes()))
def location(g,node,p):
 n=g.fn('/Script/Engine.Actor.K2_GetActorLocation');link(node,p,n,'self');return n
def distance(g,e):
 target=g.bbget('Actor','TargetActor');pl=location(g,e,'ControlledPawn');tl=location(g,target,'ReturnValue')
 d=g.fn(KM+'Vector_Distance2D');link(pl,'ReturnValue',d,'V1');link(tl,'ReturnValue',d,'V2');return d,pl,tl,target
def now(g):return g.fn('/Script/Engine.GameplayStatics.GetTimeSeconds')
def finish(g,previous,success=True,out='then',abort=False):
 n=g.fn('/Script/AIModule.BTTask_BlueprintBase.'+('FinishAbort' if abort else 'FinishExecute'));seq(previous,n,out)
 if not abort:val(n,'bSuccess',str(success).lower())
 return n
def compare(g,op,node,p='ReturnValue',constant=None,other=None,otherpin='ReturnValue'):
 return g.calc(op,node,p,other,otherpin,constant)
def stop(g,e,previous,out='then'):
 n=g.fn('/Script/Engine.Controller.StopMovement');link(e,'OwnerController',n,'self');seq(previous,n,out);return n
def movement(g,e,previous):
 m=g.fn('/Script/Engine.Pawn.GetMovementComponent');link(e,'ControlledPawn',m,'self');c=g.cast('CharacterMovementComponent');link(m,'ReturnValue',c,'Object');seq(previous,c);return c,castout(c)
def flag(g,prop,obj,op,previous,value):
 n=g.set(prop,'/Script/Engine.CharacterMovementComponent');link(obj,op,n,'self');val(n,prop,str(value).lower());seq(previous,n);return n
