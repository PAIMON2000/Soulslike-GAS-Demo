"""Build the DS3 110050 logical prototype as inspectable Blueprint BT tasks.
Only task execution waits/updates movement; action selection never runs on Tick.
"""
import unreal,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import ds3_blueprint_graph,importlib
importlib.reload(ds3_blueprint_graph)
from ds3_blueprint_graph import *
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()

# One-time blackboard setup, preserving debug/configuration overrides on tree restart.
g=Graph('BTT_DSInit',[('UnitScale','real',100.0)],['ReceiveExecuteAI']);e=g.events['ReceiveExecuteAI']
ready=g.bbget('Bool','Initialized');b=g.branch((ready,'ReturnValue'));seq(e,b);finish(g,b)
last=g.bbset('Float','Last3003Time',b,-10000,out='else');scale=g.bbset('Float','UnitScale',last,source=(g.get('UnitScale'),'UnitScale'))
mc,mcp=movement(g,e,scale);speed=g.get('MaxWalkSpeed','/Script/Engine.CharacterMovementComponent');link(mc,mcp,speed,'self');cache=g.bbset('Float','RunSpeed',mc,source=(speed,'MaxWalkSpeed'))
cast=g.cast('Character');link(e,'ControlledPawn',cast,'Object');seq(cache,cast)
capsule=g.get('CapsuleComponent','/Script/Engine.Character');link(cast,castout(cast),capsule,'self');radius=g.fn('/Script/Engine.CapsuleComponent.GetScaledCapsuleRadius');link(capsule,'CapsuleComponent',radius,'self')
r=g.bbset('Float','RadiusCm',cast,source=(radius,'ReturnValue'));mark=g.bbset('Bool','Initialized',r,True);finish(g,mark)
g.finish()

# Weighted choice. All random values are stored once before reuse.
ids=[1,2,4,5,6,11,12,13,20,21]
variables=[('W'+str(i),'real',0.0) for i in ids]+[('Distance','real',0.0),('Yaw','real',0.0),('Roll','real',0.0)]
g=Graph('BTT_DSDecide',variables,['ReceiveExecuteAI']);e=g.events['ReceiveExecuteAI'];tail=e
for i in ids:tail=g.store('W'+str(i),tail,0)
d,pl,tl,target=distance(g,e);units=g.calc('Divide_DoubleDouble',d,b=g.bbget('Float','UnitScale'));tail=g.store('Distance',tail,source=(units,'ReturnValue'))
look=g.fn(KM+'FindLookAtRotation');link(pl,'ReturnValue',look,'Start');link(tl,'ReturnValue',look,'Target');rotation=g.fn('/Script/Engine.Actor.K2_GetActorRotation');link(e,'ControlledPawn',rotation,'self');delta=g.calc('NormalizedDeltaRotator',look,b=rotation);br=g.fn(KM+'BreakRotator');link(delta,'ReturnValue',br,'InRot');tail=g.store('Yaw',tail,source=(br,'Yaw'))
counter=g.calc('Add_IntInt',g.bbget('Int','DecisionCount'),constant=1);tail=g.bbset('Int','DecisionCount',tail,source=(counter,'ReturnValue'))
ends=[]
def weights(previous,values,out='then'):
 t=previous
 for index,value in values.items():t=g.store('W'+str(index),t,value,out=out);out='then'
 ends.append(t);return t
def eqkey(name,value):return g.calc('EqualEqual_IntInt',g.bbget('Int',name),constant=value)
def condition(previous,cond,out='else'):
 b=g.branch((cond,'ReturnValue'));seq(previous,b,out);return b
