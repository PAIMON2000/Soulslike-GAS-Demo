"""Read-only dependency audit before removing explicitly retired behavior trees."""
import json
from pathlib import Path
import unreal
P=Path(unreal.Paths.project_dir())
old=[
 '/Game/Gameplay/AI/BT_Enemy',
 '/Game/Gameplay/AI/Archive/BeforeDS3BrokenSword/BT_EnemyMeleeCombat',
 '/Game/Gameplay/AI/Archive/BeforeDS3BrokenSword/BT_EnemyMeleeCombat_V2',
 '/Game/Gameplay/AI/DS3BrokenSword/BT_DS3BrokenSword',
 '/Game/Gameplay/AI/DS3BrokenSword/Readable/BT_DS3_Melee',
 '/Game/Gameplay/AI/DS3BrokenSword/ReadableStandard/BT_DS3_Melee',
 '/Game/Gameplay/AI/DS3BrokenSword/Standard/BT_DS3Melee',
 '/Game/Gameplay/AI/DS3BrokenSword/Standard/BT_DS3Ranged',
]
lib=unreal.EditorAssetLibrary
report={'old_trees':[],'tasks':[]}
for path in old:
 if lib.does_asset_exist(path):
  report['old_trees'].append({'path':path,'referencers':[str(x) for x in lib.find_package_referencers_for_asset(path,True)]})
controller=unreal.load_asset('/Game/Gameplay/AI/BP_EnemyAIController')
ed=unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(controller))
report['controller']=[{'pin':str(p.get_pin_name()),'value':p.get_pin_value()} for n in ed.list_all_nodes() for p in n.list_all_pins() if str(p.get_pin_name()) in ['BTAsset','BlackboardAsset']]
for name in ['BTT_DSInit','BTT_DSDecide','BTT_DSLocomotion','BTT_DSAttack','BTT_DSRelativeMove','BTT_DSAfterAttack','BTT_DSComboChoice']:
 bp=unreal.load_asset('/Game/Gameplay/AI/DS3BrokenSword/'+name)
 graph=unreal.BlueprintEditorLibrary.find_event_graph(bp)
 editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
 report['tasks'].append({'name':name,'event_graph_nodes':len(editor.list_all_nodes())})
(P/'Saved/ObsoleteTreeAudit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
