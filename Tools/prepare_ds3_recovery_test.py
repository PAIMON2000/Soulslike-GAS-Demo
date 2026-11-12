"""A one-shot test wrapper prevents zero-wait recovery from restarting."""
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
import ds3_tactical_graph as g
g.DEST='/Game/Gameplay/AI/DS3BrokenSword/Validation/'
t=g.new_tree('BT_断剑怪_验证_单轮恢复')
r=unreal.new_object(unreal.BTComposite_Sequence,outer=t,name='TestOnce')
run=unreal.new_object(unreal.BTTask_RunBehavior,outer=t,name='Recovery');run.set_editor_property('behavior_asset',unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/Tactical/BT_断剑怪_攻击后恢复'))
wait=unreal.new_object(unreal.BTTask_Wait,outer=t,name='HoldResult'); v=unreal.ValueOrBBKey_Float();v.import_text('(DefaultValue=60,Key=None)');wait.set_editor_property('wait_time',v)
r.set_editor_property('children',[g.plain_child(run),g.plain_child(wait)]);t.set_editor_property('root_node',r);g.finalize(t)
print('RECOVERY_ONCE_TEST_READY')
