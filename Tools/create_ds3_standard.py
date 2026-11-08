"""Create isolated readable trees without deleting or renaming existing objects.

Copies serialized configuration through Unreal's public reflected properties.
Graph creation is restricted to newly created packages. Existing assets are read
only. Binding the controller is a separate, reversible editor operation.

Historical one-time builder: the source tree was removed on 2026-11-09 at the
user's request. Daily validation uses verify_export_ds3_standard.py and its saved
reference JSON; do not restore retired trees just to run this builder.
"""
import ctypes,json,re
from pathlib import Path
import unreal

P=Path(unreal.Paths.project_dir());OUT=P/'Saved/DS3-Standard';OUT.mkdir(parents=True,exist_ok=True)
AI='/Game/Gameplay/AI/DS3BrokenSword/'
DEST=AI+'StandardReadable/'
assert unreal.EditorAssetLibrary.does_asset_exist(AI+'BT_DS3BrokenSword'), 'Historical source retired; use verify_export_ds3_standard.py for the current tree'
source=unreal.load_asset(AI+'BT_DS3BrokenSword');assert source
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
lib=unreal.EditorAssetLibrary;tools=unreal.AssetToolsHelpers.get_asset_tools()
bbpath=DEST+'BB_DS3_Standard'
assert not lib.does_asset_exist(bbpath), 'Refuses to overwrite the existing standard blackboard'
bb=lib.duplicate_asset(source.blackboard_asset.get_path_name(),bbpath);assert bb
target=next(k for k in bb.get_editor_property('keys') if str(k.get_editor_property('entry_name'))=='TargetActor')
target.get_editor_property('key_type').set_editor_property('BaseClass',unreal.Actor.static_class())
assert lib.save_loaded_asset(bb,False)
display=json.loads((P/'Tools/ds3_readable_labels.json').read_text(encoding='utf-8'))
GROUPS=display['GROUPS'];TITLES={int(k):v for k,v in display['TITLES'].items()}
NOTES={int(k):v for k,v in display['NOTES'].items()};RULES=display['RULES']

def export(tree,name):
    path=OUT/name;t=unreal.AssetExportTask();t.object=tree;t.filename=str(path)
    t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=unreal.ObjectExporterT3D()
    assert unreal.Exporter.run_asset_export_task(t)
    b=path.read_bytes();return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')

def blocks(text):
    result={};stack=[];body=[]
    for line in text.splitlines():
        if line.strip().startswith('Begin Object'):
            m=re.search(r'Name="([^"]+)"',line);stack.append(m.group(1) if m else '')
            if len(stack)==2:body=[]
        elif line.strip()=='End Object':
            if len(stack)==2:result[stack[-1]]='\n'.join(body)
            stack.pop()
        elif len(stack)==2:body.append(line)
    return result

baseline=blocks(export(source,'standard-source.t3d'))
def config(body):
    return '\n'.join(l for l in body.splitlines() if not re.match(r'\s*(NodeName|TreeAsset|ParentNode|CachedDescription)=',l))

def kids(n):return [c.child_composite or c.child_task for c in n.children]
cycle=kids(source.root_node)[0];dispatch=kids(cycle)[2]
assert len(dispatch.children)==11
original={c.decorators[0].get_editor_property('int_value'):c for c in dispatch.children}
notes={};created=[];copies={}

def new_tree(name):
    path=DEST+name
    assert not lib.does_asset_exist(path), 'Refuses to overwrite existing package: '+path
    tree=tools.create_asset(name,DEST.rstrip('/'),unreal.BehaviorTree,unreal.BehaviorTreeFactory());assert tree
    tree.set_editor_property('blackboard_asset',bb);created.append(tree)
    # Let the asset editor create its default graph/root through the normal UI path.
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([tree])
    graph=unreal.find_object(None,tree.get_path_name()+':Behavior Tree');assert graph
    call(nd,'?LockUpdates@UAIGraph@@QEAAXXZ',graph,tree)
    return tree