event=condition(tail,eqkey('EventRequest1',100),'then');weights(event,{20:100})
special=condition(event,eqkey('ThinkParamID',110054))
# 110054 is an approach-only variant; route to its own visible branch.
specialset=g.bbset('Int','Action',special,54);finish(g,specialset)
role1=condition(special,eqkey('TeamRole',1));weights(role1,{11:60,12:40})
role2=condition(role1,eqkey('TeamRole',2));farrole=g.calc('GreaterEqual_DoubleDouble',g.get('Distance'),'Distance',constant=5.5);r=g.branch((farrole,'ReturnValue'));seq(role2,r);weights(r,{6:20,11:50,12:30});weights(r,{11:50,12:30},'else')
def angular(center,width,limit):
 off=g.calc('Subtract_DoubleDouble',g.get('Yaw'),'Yaw',constant=center);norm=g.fn(KM+'NormalizeAxis');link(off,'ReturnValue',norm,'Angle');ab=g.fn(KM+'Abs');link(norm,'ReturnValue',ab,'A');angle=g.calc('LessEqual_DoubleDouble',ab,constant=width/2);near=g.calc('LessEqual_DoubleDouble',g.get('Distance'),'Distance',constant=limit);return g.calc('BooleanAND',angle,b=near)
right=condition(role2,angular(90,90,2));weights(right,{2:30,5:15,13:55})
left=condition(right,angular(-90,90,2));weights(left,{1:30,5:15,13:55})
back=condition(left,angular(180,240,10));weights(back,{13:100})
variant=eqkey('ThinkParamID',144041);v0=eqkey('ThinkParamID',144040)
cast=g.cast('BaseCharacter');link(e,'ControlledPawn',cast,'Object');seq(back,cast,'else');hp=g.fn('/Script/ProjectUnreal.BaseCharacter.GetHealthPercent');link(cast,castout(cast),hp,'self');low=g.calc('LessEqual_DoubleDouble',hp,constant=.8);v1=g.calc('BooleanAND',v0,b=low);v2=g.calc('BooleanOR',variant,b=v1);v=g.branch((v2,'ReturnValue'));seq(cast,v)
vf=g.calc('GreaterEqual_DoubleDouble',g.get('Distance'),'Distance',constant=13);vb=g.branch((vf,'ReturnValue'));seq(v,vb);weights(vb,{20:100});weights(vb,{21:100},'else')
far=g.calc('GreaterEqual_DoubleDouble',g.get('Distance'),'Distance',constant=5.5);fb=g.branch((far,'ReturnValue'));seq(v,fb,'else');weights(fb,{1:15,2:10,5:10,6:45,12:20})
mid=g.calc('GreaterEqual_DoubleDouble',g.get('Distance'),'Distance',constant=1.5);mb=g.branch((mid,'ReturnValue'));seq(fb,mb,'else');weights(mb,{1:20,2:20,4:15,5:35,12:10});weights(mb,{1:25,2:15,4:15,5:45},'else')
# 144040 above the HP trigger retains nonzero special weights in ordinary ranges.
ordinary=ends[-3:];ends=ends[:-3]
for index,endpoint in enumerate(ordinary):
 vb=g.branch((eqkey('ThinkParamID',144040),'ReturnValue'));seq(endpoint,vb);ends.append((vb,'else'))
 if index==0:
  z=g.calc('GreaterEqual_DoubleDouble',g.get('Distance'),'Distance',constant=10);zb=g.branch((z,'ReturnValue'));seq(vb,zb);weights(zb,{20:20,21:10});weights(zb,{20:10,21:20},'else')
 elif index==1:weights(vb,{21:30})
 else:ends.append(vb)

cool=g.calc('Subtract_DoubleDouble',now(g),b=g.bbget('Float','Last3003Time'));coolok=g.calc('Greater_DoubleDouble',cool,constant=20)
cb=g.branch((coolok,'ReturnValue'))
for endpoint in ends:
 if isinstance(endpoint,tuple):seq(endpoint[0],cb,endpoint[1])
 else:seq(endpoint,cb)
zero=g.store('W5',cb,0,out='else')
sample=g.fn(KM+'RandomFloatInRange');val(sample,'Min',0)
total=None
for i in ids:
 if total is None:total=g.get('W'+str(i));totalpin='W'+str(i)
 else:total=g.calc('Add_DoubleDouble',total,totalpin,g.get('W'+str(i)),'W'+str(i));totalpin='ReturnValue'
