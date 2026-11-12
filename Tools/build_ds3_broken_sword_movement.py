"""Execution-only navigation task and source AfterAttackAct probabilities."""
import unreal,sys,importlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import ds3_blueprint_graph;importlib.reload(ds3_blueprint_graph)
from ds3_blueprint_graph import *
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not any(str(k.get_editor_property('entry_name'))=='PostCycles' for k in bb.get_editor_property('keys')):
 k=unreal.BlackboardEntry();k.set_editor_property('entry_name','PostCycles');k.set_editor_property('key_type',unreal.new_object(unreal.load_class(None,'/Script/AIModule.BlackboardKeyType_Int'),outer=bb));bb.set_editor_property('keys',list(bb.get_editor_property('keys'))+[k]);unreal.EditorAssetLibrary.save_loaded_asset(bb,False)
 importlib.reload(ds3_blueprint_graph)
 from ds3_blueprint_graph import *

vars=[('Mode','int',1),('UseAfterSettings','bool',False),('Duration','real',2.0),('TargetDistance','real',10.0),('StartTime','real',0.0),('LastUpdate','real',0.0),('Life','real',2.0),('DesiredDistance','real',10.0),('HeldAngle','real',30.0),('TurnTolerance','real',15.0),('RangeBound','bool',False)]
g=Graph('BTT_DSRelativeMove',vars,['ReceiveExecuteAI','ReceiveTickAI','ReceiveAbortAI']);e=g.events['ReceiveExecuteAI'];tick=g.events['ReceiveTickAI'];abort=g.events['ReceiveAbortAI']
tail=stop(g,e,e);tail=g.store('StartTime',tail,source=(now(g),'ReturnValue'));tail=g.store('LastUpdate',tail,-10000)
rng=g.fn(KM+'RandomFloatInRange');val(rng,'Min',30);val(rng,'Max',45);side=g.fn(KM+'RandomBool');sb=g.branch((side,'ReturnValue'));seq(tail,sb)
positive=g.store('HeldAngle',sb,source=(rng,'ReturnValue'));negative=g.calc('Multiply_DoubleDouble',rng,constant=-1);neg=g.store('HeldAngle',sb,source=(negative,'ReturnValue'),out='else')
tr=g.fn(KM+'RandomFloatInRange');val(tr,'Min',15);val(tr,'Max',20);turn=g.store('TurnTolerance',positive,source=(tr,'ReturnValue'));seq(neg,turn)
use=g.branch((g.get('UseAfterSettings'),'UseAfterSettings'));seq(turn,use)
afterlife=g.store('Life',use,source=(g.bbget('Float','MoveDuration'),'ReturnValue'));afterdist=g.store('DesiredDistance',afterlife,source=(g.bbget('Float','MoveDistance'),'ReturnValue'))
life=g.store('Life',use,source=(g.get('Duration'),'Duration'),out='else');dist=g.store('DesiredDistance',life,source=(g.get('TargetDistance'),'TargetDistance'))
d,pl,tl,target=distance(g,e);units=g.calc('Divide_DoubleDouble',d,b=g.bbget('Float','UnitScale'));near=g.calc('Less_DoubleDouble',units,constant=5.5);isSide=g.calc('EqualEqual_IntInt',g.get('Mode'),'Mode',constant=1);bound=g.calc('BooleanAND',near,b=isSide);notafter=g.fn(KM+'Not_PreBool');link(g.get('UseAfterSettings'),'UseAfterSettings',notafter,'A');bound=g.calc('BooleanAND',bound,b=notafter);boundset=g.store('RangeBound',dist,source=(bound,'ReturnValue'));seq(afterdist,boundset)
# Active relative movement recalculates its destination at 0.2s. No behavior choices occur here.
elapsed=g.calc('Subtract_DoubleDouble',now(g),b=g.get('StartTime'),bp='StartTime');expired=g.calc('GreaterEqual_DoubleDouble',elapsed,b=g.get('Life'),bp='Life');expiry=g.branch((expired,'ReturnValue'));seq(tick,expiry)
def end(previous,out='then'):
 t=stop(g,tick,previous,out);finish(g,t)
