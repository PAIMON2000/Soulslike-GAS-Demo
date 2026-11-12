"""Read saved standard assets, verify action equivalence, export reading archives."""
import json,re
from pathlib import Path
import unreal
P=Path(unreal.Paths.project_dir());OUT=P/'Saved/DS3-Tactical'
AI='/Game/Gameplay/AI/DS3BrokenSword/'
display=json.loads((P/'Tools/ds3_readable_labels.json').read_text(encoding='utf-8'))
groups=display['GROUPS'];titles={int(k):v for k,v in display['TITLES'].items()}
notes={int(k):v for k,v in display['NOTES'].items()}
source=unreal.load_asset(AI+'BT_DS3BrokenSword') if unreal.EditorAssetLibrary.does_asset_exist(AI+'BT_DS3BrokenSword') else None
main=unreal.load_asset(AI+'Tactical/BT_断剑怪_历史_战术战斗总览');assert main and main.root_node
asset_names={'Melee':'近身攻击','Ranged':'远距攻击','Spacing':'调整位置与朝向','Special':'执行特殊招式'}
subtrees=[unreal.load_asset(AI+'StandardReadable/BT_断剑怪_'+asset_names[g[0]]) for g in groups];assert all(subtrees)
bb=main.blackboard_asset
assert all(t.blackboard_asset==bb for t in subtrees)
target=next(k for k in bb.get_editor_property('keys') if str(k.get_editor_property('entry_name'))=='TargetActor')
assert target.get_editor_property('key_type').get_editor_property('BaseClass')==unreal.Actor.static_class()

def kids(n):return [c.child_composite or c.child_task for c in n.children]
reference_path=P/'docs/reproduction/ds3-standard-action-reference.json'
def shape(c):
    n=c.child_composite or c.child_task
    return dict(name=n.get_name(),cls=n.get_class().get_path_name(),
                decorators=[d.get_name() for d in c.decorators],ops=[x.export_text() for x in c.decorator_ops],
                children=[shape(x) for x in n.children] if isinstance(n,unreal.BTCompositeNode) else [])
def config(n):
    # Compare every serialized leaf override represented in the original export.
    # Same class guarantees the same remaining class defaults.
    t=unreal.AssetExportTask();t.object=n;t.filename=str(OUT/'node-check.t3d')
    t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=unreal.ObjectExporterT3D()
    assert unreal.Exporter.run_asset_export_task(t)
    b=Path(t.filename).read_bytes();s=b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    lines=[]
    for line in s.splitlines():
        if line.startswith('   ') and not line.startswith('      ') and '=' in line:
            if not re.match(r'\s*(NodeName|TreeAsset|ParentNode|CachedDescription)=',line):lines.append(line)
    return lines
def leaves(c):
    n=c.child_composite or c.child_task;result=list(c.decorators)
    if isinstance(n,unreal.BTCompositeNode):
        for ch in n.children:result+=leaves(ch)
    else:result.append(n)
    return result
checked=[]
if source:
    original_dispatch=kids(kids(source.root_node)[0])[2]
    original={c.decorators[0].get_editor_property('int_value'):c for c in original_dispatch.children}
    reference={str(aid):dict(shape=shape(c),configuration={n.get_name():config(n) for n in leaves(c)}) for aid,c in original.items()}
    if not reference_path.exists():
        reference_path.write_text(json.dumps(reference,ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        assert reference==json.loads(reference_path.read_text(encoding='utf-8')), 'Historical action reference differs'
else:
    reference=json.loads(reference_path.read_text(encoding='utf-8'))
for (_,title,ids),tree in zip(groups,subtrees):
    assert str(tree.root_node.get_editor_property('node_name'))==title
    actual={c.decorators[0].get_editor_property('int_value'):c for c in tree.root_node.children}
    assert set(actual)==set(ids)
    for aid in ids:
        expected=reference[str(aid)]
        assert shape(actual[aid])==expected['shape'], ('Action shape',aid)
        for n in leaves(actual[aid]):assert config(n)==expected['configuration'][n.get_name()], ('Action configuration',aid,n.get_name())
        checked.append(aid)

(OUT/'action-reference.json').write_text(json.dumps(dict(passed=True,actions=checked),indent=2),encoding='utf-8')
print("TACTICAL_ACTION_REFERENCE_VERIFIED",checked)
