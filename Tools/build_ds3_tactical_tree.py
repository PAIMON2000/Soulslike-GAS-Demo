"""Historical one-time builder; source main retired after successful migration.
Do not rerun to recreate obsolete assets. Validate with verify_ds3_tactical.py.
"""
import sys,json,re
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from ds3_tactical_graph import *
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
AI='/Game/Gameplay/AI/DS3BrokenSword/'
old=unreal.load_asset(AI+'StandardReadable/BT_DS3_CombatOverview'); assert old
keys=list(bb.get_editor_property('keys'))
def key(name):
    i=next(i for i,k in enumerate(keys) if str(k.get_editor_property('entry_name'))==name)
    s=unreal.BlackboardKeySelector(); s.set_editor_property('selected_key_name',name); s.set_editor_property('selected_key_id',i)
    s.set_editor_property('selected_key_type',keys[i].get_editor_property('key_type').get_class()); return s
serial=0
def node(tree,cls,title,**props):
    global serial
    serial+=1
    typ=unreal.load_class(None,DEST+cls+'.'+cls+'_C') if cls.startswith('BTT_') else getattr(unreal,cls)
    n=unreal.new_object(typ,outer=tree,name='TacticalNode'+str(serial)); label(n,title,title)
    for k,v in props.items(): n.set_editor_property(k,v)
    return n
def child(n,conditions=()):
    c=plain_child(n); c.set_editor_property('decorators',list(conditions)); return c
def group(t,kind,title,children): return node(t,'BTComposite_'+kind,title,children=children)
def cond(t,name,op,value,title=None):
    n=node(t,'BTDecorator_Blackboard',title or f'{name} {op} {value}',blackboard_key=key(name))
    if isinstance(value,bool): n.set_editor_property('basic_operation',getattr(type(n.get_editor_property('basic_operation')),'SET' if value else 'NOT_SET'))
    else:
        n.set_editor_property('arithmetic_operation',getattr(type(n.get_editor_property('arithmetic_operation')),op))
        typ=keys[next(i for i,k in enumerate(keys) if str(k.get_editor_property('entry_name'))==name)].get_editor_property('key_type').get_class().get_name()
        n.set_editor_property('float_value' if typ.endswith('_Float') else 'int_value',value)
    return n
def conditions(t,specs): return [cond(t,*s) for s in specs]
def run(t,sub,title): return node(t,'BTTask_RunBehavior',title,behavior_asset=sub)
def wait(t,title):
    v=unreal.ValueOrBBKey_Float(); v.import_text('(DefaultValue=0.0,Key=None)')
    return node(t,'BTTask_Wait',title,wait_time=v,random_deviation=v)
def weights(t,title,values): return node(t,'BTT_SetCandidates',title,**{'W'+str(i):v for i,v in values.items()})
def choice(t,title,specs,values): return child(weights(t,title,values),conditions(t,specs))
def finish_tree(t,root): t.set_editor_property('root_node',root); finalize(t); return t
D='TacticalDistance'; Y='TacticalYaw'; H='TacticalHealth'

team=new_tree('BT_TeamRole')
finish_tree(team,group(team,'Selector','按队伍职责配合（从左到右）',[
    choice(team,'旁观：后退60 / 侧移40',[('TeamRole','EQUAL',1,'旁观角色')],{11:60,12:40}),
    choice(team,'围攻远距：前冲20 / 后退50 / 侧移30',[('TeamRole','EQUAL',2,'围攻角色'),(D,'GREATER_OR_EQUAL',5.5,'距离 ≥ 5.5')],{6:20,11:50,12:30}),
    choice(team,'围攻近中距：后退50 / 侧移30',[('TeamRole','EQUAL',2,'围攻角色')],{11:50,12:30})]))

direction=new_tree('BT_FacingResponse')
finish_tree(direction,group(direction,'Selector','目标在侧后方时的选择',[
    choice(direction,'右侧：连击B30 / 冷却攻击15 / 转身55',[(D,'LESS_OR_EQUAL',2.0,'距离 ≤ 2'),(Y,'GREATER_OR_EQUAL',45.0,'目标右侧 ≥ 45°'),(Y,'LESS_OR_EQUAL',135.0,'目标右侧 ≤ 135°')],{2:30,5:15,13:55}),
    choice(direction,'左侧：连击A30 / 冷却攻击15 / 转身55',[(D,'LESS_OR_EQUAL',2.0,'距离 ≤ 2'),(Y,'GREATER_OR_EQUAL',-135.0,'目标左侧 ≥ -135°'),(Y,'LESS_OR_EQUAL',-45.0,'目标左侧 ≤ -45°')],{1:30,5:15,13:55}),
    choice(direction,'右后方：转身',[(D,'LESS_OR_EQUAL',10.0,'距离 ≤ 10'),(Y,'GREATER_OR_EQUAL',60.0,'偏离正面 ≥ 60°')],{13:100}),
    choice(direction,'左后方：转身',[(D,'LESS_OR_EQUAL',10.0,'距离 ≤ 10'),(Y,'LESS_OR_EQUAL',-60.0,'偏离正面 ≤ -60°')],{13:100})]))

