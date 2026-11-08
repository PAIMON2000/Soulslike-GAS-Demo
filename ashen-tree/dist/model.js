(function(scope){
const groups=[['life','生命周期','死亡、出生和初始化'],['react','强制反应','处决、硬直、击退、破防'],['target','目标管理','发现、锁敌、丢失与重新搜索'],['phase','阶段管理','阶段切换和强化'],['defend','防御反应','举盾、闪避和反击'],['range','距离把控','接近、侧移、保持距离和后撤'],['attack','攻击决策','选招、起手、连击和收招'],['peace','非战斗','警戒、脱战归位、巡逻和待机']];
function skeleton(){let nodes=[{id:'root',name:'AI 主决策',type:'选择器',parent:'',priority:0,category:'all',condition:'true',sourceIds:[],note:'每次 Tick 从最高优先级重新评估；高优先分支可中断低优先动作。'}];
 function add(id,name,type,parent,priority,category,condition='true',extra={}){nodes.push({id,name,type,parent,priority,category,condition,sourceIds:[],note:'人工重构示例，待验证',...extra})}
 function branch(id,name,parent,priority,cat,condition,actions){add(id,name,'顺序器',parent,priority,cat);add(id+'_if','条件：'+condition,'条件',id,100,cat,condition);actions.forEach((a,i)=>add(id+'_a'+i,a,'动作',id,90-i,cat,'true',{instant:false}))}
 branch('death','死亡处理','root',100,'life','hp <= 0',['执行死亡']);
 add('reaction','强制反应','选择器','root',95,'react');branch('execute','被处决','reaction',100,'react','executed == true',['处决反应']);branch('stagger','韧性耗尽','reaction',90,'react','staggered == true',['受击硬直']);branch('break','破防','reaction',80,'react','guardBroken == true',['破防动作']);branch('knock','被击退','reaction',70,'react','knockedBack == true',['击退动作']);
 branch('spawn','出生与初始化','root',90,'life','spawned == false',['出生动作','初始化 AI']);nodes.find(n=>n.name==='初始化 AI').instant=true;
 add('combat','战斗','顺序器','root',80,'all');add('combat_if','存在战斗意图','条件','combat',100,'all','combatIntent == true');add('combat_select','战斗决策','选择器','combat',90,'all');
 branch('acquire','目标获取与重新锁定','combat_select',100,'target','targetVisible == false',['搜索目标','锁定目标']);
 branch('phasechange','阶段切换','combat_select',90,'phase','phasePending == true',['切换阶段','强化']);
 branch('defense','防御威胁','combat_select',80,'defend','threat == true',['举盾防御']);
 add('spacing','距离决策','选择器','combat_select',70,'range');branch('approach','接近目标','spacing',90,'range','distance > 4',['接近目标']);branch('retreat','拉开距离','spacing',80,'range','distance < 1',['后撤']);
 add('attacks','攻击决策','选择器','combat_select',60,'attack');branch('heavy','重攻击连段','attacks',90,'attack','distance <= 4 && heavyReady == true',['重攻击起手','连击衔接','收招恢复']);branch('light','轻攻击','attacks',80,'attack','distance <= 3',['轻攻击','收招恢复']);
 branch('hold','保持战斗距离','combat_select',10,'range','true',['侧移与保持距离']);
 add('noncombat','非战斗','选择器','root',10,'peace');branch('return','脱战返回','noncombat',90,'peace','outsideHome == true',['脱战返回']);branch('alert','警戒','noncombat',80,'peace','suspicious == true',['警戒']);branch('patrol','巡逻','noncombat',70,'peace','patrolEnabled == true',['巡逻']);add('idle','待机','动作','noncombat',0,'peace');return nodes;
}
const rawNames=[['出生','Spawn'],['初始化 AI','InitAI'],['待机','Idle'],['发现目标','Discover'],['锁定目标','LockOn'],['丢失目标','LostTarget'],['搜索目标','Search'],['接近目标','Approach'],['后撤','BackStep'],['侧移','Strafe'],['轻攻击','AttackLight'],['重攻击','AttackHeavy'],['连击衔接','Combo'],['收招恢复','Recover'],['举盾防御','Guard'],['闪避','Dodge'],['反击','Counter'],['受击硬直','Damage'],['被击退','KnockBack'],['破防','GuardBreak'],['处决反应','Executed'],['死亡','Dead'],['阶段切换','PhaseChange'],['强化','Buff'],['脱战返回','ReturnHome'],['巡逻','Patrol'],['警戒','Alert']];
function category(name){return /死亡|出生|初始化/.test(name)?'life':/硬直|击退|破防|处决/.test(name)?'react':/目标|索敌|锁敌/.test(name)?'target':/阶段|强化/.test(name)?'phase':/防御|闪避|反击/.test(name)?'defend':/接近|后撤|侧移|距离|追击|转身/.test(name)?'range':/攻击|连击|恢复|战技|突刺|终止/.test(name)?'attack':'peace'}
function make(){let states=rawNames.map((n,i)=>({id:'s'+i,name:n[0],originalName:n[1]+'_Demo',monster:'示例怪物',category:category(n[0]),trigger:'待补充原始触发条件',priority:0,entry:'待补充',exit:'待补充',mutex:'',transitions:'',phase:'全部阶段',distance:'全部距离',status:'待验证',raw:'示例占位，非 DS3 实测数据。',notes:''}));return {schemaVersion:2,title:'行为树研究档案',monsters:['示例怪物'],states,trees:{'示例怪物':skeleton()},log:[]}}
function migrate(d){if(d.schemaVersion===2)return d;let out={schemaVersion:2,title:d.title,monsters:d.monsters,states:d.states.map(s=>({...s,category:category(s.name)})),trees:{},log:d.log||[],legacyTree:d.states.map(s=>({...s}))};for(let m of out.monsters)out.trees[m]=skeleton();return out}
scope.Model={groups,skeleton,make,migrate,category};if(typeof module!=='undefined')module.exports=scope.Model;
})(typeof window==='undefined'?globalThis:window);