end(expiry)
td,tpl,ttl,ttarget=distance(g,tick);tunits=g.calc('Divide_DoubleDouble',td,b=g.bbget('Float','UnitScale'))
exceeded=g.calc('Greater_DoubleDouble',tunits,constant=5.5);activebound=g.calc('BooleanAND',exceeded,b=g.get('RangeBound'),bp='RangeBound');rb=g.branch((activebound,'ReturnValue'));seq(expiry,rb,'else');end(rb)
mode4=g.calc('EqualEqual_IntInt',g.get('Mode'),'Mode',constant=4);turnbranch=g.branch((mode4,'ReturnValue'));seq(rb,turnbranch,'else')
look=g.fn(KM+'FindLookAtRotation');link(tpl,'ReturnValue',look,'Start');link(ttl,'ReturnValue',look,'Target');rot=g.fn('/Script/Engine.Actor.K2_GetActorRotation');link(tick,'ControlledPawn',rot,'self');delta=g.calc('NormalizedDeltaRotator',look,b=rot);br=g.fn(KM+'BreakRotator');link(delta,'ReturnValue',br,'InRot');ab=g.fn(KM+'Abs');link(br,'Yaw',ab,'A');aligned=g.calc('LessEqual_DoubleDouble',ab,b=g.get('TurnTolerance'),bp='TurnTolerance');done=g.branch((aligned,'ReturnValue'));seq(turnbranch,done);end(done)
retreat=g.calc('EqualEqual_IntInt',g.get('Mode'),'Mode',constant=2);approach=g.calc('EqualEqual_IntInt',g.get('Mode'),'Mode',constant=3)
backdist=g.calc('Subtract_DoubleDouble',g.get('DesiredDistance'),'DesiredDistance',constant=.05);backdone=g.calc('GreaterEqual_DoubleDouble',tunits,b=backdist);backdone=g.calc('BooleanAND',backdone,b=retreat)
frontdist=g.calc('Add_DoubleDouble',g.get('DesiredDistance'),'DesiredDistance',constant=.05);frontdone=g.calc('LessEqual_DoubleDouble',tunits,b=frontdist);frontdone=g.calc('BooleanAND',frontdone,b=approach);reached=g.calc('BooleanOR',backdone,b=frontdone);reach=g.branch((reached,'ReturnValue'));seq(turnbranch,reach,'else');end(reach)
since=g.calc('Subtract_DoubleDouble',now(g),b=g.get('LastUpdate'),bp='LastUpdate');refresh=g.calc('GreaterEqual_DoubleDouble',since,constant=.2);update=g.branch((refresh,'ReturnValue'));seq(reach,update,'else')
stamp=g.store('LastUpdate',update,source=(now(g),'ReturnValue'))
direction=g.fn(KM+'GetDirectionUnitVector');link(ttl,'ReturnValue',direction,'From');link(tpl,'ReturnValue',direction,'To');bv=g.fn(KM+'BreakVector');link(direction,'ReturnValue',bv,'InVec');flat=g.fn(KM+'MakeVector');link(bv,'X',flat,'X');link(bv,'Y',flat,'Y');norm=g.fn(KM+'Normal');link(flat,'ReturnValue',norm,'A')
sidevec=g.fn(KM+'RotateAngleAxis');link(norm,'ReturnValue',sidevec,'InVect');link(g.get('HeldAngle'),'HeldAngle',sidevec,'AngleDeg');val(sidevec,'Axis','(X=0,Y=0,Z=1)')
isSide=g.calc('EqualEqual_IntInt',g.get('Mode'),'Mode',constant=1);select=g.fn(KM+'SelectVector');link(sidevec,'ReturnValue',select,'A');link(norm,'ReturnValue',select,'B');link(isSide,'ReturnValue',select,'bPickA')
radius=g.fn(KM+'SelectFloat');link(td,'ReturnValue',radius,'A');goalcm=g.calc('Multiply_DoubleDouble',g.get('DesiredDistance'),'DesiredDistance',g.bbget('Float','UnitScale'));link(goalcm,'ReturnValue',radius,'B');link(isSide,'ReturnValue',radius,'bPickA')
scaled=g.calc('Multiply_VectorFloat',select,b=radius);goal=g.calc('Add_VectorVector',ttl,b=scaled)
project=g.fn('/Script/NavigationSystem.NavigationSystemV1.K2_ProjectPointToNavigation');link(goal,'ReturnValue',project,'Point');val(project,'QueryExtent','(X=100,Y=100,Z=300)');valid=g.branch((project,'ReturnValue'));seq(stamp,valid)
move=g.fn('/Script/AIModule.AIController.MoveToLocation');link(tick,'OwnerController',move,'self');link(project,'ProjectedLocation',move,'Dest');val(move,'AcceptanceRadius',3);val(move,'bStopOnOverlap','false');val(move,'bCanStrafe','true');seq(valid,move)
end(valid,'else')
tail=stop(g,abort,abort);finish(g,tail,abort=True)
g.finish()

