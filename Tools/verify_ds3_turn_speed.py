import unreal,json
from pathlib import Path
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
d=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/Gameplay/Characters/BP_Dummy.BP_Dummy_C'))[0]
p=unreal.GameplayStatics.get_player_character(w,0);c=d.get_controller()
brain=c.get_component_by_class(unreal.BrainComponent);bb=c.get_component_by_class(unreal.BlackboardComponent)
brain.stop_logic('Turn speed check');d.cancel_attack();c.stop_movement()
d.set_actor_rotation(unreal.Rotator(0,0,0),True);p.set_actor_enable_collision(False)
p.set_actor_location(d.get_actor_location()+unreal.Vector(-300,0,0),False,True)
bb.set_value_as_object('TargetActor',p);bb.set_value_as_int('ForcedAction',13)
start=unreal.GameplayStatics.get_time_seconds(w);brain.restart_logic()
def tick(dt):
    elapsed=unreal.GameplayStatics.get_time_seconds(w)-start
    if elapsed<.35:return
    movement=d.get_component_by_class(unreal.CharacterMovementComponent)
    rate=movement.get_editor_property('rotation_rate').yaw;yaw=abs(d.get_actor_rotation().yaw)
    result=dict(passed=rate==360 and yaw>75,tests=[dict(name='live_turn_rate_and_rotation',passed=rate==360 and yaw>75,rate=rate,yaw=yaw,elapsed=elapsed)])
    unreal.unregister_slate_post_tick_callback(handle)
    (Path(unreal.Paths.project_dir())/'Saved/DS3-Tactical/turn-runtime.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
handle=unreal.register_slate_post_tick_callback(tick)