def label(n,title,note):
    n.set_editor_property('node_name',title);notes[n.get_path_name()]=note

def copy_node(n,tree):
    key=(tree.get_path_name(),n.get_name())
    if key in copies:return copies[key]
    out=unreal.new_object(n.get_class(),outer=tree,name=n.get_name());copies[key]=out
    # Only serialized overrides need copying: each node uses the same class/CDO.
    for prop in dict.fromkeys(re.findall(r'^      (\w+)=',baseline[n.get_name()],re.M)):
        if prop in ['Children','TreeAsset','ParentNode','CachedDescription']:continue
        out.set_editor_property(prop,n.get_editor_property(prop))
    if isinstance(n,unreal.BTCompositeNode):
        assert not n.services, 'Unexpected service requires explicit review'
        out.set_editor_property('children',[copy_child(c,tree) for c in n.children])
    return out

def copy_child(c,tree):
    out=unreal.BTCompositeChild();n=c.child_composite or c.child_task
    out.set_editor_property('child_composite' if c.child_composite else 'child_task',copy_node(n,tree))
    out.set_editor_property('decorators',[copy_node(d,tree) for d in c.decorators])
    out.set_editor_property('decorator_ops',list(c.decorator_ops));return out

def plain_child(n):
    c=unreal.BTCompositeChild();c.set_editor_property('child_composite' if isinstance(n,unreal.BTCompositeNode) else 'child_task',n);return c

def walk(tree):
    ns=[]
    def visit(n):
        ns.append(n)
        if isinstance(n,unreal.BTCompositeNode):
            for c in n.children:ns.extend(c.decorators);visit(c.child_composite or c.child_task)
    visit(tree.root_node);return ns

gd=ctypes.WinDLL('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-BehaviorTreeEditor.dll')
nd=ctypes.WinDLL('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-AIGraph.dll')
def call(dll,symbol,obj,tree,*args):
    assert tree in created
    assert obj.get_path_name().startswith(tree.get_path_name()+':')
    f=getattr(dll,symbol);f.argtypes=[ctypes.c_void_p]+[ctypes.c_int for _ in args];f.restype=None
    f(int(re.search(r'\(0x([0-9a-fA-F]+)\)',str(obj)).group(1),16),*args)

def finalize(tree):
    # New factory graph only; no removal, PostCopyNode, object rename or old-graph edits.
    graph=unreal.find_object(None,tree.get_path_name()+':Behavior Tree');assert graph
    call(gd,'?SpawnMissingNodes@UBehaviorTreeGraph@@QEAAXXZ',graph,tree)
    text=export(tree,tree.get_name()+'-graph.t3d');stack=[];mapping={};root=None
    for line in text.splitlines():
        if line.strip().startswith('Begin Object'):
            m=re.search(r'Name="([^"]+)"',line);stack.append(m.group(1) if m else '')
            if 'BehaviorTreeGraphNode_Root' in line and m:root=m.group(1)
        elif line.strip()=='End Object':stack.pop()
        elif 'NodeInstance=' in line and stack and stack[-1].startswith('BehaviorTreeGraphNode'):
            m=re.search(r"NodeInstance=.*?:([^']+)'",line)
            if m:mapping[m.group(1)]=stack[-1]
    setter=unreal.get_default_object(unreal.SystemLibrary)
    def wrapper(name):return unreal.find_object(None,tree.get_path_name()+':Behavior Tree.'+name)
    def pos(name,x,y):
        o=wrapper(name);assert o
        setter.call_method('SetIntPropertyByName',(o,unreal.Name('NodePosX'),int(x)))
        setter.call_method('SetIntPropertyByName',(o,unreal.Name('NodePosY'),int(y)))
    leaf=[0]
    def layout(n,depth):
        if isinstance(n,unreal.BTCompositeNode):
            xs=[layout(ch,depth+1) for ch in kids(n)];x=(min(xs)+max(xs))/2
        else:x=leaf[0]*360;leaf[0]+=1
        pos(mapping[n.get_name()],x,depth*230);return x
    x=layout(tree.root_node,1);pos(root,x,0)
    for n in walk(tree):
        w=wrapper(mapping[n.get_name()]);call(nd,'?UpdateNodeClassData@UAIGraphNode@@UEAAXXZ',w,tree)
        note=notes.get(n.get_path_name())
        if note:setter.call_method('SetStringPropertyByName',(w,unreal.Name('NodeComment'),note))
        if isinstance(n,unreal.BTTask_BlueprintBase):n.set_editor_property('bShowPropertyDetails',False)
    wrapper(root).set_editor_property('BlackboardAsset',bb)
    call(nd,'?UnlockUpdates@UAIGraph@@QEAAXXZ',graph,tree)
    call(gd,'?UpdateAsset@UBehaviorTreeGraph@@UEAAXH@Z',graph,tree,0)
    assert lib.save_loaded_asset(tree,False)
    result=blocks(export(tree,tree.get_name()+'-saved.t3d'))
    live=set(walk(tree))
    for (path,name),n in copies.items():
        if path==tree.get_path_name() and n in live and not isinstance(n,unreal.BTCompositeNode):
            assert config(baseline[name])==config(result[name]), ('Configuration mismatch',name)

