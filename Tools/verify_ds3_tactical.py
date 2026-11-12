"""Read actual tree conditions, compare boundary decisions and recovery rules."""
import unreal,json,math
from pathlib import Path
P=Path(unreal.Paths.project_dir()); OUT=P/'Saved/DS3-Tactical'; OUT.mkdir(parents=True,exist_ok=True)
AI='/Game/Gameplay/AI/DS3BrokenSword/'; T=AI+'Tactical/'
main=unreal.load_asset(T+'BT_断剑怪_历史_战术战斗总览'); decision=unreal.load_asset(T+'BT_断剑怪_历史_战术选招'); recovery=unreal.load_asset(T+'BT_断剑怪_恢复走位规则')
assert main and decision and recovery
ids=[1,2,4,5,6,11,12,13,20,21,54]
def kids(n): return [c.child_composite or c.child_task for c in n.children]
def passes(d,s):
    assert isinstance(d,unreal.BTDecorator_Blackboard),d
    key=str(d.get_editor_property('blackboard_key').get_editor_property('selected_key_name')); x=s[key]
    if isinstance(x,bool): return x==(d.get_editor_property('basic_operation')==unreal.BasicKeyOperation.SET)
    v=d.get_editor_property('float_value' if key.startswith('Tactical') else 'int_value')
    op=str(d.get_editor_property('arithmetic_operation')).split('.')[-1].split(':')[0]
    return {'EQUAL':x==v,'NOT_EQUAL':x!=v,'LESS':x<v,'LESS_OR_EQUAL':x<=v,'GREATER':x>v,'GREATER_OR_EQUAL':x>=v}[op]
def eval_node(n,s):
    if isinstance(n,unreal.BTCompositeNode):
        sequence=isinstance(n,unreal.BTComposite_Sequence)
        for c in n.children:
            ok=all(passes(d,s) for d in c.decorators) and eval_node(c.child_composite or c.child_task,s)
            if sequence and not ok:return False
            if not sequence and ok:return True
        return sequence
    if isinstance(n,unreal.BTTask_RunBehavior): return eval_node(n.behavior_asset.root_node,s)
    cls=n.get_class().get_name()
    if cls=='BTT_SetCandidates_C': s['weights']={i:n.get_editor_property('W'+str(i)) for i in ids}
    elif cls=='BTT_ExcludeCoolingAttack_C': s['weights'][5]=0
    elif cls=='BTT_SetRecovery_C':
        s['AfterAction']=n.get_editor_property('Mode')
        if n.get_editor_property('OverrideDistance'):s['MoveDistance']=n.get_editor_property('Distance')
    elif cls not in ['BTTask_Wait','BTT_ReadSituation_C','BTT_DrawCandidate_C']:raise AssertionError(cls)
    return True
def expected(distance,yaw,role,event,think,hp,cool):
    w={}
    if event==100:w={20:100}
    elif think==110054:w={54:100}
    elif role==1:w={11:60,12:40}
    elif role==2:w={6:20,11:50,12:30} if distance>=5.5 else {11:50,12:30}
    elif distance<=2 and 45<=yaw<=135:w={2:30,5:15,13:55}
    elif distance<=2 and -135<=yaw<=-45:w={1:30,5:15,13:55}
    elif distance<=10 and abs(yaw)>=60:w={13:100}
    elif think==144041 or (think==144040 and hp<=.8):w={20 if distance>=13 else 21:100}
    elif distance>=5.5:
        w={1:15,2:10,5:10,6:45,12:20}
        if think==144040:w.update({20:20,21:10} if distance>=10 else {20:10,21:20})
    elif distance>=1.5:
        w={1:20,2:20,4:15,5:35,12:10}
        if think==144040:w[21]=30
    else:w={1:25,2:15,4:15,5:45}
    if not cool:w[5]=0
    return {i:w.get(i,0) for i in ids}
count=0
for distance in [0,.5,1.499,1.5,2,2.001,5.499,5.5,9.999,10,10.001,12.999,13,15]:
 for yaw in [-180,-135,-60,-45,-44.999,0,44.999,45,60,135,180]:
  for role in [0,1,2]:
   for event,think,hp in [(0,110050,1),(100,110050,1),(0,110054,1),(0,144040,1),(0,144040,.8),(0,144041,1)]:
    for cool in [True,False]:
     s=dict(TacticalDistance=distance,TacticalYaw=yaw,TacticalHealth=hp,TeamRole=role,EventRequest1=event,ThinkParamID=think,Cooldown3003Ready=cool)
     assert eval_node(decision.root_node,s)
     assert s['weights']==expected(distance,yaw,role,event,think,hp,cool),(s,expected(distance,yaw,role,event,think,hp,cool))
     count+=1
recovery_count=0
for distance in [0,.499,.5,1.999,2,3.999,4,5.999,6,6.001,10]:
 for role in [0,1,2]:
  for roll in range(1,101):
   s=dict(TacticalDistance=distance,TeamRole=role,PostChoiceRoll=roll,AfterAction=0,MoveDistance=distance+3)
   assert eval_node(recovery.root_node,s)
   if role in [1,2]: target=2 if distance<=6 else 1; md=8 if distance<=6 else distance+3
   elif distance>=6:target=1 if roll<=25 else 3; md=5.5 if target==3 else distance+3
   else:
    a,b=(30,30) if distance>=4 else (15,25) if distance>=2 else (5,20) if distance>=.5 else (0,15)
    target=1 if roll<=a else 2 if roll<=b else 0; md=distance+3
   assert s['AfterAction']==target and abs(s['MoveDistance']-md)<.001,s
   recovery_count+=1
seen=set(); classes=set(); tree_paths=[]
def inspect(tree):
    if tree.get_path_name() in seen:return
    seen.add(tree.get_path_name()); tree_paths.append(tree.get_path_name())
    assert tree.blackboard_asset==main.blackboard_asset
    def walk(n):
        classes.add(n.get_class().get_name())
        if isinstance(n,unreal.BTTask_RunBehavior):inspect(n.behavior_asset)
        elif isinstance(n,unreal.BTCompositeNode):
            for c in n.children:walk(c.child_composite or c.child_task)
        elif isinstance(n,unreal.BTTask_MoveTo):assert str(n.get_editor_property('blackboard_key').get_editor_property('selected_key_name'))=='TargetActor'
    walk(tree.root_node)
inspect(main)
assert not ({'BTT_DSDecide_C','BTT_DSAfterAttack_C'} & classes)
for name in ([] if globals().get('SKIP_BLUEPRINT_UI',False) else ['BTT_ReadSituation','BTT_SetCandidates','BTT_ExcludeCoolingAttack','BTT_DrawCandidate','BTT_PrepareRecovery','BTT_SetRecovery']):
    bp=unreal.load_asset(T+name); ed=unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(bp))
    assert not ed.list_nodes_with_errors(),name
report=dict(passed=True,decision_boundary_cases=count,recovery_cases=recovery_count,main=main.get_path_name(),tree_paths=tree_paths,legacy_decision_tasks_used=False)
(OUT/'verified.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('TACTICAL_VERIFIED',report)
