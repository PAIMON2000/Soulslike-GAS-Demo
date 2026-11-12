"""PIE regression against actual tactical tree and blackboard, including aborts."""
import unreal,json,math,time,re
from pathlib import Path
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
d=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/Gameplay/Characters/BP_Dummy.BP_Dummy_C'))[0]
p=unreal.GameplayStatics.get_player_character(w,0);assert p
c=d.get_controller();brain=c.get_component_by_class(unreal.BrainComponent);bb=c.get_component_by_class(unreal.BlackboardComponent)
dm=d.get_component_by_class(unreal.CharacterMovementComponent);pm=p.get_component_by_class(unreal.CharacterMovementComponent);asc=d.get_component_by_class(unreal.AbilitySystemComponent)
tag=unreal.GameplayTag();tag.import_text('(TagName="State.Attacking")')
p.set_actor_enable_collision(False)
base=d.get_actor_location();phase=0;start=0;wall=time.monotonic();priorid=0;stopped=False
assert c.get_class().get_name()=='BP_EnemyAIController_C'
report={'tests':[],'samples':[],'complete':False,'tree':str(brain.get_class().get_name())}
compact=globals().get('COMPACT_RUN',False)
planner=compact or globals().get('PLANNER_RUN',False)
folder='DS3-Compact' if compact else 'DS3-Planner' if planner else 'DS3-Tactical'
out=Path(unreal.Paths.project_dir())/'Saved'/folder/'runtime.json'
runtime_tree=json.loads(out.with_name('build.json').read_text(encoding='utf-8'))['main'].split('.')[-1] if planner else 'BT_断剑怪_历史_战术战斗总览'
weight_cases=[
 ('far',800,0,0,0,110050,False,{1:15,2:10,4:0,5:10,6:45,12:20}),
 ('mid',300,0,0,0,110050,False,{1:20,2:20,4:15,5:35,6:0,12:10}),
 ('near',100,0,0,0,110050,False,{1:25,2:15,4:15,5:45,6:0,12:0}),
 ('3003_cooldown',300,0,0,0,110050,True,{1:20,2:20,4:15,5:0,6:0,12:10}),
 ('right',150,90,0,0,110050,False,{1:0,2:30,5:15,13:55}),
 ('behind',300,180,0,0,110050,False,{1:0,5:0,13:100}),
 ('spectator',300,0,1,0,110050,False,{11:60,12:40}),
 ('encircle',800,0,2,0,110050,False,{6:20,11:50,12:30}),
 ('event',300,0,0,100,110050,False,{20:100}),
 ('special144041',1500,0,0,0,144041,False,{20:100}),
 ('special144040_weights',800,0,0,0,144040,False,{20:10,21:20,6:45})]
weight_cases += [('left',150,-90,0,0,110050,False,{1:30,2:0,5:15,13:55}), ('variant_approach',300,0,0,0,110054,False,{54:100,1:0,13:0}), ('encircle_near',300,0,2,0,110050,False,{6:0,11:50,12:30})]
if compact:
 weight_cases=[case for case in weight_cases if case[0] in {'far','mid','near','3003_cooldown','right','behind','left'}]
N=len(weight_cases)
def now():return unreal.GameplayStatics.get_time_seconds(w)
def begin(i):
 global start,priorid,stopped
 brain.stop_logic('Prepare DS3 test');d.cancel_attack();c.stop_movement();dm.stop_movement_immediately();pm.stop_movement_immediately()
 d.set_actor_location(base,False,True);d.set_actor_rotation(unreal.Rotator(0,0,0),True)
 bb.set_value_as_object('TargetActor',p);bb.set_value_as_int('TeamRole',0);bb.set_value_as_int('EventRequest1',0);bb.set_value_as_int('ThinkParamID',110050);bb.set_value_as_int('DecisionCount',0);bb.set_value_as_int('AttackID',0);bb.set_value_as_float('Last3003Time',-10000)
 priorid=0;stopped=False;start=now()
 if i<N:
  name,distance,angle,role,event,think,cool,weights=weight_cases[i];bb.set_value_as_int('ForcedAction',13);bb.set_value_as_int('TeamRole',role);bb.set_value_as_int('EventRequest1',event);bb.set_value_as_int('ThinkParamID',think);bb.set_value_as_float('Last3003Time',start if cool else -10000)
 else:
  distance={N:500,N+1:450,N+2:200,N+3:1000,N+4:300,N+5:300,N+6:300}[i];angle=0;bb.set_value_as_int('ForcedAction',{N:1,N+1:12,N+2:11,N+3:6,N+4:1,N+5:12,N+6:999}[i])
  if compact and i==N+2:angle=180;bb.set_value_as_int('ForcedAction',13)
  if i==N+6 and not compact:bb.set_value_as_int('EventRequest1',100)
 p.set_actor_location(base+unreal.Vector(math.cos(math.radians(angle))*distance,math.sin(math.radians(angle))*distance,0),False,True)
 brain.restart_logic()
