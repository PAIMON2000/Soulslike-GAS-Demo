"""Give newly generated Blueprint comments persistent IDs; no execution changes."""
import unreal
prefix='/Game/Gameplay/AI/DS3BrokenSword/Tactical/'
for name in ['BTT_ReadSituation','BTT_SetCandidates','BTT_ExcludeCoolingAttack','BTT_DrawCandidate','BTT_PrepareRecovery','BTT_SetRecovery']:
    bp=unreal.load_asset(prefix+name)
    ed=unreal.BlueprintGraphEditor.get_graph_editor(unreal.BlueprintEditorLibrary.find_event_graph(bp))
    for n in ed.list_all_nodes():
        if n.get_class().get_name()=='EdGraphNode_Comment':
            n.set_editor_property('NodeGuid',unreal.SystemLibrary.new_guid())
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
print('TACTICAL_COMMENT_IDS_SAVED')