link(total,totalpin,sample,'Max');roll=g.store('Roll',cb,source=(sample,'ReturnValue'));seq(zero,roll)
forced=g.bbget('Int','ForcedAction');forceok=g.calc('Greater_IntInt',forced,constant=0);force=g.branch((forceok,'ReturnValue'));seq(roll,force);forcedset=g.bbset('Int','Action',force,source=(forced,'ReturnValue'));finish(g,forcedset)
previous=force;out='else';cumulative=None
for i in ids:
 w=g.get('W'+str(i));cumulative=w if cumulative is None else g.calc('Add_DoubleDouble',cumulative,cp,w,'W'+str(i));cp='W'+str(i) if cumulative==w else 'ReturnValue'
 less=g.calc('Less_DoubleDouble',g.get('Roll'),'Roll',cumulative,cp);choice=g.branch((less,'ReturnValue'));seq(previous,choice,out)
 selected=g.bbset('Int','Action',choice,i);finish(g,selected);previous=choice;out='else'
fallback=g.bbset('Int','Action',previous,13,out='else');finish(g,fallback)
g.finish()

# Configure native locomotion once at action entry; native CharacterMovement turns.
variables=[('BaseRange','real',2.5),('RunOffset','real',.7),('RunChance','int',100),('ForceRunOffset','real',2.5),('WalkSpeed','real',120.0),('TurnRate','real',360.0),('AlwaysWalk','bool',False)]
g=Graph('BTT_DSLocomotion',variables,['ReceiveExecuteAI']);e=g.events['ReceiveExecuteAI'];d,pl,tl,target=distance(g,e)
scale=g.bbget('Float','UnitScale');r=g.calc('Multiply_DoubleDouble',g.get('BaseRange'),'BaseRange',scale);r=g.calc('Subtract_DoubleDouble',r,b=g.bbget('Float','RadiusCm'));tail=g.bbset('Float','ApproachRadius',e,source=(r,'ReturnValue'))
runstart=g.calc('Add_DoubleDouble',g.get('BaseRange'),'BaseRange',g.get('RunOffset'),'RunOffset');runstart=g.calc('Multiply_DoubleDouble',runstart,b=scale);runstart=g.calc('Subtract_DoubleDouble',runstart,b=g.bbget('Float','RadiusCm'));far=g.calc('GreaterEqual_DoubleDouble',d,b=runstart)
rng=g.fn(KM+'RandomIntegerInRange');val(rng,'Min',1);val(rng,'Max',100);chance=g.calc('LessEqual_IntInt',rng,b=g.get('RunChance'),bp='RunChance');far=g.calc('BooleanAND',far,b=chance)
forced=g.calc('Add_DoubleDouble',g.get('BaseRange'),'BaseRange',g.get('ForceRunOffset'),'ForceRunOffset');forced=g.calc('Multiply_DoubleDouble',forced,b=scale);forced=g.calc('Subtract_DoubleDouble',forced,b=g.bbget('Float','RadiusCm'));forced=g.calc('GreaterEqual_DoubleDouble',d,b=forced);far=g.calc('BooleanOR',far,b=forced)
notwalk=g.fn(KM+'Not_PreBool');link(g.get('AlwaysWalk'),'AlwaysWalk',notwalk,'A');run=g.calc('BooleanAND',far,b=notwalk)
mc,mcp=movement(g,e,tail);tail=flag(g,'bOrientRotationToMovement',mc,mcp,mc,False);tail=flag(g,'bUseControllerDesiredRotation',mc,mcp,tail,True)
yaw=g.set('bUseControllerRotationYaw','/Script/Engine.Pawn');link(e,'ControlledPawn',yaw,'self');val(yaw,'bUseControllerRotationYaw','false');seq(tail,yaw)
rot=g.fn(KM+'MakeRotator');link(g.get('TurnRate'),'TurnRate',rot,'Yaw');setrot=g.set('RotationRate','/Script/Engine.CharacterMovementComponent');link(mc,mcp,setrot,'self');link(rot,'ReturnValue',setrot,'RotationRate');seq(yaw,setrot)
branch=g.branch((run,'ReturnValue'));seq(setrot,branch)
for output,source,sp,life in [('then',g.bbget('Float','RunSpeed'),'ReturnValue',8),('else',g.get('WalkSpeed'),'WalkSpeed',4)]:
 n=g.set('MaxWalkSpeed','/Script/Engine.CharacterMovementComponent');link(mc,mcp,n,'self');link(source,sp,n,'MaxWalkSpeed');seq(branch,n,output);t=g.bbset('Float','ApproachLife',n,life)
 focus=g.fn('/Script/AIModule.AIController.K2_SetFocus');link(e,'OwnerController',focus,'self');link(target,'ReturnValue',focus,'NewFocus');seq(t,focus);finish(g,focus)
