"""Create small reusable tasks for tree-owned decisions; never rebuild old BTTs."""
import unreal, sys, importlib, json, shutil
from pathlib import Path
P=Path(unreal.Paths.project_dir()); sys.path.insert(0,str(P/'Tools'))
import ds3_blueprint_graph as helper
importlib.reload(helper)
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
AI='/Game/Gameplay/AI/DS3BrokenSword/'
DEST=AI+'Tactical/'
lib=unreal.EditorAssetLibrary; tools=unreal.AssetToolsHelpers.get_asset_tools()
bb=unreal.load_asset(AI+'StandardReadable/BB_DS3_Standard'); assert bb
backup=P/'LocalBackups/Tactical-2026-11-09'; backup.mkdir(parents=True,exist_ok=True)
for rel in ['Gameplay/AI/DS3BrokenSword/StandardReadable/BB_DS3_Standard.uasset','Gameplay/AI/BP_EnemyAIController.uasset']:
    dst=backup/Path(rel).name
    if not dst.exists(): shutil.copy2(P/'Content'/rel,dst)
ids=[1,2,4,5,6,11,12,13,20,21,54]
fields={'TacticalDistance':'Float','TacticalYaw':'Float','TacticalHealth':'Float','Cooldown3003Ready':'Bool','PostGateRoll':'Int','PostChoiceRoll':'Int'}
fields.update({'Weight'+str(i):'Float' for i in ids})
keys=list(bb.get_editor_property('keys'))
for name,typ in fields.items():
    if any(str(k.get_editor_property('entry_name'))==name for k in keys): continue
    k=unreal.BlackboardEntry(); k.set_editor_property('entry_name',name)
    k.set_editor_property('key_type',unreal.new_object(unreal.load_class(None,'/Script/AIModule.BlackboardKeyType_'+typ),outer=bb)); keys.append(k)
bb.set_editor_property('keys',keys); assert lib.save_loaded_asset(bb,False)
helper.AI=DEST; helper.bb=bb; helper.keys=keys
from ds3_blueprint_graph import *
names=['BTT_ReadSituation','BTT_SetCandidates','BTT_ExcludeCoolingAttack','BTT_DrawCandidate','BTT_PrepareRecovery','BTT_SetRecovery']
for name in names:
    assert not lib.does_asset_exist(DEST+name), 'New assets only: '+name
    factory=unreal.BlueprintFactory(); factory.set_editor_property('parent_class',unreal.BTTask_BlueprintBase)
    assert tools.create_asset(name,DEST.rstrip('/'),unreal.Blueprint,factory)

g=Graph('BTT_ReadSituation',[],['ReceiveExecuteAI']); e=g.events['ReceiveExecuteAI']
d,pl,tl,target=distance(g,e); units=g.calc('Divide_DoubleDouble',d,b=g.bbget('Float','UnitScale'))
tail=g.bbset('Float','TacticalDistance',e,source=(units,'ReturnValue'))
look=g.fn(KM+'FindLookAtRotation'); link(pl,'ReturnValue',look,'Start'); link(tl,'ReturnValue',look,'Target')
rotation=g.fn('/Script/Engine.Actor.K2_GetActorRotation'); link(e,'ControlledPawn',rotation,'self')
delta=g.calc('NormalizedDeltaRotator',look,b=rotation); br=g.fn(KM+'BreakRotator'); link(delta,'ReturnValue',br,'InRot')
tail=g.bbset('Float','TacticalYaw',tail,source=(br,'Yaw'))
cast=g.cast('BaseCharacter'); link(e,'ControlledPawn',cast,'Object'); seq(tail,cast)
hp=g.fn('/Script/ProjectUnreal.BaseCharacter.GetHealthPercent'); link(cast,castout(cast),hp,'self')
tail=g.bbset('Float','TacticalHealth',cast,source=(hp,'ReturnValue'))
cool=g.calc('Subtract_DoubleDouble',now(g),b=g.bbget('Float','Last3003Time'))
ready=g.calc('Greater_DoubleDouble',cool,constant=20)
tail=g.bbset('Bool','Cooldown3003Ready',tail,source=(ready,'ReturnValue')); finish(g,tail)
finish(g,cast,False,out='CastFailed')
g.finish('只测量距离、方向、血量与3003冷却；不选招、不配置权重。每轮及攻击结束后采样，攻击中不重选。')

