"""Graph helpers restricted to NEW assets; existing action subtrees are read only."""
import unreal, ctypes, re
from pathlib import Path
P=Path(unreal.Paths.project_dir()); OUT=P/'Saved/DS3-Tactical'; OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Gameplay/AI/DS3BrokenSword/Tactical/'
lib=unreal.EditorAssetLibrary; tools=unreal.AssetToolsHelpers.get_asset_tools()
bb=unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/StandardReadable/BB_DS3_Standard')
created=[]; notes={}; copies={}
def kids(n): return [c.child_composite or c.child_task for c in n.children]
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
