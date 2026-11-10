const fs=require('node:fs');
const assert=require('node:assert/strict');
const source=JSON.parse(fs.readFileSync('data/断剑怪-只读树.json','utf8'));
const round=source.root.children[0], decision=round.children[1].children[0].children[1], recovery=round.children[4].children[0];
let serial=0;
const N=(name,kind,children=[],extra={})=>({id:'n'+(++serial),name,kind,children,...extra});
const refs={};
const labels={'连击A':'连续挥砍A','连击B':'连续挥砍B','固定两段':'固定两次挥砍','3003冷却攻击':'带独立冷却的单次攻击','前冲攻击':'向前冲刺攻击','后退':'后退拉开距离','侧移':'绕着玩家侧移','转身':'转身面向玩家','特殊20005':'替代招式甲（原效果待核实）','特殊20006':'替代招式乙（原效果待核实）','变体专用接近':'接近型变体：只靠近玩家'};
const aliases={'连击A':'连击A','连击B':'连击B','固定两段':'固定两段攻击','3003冷却攻击':'独立冷却攻击','前冲攻击':'远距前冲攻击','后退':'后退拉开距离','侧移':'围绕目标侧移','转身':'转身面向目标','特殊20005':'特殊动作20005','特殊20006':'特殊动作20006','变体专用接近':'110054变体专用接近'};
const actions=new Map();for(const group of round.children[2].children)for(const a of group.children[0].children)actions.set(a.name,a);
function readable(s){return s.replace(/事件请求 = 100/g,'收到要求执行替代招式甲的外部请求（用途待核实）').replace(/响应事件100/g,'外部请求分支（用途待核实）').replace(/本轮选择了三段/g,'本轮连击抽中了三段').replace(/3003距离上次发动/g,'冷却单击距离上次发动').replace(/144040变体|变体 = 144040/g,'使用受伤后改变招式的变体配置').replace(/变体 = 144041/g,'使用专用招式变体配置').replace(/变体 = 110054/g,'使用只接近的变体配置').replace(/职责 ≥ 1/g,'队伍职责是旁观或围攻').replace(/职责 ≤ 2/g,'队伍职责属于这两种配合角色').replace(/目标右侧/g,'玩家在怪物右侧').replace(/目标左侧/g,'玩家在怪物左侧').replace(/距离/g,'间距').replace(/普通攻击/g,'本轮常规攻击').replace(/特殊动作/g,'替代招式');}
function C(text,path){return N(readable(text),'条件',[],{source:path,detail:'成立返回成功，不成立返回失败。间距沿用原脚本单位，换算到厘米与测量基准仍需核对。'});}
function ref(key,name){assert(refs[key]);return N(name||refs[key].name,'子树',[],{ref:key,detail:'展开查看同一份定义。修改定义会作用于所有调用位置。'});}
function normalize(n){
 let name=readable(n.name).replace(/^\d+[①②③④⑥]?\s*/,'');
 const attack=name.match(/执行攻击(\d+)/);
 if(attack) name='播放本段攻击并等待结束';
 let result=N(name,{'按顺序完成':'顺序','按优先级尝试':'选择','展开内部步骤':'顺序'}[n.kind]||n.kind,n.children.map(normalize),{source:n.path,parameters:n.parameters||[],detail:n.explanation||''});
 if(attack){result.parameters=['原动作编号 '+attack[1],...(n.parameters||[])];result.detail='当前使用替代动画。动画或技能任务报告完成才进入下一步；失败返回本序列。具体受击和死亡中断需核对UE任务。';}
 if(/一次决定两段/.test(n.name)){result.name='本轮连击只抽一次段数';result.detail='现有行为说明记载：25%两段，75%三段。不会每个Tick重新抽签。仍需对照运行资产确认。';}
 if(/配置接近/.test(n.name)){result.name='设置本招接近距离与转向速度';result.detail='这里只设置执行参数，不选择下一招。间距参数见下方。';}
 if(/寻路接近/.test(n.name)){result.name='沿可走路径靠近玩家，直到达到本招间距';result.detail='运行中持续执行移动；到达目标范围成功，寻路失败返回失败。距离测量基准与边界包含关系待核对UE。';}
 const guards=(n.conditions||[]).filter(c=>!c.name.startsWith('本轮选择：'));
 const timeout=guards.filter(c=>/超时/.test(c.name));
 if(timeout.length)result=N('限制接近耗时（时限参数待核对）','超时',[result],{detail:'进入时开始计时；超时中止移动并返回失败。原资料只给出ApproachLife参数名，不能把它当成进入前的布尔条件。',parameters:['原参数 ApproachLife']});
 const ordinary=guards.filter(c=>!/超时/.test(c.name));
 if(ordinary.length)result=N('满足以下条件才执行','顺序',[...ordinary.map(c=>C(c.name,c.path)),result]);
 return result;
}
// Shared recovery definitions preserve original condition ordering and explicitly execute each movement.
function recoveryTree(n){
 const copy=structuredClone(n);
 copy.children=copy.children.map(recoveryTree);
 const mode=(copy.parameters||[]).find(p=>p.startsWith('移动模式'));
 if(mode&&!copy.children.length){const number=Number(mode.split('：').at(-1));const task=structuredClone(recovery.children[3].children[number-1]);task.conditions=[];copy.kind='按顺序完成';copy.children=[task];copy.explanation='满足本分支条件后直接执行移动，成功或失败结束本次调整。';}
 return copy;
}
refs.spacing=normalize(recoveryTree(recovery.children[2].children[0].children[0]));refs.spacing.name='攻击结束后，根据新间距决定走位';
refs.recover=N('常规攻击结束后：可能走位，也可能直接结束','顺序',[
 N('重新测量与玩家的间距','动作'),
 N('生成一次恢复判断所需的随机值','动作',[],{detail:'原资料区分进入调整与走位随机值，但生成方式、独立性未完整导出。需核对UE任务后才能验证联合概率。'}),
 N('是否进入走位判断','选择',[N('抽中恢复调整时','顺序',[C('本次随机值 ≤ 50'),ref('spacing')]),N('否则直接结束本轮','成功')])
]);
refs.specialRecover=N('替代招式结束后：进入走位判断','顺序',[N('重新测量间距并生成一次走位随机值','动作'),ref('spacing')]);
for(const [key,originalName] of Object.entries(aliases)){
 const action=normalize({...actions.get(originalName),conditions:[]});action.name=labels[key];
 let hit=0;function nameAttacks(n){if(n.name==='播放本段攻击并等待结束'){hit++;n.name='第'+hit+'击：播放攻击并等待结束';}n.children.forEach(nameAttacks);}nameAttacks(action);
 action.children.push(N('恢复步行并面向玩家','动作',[],{parameters:['转向速度 360°/秒','默认接近间距 2.5（脚本单位）']}));
 if(['连击A','连击B','固定两段','3003冷却攻击','前冲攻击'].includes(key)) action.children.push(ref('recover'));
 if(key.startsWith('特殊'))action.children.push(ref('specialRecover'));
 if(['后退','侧移','转身','变体专用接近'].includes(key))action.children.push(N('本轮结束，下一轮重新检查','成功'));
 refs[key]=action;
}
const rules=[];
function collect(n,parents=[]){const guards=[...parents,...(n.conditions||[])];const weights=(n.parameters||[]).map(p=>p.match(/^(.+)：权重 (\d+)$/)).filter(Boolean);if(weights.length)rules.push({guards,weights,source:n.path,original:n.name});else n.children.forEach(c=>collect(c,guards));}
collect(decision);
const ruleNames=['外部请求要求使用替代招式（用途待核实）','只接近的变体','旁观角色：后退或侧移','围攻角色且玩家较远','围攻角色的其他间距','玩家贴近右侧','玩家贴近左侧','玩家在右后方','玩家在左后方','专用招式变体：玩家较远','专用招式变体：其他间距','受伤变体：玩家较远','受伤变体：其他间距','受伤变体配置：远距离','受伤变体配置：较远距离','普通交战：较远距离','受伤变体配置：中距离','普通交战：中距离','普通交战：近距离'];
assert.equal(rules.length,ruleNames.length);
const branches=rules.map((r,i)=>{
 const candidates=r.weights.map(([,key,weight])=>N(labels[key],'候选',[ref(key)],{weight:Number(weight),refAction:key,conditions:key==='3003冷却攻击'?['距上次发动 > 20秒，才参与抽签']:[],detail:'权重 '+weight+'。在当前可用候选中按相对权重抽取，抽中后保持执行。'}));
 const select=N('从下面行动中抽取一个并执行','加权选择',candidates,{detail:'先排除未满足准入条件的候选，再归一化权重。执行期间保持本次选择，失败后不换招重抽。'});
 const finish=N('执行完本分支便结束本轮','结果转成功',[select],{detail:'内部RUNNING继续等待；内部成功或失败均让本分支结束。这样动作失败不会跌入下面的另一条局势规则。此为副本明确采用的控制结构，尚未验证UE等价性。'});
 return N(ruleNames[i],'顺序',[...r.guards.map(g=>C(g.name,g.path)),finish],{source:r.source,detail:i===18?'前面的分支都未命中时进入；普通正面情形对应间距 < 1.5。':'从上到下检查。条件失败才尝试下一分支，条件全部成立则执行该分支。',parameters:['原规则 '+r.original]});
});
refs.rules=N('从上到下检查：第一条满足条件的分支执行一轮','选择',branches);
const root=N('断剑怪：持续观察玩家并行动','每轮循环',[
 N('玩家目标是否仍然有效？','如果 / 否则',[
 C('目标对象有效'),
 N('是：执行一轮战斗','持续检查目标',[N('依次完成','顺序',[
 N('首次准备移动速度、半径和距离换算','动作',[],{detail:'初始化后跳过重复设置。'}),
 N('读取玩家间距、方向、自身血量和冷却','动作',[],{detail:'只测量数据。具体行动在下面各分支中确定。'}),ref('rules')])],{detail:'目标失效时中止本轮。具体任务是否正确取消移动、动画和技能，需UE验证。'}),
 N('否：等待0.2秒，再从顶部检查','动作')
 ])
],{detail:'RUNNING继续当前步骤；本轮结束后，下次调度从顶部重新开始。普通配置按方向和间距进入攻击或走位，攻击前可先接近，攻击后可能再调整距离。'});
const data={title:'断剑怪 · 策划阅读树',status:'本地设计副本，尚未接入UE',root,subtrees:refs,notes:[
 '这是对现有档案的策划阅读重构。原始档案保留。',
 '间距使用原脚本单位，换算到UE厘米与测量基准待核对。不能把5.5直接理解为5.5米。',
 '普通阅读情形指无外部请求、基础配置、非旁观或围攻。完整树仍显示全部19条规则。',
 '替代招式甲/乙分别对应原20005/20006；当前为近战替代，原效果未知。',
 '外部请求的发出方、触发场景与清除时机未知。这是待核实逻辑，不能当成已经讲清楚的战斗设计。',
 '结果转成功与超时节点明确副本控制语义，UE运行一致性尚待验证。'
]};
fs.writeFileSync('data/断剑怪-策划阅读树.json',JSON.stringify(data,null,2));
let count=0;function validate(n,stack=[]){count++;if(n.ref){assert(refs[n.ref]);assert(!stack.includes(n.ref),'cyclic subtree');}n.children.forEach(c=>validate(c,stack));}
validate(root);Object.values(refs).forEach(n=>validate(n));
assert.equal(rules.length,19);assert.equal(Object.keys(aliases).length,11);
const oldWeights=rules.map(r=>r.weights.map(([,key,w])=>[key,Number(w)]));
const newWeights=branches.map(b=>b.children.at(-1).children[0].children.map(c=>[c.refAction,c.weight]));assert.deepEqual(newWeights,oldWeights);
console.log('Validated '+count+' stored nodes, '+Object.keys(refs).length+' shared subtrees, 19 rule weight tables and 11 actions.');