# Independent optional post-attack behavior; source probabilities and no invented wait.
vars=[('Roll','int',0),('PostChance','int',0)]
g=Graph('BTT_DSAfterAttack',vars,['ReceiveExecuteAI']);e=g.events['ReceiveExecuteAI'];counter=g.calc('Add_IntInt',g.bbget('Int','PostCycles'),constant=1);tail=g.bbset('Int','PostCycles',e,source=(counter,'ReturnValue'));tail=g.bbset('Int','AfterAction',tail,0)
rng=g.fn(KM+'RandomIntegerInRange');val(rng,'Min',1);val(rng,'Max',100);tail=g.store('Roll',tail,source=(rng,'ReturnValue'))
action=g.bbget('Int','Action');normal=None
for aid in [1,2,4,5,6]:
 c=g.calc('EqualEqual_IntInt',action,constant=aid);normal=c if normal is None else g.calc('BooleanOR',normal,b=c)
c20=g.calc('EqualEqual_IntInt',action,constant=20);c21=g.calc('EqualEqual_IntInt',action,constant=21);special=g.calc('BooleanOR',c20,b=c21);allow=g.calc('LessEqual_IntInt',g.get('Roll'),'Roll',constant=50);allow=g.calc('BooleanAND',allow,b=normal);allow=g.calc('BooleanOR',allow,b=special);gate=g.branch((allow,'ReturnValue'));seq(tail,gate);finish(g,gate,out='else')
life=g.fn(KM+'RandomFloatInRange');val(life,'Min',2.5);val(life,'Max',4.5);tail=g.bbset('Float','MoveDuration',gate,source=(life,'ReturnValue'))
d,_,_,_=distance(g,e);units=g.calc('Divide_DoubleDouble',d,b=g.bbget('Float','UnitScale'));addition=g.fn(KM+'RandomFloatInRange');val(addition,'Min',2.5);val(addition,'Max',4.5);backdist=g.calc('Add_DoubleDouble',units,b=addition);tail=g.bbset('Float','MoveDistance',tail,source=(backdist,'ReturnValue'))
tail=g.store('Roll',tail,source=(rng,'ReturnValue'))
role=g.bbget('Int','TeamRole');r1=g.calc('EqualEqual_IntInt',role,constant=1);r2=g.calc('EqualEqual_IntInt',role,constant=2);r=g.calc('BooleanOR',r1,b=r2);team=g.branch((r,'ReturnValue'));seq(tail,team)
near=g.calc('LessEqual_DoubleDouble',units,constant=6);tb=g.branch((near,'ReturnValue'));seq(team,tb)
def choose(previous,aid,out='then',distance_override=None):
 t=g.bbset('Int','AfterAction',previous,aid,out=out)
 if distance_override is not None:t=g.bbset('Float','MoveDistance',t,distance_override)
 finish(g,t)
choose(tb,2,distance_override=8);choose(tb,1,'else')
far=g.calc('GreaterEqual_DoubleDouble',units,constant=6);fb=g.branch((far,'ReturnValue'));seq(team,fb,'else');side=g.calc('LessEqual_IntInt',g.get('Roll'),'Roll',constant=25);fside=g.branch((side,'ReturnValue'));seq(fb,fside);choose(fside,1);choose(fside,3,'else',5.5)
previous=fb
for threshold,side_odds,back_odds in [(4,30,30),(2,15,25),(.5,5,20),(-1e9,0,15)]:
 cond=g.calc('GreaterEqual_DoubleDouble',units,constant=threshold);b=g.branch((cond,'ReturnValue'));seq(previous,b,'else');side=g.calc('LessEqual_IntInt',g.get('Roll'),'Roll',constant=side_odds);s=g.branch((side,'ReturnValue'));seq(b,s);choose(s,1)
 back=g.calc('LessEqual_IntInt',g.get('Roll'),'Roll',constant=back_odds);bk=g.branch((back,'ReturnValue'));seq(s,bk,'else');choose(bk,2);finish(g,bk,out='else');previous=b
finish(g,previous,out='else')
g.finish()
print('DS3_MOVEMENT_TASKS_READY')
