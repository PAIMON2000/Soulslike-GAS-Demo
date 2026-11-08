"""Give the new standard assets a correctly typed, independent blackboard."""
import json
from pathlib import Path
import unreal
P=Path(unreal.Paths.project_dir());AI='/Game/Gameplay/AI/DS3BrokenSword/'
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
lib=unreal.EditorAssetLibrary
bbpath=AI+'StandardReadable/BB_DS3_Standard'
bb=unreal.load_asset(bbpath) if lib.does_asset_exist(bbpath) else lib.duplicate_asset(AI+'BB_DS3BrokenSword',bbpath)
assert bb
keys=list(bb.get_editor_property('keys'))
target=next(k for k in keys if str(k.get_editor_property('entry_name'))=='TargetActor')
target.get_editor_property('key_type').set_editor_property('BaseClass',unreal.Actor.static_class())
assert lib.save_loaded_asset(bb,False)
changed=[]
for suffix in ['CombatOverview','Melee','Ranged','Spacing','Special']:
 tree=unreal.load_asset(AI+'StandardReadable/BT_DS3_'+suffix);assert tree
 tree.set_editor_property('blackboard_asset',bb)
 graph=unreal.find_object(None,tree.get_path_name()+':Behavior Tree')
 for o in unreal.ObjectIterator():
  if isinstance(o,unreal.Object) and o.get_outer()==graph and o.get_class().get_name()=='BehaviorTreeGraphNode_Root':o.set_editor_property('BlackboardAsset',bb)
 def visit(n):
  if isinstance(n,unreal.BTCompositeNode):
   for c in n.children:visit(c.child_composite or c.child_task)
  elif isinstance(n,unreal.BTTask_MoveTo):
   k=n.get_editor_property('blackboard_key');k.set_editor_property('selected_key_name','TargetActor')
   n.set_editor_property('blackboard_key',k);changed.append(n.get_path_name())
 visit(tree.root_node)
 assert lib.save_loaded_asset(tree,False)
 # Deliberately save twice with native type validation enabled.
 assert lib.save_loaded_asset(tree,False)
controller=unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
ed=unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
pins=[p for n in ed.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name())=='BlackboardAsset'];assert len(pins)==1
assert pins[0].set_pin_value(bb.get_path_name()) or pins[0].get_pin_value()==bb.get_path_name()
unreal.BlueprintEditorLibrary.compile_blueprint(controller);assert not ed.list_nodes_with_errors()
assert lib.save_loaded_asset(controller,False)
(P/'Saved/DS3-Standard/blackboard-fix.json').write_text(json.dumps(dict(blackboard=bb.get_path_name(),target_type='Actor',restored_move_targets=changed,normal_save_twice=True),indent=2),encoding='utf-8')
print('STANDARD_ACTOR_BLACKBOARD_SAVED',len(changed))
