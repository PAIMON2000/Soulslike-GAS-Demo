"""PIE test without ForcedAction: actual weighted draw and recovery subtrees."""
import unreal,json,time,math
from pathlib import Path
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(); assert w
d=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/Gameplay/Characters/BP_Dummy.BP_Dummy_C'))[0]
p=unreal.GameplayStatics.get_player_character(w,0); c=d.get_controller()
brain=c.get_component_by_class(unreal.BrainComponent); bb=c.get_component_by_class(unreal.BlackboardComponent)
base=d.get_actor_location(); p.set_actor_enable_collision(False)
T='/Game/Gameplay/AI/DS3BrokenSword/Tactical/'
trees={name:unreal.load_asset(T+name) for name in ['BT_断剑怪_历史_战术选招','BT_断剑怪_攻击后恢复']}
cases=[
 ('draw_mid', 'BT_断剑怪_历史_战术选招',300,0,0,110050,False,{1:.20,2:.20,4:.15,5:.35,12:.10}),
 ('draw_cooldown','BT_断剑怪_历史_战术选招',300,0,0,110050,True,{1:20/65,2:20/65,4:15/65,12:10/65}),
 ('event_single_candidate','BT_断剑怪_历史_战术选招',300,0,100,110050,False,{20:1}),
 ('variant_single_candidate','BT_断剑怪_历史_战术选招',300,0,0,110054,False,{54:1}),
 ('recovery_normal_mid','BT_断剑怪_攻击后恢复',300,0,0,1,False,{0:.875,1:.075,2:.05}),
 ('recovery_special_far','BT_断剑怪_攻击后恢复',700,0,0,20,False,{1:.25,3:.75}),
 ('recovery_movement_skips','BT_断剑怪_攻击后恢复',300,0,0,12,False,{0:1}),
 ('recovery_team_special','BT_断剑怪_攻击后恢复',300,1,0,20,False,{2:1})]
cases=cases[:4]  # Recovery is tested separately after its subtree completes.
phase=0; samples=0; counts={}; wall=time.monotonic(); pending=False; started=0
report={'passed':False,'tests':[]}; out=Path(unreal.Paths.project_dir())/'Saved/DS3-Tactical/sampling.json'
def begin():
 global started
 name,tree,distance,role,event,aid,cool,expected=cases[phase]
 brain.stop_logic('Sampling one tactical decision'); d.cancel_attack(); c.stop_movement()
 d.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
 d.set_actor_location(base,False,True); d.set_actor_rotation(unreal.Rotator(0,0,0),True)
 p.set_actor_location(base+unreal.Vector(distance,0,0),False,True)
 bb.set_value_as_object('TargetActor',p); bb.set_value_as_float('UnitScale',100)
 for k,v in {'TeamRole':role,'EventRequest1':event,'ThinkParamID':aid if tree=='BT_断剑怪_历史_战术选招' else 110050,'Action':aid if tree=='BT_断剑怪_攻击后恢复' else 0,'ForcedAction':0,'DecisionCount':0,'PostCycles':0,'AfterAction':-1}.items():bb.set_value_as_int(k,v)
 bb.set_value_as_float('Last3003Time',unreal.GameplayStatics.get_time_seconds(w) if cool else -10000)
 assert c.run_behavior_tree(trees[tree]); brain.restart_logic(); started=time.monotonic()
def finish(error=None):
 unreal.unregister_slate_post_tick_callback(handle); brain.stop_logic('Sampling complete'); c.stop_movement(); d.cancel_attack()
 report['error']=error;report['passed']=not error and all(t['passed'] for t in report['tests'])
 out.write_text(json.dumps(report,indent=2),encoding='utf-8');print('TACTICAL_SAMPLING',report['passed'])
def tick(dt):
 global phase,samples,counts
 try:
  name,tree,distance,role,event,aid,cool,expected=cases[phase]
  ready=bb.get_value_as_int('DecisionCount' if tree=='BT_断剑怪_历史_战术选招' else 'PostCycles')>0
  if ready:
   actual=bb.get_value_as_int('Action' if tree=='BT_断剑怪_历史_战术选招' else 'AfterAction')
   counts[actual]=counts.get(actual,0)+1;samples+=1
   if samples>=120:
    # Broad statistical check plus strict exclusion of ineligible actions.
    passed=set(counts)<=set(expected) and all(abs(counts.get(k,0)/samples-v)<.16 for k,v in expected.items())
    report['tests'].append(dict(name=name,passed=passed,samples=samples,counts=counts,expected=expected))
    phase+=1;samples=0;counts={}
    if phase==len(cases):finish();return
   begin()
  elif time.monotonic()-started>3:finish('No decision completed');return
  if time.monotonic()-wall>110:finish('Sampling timeout')
 except Exception as ex:finish(repr(ex))
begin(); handle=unreal.register_slate_post_tick_callback(tick)
print('TACTICAL_SAMPLING_STARTED')