special=new_tree('BT_SpecialDistance')
finish_tree(special,group(special,'Selector','特殊变体：按距离选动作',[
    choice(special,'距离远：特殊动作20005',[(D,'GREATER_OR_EQUAL',13.0,'距离 ≥ 13')],{20:100}),
    choice(special,'距离近：特殊动作20006',[],{21:100})]))

ordinary=new_tree('BT_DistanceChoices')
finish_tree(ordinary,group(ordinary,'Selector','正面交战：距离决定候选，不强制唯一出招',[
    choice(ordinary,'144040远距≥10：前冲、连击与特殊动作',[('ThinkParamID','EQUAL',144040,'144040变体'),(D,'GREATER_OR_EQUAL',10.0,'距离 ≥ 10')],{1:15,2:10,5:10,6:45,12:20,20:20,21:10}),
    choice(ordinary,'144040远距：特殊20006权重略高',[('ThinkParamID','EQUAL',144040,'144040变体'),(D,'GREATER_OR_EQUAL',5.5,'距离 ≥ 5.5')],{1:15,2:10,5:10,6:45,12:20,20:10,21:20}),
    choice(ordinary,'普通远距：前冲45 / 连击A15 B10 / 冷却10 / 侧移20',[(D,'GREATER_OR_EQUAL',5.5,'距离 ≥ 5.5')],{1:15,2:10,5:10,6:45,12:20}),
    choice(ordinary,'144040中距：普通候选加特殊20006权重30',[('ThinkParamID','EQUAL',144040,'144040变体'),(D,'GREATER_OR_EQUAL',1.5,'距离 ≥ 1.5')],{1:20,2:20,4:15,5:35,12:10,21:30}),
    choice(ordinary,'普通中距：连击A20 B20 / 两段15 / 冷却35 / 侧移10',[(D,'GREATER_OR_EQUAL',1.5,'距离 ≥ 1.5')],{1:20,2:20,4:15,5:35,12:10}),
    choice(ordinary,'近距：连击A25 B15 / 两段15 / 冷却攻击45',[],{1:25,2:15,4:15,5:45})]))

decision=new_tree('BT_DecisionRules')
rules=group(decision,'Selector','优先级：事件 → 变体 → 职责 → 方向 → 距离',[
    choice(decision,'响应事件100：特殊动作20005',[('EventRequest1','EQUAL',100,'事件请求 = 100')],{20:100}),
    choice(decision,'110054变体：专用接近',[('ThinkParamID','EQUAL',110054,'变体 = 110054')],{54:100}),
    child(run(decision,team,'队伍职责｜旁观或围攻'),conditions(decision,[('TeamRole','GREATER_OR_EQUAL',1,'职责 ≥ 1'),('TeamRole','LESS_OR_EQUAL',2,'职责 ≤ 2')])),
    child(run(decision,direction,'侧后响应｜无匹配则继续判断')),
    child(run(decision,special,'144041特殊动作'),conditions(decision,[('ThinkParamID','EQUAL',144041,'变体 = 144041')])),
    child(run(decision,special,'144040低血量特殊动作'),conditions(decision,[('ThinkParamID','EQUAL',144040,'变体 = 144040'),(H,'LESS_OR_EQUAL',0.8,'生命比例 ≤ 80%')])),
    child(run(decision,ordinary,'正面交战｜按距离配置招式候选'))])
cool=group(decision,'Selector','独立冷却：只过滤3003，不影响其他攻击',[
    child(node(decision,'BTT_ExcludeCoolingAttack','3003未冷却：排除本轮候选'),[cond(decision,'Cooldown3003Ready','',False,'3003距离上次发动 ≤ 20秒')]),
    child(wait(decision,'3003已冷却：保留权重'))])
finish_tree(decision,group(decision,'Sequence','每轮只选择一次；攻击期间不重新抽签',[
    child(node(decision,'BTT_ReadSituation','读取距离、方向、血量、冷却')),
    child(rules),child(cool),child(node(decision,'BTT_DrawCandidate','按树上的候选权重抽取一次'))]))

# Recovery choice also belongs to the tree, not the old 136-node BTT.
recovery_rules=new_tree('BT_RecoveryDistance')
def recovery(t,title,specs,mode,dist=None):
    return child(node(t,'BTT_SetRecovery',title,Mode=mode,OverrideDistance=dist is not None,Distance=dist or 0),conditions(t,specs))
def band(t,title,minimum,side,back):
    options=[]
    if side: options.append(recovery(t,'侧移', [('PostChoiceRoll','LESS_OR_EQUAL',side,f'随机值 ≤ {side}')],1))
    if back>side: options.append(recovery(t,'后退',[('PostChoiceRoll','LESS_OR_EQUAL',back,f'随机值 ≤ {back}')],2))
    options.append(child(wait(t,'不追加走位')))
    return child(group(t,'Selector',title,options),conditions(t,[(D,'GREATER_OR_EQUAL',minimum,f'距离 ≥ {minimum}')]))
