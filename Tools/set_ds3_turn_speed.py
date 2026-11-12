"""Double only facing speed on active trees and the reusable task default."""
import unreal,json,shutil
from pathlib import Path
P=Path(unreal.Paths.project_dir()); assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
AI='/Game/Gameplay/AI/DS3BrokenSword/'
main=unreal.load_asset(AI+'Tactical/BT_断剑怪_历史_战术战斗总览'); seen=set(); changes=[]
backup=P/'LocalBackups/TurnSpeed-2026-11-09'; backup.mkdir(parents=True,exist_ok=True)
def back(asset):
    rel=asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset'
    dst=backup/rel; dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():shutil.copy2(P/'Content'/rel,dst)
def visit(tree):
    if tree.get_path_name() in seen:return
    seen.add(tree.get_path_name()); nodes=[]
    def walk(n):
        if isinstance(n,unreal.BTCompositeNode):
            for c in n.children:walk(c.child_composite or c.child_task)
        elif isinstance(n,unreal.BTTask_RunBehavior):visit(n.behavior_asset)
        elif n.get_class().get_name()=='BTT_DSLocomotion_C':nodes.append(n)
    walk(tree.root_node)
    if nodes:
        back(tree)
        for n in nodes:
            old=n.get_editor_property('TurnRate');assert old==180,(n,old)
            n.set_editor_property('TurnRate',360.0);changes.append(dict(node=n.get_path_name(),old=old,new=360))
        assert unreal.EditorAssetLibrary.save_loaded_asset(tree,False)
        assert all(n.get_editor_property('TurnRate')==360 for n in nodes)
visit(main)
bp=unreal.load_asset(AI+'BTT_DSLocomotion');back(bp)
cdo=unreal.get_default_object(bp.generated_class());assert cdo.get_editor_property('TurnRate')==180
cdo.set_editor_property('TurnRate',360.0);assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
assert len(changes)==12,len(changes)
(P/'Saved/DS3-Tactical/turn-speed.json').write_text(json.dumps(dict(passed=True,default=360,changes=changes),ensure_ascii=False,indent=2),encoding='utf-8')
print('TURN_SPEED_DOUBLED',len(changes),'instances',180,360)