def finish(reason,exception=None):
 unreal.unregister_slate_post_tick_callback(handle);report['complete']=True;report['reason']=reason;report['exception']=exception;report['passed']=reason=='finished' and all(x['passed'] for x in report['tests']);out.write_text(json.dumps(report,indent=2),encoding='utf-8');print('DS3_RUNTIME',reason,report['passed'])
def advance(test):
 global phase
 report['tests'].append(test);phase+=1
 if phase>N+(6 if planner else 5):finish('finished')
 else:begin(phase)
def tick(dt):
 global phase,priorid,stopped
 try:
  n=now();elapsed=n-start;distance=d.get_distance_to(p);loc=d.get_actor_location();active=asc.get_gameplay_tag_count(tag)>0;aid=bb.get_value_as_int('AttackID');decisions=bb.get_value_as_int('DecisionCount')
  sample={'phase':phase,'time':elapsed,'distance':distance,'x':loc.x-base.x,'y':loc.y-base.y,'speed':d.get_velocity().length(),'active':active,'attack':aid,'decisions':decisions,'last3003':bb.get_value_as_float('Last3003Time')}
  if phase==N+6:
   sample['matched_rule']=bb.get_value_as_float('Weight1')==20 if compact else bb.get_value_as_float('Weight20')==100 and bb.get_value_as_float('Weight1')==0
  report['samples'].append(sample)
  if phase<N:
   if decisions>=1:
    expected=weight_cases[phase][-1];actual={i:bb.get_value_as_float('Weight'+str(i)) for i in expected}
    advance({'name':'weights_'+weight_cases[phase][0],'passed':all(abs(actual[i]-expected[i])<.01 for i in expected),'expected':expected,'actual':actual,'runtime_tree':runtime_tree})
   elif elapsed>3:finish('decision_timeout')
   return
  samples=[s for s in report['samples'] if s['phase']==phase]
  if phase==N:
   ids=[]
   for s in samples:
    if s['attack'] and (not ids or ids[-1]!=s['attack']):ids.append(s['attack'])
   if (len(ids)>=2 and not active and elapsed>4) or elapsed>8:
    first=[s for s in samples if s['attack']==3000]
    advance({'name':'approach_then_committed_combo','passed':ids[:2]==[3000,3001] and max(s['decisions'] for s in first)==1 and min(s['distance'] for s in first)<230,'attack_ids':ids,'first_attack_min_distance':min([s['distance'] for s in first] or [99999]),'max_speed':max(s['speed'] for s in samples)})
  elif phase==N+1 and elapsed>1.7:
   advance({'name':'sideway_moves_and_holds_distance','passed':max(abs(s['y']) for s in samples)>40 and max(abs(s['distance']-450) for s in samples)<100,'lateral':max(abs(s['y']) for s in samples),'distance_min':min(s['distance'] for s in samples),'distance_max':max(s['distance'] for s in samples)})
  elif phase==N+2 and elapsed>2:
   if compact:
    yaw=abs(d.get_actor_rotation().yaw)
    advance({'name':'turn_to_player_behind','passed':yaw>=155,'yaw':yaw})
   else:advance({'name':'retreat_is_executed','passed':distance>360 and max(s['speed'] for s in samples)>80,'distance':distance})
  elif phase==N+3:
   if active and elapsed>.4 and not stopped:
    report['long_start']={'distance':distance,'time':elapsed};stopped=True
   if stopped and not active:
    advance({'name':'long_action_uses_distinct_approach_and_advance','passed':report['long_start']['distance']>500 and min(s['distance'] for s in samples)<250,'start':report['long_start'],'min_distance':min(s['distance'] for s in samples)})
   elif elapsed>8:finish('long_attack_timeout')
  elif phase==N+4:
   if active and not stopped:brain.stop_logic('Verify abort cleanup');stopped=True;report['stop_time']=n
   if stopped and n-report['stop_time']>.5:advance({'name':'stop_tree_cancels_attack_and_movement','passed':not active and d.get_velocity().length()<1,'active':active,'speed':d.get_velocity().length()})
   elif elapsed>5:finish('stop_test_timeout')
  elif phase==N+5:
   if elapsed>.4 and not stopped:bb.set_value_as_object('TargetActor',None);stopped=True
   if elapsed>1:advance({'name':'invalid_target_cancels_navigation','passed':d.get_velocity().length()<1,'speed':d.get_velocity().length()})
  elif phase==N+6 and elapsed>.7:
   observed=[s for s in samples if s['decisions']>0]
   advance({'name':'failed_action_ends_round_without_trying_lower_rule',
            'passed':decisions>=2 and bool(observed) and all(s['matched_rule'] and not s['attack'] for s in observed),
            'rounds':decisions,'samples':len(observed)})
  if time.monotonic()-wall>85:finish('wall_timeout')
 except Exception as ex:finish('exception',repr(ex))
begin(0);handle=unreal.register_slate_post_tick_callback(tick)
print('DS3_RUNTIME_STARTED')