teamconds=[('TeamRole','GREATER_OR_EQUAL',1,'职责 ≥ 1'),('TeamRole','LESS_OR_EQUAL',2,'职责 ≤ 2')]
far=group(recovery_rules,'Selector','远距：25%侧移 / 75%靠近',[
    recovery(recovery_rules,'侧移',[('PostChoiceRoll','LESS_OR_EQUAL',25,'随机值 ≤ 25')],1),recovery(recovery_rules,'靠近到5.5',[],3,5.5)])
finish_tree(recovery_rules,group(recovery_rules,'Selector','攻击结束后重新看距离，再选走位',[
    recovery(recovery_rules,'配合队伍：近时后退到8',teamconds+[(D,'LESS_OR_EQUAL',6.0,'距离 ≤ 6')],2,8),
    recovery(recovery_rules,'配合队伍：远时侧移',teamconds,1),
    child(far,conditions(recovery_rules,[(D,'GREATER_OR_EQUAL',6.0,'距离 ≥ 6')])),
    band(recovery_rules,'距离4～6：30%侧移 / 70%结束',4.0,30,30),
    band(recovery_rules,'距离2～4：15%侧移 / 10%后退 / 75%结束',2.0,15,25),
    band(recovery_rules,'距离0.5～2：5%侧移 / 15%后退 / 80%结束',0.5,5,20),
    band(recovery_rules,'贴身：15%后退 / 85%结束',0.0,0,15)]))

baseline=blocks(export(old,'previous-main.t3d')); copied={}
def copy(n,t):
    token=(n.get_path_name(),t.get_path_name())
    if token in copied: return copied[token]
    out=unreal.new_object(n.get_class(),outer=t,name='Preserved_'+n.get_name()); copied[token]=out
    for prop in dict.fromkeys(re.findall(r'^      (\w+)=',baseline[n.get_name()],re.M)):
        if prop not in ['Children','TreeAsset','ParentNode','CachedDescription']: out.set_editor_property(prop,n.get_editor_property(prop))
    if isinstance(n,unreal.BTCompositeNode):
        children=[]
        for c in n.children:
            cc=child(copy(c.child_composite or c.child_task,t),[copy(d,t) for d in c.decorators]); cc.set_editor_property('decorator_ops',list(c.decorator_ops)); children.append(cc)
        out.set_editor_property('children',children)
    return out
oldcycle=kids(old.root_node)[0]
recovery_tree=new_tree('BT_AfterAttack')
gate=group(recovery_tree,'Selector','本轮是否需要攻击后调整',[
    child(run(recovery_tree,recovery_rules,'普通攻击：50%进入距离判断'),conditions(recovery_tree,[('Action','GREATER_OR_EQUAL',1,'行动 ≥ 1'),('Action','LESS_OR_EQUAL',6,'行动 ≤ 6'),('PostGateRoll','LESS_OR_EQUAL',50,'本次随机值 ≤ 50')])),
    child(run(recovery_tree,recovery_rules,'特殊动作：必定进入距离判断'),conditions(recovery_tree,[('Action','GREATER_OR_EQUAL',20,'行动 ≥ 20'),('Action','LESS_OR_EQUAL',21,'行动 ≤ 21')])),
    child(wait(recovery_tree,'移动行动或未命中概率：结束本轮'))])
finish_tree(recovery_tree,group(recovery_tree,'Sequence','攻击后调整：判断与执行分开',[
    child(node(recovery_tree,'BTT_ReadSituation','重新测量当前距离')),
    child(node(recovery_tree,'BTT_PrepareRecovery','重置走位并准备本轮随机值')),
    child(gate),child(copy(kids(oldcycle)[5],recovery_tree))]))

main=new_tree('BT_BrokenSword_Combat')
cycle=group(main,'Sequence','一次完整战斗行动',[
    child(copy(kids(oldcycle)[0],main)),child(run(main,decision,'① 判断局势｜双击查看所有选招条件')),
    child(copy(kids(oldcycle)[2],main)),child(copy(kids(oldcycle)[3],main)),
    child(run(main,recovery_tree,'③ 攻击后调整｜双击查看距离与概率条件'))])
label(kids(cycle)[0],'准备战斗所需数据','初始化比例、半径、速度。')
label(kids(cycle)[2],'② 执行已选招式｜连击期间保持本次选择','四类行动只负责执行，判断在①中。')
guard=copy(old.root_node.children[0].decorators[0],main)
finish_tree(main,group(main,'Selector','断剑怪｜局势决策与行动执行',[
    child(cycle,[guard]),child(copy(kids(old.root_node)[1],main))]))
report={'passed':True,'main':main.get_path_name(),'blackboard':bb.get_path_name(),'created':[t.get_path_name() for t in created],
        'legacy_decision_tasks_used':False,'old_main':old.get_path_name()}
(OUT/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('TACTICAL_TREES_CREATED',report)