g=Graph('BTT_SetCandidates',[('W'+str(i),'real',0.0) for i in ids],['ReceiveExecuteAI']); tail=g.events['ReceiveExecuteAI']
for i in ids: tail=g.bbset('Float','Weight'+str(i),tail,source=(g.get('W'+str(i)),'W'+str(i)))
finish(g,tail); g.finish('通用配置任务：把当前树分支的公开权重写入黑板。没有距离、角色或变体判断；每次覆盖全部候选，避免残留。')

g=Graph('BTT_ExcludeCoolingAttack',[],['ReceiveExecuteAI'])
tail=g.bbset('Float','Weight5',g.events['ReceiveExecuteAI'],0); finish(g,tail)
g.finish('只将3003对应的候选权重归零。是否处于冷却由行为树条件决定。')

g=Graph('BTT_DrawCandidate',[('Roll','real',0.0)],['ReceiveExecuteAI']); e=g.events['ReceiveExecuteAI']
counter=g.calc('Add_IntInt',g.bbget('Int','DecisionCount'),constant=1)
tail=g.bbset('Int','DecisionCount',e,source=(counter,'ReturnValue'))
forced=g.bbget('Int','ForcedAction'); forceok=g.calc('Greater_IntInt',forced,constant=0)
force=g.branch((forceok,'ReturnValue')); seq(tail,force)
forcedset=g.bbset('Int','Action',force,source=(forced,'ReturnValue')); finish(g,forcedset)
total=None
for i in ids:
    w=g.bbget('Float','Weight'+str(i)); total=w if total is None else g.calc('Add_DoubleDouble',total,b=w)
sample=g.fn(KM+'RandomFloatInRange'); val(sample,'Min',0); link(total,'ReturnValue',sample,'Max')
roll=g.store('Roll',force,source=(sample,'ReturnValue'),out='else')
previous=roll; out='then'; cumulative=None
for i in ids:
    w=g.bbget('Float','Weight'+str(i)); cumulative=w if cumulative is None else g.calc('Add_DoubleDouble',cumulative,b=w)
    less=g.calc('Less_DoubleDouble',g.get('Roll'),'Roll',cumulative)
    choice=g.branch((less,'ReturnValue')); seq(previous,choice,out)
    selected=g.bbset('Int','Action',choice,i); finish(g,selected); previous=choice; out='else'
fallback=g.bbset('Int','Action',previous,13,out='else'); finish(g,fallback)
g.finish('通用加权抽签：只读取树配置的Weight黑板值；随机数只存一次。零权重不命中，无候选时转身；ForcedAction仅用于测试。')

g=Graph('BTT_PrepareRecovery',[],['ReceiveExecuteAI']); e=g.events['ReceiveExecuteAI']
counter=g.calc('Add_IntInt',g.bbget('Int','PostCycles'),constant=1)
tail=g.bbset('Int','PostCycles',e,source=(counter,'ReturnValue')); tail=g.bbset('Int','AfterAction',tail,0)
for key in ['PostGateRoll','PostChoiceRoll']:
    rng=g.fn(KM+'RandomIntegerInRange'); val(rng,'Min',1); val(rng,'Max',100)
    tail=g.bbset('Int',key,tail,source=(rng,'ReturnValue'))
life=g.fn(KM+'RandomFloatInRange'); val(life,'Min',2.5); val(life,'Max',4.5)
tail=g.bbset('Float','MoveDuration',tail,source=(life,'ReturnValue'))
addition=g.fn(KM+'RandomFloatInRange'); val(addition,'Min',2.5); val(addition,'Max',4.5)
backdist=g.calc('Add_DoubleDouble',g.bbget('Float','TacticalDistance'),b=addition)
tail=g.bbset('Float','MoveDistance',tail,source=(backdist,'ReturnValue')); finish(g,tail)
g.finish('只准备本次恢复的随机数、时长与默认后退距离。走位门槛和方向由树上条件选择。')

g=Graph('BTT_SetRecovery',[('Mode','int',0),('OverrideDistance','bool',False),('Distance','real',0.0)],['ReceiveExecuteAI'])
tail=g.bbset('Int','AfterAction',g.events['ReceiveExecuteAI'],source=(g.get('Mode'),'Mode'))
b=g.branch((g.get('OverrideDistance'),'OverrideDistance')); seq(tail,b)
tail=g.bbset('Float','MoveDistance',b,source=(g.get('Distance'),'Distance')); finish(g,tail); finish(g,b,out='else')
g.finish('只写入树所选择的走位方式与可选目标间距；条件判断全部在恢复子树中。')
print('TACTICAL_TASKS_CREATED')