subtrees=[]
for suffix,title,ids in GROUPS:
    tree=new_tree('BT_DS3_'+suffix)
    root=unreal.new_object(unreal.BTComposite_Selector,outer=tree,name='ReadableRoot')
    label(root,title,'只执行已经选中的行动。分类顺序不改变选招权重。')
    cs=[copy_child(original[i],tree) for i in ids]
    for aid,c in zip(ids,cs):
        label(c.child_composite,TITLES[aid],NOTES[aid]+f' 原脚本Act{aid:02d}。')
        label(c.decorators[0],'本轮选择：'+TITLES[aid],NOTES[aid])
    root.set_editor_property('children',cs);tree.set_editor_property('root_node',root)
    finalize(tree);subtrees.append(tree)

main=new_tree('BT_DS3_CombatOverview')
root=copy_node(source.root_node,main);main.set_editor_property('root_node',root)
newcycle=kids(root)[0];newdispatch=kids(newcycle)[2]
label(root,'断剑敌人｜战斗总览','从主干了解战斗周期；双击四类行动入口查看执行流程。')
label(kids(newcycle)[0],'① 准备本轮战斗','初始化比例、速度、角色半径与历史。')
label(kids(newcycle)[1],'② 根据局势选择一次行动',RULES)
label(newdispatch,'③ 执行本轮战斗行动','双击类别查看具体行动。类别是阅读分组，概率由②统一抽取。')
calls=[]
for (suffix,title,ids),sub in zip(GROUPS,subtrees):
    task=unreal.new_object(unreal.BTTask_RunBehavior,outer=main,name='Run'+suffix)
    task.set_editor_property('behavior_asset',sub)
    label(task,title,'包含：'+'、'.join(TITLES[i] for i in ids)+'。双击打开子树。')
    calls.append(plain_child(task))
newdispatch.set_editor_property('children',calls)
label(kids(newcycle)[4],'⑤ 决定攻击后的距离调整','普通攻击50%、特殊20/21为100%；移动行动不追加，按原距离表决定走位。')
label(kids(newcycle)[5],'⑥ 调整距离或结束本轮','侧移、后退、靠近或结束；不重新选择攻击。')
finalize(main)
report=dict(passed=True,main=main.get_path_name(),source=source.get_path_name(),subtrees=[s.get_path_name() for s in subtrees],
            preserved_actions=sorted(original),overview_nodes=len(walk(main)),source_asset_untouched=True)
(OUT/'safe-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('STANDARD_NEW_ASSETS_VERIFIED',report)