g.finish()

# Combo length sampled once and retained until sequence finishes.
g=Graph('BTT_DSComboChoice',[],['ReceiveExecuteAI']);e=g.events['ReceiveExecuteAI'];rng=g.fn(KM+'RandomIntegerInRange');val(rng,'Min',1);val(rng,'Max',100);third=g.calc('Greater_IntInt',rng,constant=25);s=g.bbset('Bool','ThirdHit',e,source=(third,'ReturnValue'));finish(g,s);g.finish()

# Committed strike using a fresh montage mapping; no global cooldown or extra range gate.
g=Graph('BTT_DSAttack',[('Montage','montage',unreal.load_asset('/Game/Gameplay/Anims/Enemy/AM_EnemyAttack')),('SourceAttackID','int',3000),('Started','bool',False)],['ReceiveExecuteAI','ReceiveTickAI','ReceiveAbortAI'])
e=g.events['ReceiveExecuteAI'];tick=g.events['ReceiveTickAI'];abort=g.events['ReceiveAbortAI'];tail=g.store('Started',e,False);tail=stop(g,e,tail);mc,mcp=movement(g,e,tail);tail=flag(g,'bUseControllerDesiredRotation',mc,mcp,mc,False)
clear=g.fn('/Script/AIModule.AIController.K2_ClearFocus');link(e,'OwnerController',clear,'self');seq(tail,clear);cast=g.cast('BP_Dummy');link(e,'ControlledPawn',cast,'Object');seq(clear,cast)
montage=g.set('DS3AttackMontage','/Game/Gameplay/Characters/BP_Dummy.BP_Dummy_C');link(cast,castout(cast),montage,'self');link(g.get('Montage'),'Montage',montage,'DS3AttackMontage');seq(cast,montage)
aid=g.bbset('Int','AttackID',montage,source=(g.get('SourceAttackID'),'SourceAttackID'))
asc=g.fn('/Script/GameplayAbilities.AbilitySystemBlueprintLibrary.GetAbilitySystemComponent');link(e,'ControlledPawn',asc,'Actor');activate=g.fn('/Script/GameplayAbilities.AbilitySystemComponent.TryActivateAbilityByClass');link(asc,'ReturnValue',activate,'self');val(activate,'InAbilityToActivate','/Game/Gameplay/GAS/Abilities/GA_DS3BrokenSwordAttack.GA_DS3BrokenSwordAttack_C');seq(aid,activate)
ok=g.branch((activate,'ReturnValue'));seq(activate,ok);mark=g.store('Started',ok,True);idmatch=g.calc('EqualEqual_IntInt',g.get('SourceAttackID'),'SourceAttackID',constant=3003);special=g.branch((idmatch,'ReturnValue'));seq(mark,special);g.bbset('Float','Last3003Time',special,source=(now(g),'ReturnValue'));finish(g,ok,False,'else');finish(g,cast,False,'CastFailed')
asc2=g.fn('/Script/GameplayAbilities.AbilitySystemBlueprintLibrary.GetAbilitySystemComponent');link(tick,'ControlledPawn',asc2,'Actor');tags=g.fn('/Script/GameplayAbilities.AbilitySystemComponent.GetGameplayTagCount');link(asc2,'ReturnValue',tags,'self');val(tags,'GameplayTag','(TagName="State.Attacking")');zero=g.calc('EqualEqual_IntInt',tags,constant=0);started=g.branch((g.get('Started'),'Started'));seq(tick,started);done=g.branch((zero,'ReturnValue'));seq(started,done);finish(g,done)
cast=g.cast('BaseCharacter');link(abort,'ControlledPawn',cast,'Object');seq(abort,cast);cancel=g.fn('/Script/ProjectUnreal.BaseCharacter.CancelAttack');link(cast,castout(cast),cancel,'self');seq(cast,cancel);tail=stop(g,abort,cancel);finish(g,tail,abort=True);finish(g,cast,out='CastFailed',abort=True)
g.finish()
print('DS3_CORE_TASKS_READY')
